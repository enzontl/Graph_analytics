"""Analyses complémentaires : autre algorithme de communautés, graphe des
thèmes, et prédiction du thème d'un set par ses voisins."""

import time
from collections import Counter, defaultdict

import networkx as nx
import numpy as np
import pandas as pd
from sklearn.metrics import adjusted_rand_score, normalized_mutual_info_score


# ---------------------------------------------------------------------------
# Louvain à plusieurs résolutions et label propagation
# ---------------------------------------------------------------------------
def partition_scores(G: nx.Graph, comms) -> dict:
    """Mesures d'une partition, comparables d'un algorithme à l'autre.

    La modularité est toujours la modularité standard (résolution 1), même
    pour Louvain lancé à une autre résolution : sinon les valeurs ne se
    comparent pas. NMI et ARI sont aussi calculées sans les sets isolés,
    qui forment chacun leur propre communauté (comme dans analysis.communities).
    """
    comms = sorted((set(c) for c in comms), key=len, reverse=True)
    label = {n: k for k, comm in enumerate(comms) for n in comm}
    nodes = list(G.nodes)
    theme = np.array([G.nodes[n]["root_theme"] for n in nodes])
    comm = np.array([label[n] for n in nodes])
    linked = np.array([G.degree(n) > 0 for n in nodes])
    return {
        "n_communities": len(comms),
        "n_communities_size_ge_10": sum(len(c) >= 10 for c in comms),
        "largest_community_share": len(comms[0]) / len(nodes) if comms else float("nan"),
        "modularity": nx.community.modularity(G, comms, weight="weight"),
        "nmi_vs_root_theme": normalized_mutual_info_score(theme, comm),
        "nmi_vs_root_theme_non_isolated": normalized_mutual_info_score(theme[linked], comm[linked]),
        "ari_vs_root_theme_non_isolated": adjusted_rand_score(theme[linked], comm[linked]),
    }


def compare_communities(
    G: nx.Graph,
    resolutions=(0.5, 1.0, 2.0, 4.0),
    seeds=(42,),
    log=print,
) -> pd.DataFrame:
    """Une ligne par partition : thèmes officiels (repère), Louvain à chaque
    résolution, label propagation pondérée (asynchrone, aléatoire) et label
    propagation semi-synchrone (déterministe, non pondérée)."""
    rows = []

    groups: dict[str, set] = defaultdict(set)
    for n, t in G.nodes(data="root_theme"):
        groups[t].add(n)
    rows.append({"algorithm": "thèmes officiels", **partition_scores(G, groups.values())})

    for seed in seeds:
        for res in resolutions:
            t0 = time.time()
            comms = nx.community.louvain_communities(G, weight="weight", resolution=res, seed=seed)
            rows.append(
                {"algorithm": "louvain", "resolution": res, "seed": seed,
                 **partition_scores(G, comms), "seconds": time.time() - t0}
            )
            log(f"  Louvain γ={res} graine {seed} : {rows[-1]['n_communities']} communautés, "
                f"NMI {rows[-1]['nmi_vs_root_theme_non_isolated']:.3f} ({rows[-1]['seconds']:.0f} s)")

        t0 = time.time()
        comms = nx.community.asyn_lpa_communities(G, weight="weight", seed=seed)
        rows.append(
            {"algorithm": "label propagation (asynchrone, pondérée)", "seed": seed,
             **partition_scores(G, comms), "seconds": time.time() - t0}
        )
        log(f"  Label propagation graine {seed} : {rows[-1]['n_communities']} communautés, "
            f"NMI {rows[-1]['nmi_vs_root_theme_non_isolated']:.3f} ({rows[-1]['seconds']:.0f} s)")

    t0 = time.time()
    comms = nx.community.label_propagation_communities(G)
    rows.append(
        {"algorithm": "label propagation (semi-synchrone, non pondérée)",
         **partition_scores(G, comms), "seconds": time.time() - t0}
    )
    df = pd.DataFrame(rows)
    first = ["algorithm", "resolution", "seed"]
    return df[first + [c for c in df.columns if c not in first]]


