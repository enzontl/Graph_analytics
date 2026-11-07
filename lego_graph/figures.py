"""Figures pour le rapport."""

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import networkx as nx  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402


def degree_distribution(G: nx.Graph, path: Path) -> None:
    """Distribution cumulée complémentaire des degrés (échelle log-log)."""
    degrees = np.sort(np.array([d for _, d in G.degree() if d > 0]))
    if len(degrees) == 0:
        return
    ccdf = 1.0 - np.arange(len(degrees)) / len(degrees)
    fig, ax = plt.subplots(figsize=(5, 4))
    ax.loglog(degrees, ccdf, marker=".", linestyle="none")
    ax.set_xlabel("Degré k")
    ax.set_ylabel("P(degré ≥ k)")
    ax.set_title("Distribution des degrés")
    fig.tight_layout()
    fig.savefig(path, dpi=200)
    plt.close(fig)


def community_theme_heatmap(assignment: pd.DataFrame, path: Path, top: int = 12) -> None:
    """Croisement communautés détectées x thèmes officiels (part de chaque communauté)."""
    top_comms = assignment["community"].value_counts().head(top).index
    top_themes = assignment["root_theme"].value_counts().head(top).index
    sub = assignment[assignment["community"].isin(top_comms)]
    table = pd.crosstab(sub["community"], sub["root_theme"], normalize="index")
    table = table.reindex(index=top_comms, columns=top_themes, fill_value=0)

    fig, ax = plt.subplots(figsize=(8, 5))
    im = ax.imshow(table.to_numpy(), aspect="auto", cmap="Blues", vmin=0, vmax=1)
    ax.set_xticks(range(len(table.columns)), table.columns, rotation=60, ha="right")
    ax.set_yticks(range(len(table.index)), [f"C{c}" for c in table.index])
    ax.set_xlabel("Thème officiel (racine)")
    ax.set_ylabel("Communauté détectée")
    fig.colorbar(im, ax=ax, label="Part des sets de la communauté")
    fig.tight_layout()
    fig.savefig(path, dpi=200)
    plt.close(fig)


def part_theme_distribution(universal: pd.DataFrame, path: Path) -> None:
    """Nombre de pièces selon le nombre de thèmes racines où elles apparaissent."""
    counts = universal["n_root_themes"].value_counts().sort_index()
    fig, ax = plt.subplots(figsize=(6, 4))
    ax.bar(counts.index, counts.to_numpy(), width=1.0)
    ax.set_yscale("log")
    ax.set_xlabel("Nombre de thèmes racines où la pièce apparaît")
    ax.set_ylabel("Nombre de pièces (échelle log)")
    ax.set_title("Pièces spécialisées et pièces universelles")
    fig.tight_layout()
    fig.savefig(path, dpi=200)
    plt.close(fig)


def temporal_plot(df: pd.DataFrame, path: Path) -> None:
    if df.empty:
        return
    fig, ax = plt.subplots(figsize=(6, 4))
    for col, label in [
        ("modularity_root_themes", "Modularité des thèmes officiels"),
        ("modularity_louvain", "Modularité Louvain"),
        ("exclusive_part_share", "Part de pièces exclusives à un thème"),
    ]:
        ax.plot(df["period"], df[col], marker="o", label=label)
    ax.set_xlabel("Période")
    ax.set_ylim(0, 1)
    ax.legend()
    ax.set_title("Spécialisation des thèmes dans le temps")
    plt.setp(ax.get_xticklabels(), rotation=30, ha="right")
    fig.tight_layout()
    fig.savefig(path, dpi=200)
    plt.close(fig)
