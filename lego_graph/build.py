"""Construction du graphe biparti sets-pièces et de sa projection sur les sets."""

from dataclasses import dataclass

import networkx as nx
import numpy as np
import pandas as pd
from scipy import sparse

from .config import Params

WEIGHTINGS = ("count", "jaccard", "idf")


class TooManyEdges(Exception):
    """La projection dépasse max_edges : seuil trop bas pour ce volume."""


@dataclass
class Bipartite:
    """Matrice d'incidence sets x pièces (1 si la pièce est dans le set)."""

    matrix: sparse.csr_matrix
    sets: pd.Index  # numéros de set, dans l'ordre des lignes
    parts: pd.Index  # identifiants de pièce, dans l'ordre des colonnes


def theme_table(themes: pd.DataFrame) -> pd.DataFrame:
    """Ajoute à chaque thème son thème racine (en remontant les parent_id)."""
    parent = dict(zip(themes["id"], themes["parent_id"]))
    names = dict(zip(themes["id"], themes["name"]))

    def root(theme_id):
        seen = set()
        while pd.notna(parent.get(theme_id)) and theme_id not in seen:
            seen.add(theme_id)
            theme_id = int(parent[theme_id])
        return theme_id

    out = themes[["id", "name", "parent_id"]].copy()
    out["root_id"] = out["id"].map(root)
    out["root_name"] = out["root_id"].map(names)
    return out


def select_sets(tables: dict[str, pd.DataFrame], params: Params) -> pd.DataFrame:
    """Sets retenus, avec leur thème et leur thème racine."""
    themes = theme_table(tables["themes"]).rename(
        columns={"id": "theme_id", "name": "theme", "root_name": "root_theme"}
    )
    sets = tables["sets"].merge(
        themes[["theme_id", "theme", "root_id", "root_theme"]], on="theme_id", how="left"
    )
    excluded = sets["theme"].isin(params.exclude_themes) | sets["root_theme"].isin(
        params.exclude_themes
    )
    keep = (
        sets["year"].between(params.year_min, params.year_max)
        & (sets["num_parts"] >= params.min_parts)
        & ~excluded
    )
    return sets.loc[keep].reset_index(drop=True)


def sticker_parts(tables: dict[str, pd.DataFrame]) -> set[str]:
    """Numéros des autocollants (catégories dont le nom contient « Sticker »)."""
    cats = tables["part_categories"]
    sticker_cats = cats.loc[cats["name"].astype(str).str.contains("Sticker", case=False), "id"]
    parts = tables["parts"]
    return set(parts.loc[parts["part_cat_id"].isin(sticker_cats), "part_num"].astype(str))


def set_part_pairs(
    tables: dict[str, pd.DataFrame], sets: pd.DataFrame, params: Params
) -> pd.DataFrame:
    """Couples (set, pièce) distincts, hors pièces de rechange (et hors
    autocollants si `params.drop_stickers`).

    Pour un set qui a plusieurs versions d'inventaire, on garde la plus petite
    version (l'inventaire d'origine).
    """
    inv = tables["inventories"]
    inv = inv[inv["set_num"].isin(sets["set_num"])]
    inv = inv.sort_values(["set_num", "version"]).drop_duplicates("set_num")

    ip = tables["inventory_parts"].merge(
        inv[["id", "set_num"]], left_on="inventory_id", right_on="id"
    )
    is_spare = ip["is_spare"].astype(str).str.strip().str.lower().isin(["t", "true", "1"])
    ip = ip.loc[~is_spare]

    if params.drop_stickers:
        ip = ip[~ip["part_num"].astype(str).isin(sticker_parts(tables))]

    if params.ignore_color:
        ip = ip.assign(part=ip["part_num"].astype(str))
    else:
        ip = ip.assign(part=ip["part_num"].astype(str) + "|" + ip["color_id"].astype(str))

    pairs = ip[["set_num", "part"]].drop_duplicates()

    if params.max_part_share is not None:
        n_sets = pairs["set_num"].nunique()
        share = pairs.groupby("part")["set_num"].nunique() / n_sets
        common = share.index[share > params.max_part_share]
        pairs = pairs[~pairs["part"].isin(common)]

    return pairs.reset_index(drop=True)


def incidence_matrix(pairs: pd.DataFrame) -> Bipartite:
    set_codes, set_index = pd.factorize(pairs["set_num"], sort=True)
    part_codes, part_index = pd.factorize(pairs["part"], sort=True)
    data = np.ones(len(pairs), dtype=np.float64)
    matrix = sparse.csr_matrix(
        (data, (set_codes, part_codes)), shape=(len(set_index), len(part_index))
    )
    return Bipartite(matrix=matrix, sets=pd.Index(set_index), parts=pd.Index(part_index))


