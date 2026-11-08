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


def _fr(x: float) -> str:
    """0.25 -> « 0,25 »."""
    return f"{x:g}".replace(".", ",")


def temporal_plot(df: pd.DataFrame, path: Path) -> None:
    """Évolution par période, en trois panneaux à échelles séparées.

    1. modularité des thèmes officiels (trait plein) et de Louvain (tirets),
       une couleur par seuil de projection ;
    2. part de pièces exclusives à un thème (%), avec et sans autocollants ;
    3. nombre moyen de pièces exclusives par set, avec et sans autocollants.

    `df` vient de `analysis.temporal` (une seule configuration) ou de
    temporal_robustness.py (plusieurs seuils, avec et sans autocollants).
    """
    if df.empty:
        return
    fig, axes = plt.subplots(1, 3, figsize=(13, 4))

    # 1. Modularité : dépend du seuil. Avec autocollants si disponible.
    ax = axes[0]
    ref = df[~df["drop_stickers"]] if (~df["drop_stickers"]).any() else df
    for k, (threshold, g) in enumerate(ref.groupby("min_weight", sort=True)):
        ax.plot(g["period"], g["modularity_root_themes"], marker="o", color=f"C{k}",
                label=f"Thèmes, seuil {_fr(threshold)}")
        ax.plot(g["period"], g["modularity_louvain"], marker="o", linestyle="--", color=f"C{k}",
                label=f"Louvain, seuil {_fr(threshold)}")
    ax.set_ylim(0, 1)
    ax.set_ylabel("Modularité")
    ax.set_title("Structure du graphe")
    ax.legend(fontsize=8)

    # 2 et 3. Pièces exclusives : ne dépendent pas du seuil, une seule courbe par réglage.
    first = df[df["min_weight"] == df["min_weight"].iloc[0]]
    for k, (drop, g) in enumerate(first.groupby("drop_stickers", sort=True)):
        label = "sans autocollants" if drop else "avec autocollants"
        style = dict(marker="o", color=f"C{k + 4}", label=label)
        axes[1].plot(g["period"], 100 * g["exclusive_part_share"], **style)
        axes[2].plot(g["period"], g["exclusive_parts_per_set"], **style)
    axes[1].set_ylabel("% des pièces du set")
    axes[1].set_title("Part de pièces exclusives au thème")
    axes[2].set_ylabel("Pièces par set (moyenne)")
    axes[2].set_title("Nombre de pièces exclusives au thème")
    for ax in axes[1:]:
        ax.set_ylim(bottom=0)
        ax.legend(fontsize=8)

    for ax in axes:
        ax.set_xlabel("Période")
        plt.setp(ax.get_xticklabels(), rotation=30, ha="right")
    fig.tight_layout()
    fig.savefig(path, dpi=200)
    plt.close(fig)
