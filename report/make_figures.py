"""Figures of the written report, in English, drawn from the CSV files in results/.

The analysis scripts (run_analysis.py, null_model.py, temporal_robustness.py,
run_extensions.py) must have been run first. Nothing is recomputed here except
the layout of the theme graph.

    uv run python report/make_figures.py

Writes PDF files to report/figures/ and copies the two Gephi images there.
"""

import itertools
import shutil
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import networkx as nx  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))  # to import lego_graph when run as report/make_figures.py

from lego_graph.extensions import theme_backbone  # noqa: E402

RESULTS = ROOT / "results"
OUT = ROOT / "report" / "figures"

WIDTH = 6.3  # \textwidth of the report (A4, 2.5 cm margins), in inches
BLUE, ORANGE, AQUA = "#2a78d6", "#eb6834", "#1baf7a"
INK, MUTED, GRID = "#0b0b0b", "#52514e", "#d9d8d4"
THRESHOLD = 0.25

# Franchises licensed from another company (used only to colour Figure 5).
LICENSED = {"Star Wars", "Harry Potter", "Disney", "Super Heroes DC", "Super Heroes Marvel",
            "Jurassic World", "Minecraft", "Super Mario"}

plt.rcParams.update({
    "font.size": 7.5, "axes.titlesize": 8, "axes.labelsize": 7.5, "legend.fontsize": 7,
    "xtick.labelsize": 7, "ytick.labelsize": 7,
    "axes.edgecolor": MUTED, "axes.labelcolor": INK, "xtick.color": MUTED, "ytick.color": MUTED,
    "axes.spines.top": False, "axes.spines.right": False,
    "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.5,
    "lines.linewidth": 1.5, "lines.markersize": 4,
    "legend.frameon": False, "savefig.bbox": "tight", "pdf.fonttype": 42,
})


def save(fig, name: str) -> None:
    fig.savefig(OUT / name)
    plt.close(fig)
    print(f"  {name}")


def mark_threshold(ax) -> None:
    ax.axvline(THRESHOLD, color=MUTED, linestyle=":", linewidth=1)


def sensitivity() -> None:
    """Edges, components and modularity as a function of the Jaccard threshold."""
    df = pd.read_csv(RESULTS / "sensitivity.csv")
    df = df[df["weighting"] == "jaccard"].sort_values("min_weight")
    x = df["min_weight"]
    fig, axes = plt.subplots(1, 3, figsize=(WIDTH, 2.1))

    ax = axes[0]
    ax.plot(x, df["n_edges"], marker="o", color=BLUE)
    ax.set_yscale("log")
    ax.set_title("(a) Number of edges")

    ax = axes[1]
    # Two series per panel: labelled directly next to the lines.
    ax.plot(x, df["largest_component_share"], marker="o", color=BLUE)
    ax.plot(x, df["n_isolated"] / df["n_nodes"], marker="o", color=ORANGE)
    ax.text(0.155, 0.6, "largest\ncomponent", color=INK, fontsize=6.5, va="center")
    ax.text(0.405, 0.78, "isolated", color=INK, fontsize=6.5, ha="right")
    ax.set_ylim(0, 1)
    ax.set_title("(b) Share of the 9,062 sets")

    ax = axes[2]
    ax.plot(x, df["modularity_louvain"], marker="o", color=BLUE)
    ax.plot(x, df["modularity_root_themes"], marker="o", color=ORANGE)
    ax.text(0.405, 0.94, "Louvain", color=INK, fontsize=6.5, ha="right")
    ax.text(0.405, 0.37, "root themes", color=INK, fontsize=6.5, ha="right")
    ax.set_ylim(0, 1)
    ax.set_title("(c) Modularity")

    for ax in axes:
        mark_threshold(ax)
        ax.set_xlabel("Jaccard threshold")
        ax.set_xticks([0.15, 0.25, 0.35])
    fig.tight_layout(w_pad=1.0)
    save(fig, "sensitivity.pdf")