# ---------------------------------------------------------------------------
# Graphe des thèmes
# ---------------------------------------------------------------------------
def theme_graph(G: nx.Graph) -> nx.Graph:
    """Un nœud par thème racine ; une arête entre deux thèmes si au moins un
    set de l'un est relié à un set de l'autre.

    Nœud : n_sets, volume (somme des degrés pondérés de ses sets),
    internal_weight, internal_share (même définition que theme_cohesion),
    median_year.
    Arête : weight = somme des poids des arêtes entre les deux thèmes,
    n_links = nombre de ces arêtes, lift = weight / poids attendu si les
    arêtes ignoraient les thèmes (volume_a × volume_b / volume total, comme
    dans la modularité). lift > 1 : thèmes plus liés que le hasard.
    """
    theme_of = dict(G.nodes(data="root_theme"))
    strength = dict(G.degree(weight="weight"))
    total = sum(strength.values())  # = 2 × poids total des arêtes

    members: dict[str, list] = defaultdict(list)
    for n, t in theme_of.items():
        members[t].append(n)

    T = nx.Graph()
    for t, nodes in members.items():
        T.add_node(
            t,
            label=t,
            n_sets=len(nodes),
            volume=float(sum(strength[n] for n in nodes)),
            internal_weight=0.0,
            median_year=float(np.median([G.nodes[n]["year"] for n in nodes])),
        )

    weight: dict[tuple, float] = defaultdict(float)
    n_links: Counter = Counter()
    for u, v, d in G.edges(data=True):
        a, b = theme_of[u], theme_of[v]
        if a == b:
            T.nodes[a]["internal_weight"] += d["weight"]
        else:
            key = (a, b) if a < b else (b, a)
            weight[key] += d["weight"]
            n_links[key] += 1

    for t, data in T.nodes(data=True):
        data["internal_share"] = 2 * data["internal_weight"] / data["volume"] if data["volume"] else 0.0
    for (a, b), w in weight.items():
        expected = T.nodes[a]["volume"] * T.nodes[b]["volume"] / total
        T.add_edge(a, b, weight=w, n_links=n_links[(a, b)], lift=w / expected)
    return T


def theme_edges_table(T: nx.Graph) -> pd.DataFrame:
    rows = [{"theme_a": a, "theme_b": b, **d} for a, b, d in T.edges(data=True)]
    if not rows:
        return pd.DataFrame(columns=["theme_a", "theme_b", "weight", "n_links", "lift"])
    return pd.DataFrame(rows).sort_values("weight", ascending=False).reset_index(drop=True)


def theme_backbone(T: nx.Graph, min_sets: int = 30, per_node: int = 3) -> nx.Graph:
    """Sous-graphe lisible pour la figure : thèmes d'au moins `min_sets` sets,
    et pour chacun ses `per_node` liens les plus forts (union)."""
    keep = [t for t, n in T.nodes(data="n_sets") if n >= min_sets]
    H = T.subgraph(keep)
    B = nx.Graph()
    B.add_nodes_from(H.nodes(data=True))
    for t in H.nodes:
        strongest = sorted(H[t].items(), key=lambda kv: (-kv[1]["weight"], kv[0]))[:per_node]
        for other, d in strongest:
            B.add_edge(t, other, **d)
    return B


# ---------------------------------------------------------------------------
# Deviner le thème d'un set par vote de ses voisins
# ---------------------------------------------------------------------------
def predict_theme(G: nx.Graph, weighted: bool = True) -> pd.DataFrame:
    """Pour chaque set, thème racine prédit par vote de ses voisins.

    Chaque voisin vote pour son thème, avec le poids de l'arête (ou 1 si
    `weighted=False`). Le thème du set lui-même n'est jamais utilisé : c'est
    une évaluation « leave-one-out ». Égalité : premier thème par ordre
    alphabétique. Un set isolé n'a pas de prédiction.
    """
    rows = []
    for n, data in G.nodes(data=True):
        votes: dict[str, float] = defaultdict(float)
        for m, d in G[n].items():
            votes[G.nodes[m]["root_theme"]] += d["weight"] if weighted else 1.0
        pred = max(sorted(votes), key=votes.get) if votes else None
        rows.append(
            {
                "set_num": n,
                "root_theme": data["root_theme"],
                "degree": G.degree(n),
                "predicted": pred,
                "vote_share": votes[pred] / sum(votes.values()) if votes else float("nan"),
                "correct": pred == data["root_theme"],
            }
        )
    return pd.DataFrame(rows)


def prediction_by_theme(pred: pd.DataFrame, pred_unweighted: pd.DataFrame | None = None) -> pd.DataFrame:
    """Taux de réussite par thème racine.

    accuracy : part des sets non isolés dont le thème est bien deviné.
    accuracy_all : idem en comptant les sets isolés comme des échecs.
    random_baseline : réussite attendue en tirant le thème au hasard selon
    les fréquences des thèmes (= part du thème parmi les sets non isolés).
    """
    linked = pred[pred["degree"] > 0]
    share = linked["root_theme"].value_counts(normalize=True)
    rows = []
    for theme, group in pred.groupby("root_theme"):
        g = group[group["degree"] > 0]
        wrong = g.loc[~g["correct"], "predicted"].value_counts()
        rows.append(
            {
                "root_theme": theme,
                "n_sets": len(group),
                "n_non_isolated": len(g),
                "n_correct": int(g["correct"].sum()),
                "accuracy": g["correct"].mean() if len(g) else float("nan"),
                "accuracy_all": group["correct"].mean(),
                "random_baseline": share.get(theme, 0.0),
                "most_confused_with": wrong.index[0] if len(wrong) else "",
                "n_confused": int(wrong.iloc[0]) if len(wrong) else 0,
            }
        )
    out = pd.DataFrame(rows)
    if pred_unweighted is not None:
        unw = pred_unweighted[pred_unweighted["degree"] > 0].groupby("root_theme")["correct"].mean()
        out["accuracy_unweighted"] = out["root_theme"].map(unw)
    return out.sort_values("n_sets", ascending=False).reset_index(drop=True)


