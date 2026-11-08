"""Mesures demandées par le sujet : taille, connectivité, distances,
centralités, communautés, et analyse temporelle."""

from dataclasses import replace

import networkx as nx
import numpy as np
import pandas as pd
from sklearn.metrics import adjusted_rand_score, normalized_mutual_info_score

from .build import build_set_graph, prepare
from .config import Params


# ---------------------------------------------------------------------------
# Description du graphe
# ---------------------------------------------------------------------------
def basic_stats(G: nx.Graph) -> dict:
    weights = np.array([d["weight"] for _, _, d in G.edges(data=True)])
    degrees = np.array([d for _, d in G.degree()])
    return {
        "n_nodes": G.number_of_nodes(),
        "n_edges": G.number_of_edges(),
        "directed": G.is_directed(),
        "multigraph": G.is_multigraph(),
        "weighted": True,
        "density": nx.density(G),
        "mean_degree": float(degrees.mean()) if len(degrees) else 0.0,
        "max_degree": int(degrees.max()) if len(degrees) else 0,
        "weight_quantiles": (
            {q: float(np.quantile(weights, q)) for q in (0.0, 0.25, 0.5, 0.75, 0.9, 0.99, 1.0)}
            if len(weights)
            else {}
        ),
        "average_clustering_weighted": average_clustering_weighted(G),
    }


def average_clustering_weighted(G: nx.Graph, chunk: int = 1000) -> float:
    """Même valeur que nx.average_clustering(G, weight="weight") (Onnela et al.),
    calculée avec des produits de matrices creuses : NetworkX met ~1 min sur le
    graphe réel. c_i = sum_jk (w_ij w_jk w_ki)^(1/3) / (k_i (k_i - 1)), poids
    divisés par le poids maximal ; moyenne sur tous les nœuds (0 si degré < 2).
    """
    W = nx.to_scipy_sparse_array(G, weight="weight", format="csr")
    if W.nnz == 0:
        return 0.0
    W = (W / W.max()).power(1 / 3).tocsr()
    deg = np.diff(W.indptr)
    tri = np.concatenate(
        [(W[i : i + chunk] @ W).multiply(W[i : i + chunk]).sum(axis=1) for i in range(0, W.shape[0], chunk)]
    )
    c = np.divide(tri, deg * (deg - 1.0), out=np.zeros(len(deg)), where=deg > 1)
    return float(c.mean())


def largest_component(G: nx.Graph) -> nx.Graph:
    nodes = max(nx.connected_components(G), key=len)
    return G.subgraph(nodes).copy()


def connectivity(G: nx.Graph, top: int = 20) -> tuple[dict, pd.DataFrame]:
    """Composantes connexes, avec la composition en thèmes de chacune."""
    components = sorted(nx.connected_components(G), key=len, reverse=True)
    rows = []
    for k, comp in enumerate(components[:top]):
        themes = pd.Series([G.nodes[n]["root_theme"] for n in comp]).value_counts()
        rows.append(
            {
                "component": k,
                "size": len(comp),
                "share_of_nodes": len(comp) / G.number_of_nodes(),
                "main_themes": "; ".join(f"{t} ({c})" for t, c in themes.head(3).items()),
            }
        )
    summary = {
        "is_connected": nx.is_connected(G) if G.number_of_nodes() else False,
        "n_components": len(components),
        "n_isolated_nodes": nx.number_of_isolates(G),
        "largest_component_size": len(components[0]) if components else 0,
        "largest_component_share": len(components[0]) / G.number_of_nodes() if components else 0,
    }
    return summary, pd.DataFrame(rows)


def distances(G: nx.Graph, sample: int = 200, seed: int = 42) -> dict:
    """Diamètre et rayon de la plus grande composante connexe.

    Convention : distance = nombre d'arêtes (non pondérée). Le calcul est exact
    (bornes de Takes & Kosters via `usebounds=True` de NetworkX). La distance
    moyenne est estimée à partir de `sample` sources tirées au hasard.
    """
    H = largest_component(G)
    rng = np.random.default_rng(seed)
    nodes = list(H.nodes)
    sources = rng.choice(len(nodes), size=min(sample, len(nodes)), replace=False)
    lengths = []
    for s in sources:
        lengths.extend(
            d for d in nx.single_source_shortest_path_length(H, nodes[s]).values() if d > 0
        )
    center = nx.center(H, usebounds=True)
    periphery = nx.periphery(H, usebounds=True)
    return {
        "component_size": H.number_of_nodes(),
        "convention": "plus grande composante connexe, distance = nombre d'arêtes",
        "diameter": nx.diameter(H, usebounds=True),
        "radius": nx.radius(H, usebounds=True),
        "n_center_nodes": len(center),
        "center_examples": [_label(H, n) for n in center[:5]],
        "n_periphery_nodes": len(periphery),
        "periphery_examples": [_label(H, n) for n in periphery[:5]],
        "mean_distance_estimate": float(np.mean(lengths)) if lengths else 0.0,
    }


