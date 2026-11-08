"""Robustesse de l'évolution par période : seuil de la projection et autocollants.

Relance analysis.temporal() pour chaque seuil (0,25 et 0,35 par défaut),
avec puis sans les autocollants (catégorie « Stickers » de Rebrickable).
La part de pièces exclusives ne dépend pas du seuil ; la modularité, si.

    uv run python temporal_robustness.py
    uv run python temporal_robustness.py --thresholds 0.25 0.3 0.35
    uv run python temporal_robustness.py --demo   # données synthétiques, pour tester

Écrit results/temporal_robustness.csv et figures/temporal_robustness.png.
"""

import argparse
import tempfile
import time
from dataclasses import replace
from pathlib import Path

import pandas as pd

from lego_graph import analysis, figures
from lego_graph.config import Params
from lego_graph.load import load_tables
from lego_graph.synthetic import write_tables
from run_analysis import DEFAULT_PERIODS

T0 = time.time()


def log(msg: str) -> None:
    print(f"[{time.time() - T0:6.0f} s] {msg}", flush=True)


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--data-dir", default="data/raw")
    p.add_argument("--results-dir", default="results")
    p.add_argument("--figures-dir", default="figures")
    p.add_argument("--demo", action="store_true", help="utiliser des données synthétiques")
    p.add_argument("--thresholds", type=float, nargs="+", default=[0.25, 0.35])
    args = p.parse_args()

    base = Params()
    data_dir = args.data_dir
    thresholds = args.thresholds
    periods = DEFAULT_PERIODS
    if args.demo:  # les sets synthétiques sont petits et commencent en 1985
        data_dir = write_tables(Path(tempfile.mkdtemp()) / "demo")
        base = replace(base, year_min=1980, min_parts=1)
        thresholds = [0.05, 0.1]
        periods = [(1985, 1999), (2000, 2014), (2015, 2025)]

    log("Chargement des tables...")
    tables = load_tables(data_dir)

    frames = []
    for threshold in thresholds:
        for drop in (False, True):
            params = replace(base, min_weight=threshold, drop_stickers=drop)
            log(f"Seuil {threshold}, {'sans' if drop else 'avec'} autocollants...")
            frames.append(analysis.temporal(tables, params, periods))
    df = pd.concat(frames, ignore_index=True)
    first = ["period", "min_weight", "drop_stickers"]
    df = df[first + [c for c in df.columns if c not in first]]

    results = Path(args.results_dir)
    figs = Path(args.figures_dir)
    results.mkdir(parents=True, exist_ok=True)
    figs.mkdir(parents=True, exist_ok=True)
    df.to_csv(results / "temporal_robustness.csv", index=False)
    figures.temporal_plot(df, figs / "temporal_robustness.png")

    cols = ["period", "min_weight", "drop_stickers", "modularity_root_themes",
            "exclusive_part_share", "exclusive_parts_per_set", "parts_per_set"]
    print("\n" + df[cols].round(3).to_string(index=False))
    print(f"\nRésultats dans {results}/temporal_robustness.csv et {figs}/temporal_robustness.png")


if __name__ == "__main__":
    main()
