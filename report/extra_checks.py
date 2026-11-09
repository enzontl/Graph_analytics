"""Numbers of the report that are not in results/.

1. Size of the bipartite graph.
2. Modularity of the decade partition against the theme partition at the
   thresholds 0.25, 0.30 and 0.35.
3. Share of theme-exclusive parts by period under other modelling choices
   (minimum set size, colours, excluded themes, most frequent parts removed).

    uv run python report/extra_checks.py   # about 2 min
"""

import sys
from collections import defaultdict
from dataclasses import replace
from pathlib import Path

import networkx as nx
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from lego_graph.analysis import exclusive_parts  # noqa: E402
from lego_graph.build import graph_from_edges, prepare, project  # noqa: E402
from lego_graph.config import Params  # noqa: E402
from lego_graph.load import load_tables  # noqa: E402
from run_analysis import DEFAULT_PERIODS  # noqa: E402


def themes_vs_decades(tables, params: Params) -> None:
    sets, pairs, bip = prepare(tables, params)
    print(f"Rebrickable sets: {len(tables['sets'])}, selected sets: {len(sets)}, "
          f"root themes: {sets['root_theme'].nunique()}")
    print(f"Bipartite graph: {pairs['part'].nunique()} parts, {len(pairs)} set-part edges\n")

    edges = project(bip, params)  # every pair with weight >= 0.25
    for threshold in (0.25, 0.30, 0.35):
        p = replace(params, min_weight=threshold)
        G = graph_from_edges(sets, pairs, bip, edges[edges["weight"] >= threshold], p)
        themes, decades = defaultdict(set), defaultdict(set)
        for n, d in G.nodes(data=True):
            themes[d["root_theme"]].add(n)
            decades[d["year"] // 10].add(n)
        q_themes = nx.community.modularity(G, themes.values(), weight="weight")
        q_decades = nx.community.modularity(G, decades.values(), weight="weight")
        print(f"threshold {threshold:.2f}: {G.number_of_edges()} edges, "
              f"modularity themes {q_themes:.3f}, decades {q_decades:.3f}")


def exclusive_share_by_period(tables, params: Params) -> None:
    variants = {
        "default": params,
        "min 20 parts": replace(params, min_parts=20),
        "min 100 parts": replace(params, min_parts=100),
        "part = shape + colour": replace(params, ignore_color=False),
        "no theme excluded": replace(params, exclude_themes=()),
        "parts in > 20% of sets removed": replace(params, max_part_share=0.2),
    }
    rows = {}
    for name, p in variants.items():
        sets, pairs, _ = prepare(tables, p)
        row = {}
        for start, end in DEFAULT_PERIODS:
            period = sets.loc[sets["year"].between(start, end), "set_num"]
            row[f"{start}-{end}"] = exclusive_parts(pairs, sets, period)["exclusive_share"].mean()
        rows[name] = row
    print("\nShare of theme-exclusive parts (mean over the sets of the period):")
    print((100 * pd.DataFrame(rows).T).round(1).to_string())


def main() -> None:
    tables = load_tables(ROOT / "data" / "raw")
    params = Params()
    themes_vs_decades(tables, params)
    exclusive_share_by_period(tables, params)


if __name__ == "__main__":
    main()