def degree_and_parts() -> None:
    """(a) Degree distribution of the set graph, (b) number of themes per part."""
    cent = pd.read_csv(RESULTS / "centralities.csv")
    parts = pd.read_csv(RESULTS / "parts_universality.csv")
    fig, axes = plt.subplots(1, 2, figsize=(WIDTH, 2.3))

    ax = axes[0]
    degrees = np.sort(cent.loc[cent["degree"] > 0, "degree"].to_numpy())
    ccdf = 1.0 - np.arange(len(degrees)) / len(degrees)
    ax.loglog(degrees, ccdf, marker=".", markersize=2.5, linestyle="none", color=BLUE)
    ax.set_xlabel("degree $k$")
    ax.set_ylabel(r"$P(\mathrm{degree} \geq k)$")
    ax.set_title("(a) Degree distribution (non-isolated sets)")

    ax = axes[1]
    counts = parts["n_root_themes"].value_counts().sort_index()
    ax.bar(counts.index, counts.to_numpy(), width=1.0, color=BLUE, linewidth=0)
    ax.set_yscale("log")
    ax.set_xlabel("number of root themes using the part")
    ax.set_ylabel("number of parts")
    ax.set_title("(b) Specialised and universal parts")
    ax.grid(axis="x", visible=False)
    ax.set_axisbelow(True)
    fig.tight_layout(w_pad=1.5)
    save(fig, "degree_parts.pdf")


def communities_heatmap(top: int = 12) -> None:
    """Theme composition of the largest Louvain communities."""
    a = pd.read_csv(RESULTS / "communities_assignment.csv")
    sizes = a["community"].value_counts()
    top_comms = sizes.head(top).index
    top_themes = a["root_theme"].value_counts().head(top).index
    sub = a[a["community"].isin(top_comms)]
    table = pd.crosstab(sub["community"], sub["root_theme"], normalize="index")
    table = table.reindex(index=top_comms, columns=top_themes, fill_value=0)

    fig, ax = plt.subplots(figsize=(WIDTH, 3.0))
    im = ax.imshow(table.to_numpy(), aspect="auto", cmap="Blues", vmin=0, vmax=1)
    ax.grid(False)
    ax.set_xticks(range(len(table.columns)), table.columns, rotation=40, ha="right")
    ax.set_yticks(range(len(table.index)), [f"C{c} ({sizes[c]:,} sets)" for c in table.index])
    ax.set_xlabel("root theme (12 largest)")
    ax.set_ylabel("Louvain community (12 largest)")
    fig.colorbar(im, ax=ax, label="share of the community's sets", shrink=0.9)
    fig.tight_layout()
    save(fig, "communities_heatmap.pdf")