# ---------------------------------------------------------------------------
# Centralités
# ---------------------------------------------------------------------------
def centralities(G: nx.Graph, params: Params) -> pd.DataFrame:
    """Une ligne par set avec plusieurs centralités.

    - degree : nombre de sets avec lesquels il partage assez de pièces ;
    - strength : somme des poids (degré pondéré) ;
    - betweenness : part des plus courts chemins (distance = 1/poids) qui
      passent par le set -> sets « ponts » entre univers ;
    - eigenvector : être relié à des sets eux-mêmes centraux (calculé sur la
      plus grande composante, 0 ailleurs).
    """
    k = params.betweenness_k
    if k is not None and k >= G.number_of_nodes():
        k = None
    betweenness = nx.betweenness_centrality(
        G, k=k, weight="distance", normalized=True, seed=params.seed
    )
    H = largest_component(G)
    try:
        eigen = nx.eigenvector_centrality(H, weight="weight", max_iter=1000)
    except nx.PowerIterationFailedConvergence:
        eigen = nx.eigenvector_centrality_numpy(H, weight="weight")

    rows = []
    for n, data in G.nodes(data=True):
        rows.append(
            {
                "set_num": n,
                "name": data["name"],
                "year": data["year"],
                "theme": data["theme"],
                "root_theme": data["root_theme"],
                "degree": G.degree(n),
                "strength": G.degree(n, weight="weight"),
                "betweenness": betweenness[n],
                "eigenvector": eigen.get(n, 0.0),
            }
        )
    return pd.DataFrame(rows)


def part_universality(pairs: pd.DataFrame, sets: pd.DataFrame, parts: pd.DataFrame) -> pd.DataFrame:
    """Pour chaque pièce : nombre de sets et nombre de thèmes racines où elle apparaît.

    C'est le degré de la pièce dans le graphe biparti (et sa diversité de thèmes).
    """
    df = pairs.merge(sets[["set_num", "root_theme"]], on="set_num")
    out = df.groupby("part").agg(
        n_sets=("set_num", "nunique"), n_root_themes=("root_theme", "nunique")
    )
    out["share_of_sets"] = out["n_sets"] / sets["set_num"].nunique()
    # Le nom n'est disponible que si une pièce = une forme (sans couleur).
    names = parts.assign(part_num=parts["part_num"].astype(str)).set_index("part_num")["name"]
    out["name"] = out.index.map(lambda p: names.get(p.split("|")[0], ""))
    return out.sort_values("n_sets", ascending=False).reset_index()


def signature_parts(
    pairs: pd.DataFrame, sets: pd.DataFrame, universal: pd.DataFrame, min_sets: int = 10, top: int = 5
) -> pd.DataFrame:
    """Pièces « signature » de chaque thème racine : presque toujours dans ce thème
    (specificity = part de ses sets qui sont du thème) et dans beaucoup de ses sets
    (coverage). On garde les pièces présentes dans au moins `min_sets` sets du thème.
    """
    df = pairs.merge(sets[["set_num", "root_theme"]], on="set_num").drop_duplicates(["set_num", "part"])
    counts = df.groupby(["root_theme", "part"]).size().rename("n_sets_in_theme").reset_index()
    counts = counts[counts["n_sets_in_theme"] >= min_sets]
    info = universal.set_index("part")
    counts["specificity"] = counts["n_sets_in_theme"] / counts["part"].map(info["n_sets"])
    counts["coverage"] = counts["n_sets_in_theme"] / counts["root_theme"].map(sets["root_theme"].value_counts())
    counts["name"] = counts["part"].map(info["name"])
    counts = counts.sort_values(["root_theme", "specificity", "coverage"], ascending=[True, False, False])
    return counts.groupby("root_theme").head(top).reset_index(drop=True)