def project(bip: Bipartite, params: Params, max_edges: int | None = None) -> pd.DataFrame:
    """Projection du biparti sur les sets.

    Calcule B @ B.T par blocs de lignes pour limiter la mémoire, applique la
    pondération choisie puis le seuil. Renvoie une table d'arêtes (u, v,
    shared, weight) avec u < v, u et v étant des indices de ligne de `bip`.
    Lève TooManyEdges dès que plus de `max_edges` arêtes sont gardées.
    """
    if params.weighting not in WEIGHTINGS:
        raise ValueError(f"weighting doit être parmi {WEIGHTINGS}")

    B = bip.matrix
    n_sets = B.shape[0]
    n_parts_per_set = np.asarray(B.sum(axis=1)).ravel()
    right_count = B.T.tocsr()
    if params.weighting == "idf":
        doc_freq = np.asarray(B.sum(axis=0)).ravel()
        # Plancher > 0 : une pièce présente partout garde le même motif creux que `shared`.
        idf = np.maximum(np.log(n_sets / doc_freq), 1e-9)
        right_weight = (B @ sparse.diags(idf)).T.tocsr()

    chunks = []
    n_kept = 0
    for start in range(0, n_sets, params.chunk_size):
        stop = min(start + params.chunk_size, n_sets)
        block = B[start:stop]
        shared = (block @ right_count).tocoo()
        i = shared.row + start
        j = shared.col
        upper = i < j
        i, j, n_shared = i[upper], j[upper], shared.data[upper]

        if params.weighting == "count":
            weight = n_shared
        elif params.weighting == "jaccard":
            weight = n_shared / (n_parts_per_set[i] + n_parts_per_set[j] - n_shared)
        else:  # idf : même motif creux que `shared`, donc on réaligne par (i, j)
            w = (block @ right_weight).tocoo()
            w_upper = (w.row + start) < w.col
            w_df = pd.DataFrame(
                {"i": w.row[w_upper] + start, "j": w.col[w_upper], "w": w.data[w_upper]}
            )
            s_df = pd.DataFrame({"i": i, "j": j})
            weight = s_df.merge(w_df, on=["i", "j"], how="left")["w"].to_numpy()

        keep = weight >= params.min_weight
        n_kept += int(keep.sum())
        if max_edges is not None and n_kept > max_edges:
            raise TooManyEdges(f"plus de {max_edges} arêtes")
        chunks.append(
            pd.DataFrame(
                {
                    "u": i[keep],
                    "v": j[keep],
                    "shared": n_shared[keep].astype(int),
                    "weight": weight[keep],
                }
            )
        )

    edges = pd.concat(chunks, ignore_index=True) if chunks else pd.DataFrame(
        columns=["u", "v", "shared", "weight"]
    )

    if params.top_k is not None and len(edges):
        both = pd.concat(
            [
                edges.assign(node=edges["u"], idx=edges.index),
                edges.assign(node=edges["v"], idx=edges.index),
            ]
        )
        top = (
            both.sort_values("weight", ascending=False)
            .groupby("node")
            .head(params.top_k)["idx"]
            .unique()
        )
        edges = edges.loc[np.sort(top)]

    return edges.reset_index(drop=True)


def prepare(tables: dict[str, pd.DataFrame], params: Params):
    """Sélection des sets, couples set-pièce et biparti. Renvoie (sets, pairs, bip)."""
    sets = select_sets(tables, params)
    pairs = set_part_pairs(tables, sets, params)
    # Les sets sans inventaire de pièces ne peuvent pas être reliés : on les retire.
    sets = sets[sets["set_num"].isin(pairs["set_num"])].reset_index(drop=True)
    return sets, pairs, incidence_matrix(pairs)


def graph_from_edges(sets, pairs, bip: Bipartite, edges: pd.DataFrame, params: Params) -> nx.Graph:
    """Graphe NetworkX à partir des arêtes de `project` (indices de ligne de `bip`)."""
    edges = edges.assign(u=bip.sets[edges["u"].to_numpy()], v=bip.sets[edges["v"].to_numpy()])
    n_distinct = pairs.groupby("set_num")["part"].nunique()
    G = nx.Graph()
    for row in sets.itertuples(index=False):
        G.add_node(
            row.set_num,
            name=str(row.name),
            year=int(row.year),
            theme=str(row.theme),
            root_theme=str(row.root_theme),
            num_parts=int(row.num_parts),
            n_distinct_parts=int(n_distinct.get(row.set_num, 0)),
        )
    for row in edges.itertuples(index=False):
        G.add_edge(
            row.u,
            row.v,
            weight=float(row.weight),
            shared=int(row.shared),
            # Distance pour les plus courts chemins pondérés : un lien fort = proche.
            distance=1.0 / float(row.weight),
        )
    G.graph.update(
        directed=False,
        multigraph=False,
        weighting=params.weighting,
        min_weight=params.min_weight,
    )
    return G


def build_set_graph(tables: dict[str, pd.DataFrame], params: Params, max_edges: int | None = None):
    """Pipeline complet.

    Renvoie (G, pairs, sets) :
      - G : graphe non orienté, simple, pondéré ; un nœud = un set ;
      - pairs : couples (set, pièce) utilisés ;
      - sets : métadonnées des sets retenus (présents dans G).
    """
    sets, pairs, bip = prepare(tables, params)
    edges = project(bip, params, max_edges=max_edges)
    return graph_from_edges(sets, pairs, bip, edges, params), pairs, sets
