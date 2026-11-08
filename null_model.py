"""Modèle nul : la cohésion des thèmes est-elle plus forte qu'au hasard ?

On mélange les pièces entre les sets (chaque set garde son nombre de pièces,
chaque pièce son nombre de sets), on refait le graphe une dizaine de fois et
on compare la cohésion réelle de chaque thème à celle de ces graphes nuls.

Au seuil réel, un graphe nul n'a presque aucune arête : on garde donc ses
arêtes les plus fortes, autant que dans le graphe réel (même densité).

    uv run python null_model.py
    uv run python null_model.py --n-null 20
    uv run python null_model.py --demo   # données synthétiques, pour tester

Écrit results/theme_cohesion_null.csv (une ligne par thème) et
results/null_model_runs.csv (une ligne par graphe : réel puis tirages).
"""

import argparse
import tempfile
import time
from dataclasses import replace
from pathlib import Path

from lego_graph.build import prepare
from lego_graph.config import Params
from lego_graph.load import load_tables
from lego_graph.null_model import cohesion_vs_null
from lego_graph.synthetic import write_tables

T0 = time.time()


def log(msg: str) -> None:
    print(f"[{time.time() - T0:6.0f} s] {msg}", flush=True)


def main() -> None:
    d = Params()
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--data-dir", default="data/raw")
    p.add_argument("--results-dir", default="results")
    p.add_argument("--demo", action="store_true", help="utiliser des données synthétiques")
    p.add_argument("--n-null", type=int, default=10, help="nombre de graphes nuls")
    p.add_argument("--rounds", type=int, default=20, help="tours de mélange curveball par graphe nul")
    p.add_argument("--min-weight", type=float, default=d.min_weight)
    p.add_argument("--min-sets", type=int, default=30, help="taille minimale d'un thème")
    p.add_argument("--drop-stickers", action="store_true", help="retirer les autocollants")
    p.add_argument("--seed", type=int, default=d.seed)
    args = p.parse_args()

    params = replace(d, min_weight=args.min_weight, drop_stickers=args.drop_stickers, seed=args.seed)
    data_dir = args.data_dir
    min_sets = args.min_sets
    if args.demo:  # les sets synthétiques sont petits, peu nombreux et commencent en 1985
        data_dir = write_tables(Path(tempfile.mkdtemp()) / "demo")
        params = replace(params, year_min=1980, min_parts=1, min_weight=0.05)
        min_sets = 5

    log("Chargement des tables...")
    sets, pairs, bip = prepare(load_tables(data_dir), params)
    log(f"{len(bip.sets)} sets, {len(bip.parts)} pièces, {len(pairs)} couples set-pièce")

    log(f"Graphe réel et {args.n_null} graphes nuls...")
    themes, runs = cohesion_vs_null(
        sets, pairs, bip, params, n_null=args.n_null, n_rounds=args.rounds, min_sets=min_sets, log=log
    )

    out = Path(args.results_dir)
    out.mkdir(parents=True, exist_ok=True)
    themes.to_csv(out / "theme_cohesion_null.csv", index=False)
    runs.to_csv(out / "null_model_runs.csv", index=False)

    real, null = runs.iloc[0], runs.iloc[1:]
    above = themes["n_null_ge_real"] == 0
    print(
        "\nRésumé :"
        f"\n  arêtes au seuil {params.min_weight} : réel {real['n_edges_at_min_weight']},"
        f" hasard {null['n_edges_at_min_weight'].mean():.0f} en moyenne"
        f"\n  modularité des thèmes : réel {real['modularity_root_themes']:.3f},"
        f" hasard {null['modularity_root_themes'].mean():.3f} ± {null['modularity_root_themes'].std():.3f}"
        f"\n  thèmes plus cohésifs que dans tous les tirages : {above.sum()} sur {len(themes)}"
        f"\n  rapport cohésion réelle / hasard : médiane {themes['ratio_to_null'].median():.1f}"
        f"\nRésultats dans {out}/theme_cohesion_null.csv et {out}/null_model_runs.csv"
    )


if __name__ == "__main__":
    main()
