"""Analyses complémentaires sur le graphe des sets :

1. Autre algorithme : Louvain à plusieurs résolutions et label propagation,
   comparés aux thèmes officiels (modularité, NMI, ARI).
2. Graphe des thèmes : un nœud par thème racine, arêtes pondérées par les
   liens entre leurs sets.
3. Deviner le thème : thème d'un set prédit par vote de ses voisins,
   pourcentage de réussite par thème.

    uv run python run_extensions.py
    uv run python run_extensions.py --n-seeds 3 --resolutions 0.5 1 2 4
    uv run python run_extensions.py --demo   # données synthétiques, pour tester

Écrit dans results/ : communities_comparison.csv, theme_graph.gexf,
theme_graph_edges.csv, theme_prediction.csv, theme_prediction_sets.csv,
extensions_summary.json ; et figures/theme_graph.png.
"""

import argparse
import json
import tempfile
import time
from dataclasses import asdict, replace
from pathlib import Path

import networkx as nx

from lego_graph import extensions
from lego_graph.build import build_set_graph
from lego_graph.config import Params
from lego_graph.load import load_tables
from lego_graph.synthetic import write_tables

T0 = time.time()


def log(msg: str) -> None:
    print(f"[{time.time() - T0:6.0f} s] {msg}", flush=True)


def main() -> None:
    d = Params()
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--data-dir", default="data/raw")
    p.add_argument("--results-dir", default="results")
    p.add_argument("--figures-dir", default="figures")
    p.add_argument("--demo", action="store_true", help="utiliser des données synthétiques")
    p.add_argument("--min-weight", type=float, default=d.min_weight)
    p.add_argument("--drop-stickers", action="store_true", help="retirer les autocollants")
    p.add_argument("--seed", type=int, default=d.seed)
    p.add_argument("--n-seeds", type=int, default=1,
                   help="nombre de graines pour Louvain et label propagation (seed, seed+1, ...)")
    p.add_argument("--resolutions", type=float, nargs="+", default=[0.5, 1.0, 2.0, 4.0])
    p.add_argument("--min-sets", type=int, default=30, help="taille minimale d'un thème sur la figure")
    args = p.parse_args()

    params = replace(d, min_weight=args.min_weight, drop_stickers=args.drop_stickers, seed=args.seed)
    data_dir = args.data_dir
    min_sets = args.min_sets
    if args.demo:  # les sets synthétiques sont petits, peu nombreux et commencent en 1985
        data_dir = write_tables(Path(tempfile.mkdtemp()) / "demo")
        params = replace(params, year_min=1980, min_parts=1, min_weight=0.05)
        min_sets = 1

    results = Path(args.results_dir)
    figs = Path(args.figures_dir)
    results.mkdir(parents=True, exist_ok=True)
    figs.mkdir(parents=True, exist_ok=True)

    log("Chargement et construction du graphe...")
    G, _, _ = build_set_graph(load_tables(data_dir), params)
    log(f"{G.number_of_nodes()} sets, {G.number_of_edges()} arêtes")
    summary = {"params": asdict(params)}

    # 1. Communautés -----------------------------------------------------
    log("Louvain à plusieurs résolutions et label propagation...")
    seeds = [args.seed + i for i in range(args.n_seeds)]
    comparison = extensions.compare_communities(G, resolutions=args.resolutions, seeds=seeds, log=log)
    comparison.to_csv(results / "communities_comparison.csv", index=False)

    # 2. Graphe des thèmes ----------------------------------------------
    log("Graphe des thèmes...")
    T = extensions.theme_graph(G)
    nx.write_gexf(T, results / "theme_graph.gexf")
    extensions.theme_edges_table(T).to_csv(results / "theme_graph_edges.csv", index=False)
    extensions.theme_graph_figure(T, figs / "theme_graph.png", min_sets=min_sets, seed=args.seed)
    summary["theme_graph"] = {
        "n_themes": T.number_of_nodes(),
        "n_edges": T.number_of_edges(),
        "density": nx.density(T),
        "n_isolated_themes": nx.number_of_isolates(T),
    }

    # 3. Deviner le thème -----------------------------------------------
    log("Prédiction du thème par vote des voisins...")
    pred = extensions.predict_theme(G, weighted=True)
    pred_unw = extensions.predict_theme(G, weighted=False)
    by_theme = extensions.prediction_by_theme(pred, pred_unw)
    by_theme.to_csv(results / "theme_prediction.csv", index=False)
    pred.to_csv(results / "theme_prediction_sets.csv", index=False)
    summary["theme_prediction"] = extensions.prediction_summary(pred, by_theme, min_sets=args.min_sets)
    summary["theme_prediction"]["accuracy_unweighted"] = float(
        pred_unw.loc[pred_unw["degree"] > 0, "correct"].mean()
    )

    with open(results / "extensions_summary.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False, default=str)

    tp = summary["theme_prediction"]
    cols = ["algorithm", "resolution", "seed", "n_communities", "modularity", "nmi_vs_root_theme_non_isolated"]
    print("\nCommunautés :\n" + comparison[cols].to_string(index=False, float_format="%.3f"))
    print(
        f"\nGraphe des thèmes : {T.number_of_nodes()} thèmes, {T.number_of_edges()} arêtes"
        f"\nThème deviné : {tp['accuracy']:.1%} de réussite (sets non isolés),"
        f" {tp['accuracy_unweighted']:.1%} sans pondération ;"
        f" repères : thème majoritaire {tp['majority_baseline']:.1%}, hasard {tp['random_baseline']:.1%}"
        f"\nRésultats dans {results}/ et {figs}/"
    )


if __name__ == "__main__":
    main()