def cohesion_vs_null() -> None:
    """Real cohesion of each theme against its mean cohesion in the null graphs."""
    df = pd.read_csv(RESULTS / "theme_cohesion_null.csv")
    lic = df["root_theme"].isin(LICENSED)
    fig, ax = plt.subplots(figsize=(WIDTH, 3.6))
    lim = (1.5e-3, 1.0)
    xs = np.array(lim)
    ax.plot(xs, xs, color=MUTED, linewidth=1, label="real = null")
    ax.plot(xs, 10 * xs, color=MUTED, linewidth=1, linestyle="--", label="real = 10 × null")
    for mask, color, label in ((~lic, BLUE, "other themes"), (lic, ORANGE, "licensed franchises")):
        ax.scatter(df.loc[mask, "null_mean"], df.loc[mask, "internal_share"], s=6 + df.loc[mask, "n_sets"] / 6,
                   color=color, edgecolor="white", linewidth=0.5, label=label, zorder=3)
    # Label position in data coordinates, with a thin leader line to the point.
    text_at = {
        "Duplo": (0.2, 0.95), "Technic": (0.2, 0.72), "Belville": (0.0045, 1.12),
        "Star Wars": (0.2, 0.47), "City": (0.2, 0.34), "Friends": (0.2, 0.25), "Ninjago": (0.2, 0.18),
        "Icons": (0.2, 0.125), "Harry Potter": (0.2, 0.095), "LEGO Ideas and CUUSOO": (0.2, 0.072),
        "Disney": (0.2, 0.055), "Super Heroes DC": (0.2, 0.042), "Jurassic World": (0.2, 0.031),
    }
    for _, r in df[df["root_theme"].isin(text_at)].iterrows():
        ax.annotate(r["root_theme"].replace(" and CUUSOO", ""), (r["null_mean"], r["internal_share"]),
                    xytext=text_at[r["root_theme"]], textcoords="data", fontsize=6.5, color=INK,
                    ha="center" if r["root_theme"] == "Belville" else "left", va="center",
                    arrowprops=dict(arrowstyle="-", color=MUTED, linewidth=0.4, shrinkA=1, shrinkB=2))
    ax.set_xscale("log")
    ax.set_yscale("log")
    ticks = [0.002, 0.005, 0.01, 0.02, 0.05, 0.1, 0.2, 0.5, 1]
    ax.set_xticks(ticks, [f"{t:g}" for t in ticks])
    ax.set_yticks(ticks[3:], [f"{t:g}" for t in ticks[3:]])
    ax.minorticks_off()
    ax.set_xlim(*lim)
    ax.set_ylim(1.8e-2, 1.3)
    ax.set_xlabel("cohesion in the null graphs (mean of 10 draws)")
    ax.set_ylabel("real cohesion (internal share)")
    fig.legend(*ax.get_legend_handles_labels(), loc="lower center", ncol=4, bbox_to_anchor=(0.5, -0.04))
    fig.tight_layout(rect=(0, 0.06, 1, 1))
    save(fig, "cohesion_null.pdf")


def repel_labels(fig, ax, texts, steps: int = 300) -> None:
    """Push overlapping labels apart vertically until no two boxes overlap."""
    renderer = fig.canvas.get_renderer()
    items = list(texts)
    for _ in range(steps):
        fig.canvas.draw()
        px_per_y = ax.transData.transform((0, 1))[1] - ax.transData.transform((0, 0))[1]
        boxes = [t.get_window_extent(renderer).expanded(1.03, 1.15) for t in items]
        moved = False
        for i, j in itertools.combinations(range(len(items)), 2):
            a, b = boxes[i], boxes[j]
            if not a.overlaps(b):
                continue
            shift = (min(a.y1, b.y1) - max(a.y0, b.y0)) / 2 + 0.5  # pixels
            up, down = (items[i], items[j]) if a.y0 + a.y1 >= b.y0 + b.y1 else (items[j], items[i])
            for t, sign in ((up, 1), (down, -1)):
                x, y = t.get_position()
                t.set_position((x, y + sign * shift / px_per_y))
            moved = True
        if not moved:
            return


