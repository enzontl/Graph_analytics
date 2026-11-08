"""Paramètres de construction du graphe.

Tous les choix de modélisation sont regroupés ici pour pouvoir les citer
dans le rapport et les faire varier (voir sensitivity.py).
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Params:
    # --- Sélection des sets ---------------------------------------------
    year_min: int = 1990
    year_max: int = 2025
    # Nombre minimal de pièces (colonne `num_parts` de sets.csv).
    min_parts: int = 50
    # Thèmes retirés (comparés au nom du thème ET au nom de son thème racine).
    # Ce sont des produits dérivés ou des sacs de pièces en vrac, qui ne sont
    # pas des « modèles » et relieraient artificiellement tous les sets.
    # À vérifier dans data/raw/themes.csv.gz : les noms exacts peuvent varier.
    exclude_themes: tuple[str, ...] = (
        "Gear",
        "Books",
        "Key Chain",
        "Bulk Bricks",
        "Service Packs",
        "Supplemental",
        "Collectible Minifigures",
    )

    # --- Définition d'une « pièce » -------------------------------------
    # True : une pièce = une forme (part_num), toutes couleurs confondues.
    # False : une pièce = (forme, couleur).
    ignore_color: bool = True
    # Retire les pièces présentes dans plus de cette part des sets
    # (comme les « mots vides » en texte). None = aucune pièce retirée.
    max_part_share: float | None = None
    # True : retire les autocollants (catégorie « Stickers »). Une planche
    # d'autocollants est propre à un set et gonfle les pièces exclusives.
    drop_stickers: bool = False

    # --- Projection sets-sets -------------------------------------------
    # "count"   : nombre de pièces partagées
    # "jaccard" : pièces partagées / pièces de l'un ou l'autre set
    # "idf"     : somme des log(N / nb de sets contenant la pièce) sur les
    #             pièces partagées (une pièce rare compte plus)
    weighting: str = "jaccard"
    # Seuil : une arête est gardée si son poids >= min_weight.
    # Choisi avec sensitivity.py : à 0.1 le graphe réel dépasse 5 M d'arêtes.
    min_weight: float = 0.25
    # Si renseigné, on ne garde pour chaque set que ses top_k arêtes les plus
    # fortes (union sur tous les sets), en plus du seuil.
    top_k: int | None = None
    # Nombre de sets traités à la fois lors de la projection (mémoire).
    chunk_size: int = 2000

    # --- Analyse ---------------------------------------------------------
    seed: int = 42
    # Résolution de Louvain (1.0 = modularité standard).
    resolution: float = 1.0
    # Nombre de sources échantillonnées pour la betweenness (None = exact).
    betweenness_k: int | None = 500
