"""Étude de sensibilité : comment les résultats changent-ils avec la
pondération et le seuil de la projection ?

Écrit results/sensitivity.csv. À utiliser pour choisir et justifier les
paramètres retenus dans le rapport.

    uv run python sensitivity.py
    uv run python sensitivity.py --demo

Un seuil trop bas relie presque toutes les paires de sets (des dizaines de
millions d'arêtes) : ces configurations sont arrêtées dès que la limite
--max-edges est dépassée et notées comme telles dans le tableau. Louvain n'est
lancé que si le graphe a au plus --max-edges-louvain arêtes.
"""

import argparse
import tempfile
import time
from dataclasses import replace
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import sparse
from scipy.sparse.csgraph import connected_components

from lego_graph import analysis
from lego_graph.build import TooManyEdges, graph_from_edges, prepare, project
from lego_graph.config import Params
from lego_graph.load import load_tables
from lego_graph.synthetic import write_tables

# Grille resserrée sur la zone de transition observée sur les données réelles
# (premier passage : Jaccard 0.05-0.15, count <= 20, idf <= 20 dépassent 5 M d'arêtes ;
# voir results/sensitivity_coarse.csv).
GRID = {
    "jaccard": [0.15, 0.2, 0.225, 0.25, 0.275, 0.3, 0.35, 0.4],
    "count": [40, 60, 80, 120],
    "idf": [80, 120, 160, 240],
}


def fast_stats(edges: pd.DataFrame, n_nodes: int) -> dict:
    """Taille et connectivité calculées avec SciPy, sans construire de graphe NetworkX."""
    u = edges["u"].to_numpy()
    v = edges["v"].to_numpy()
    adjacency = sparse.coo_matrix((np.ones(len(u)), (u, v)), shape=(n_nodes, n_nodes))
    n_components, labels = connected_components(adjacency, directed=False)
    degree = np.bincount(u, minlength=n_nodes) + np.bincount(v, minlength=n_nodes)
    return {
        "n_edges": len(edges),
        "density": 2 * len(edges) / (n_nodes * (n_nodes - 1)) if n_nodes > 1 else 0.0,
        "mean_degree": float(degree.mean()),
        "n_components": int(n_components),
        "n_isolated": int((degree == 0).sum()),
        "largest_component_share": float(np.bincount(labels).max() / n_nodes),
    }


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--data-dir", default="data/raw")
    p.add_argument("--results-dir", default="results")
    p.add_argument("--demo", action="store_true")
    p.add_argument("--max-edges", type=int, default=5_000_000,
                   help="au-delà, la configuration est abandonnée (seuil trop bas)")
    p.add_argument("--max-edges-louvain", type=int, default=1_000_000,
                   help="Louvain seulement si le graphe a au plus ce nombre d'arêtes (0 = jamais)")
    args = p.parse_args()

    data_dir = write_tables(Path(tempfile.mkdtemp()) / "demo") if args.demo else args.data_dir
    base = Params()
    grid = GRID
    if args.demo:  # les sets synthétiques sont petits et commencent en 1985
        base = replace(base, year_min=1980, min_parts=1)
        grid = {"jaccard": [0.02, 0.05, 0.1, 0.2], "count": [1, 2, 4], "idf": [1, 5, 10]}

    t0 = time.time()
    tables = load_tables(data_dir)
    sets, pairs, bip = prepare(tables, base)
    n = len(bip.sets)
    print(
        f"{n} sets, {len(bip.parts)} pièces distinctes, {len(pairs)} couples set-pièce "
        f"({time.time() - t0:.0f} s)",
        flush=True,
    )

    rows = []
    for weighting, thresholds in grid.items():
        for t in thresholds:
            t0 = time.time()
            params = replace(base, weighting=weighting, min_weight=t)
            row = {"weighting": weighting, "min_weight": t, "n_nodes": n}
            try:
                edges = project(bip, params, max_edges=args.max_edges)
            except TooManyEdges:
                row["note"] = f"abandonné : plus de {args.max_edges} arêtes"
                rows.append(row)
                print(f"{weighting} >= {t}: {row['note']} ({time.time() - t0:.0f} s)", flush=True)
                continue

            row.update(fast_stats(edges, n))
            if 0 < row["n_edges"] <= args.max_edges_louvain:
                G = graph_from_edges(sets, pairs, bip, edges, params)
                comm, _, _ = analysis.communities(G, params)
                row.update(
                    n_communities=comm["n_communities"],
                    n_communities_size_ge_10=comm["n_communities_size_ge_10"],
                    modularity_louvain=comm["modularity_louvain"],
                    modularity_root_themes=comm["modularity_root_themes"],
                    nmi_vs_root_theme=comm["nmi_vs_root_theme"],
                    nmi_vs_root_theme_non_isolated=comm["nmi_vs_root_theme_non_isolated"],
                    ari_vs_root_theme_non_isolated=comm["ari_vs_root_theme_non_isolated"],
                )
            elif row["n_edges"] > args.max_edges_louvain:
                row["note"] = "Louvain non lancé (graphe trop grand)"
            rows.append(row)
            print(
                f"{weighting} >= {t}: {row['n_edges']} arêtes, "
                f"{row['n_components']} composantes, "
                f"plus grande = {row['largest_component_share']:.0%}, "
                f"NMI = {row.get('nmi_vs_root_theme', float('nan')):.3f} "
                f"({time.time() - t0:.0f} s)",
                flush=True,
            )

    out = Path(args.results_dir)
    out.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(out / "sensitivity.csv", index=False)
    print(f"Écrit {out / 'sensitivity.csv'}")


if __name__ == "__main__":
    main()