def theme_graph(min_sets: int = 30, per_node: int = 3, k: float = 5.0, seed: int = 71) -> None:
    """Backbone of the theme graph (same selection as run_extensions.py).

    The spring layout is a little more spread out than in run_extensions.py
    (k = 5 instead of 2.6, another seed) and the few labels that still
    overlap are pushed apart vertically, so that they stay readable at the
    width of the report.
    """
    T = nx.read_gexf(RESULTS / "theme_graph.gexf")
    B = theme_backbone(T, min_sets=min_sets, per_node=per_node)
    B.remove_nodes_from(list(nx.isolates(B)))
    for _, _, d in B.edges(data=True):
        d["layout_weight"] = float(np.log1p(d["lift"]))
    pos = nx.spring_layout(B, weight="layout_weight", k=k / np.sqrt(B.number_of_nodes()),
                           iterations=300, seed=seed)

    sizes = np.array([B.nodes[t]["n_sets"] for t in B.nodes])
    colors = np.array([B.nodes[t]["internal_share"] for t in B.nodes])
    weights = np.array([d["weight"] for _, _, d in B.edges(data=True)])
    fig, ax = plt.subplots(figsize=(WIDTH, 5.2))
    ax.grid(False)
    nx.draw_networkx_edges(B, pos, ax=ax, width=0.3 + 3 * np.sqrt(weights / weights.max()),
                           edge_color="#9a9993", alpha=0.6)
    nodes = nx.draw_networkx_nodes(B, pos, ax=ax, node_size=8 + 0.35 * sizes, node_color=colors,
                                   cmap="Blues", vmin=0, vmax=1, edgecolors=MUTED, linewidths=0.4)
    label_pos = {t: (x, y + 0.035) for t, (x, y) in pos.items()}
    short = {"LEGO Ideas and CUUSOO": "LEGO Ideas", "Educational and Dacta": "Educational",
             "Chinese Traditional Festivals": "Chinese Trad. Festivals",
             "BrickLink Designer Program": "BrickLink Designer"}
    labels = {t: short.get(t, t) for t in B.nodes}
    texts = nx.draw_networkx_labels(B, label_pos, labels=labels, ax=ax, font_size=5.5, font_color=INK,
                                    bbox=dict(facecolor="white", edgecolor="none", alpha=0.7, pad=0.3))
    fig.colorbar(nodes, ax=ax, orientation="horizontal", shrink=0.4, pad=0.01, aspect=30,
                 label="cohesion of the theme (internal share)")
    ax.axis("off")
    fig.tight_layout()
    repel_labels(fig, ax, texts.values())
    save(fig, "theme_graph.pdf")


def temporal() -> None:
    """Evolution by period: modularity at two thresholds, exclusive parts with and without stickers."""
    df = pd.read_csv(RESULTS / "temporal_robustness.csv")
    periods = list(dict.fromkeys(df["period"]))
    x = np.arange(len(periods))
    base = df[(df["min_weight"] == THRESHOLD) & ~df["drop_stickers"]]
    no_stk = df[(df["min_weight"] == THRESHOLD) & df["drop_stickers"]]
    high = df[(df["min_weight"] == 0.35) & ~df["drop_stickers"]]
    fig, axes = plt.subplots(2, 2, figsize=(WIDTH, 3.6), sharex=True)

    ax = axes[0, 0]
    ax.plot(x, base["modularity_root_themes"], marker="o", color=BLUE, label="threshold 0.25")
    ax.plot(x, high["modularity_root_themes"], marker="o", color=ORANGE, label="threshold 0.35")
    ax.set_ylim(0, 1)
    ax.set_title("(a) Modularity of the theme partition")
    ax.legend(loc="lower left")

    ax = axes[0, 1]
    ax.plot(x, 100 * base["exclusive_part_share"], marker="o", color=BLUE, label="stickers kept")
    ax.plot(x, 100 * no_stk["exclusive_part_share"], marker="o", color=AQUA, label="stickers removed")
    ax.set_ylim(0, 10)
    ax.set_title("(b) Theme-exclusive parts (% of a set)")
    ax.legend(loc="lower left")

    ax = axes[1, 0]
    ax.plot(x, base["exclusive_parts_per_set"], marker="o", color=BLUE, label="stickers kept")
    ax.plot(x, no_stk["exclusive_parts_per_set"], marker="o", color=AQUA, label="stickers removed")
    ax.set_ylim(0, 5)
    ax.set_title("(c) Theme-exclusive parts per set")
    ax.legend(loc="lower left")

    ax = axes[1, 1]
    ax.plot(x, base["parts_per_set"], marker="o", color=BLUE)
    ax.set_ylim(0, 110)
    ax.set_title("(d) Distinct parts per set")

    for ax in axes[1]:
        ax.set_xticks(x, periods)
    fig.tight_layout(h_pad=1.0, w_pad=1.5)
    save(fig, "temporal.pdf")


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    print(f"Figures in {OUT}:")
    sensitivity()
    degree_and_parts()
    communities_heatmap()
    cohesion_vs_null()
    theme_graph()
    temporal()
    for name in ("gephi_communities.png", "gephi_root_themes.png"):
        shutil.copy(ROOT / "figures" / name, OUT / name)
        print(f"  {name} (copied)")


if __name__ == "__main__":
    main()
