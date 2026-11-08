"""Modèle nul : les mêmes sets, mais des pièces tirées au hasard.

On mélange la matrice d'incidence sets x pièces avec l'algorithme
« curveball » (Strona et al., 2014) : chaque set garde son nombre de pièces
et chaque pièce garde son nombre de sets. Seul le lien entre les pièces et
les thèmes est cassé. On refait ensuite le graphe des sets et on compare la
cohésion de chaque thème à celle obtenue au hasard.
"""

from dataclasses import replace

import networkx as nx
import numpy as np
import pandas as pd
from scipy import sparse

from .analysis import theme_cohesion
from .build import Bipartite, graph_from_edges, project
from .config import Params


def curveball(bip: Bipartite, n_rounds: int = 20, seed: int = 42) -> Bipartite:
    """Mélange curveball de la matrice d'incidence.

    À chaque tour, les sets sont groupés deux à deux au hasard. Pour chaque
    paire (a, b), les pièces qu'ils ont en commun restent en place ; les autres
    sont remises en jeu et redistribuées au hasard, chaque set gardant son
    nombre de pièces. Les tailles des sets (lignes) et les fréquences des
    pièces (colonnes) sont donc exactement conservées.
    """
    rng = np.random.default_rng(seed)
    B = bip.matrix.tocsr()
    rows = [set(B.indices[B.indptr[i] : B.indptr[i + 1]].tolist()) for i in range(B.shape[0])]
    n = len(rows)
    for _ in range(n_rounds):
        order = rng.permutation(n)
        for a, b in zip(order[0::2], order[1::2]):
            only_a = rows[a] - rows[b]
            only_b = rows[b] - rows[a]
            if not only_a or not only_b:
                continue
            shared = rows[a] & rows[b]
            pool = rng.permutation(np.array(sorted(only_a | only_b)))
            k = len(only_a)
            rows[a] = shared | set(pool[:k].tolist())
            rows[b] = shared | set(pool[k:].tolist())

    indptr = np.cumsum([0] + [len(r) for r in rows])
    indices = np.concatenate([np.array(sorted(r), dtype=np.int64) for r in rows])
    matrix = sparse.csr_matrix((np.ones(len(indices)), indices, indptr), shape=B.shape)
    return Bipartite(matrix=matrix, sets=bip.sets, parts=bip.parts)


def share_unchanged(bip: Bipartite, null: Bipartite) -> float:
    """Part des couples (set, pièce) d'origine encore présents après le mélange."""
    return bip.matrix.multiply(null.matrix).sum() / bip.matrix.sum()


def strongest_edges(bip: Bipartite, params: Params, n_edges: int, step: float = 0.85):
    """Les `n_edges` arêtes les plus fortes de la projection.

    Sert à donner au graphe nul la même densité que le graphe réel : au seuil
    réel, le graphe nul n'a presque pas d'arêtes. On baisse le seuil par
    paliers jusqu'à avoir au moins `n_edges` arêtes, puis on garde les plus
    fortes. Renvoie (arêtes, nombre d'arêtes au seuil d'origine, poids minimal gardé).
    """
    edges = project(bip, params)
    n_at_threshold = len(edges)
    threshold = params.min_weight
    while len(edges) < n_edges and threshold > 1e-6:
        threshold *= step
        edges = project(bip, replace(params, min_weight=threshold), max_edges=20 * n_edges)
    top = edges.sort_values(["weight", "u", "v"], ascending=[False, True, True]).head(n_edges)
    cutoff = float(top["weight"].min()) if len(top) else float("nan")
    return top.reset_index(drop=True), n_at_threshold, cutoff


def theme_modularity(G: nx.Graph) -> float:
    """Modularité de la partition « un groupe par thème racine »."""
    groups: dict[str, set] = {}
    for n, theme in G.nodes(data="root_theme"):
        groups.setdefault(theme, set()).add(n)
    return nx.community.modularity(G, groups.values(), weight="weight")


def cohesion_vs_null(
    sets: pd.DataFrame,
    pairs: pd.DataFrame,
    bip: Bipartite,
    params: Params,
    n_null: int = 10,
    n_rounds: int = 20,
    min_sets: int = 30,
    log=print,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Cohésion réelle des thèmes comparée à `n_null` graphes nuls.

    Renvoie (une ligne par thème, une ligne par graphe : réel puis tirages).
    Le tirage r utilise la graine params.seed + r.
    """
    edges = project(bip, params)
    G = graph_from_edges(sets, pairs, bip, edges, params)
    real = theme_cohesion(G, min_sets=min_sets).set_index("root_theme")
    runs = [
        {
            "run": "réel",
            "n_edges": G.number_of_edges(),
            "n_edges_at_min_weight": len(edges),
            "weight_cutoff": params.min_weight,
            "n_isolated": nx.number_of_isolates(G),
            "share_pairs_unchanged": 1.0,
            "modularity_root_themes": theme_modularity(G),
        }
    ]

    null_shares = {}
    for r in range(n_null):
        null = curveball(bip, n_rounds=n_rounds, seed=params.seed + r)
        null_edges, n_at_threshold, cutoff = strongest_edges(null, params, len(edges))
        H = graph_from_edges(sets, pairs, null, null_edges, params)
        null_shares[r] = theme_cohesion(H, min_sets=min_sets).set_index("root_theme")["internal_share"]
        runs.append(
            {
                "run": r,
                "n_edges": H.number_of_edges(),
                "n_edges_at_min_weight": n_at_threshold,
                "weight_cutoff": cutoff,
                "n_isolated": nx.number_of_isolates(H),
                "share_pairs_unchanged": share_unchanged(bip, null),
                "modularity_root_themes": theme_modularity(H),
            }
        )
        log(
            f"  tirage {r + 1}/{n_null} : {n_at_threshold} arêtes au seuil {params.min_weight}, "
            f"poids minimal gardé {cutoff:.3f}, modularité des thèmes {runs[-1]['modularity_root_themes']:.3f}"
        )

    # Un thème dont tous les sets sont isolés dans un tirage n'a pas de cohésion (NaN).
    null_table = pd.DataFrame(null_shares).reindex(real.index)
    out = real[["n_sets", "internal_share", "expected_share"]].copy()
    out["null_mean"] = null_table.mean(axis=1)
    out["null_std"] = null_table.std(axis=1)
    out["null_min"] = null_table.min(axis=1)
    out["null_max"] = null_table.max(axis=1)
    out["n_null_valid"] = null_table.notna().sum(axis=1)
    out["ratio_to_null"] = out["internal_share"] / out["null_mean"]
    out["z_score"] = (out["internal_share"] - out["null_mean"]) / out["null_std"].where(out["null_std"] > 0)
    out["n_null_ge_real"] = null_table.ge(out["internal_share"], axis=0).sum(axis=1)
    # p-valeur empirique : (1 + nombre de tirages au moins aussi cohésifs) / (1 + nombre de tirages).
    out["p_value"] = (1 + out["n_null_ge_real"]) / (1 + out["n_null_valid"])
    out = out.sort_values("internal_share", ascending=False).reset_index()
    return out, pd.DataFrame(runs)
