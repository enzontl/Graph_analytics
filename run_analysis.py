"""Lance toute l'analyse et écrit les résultats dans results/ et figures/.

Exemples :
    python run_analysis.py
    python run_analysis.py --weighting idf --min-weight 5
    python run_analysis.py --demo   # données synthétiques, pour tester
"""

import argparse
import json
import tempfile
import time
from dataclasses import asdict
from pathlib import Path

import networkx as nx

from lego_graph import analysis, figures
from lego_graph.build import WEIGHTINGS, build_set_graph
from lego_graph.config import Params
from lego_graph.load import load_tables
from lego_graph.synthetic import write_tables

T0 = time.time()


def log(msg: str) -> None:
    """Affiche le temps écoulé depuis le début : l'écart entre deux lignes = durée de l'étape."""
    print(f"[{time.time() - T0:6.0f} s] {msg}", flush=True)


DEFAULT_PERIODS = [(1990, 1999), (2000, 2009), (2010, 2019), (2020, 2025)]


def parse_args() -> argparse.Namespace:
    d = Params()
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--data-dir", default="data/raw")
    p.add_argument("--results-dir", default="results")
    p.add_argument("--figures-dir", default="figures")
    p.add_argument("--demo", action="store_true", help="utiliser des données synthétiques")
    p.add_argument("--year-min", type=int, default=d.year_min)
    p.add_argument("--year-max", type=int, default=d.year_max)
    p.add_argument("--min-parts", type=int, default=d.min_parts)
    p.add_argument("--with-color", action="store_true", help="une pièce = (forme, couleur)")
    p.add_argument("--max-part-share", type=float, default=d.max_part_share)
    p.add_argument("--weighting", choices=WEIGHTINGS, default=d.weighting)
    p.add_argument("--min-weight", type=float, default=d.min_weight)
    p.add_argument("--top-k", type=int, default=d.top_k)
    p.add_argument("--resolution", type=float, default=d.resolution)
    p.add_argument("--betweenness-k", type=int, default=d.betweenness_k)
    p.add_argument("--seed", type=int, default=d.seed)
    p.add_argument("--no-temporal", action="store_true", help="sauter l'analyse par période")
    p.add_argument("--no-gexf", action="store_true", help="ne pas exporter le graphe pour Gephi")
    return p.parse_args()


def main() -> None:
    args = parse_args()
    params = Params(
        year_min=args.year_min,
        year_max=args.year_max,
        min_parts=args.min_parts,
        ignore_color=not args.with_color,
        max_part_share=args.max_part_share,
        weighting=args.weighting,
        min_weight=args.min_weight,
        top_k=args.top_k,
        resolution=args.resolution,
        betweenness_k=args.betweenness_k,
        seed=args.seed,
    )
    results = Path(args.results_dir)
    figs = Path(args.figures_dir)
    results.mkdir(parents=True, exist_ok=True)
    figs.mkdir(parents=True, exist_ok=True)

    data_dir = args.data_dir
    if args.demo:
        data_dir = write_tables(Path(tempfile.mkdtemp()) / "demo")
        print(f"Données synthétiques écrites dans {data_dir}")

    log("Chargement des tables...")
    tables = load_tables(data_dir)

    log("Construction du graphe...")
    G, pairs, sets = build_set_graph(tables, params)
    summary = {"params": asdict(params), "basic": analysis.basic_stats(G)}
    print(f"  {G.number_of_nodes()} sets, {G.number_of_edges()} arêtes")

    log("Connectivité...")
    summary["connectivity"], components = analysis.connectivity(G)
    components.to_csv(results / "components.csv", index=False)

    log("Diamètre et rayon (plus grande composante)...")
    summary["distances"] = analysis.distances(G, seed=params.seed)

    log("Centralités...")
    cent = analysis.centralities(G, params)
    cent.to_csv(results / "centralities.csv", index=False)
    summary["top_sets"] = {
        col: cent.nlargest(10, col)[["set_num", "name", "root_theme", "year", col]].to_dict("records")
        for col in ("degree", "strength", "betweenness", "eigenvector")
    }

    log("Pièces universelles (degré dans le biparti)...")
    universal = analysis.part_universality(pairs, sets, tables["parts"])
    universal.to_csv(results / "parts_universality.csv", index=False)
    analysis.signature_parts(pairs, sets, universal).to_csv(results / "signature_parts.csv", index=False)
    figures.part_theme_distribution(universal, figs / "parts_themes.png")
    summary["exclusive_part_share"] = analysis.exclusive_part_share(pairs, sets)

    log("Communautés...")
    summary["communities"], assignment, comm_table = analysis.communities(G, params)
    assignment.to_csv(results / "communities_assignment.csv", index=False)
    comm_table.to_csv(results / "communities_summary.csv", index=False)
    analysis.theme_cohesion(G).to_csv(results / "theme_cohesion.csv", index=False)

    if not args.no_temporal:
        log("Analyse par période...")
        periods = DEFAULT_PERIODS
        if args.demo:
            periods = [(1985, 1999), (2000, 2014), (2015, 2025)]
        temporal = analysis.temporal(tables, params, periods)
        temporal.to_csv(results / "temporal.csv", index=False)
        figures.temporal_plot(temporal, figs / "temporal.png")

    log("Figures...")
    figures.degree_distribution(G, figs / "degree_distribution.png")
    figures.community_theme_heatmap(assignment, figs / "communities_vs_themes.png")

    if not args.no_gexf:
        log("Export GEXF...")
        community_of = dict(zip(assignment["set_num"], assignment["community"]))
        nx.set_node_attributes(G, community_of, "community")
        nx.write_gexf(G, results / "lego_sets.gexf")

    with open(results / "summary.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False, default=str)

    c = summary["communities"]
    print(
        "\nRésumé :"
        f"\n  connexe : {summary['connectivity']['is_connected']}"
        f" ({summary['connectivity']['n_components']} composantes)"
        f"\n  diamètre / rayon (plus grande composante) : "
        f"{summary['distances']['diameter']} / {summary['distances']['radius']}"
        f"\n  communautés Louvain : {c['n_communities']}, modularité {c['modularity_louvain']:.3f}"
        f"\n  modularité des thèmes officiels : {c['modularity_root_themes']:.3f}"
        f" (thèmes mélangés : {c['modularity_shuffled_themes']:.3f}, décennies : {c['modularity_decades']:.3f})"
        f"\n  NMI communautés / thèmes : {c['nmi_vs_root_theme']:.3f}"
        f" (sans les {c['n_isolated_singletons']} sets isolés : {c['nmi_vs_root_theme_non_isolated']:.3f},"
        f" ARI {c['ari_vs_root_theme_non_isolated']:.3f})"
        f"\nRésultats dans {results}/ et {figs}/"
    )


if __name__ == "__main__":
    main()