# ---------------------------------------------------------------------------
# Communautés
# ---------------------------------------------------------------------------
def communities(G: nx.Graph, params: Params) -> tuple[dict, pd.DataFrame, pd.DataFrame]:
    """Louvain pondéré, puis comparaison avec les thèmes officiels.

    Renvoie (résumé, affectation set -> communauté, description des communautés).
    """
    comms = nx.community.louvain_communities(
        G, weight="weight", resolution=params.resolution, seed=params.seed
    )
    comms = sorted(comms, key=len, reverse=True)
    label = {n: k for k, comm in enumerate(comms) for n in comm}

    assignment = pd.DataFrame(
        {
            "set_num": list(G.nodes),
            "community": [label[n] for n in G.nodes],
            "theme": [G.nodes[n]["theme"] for n in G.nodes],
            "root_theme": [G.nodes[n]["root_theme"] for n in G.nodes],
            "year": [G.nodes[n]["year"] for n in G.nodes],
        }
    )

    # Partition « officielle » : un groupe par thème racine.
    theme_groups = assignment.groupby("root_theme")["set_num"].apply(set).tolist()
    # Deux repères : par décennie (l'époque structure-t-elle autant que le thème ?)
    # et thèmes mélangés au hasard (mêmes tailles de groupes), dont la modularité attendue est ~0.
    decade_groups = assignment.groupby(assignment["year"] // 10)["set_num"].apply(set).tolist()
    shuffled = np.random.default_rng(params.seed).permutation(assignment["root_theme"].to_numpy())
    shuffled_groups = assignment.groupby(shuffled)["set_num"].apply(set).tolist()

    summary = {
        "algorithm": "Louvain (networkx.community.louvain_communities)",
        "resolution": params.resolution,
        "seed": params.seed,
        "n_communities": len(comms),
        "n_communities_size_ge_10": sum(len(c) >= 10 for c in comms),
        "modularity_louvain": nx.community.modularity(G, comms, weight="weight"),
        "modularity_root_themes": nx.community.modularity(G, theme_groups, weight="weight"),
        "modularity_decades": nx.community.modularity(G, decade_groups, weight="weight"),
        "modularity_shuffled_themes": nx.community.modularity(G, shuffled_groups, weight="weight"),
        "nmi_vs_root_theme": normalized_mutual_info_score(
            assignment["root_theme"], assignment["community"]
        ),
        "ari_vs_root_theme": adjusted_rand_score(assignment["root_theme"], assignment["community"]),
        "nmi_vs_theme": normalized_mutual_info_score(assignment["theme"], assignment["community"]),
    }
    # Un set isolé forme sa propre communauté, ce qui fausse NMI/ARI : on les recalcule sans eux.
    linked = assignment[[G.degree(n) > 0 for n in assignment["set_num"]]]
    summary["n_isolated_singletons"] = len(assignment) - len(linked)
    summary["nmi_vs_root_theme_non_isolated"] = normalized_mutual_info_score(
        linked["root_theme"], linked["community"]
    )
    summary["ari_vs_root_theme_non_isolated"] = adjusted_rand_score(
        linked["root_theme"], linked["community"]
    )

    rows = []
    for k, group in assignment.groupby("community"):
        counts = group["root_theme"].value_counts()
        rows.append(
            {
                "community": k,
                "size": len(group),
                "purity": counts.iloc[0] / len(group),
                "dominant_theme": counts.index[0],
                "top_themes": "; ".join(f"{t} ({c})" for t, c in counts.head(4).items()),
                "median_year": float(group["year"].median()),
            }
        )
    return summary, assignment, pd.DataFrame(rows)


def theme_cohesion(G: nx.Graph, min_sets: int = 30) -> pd.DataFrame:
    """Pour chaque thème racine : part du poids de ses arêtes qui reste dans le thème.

    internal_share = 2 * poids interne / somme des forces des sets du thème.
    expected_share = valeur attendue si les arêtes ignoraient les thèmes
    (force du thème / force totale, comme dans la modularité).
    1 = univers fermé ; proche de expected_share = simple étiquette.
    """
    strength = dict(G.degree(weight="weight"))
    total = sum(strength.values())
    members: dict[str, list] = {}
    for n, theme in G.nodes(data="root_theme"):
        members.setdefault(theme, []).append(n)
    rows = []
    for theme, nodes in members.items():
        volume = sum(strength[n] for n in nodes)
        if len(nodes) < min_sets or volume == 0:
            continue
        rows.append(
            {
                "root_theme": theme,
                "n_sets": len(nodes),
                "internal_share": 2 * G.subgraph(nodes).size(weight="weight") / volume,
                "expected_share": volume / total,
            }
        )
    return pd.DataFrame(rows).sort_values("internal_share", ascending=False).reset_index(drop=True)


# ---------------------------------------------------------------------------
# Évolution dans le temps
# ---------------------------------------------------------------------------
def exclusive_parts(pairs: pd.DataFrame, sets: pd.DataFrame, set_nums=None) -> pd.DataFrame:
    """Pour chaque set : nombre de pièces, nombre et part de pièces exclusives à son thème.

    Une pièce est exclusive si on ne la trouve dans aucun autre thème racine.
    L'exclusivité se juge sur tous les `pairs` ; `set_nums` restreint seulement les
    sets renvoyés (une période), pour ne pas dépendre du nombre de thèmes de la période.
    """
    df = pairs.merge(sets[["set_num", "root_theme"]], on="set_num")
    themes_per_part = df.groupby("part")["root_theme"].nunique()
    df["exclusive"] = df["part"].map(themes_per_part) == 1
    if set_nums is not None:
        df = df[df["set_num"].isin(set_nums)]
    out = df.groupby("set_num").agg(n_parts=("part", "size"), n_exclusive=("exclusive", "sum"))
    out["exclusive_share"] = out["n_exclusive"] / out["n_parts"]
    return out.reset_index()


def exclusive_part_share(pairs: pd.DataFrame, sets: pd.DataFrame, set_nums=None) -> float:
    """Part moyenne des pièces d'un set qu'on ne trouve dans aucun autre thème racine.

    Indicateur de spécialisation qui ne dépend pas du seuil de la projection
    (voir `exclusive_parts`).
    """
    return float(exclusive_parts(pairs, sets, set_nums)["exclusive_share"].mean())


def temporal(
    tables: dict[str, pd.DataFrame], params: Params, periods: list[tuple[int, int]]
) -> pd.DataFrame:
    """Reconstruit le graphe pour chaque période avec les mêmes paramètres.

    Les colonnes `min_weight` et `drop_stickers` rappellent les paramètres
    utilisés, pour pouvoir empiler plusieurs configurations (temporal_robustness.py).
    """
    all_sets, all_pairs, _ = prepare(tables, params)
    rows = []
    for start, end in periods:
        p = replace(params, year_min=start, year_max=end)
        G, pairs, sets = build_set_graph(tables, p)
        if G.number_of_nodes() < 2:
            continue
        comm_summary, _, _ = communities(G, p)
        conn, _ = connectivity(G)
        excl = exclusive_parts(all_pairs, all_sets, sets["set_num"])
        rows.append(
            {
                "period": f"{start}-{end}",
                "n_sets": G.number_of_nodes(),
                "n_edges": G.number_of_edges(),
                "n_root_themes": sets["root_theme"].nunique(),
                "density": nx.density(G),
                "largest_component_share": conn["largest_component_share"],
                "modularity_louvain": comm_summary["modularity_louvain"],
                "modularity_root_themes": comm_summary["modularity_root_themes"],
                "nmi_vs_root_theme": comm_summary["nmi_vs_root_theme"],
                "nmi_vs_root_theme_non_isolated": comm_summary["nmi_vs_root_theme_non_isolated"],
                "ari_vs_root_theme_non_isolated": comm_summary["ari_vs_root_theme_non_isolated"],
                "exclusive_part_share": float(excl["exclusive_share"].mean()),
                # En nombre : la part peut baisser seulement parce que les sets grossissent.
                "exclusive_parts_per_set": float(excl["n_exclusive"].mean()),
                "parts_per_set": float(excl["n_parts"].mean()),
                "min_weight": params.min_weight,
                "drop_stickers": params.drop_stickers,
            }
        )
    return pd.DataFrame(rows)


def _label(G: nx.Graph, n) -> str:
    d = G.nodes[n]
    return f"{n} {d['name']} ({d['root_theme']}, {d['year']})"