def prediction_summary(pred: pd.DataFrame, by_theme: pd.DataFrame, min_sets: int = 30) -> dict:
    linked = pred[pred["degree"] > 0]
    share = linked["root_theme"].value_counts(normalize=True)
    big = by_theme[by_theme["n_sets"] >= min_sets]
    return {
        "n_sets": len(pred),
        "n_non_isolated": len(linked),
        "accuracy": float(linked["correct"].mean()),
        "accuracy_all": float(pred["correct"].mean()),
        f"macro_accuracy_themes_ge_{min_sets}": float(big["accuracy"].mean()),
        # Toujours prédire le thème le plus fréquent.
        "majority_baseline": float(share.iloc[0]),
        "majority_theme": str(share.index[0]),
        # Tirer au hasard selon les fréquences : somme des p².
        "random_baseline": float((share**2).sum()),
    }


def theme_graph_figure(T: nx.Graph, path, min_sets: int = 30, per_node: int = 3, seed: int = 42) -> None:
    """Figure du graphe des thèmes (squelette : voir theme_backbone).

    Taille d'un nœud = nombre de sets ; couleur = internal_share (part des
    liens qui restent dans le thème) ; épaisseur d'une arête = poids des liens.
    """
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    B = theme_backbone(T, min_sets=min_sets, per_node=per_node)
    # Un thème sans aucun lien serait rejeté au bord de la figure : on le nomme dans le titre.
    isolated = sorted(nx.isolates(B))
    B.remove_nodes_from(isolated)
    fig, ax = plt.subplots(figsize=(15, 11))
    if B.number_of_nodes() == 0:
        ax.text(0.5, 0.5, "aucun thème assez grand", ha="center")
        fig.savefig(path, dpi=200)
        plt.close(fig)
        return

    # Placement : attraction selon log(1 + lift), pour que les thèmes très
    # liés entre eux se rapprochent sans que les gros thèmes écrasent tout.
    for _, _, d in B.edges(data=True):
        d["layout_weight"] = float(np.log1p(d["lift"]))
    pos = nx.spring_layout(B, weight="layout_weight", k=2.6 / np.sqrt(B.number_of_nodes()),
                           iterations=300, seed=seed)

    sizes = np.array([B.nodes[t]["n_sets"] for t in B.nodes])
    colors = np.array([B.nodes[t]["internal_share"] for t in B.nodes])
    weights = np.array([d["weight"] for _, _, d in B.edges(data=True)])
    widths = 0.4 + 5 * np.sqrt(weights / weights.max()) if len(weights) else []

    nx.draw_networkx_edges(B, pos, ax=ax, width=widths, edge_color="#999999", alpha=0.6)
    nodes = nx.draw_networkx_nodes(
        B, pos, ax=ax, node_size=40 + 1.2 * sizes, node_color=colors,
        cmap="viridis", vmin=0, vmax=1, edgecolors="white", linewidths=0.8,
    )
    # Étiquette au-dessus du nœud, sur fond blanc : lisible même quand deux noms se touchent.
    label_pos = {t: (x, y + 0.025) for t, (x, y) in pos.items()}
    nx.draw_networkx_labels(B, label_pos, ax=ax, font_size=7,
                            bbox=dict(facecolor="white", edgecolor="none", alpha=0.75, pad=0.6))
    fig.colorbar(nodes, ax=ax, shrink=0.6, label="part des liens internes au thème (internal_share)")
    ax.set_title(
        f"Graphe des thèmes (thèmes d'au moins {min_sets} sets, {per_node} liens les plus forts par thème)\n"
        "taille = nombre de sets, épaisseur = somme des poids Jaccard entre les deux thèmes"
        + (f"\nsans aucun lien vers un autre thème : {', '.join(isolated)}" if isolated else "")
    )
    ax.axis("off")
    fig.tight_layout()
    fig.savefig(path, dpi=200)
    plt.close(fig)
