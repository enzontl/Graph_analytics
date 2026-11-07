"""Petit jeu de données synthétique au format Rebrickable.

Sert uniquement aux tests et à vérifier que le pipeline tourne sans les
vraies données. Les résultats sur ces données n'ont aucun sens réel.
"""

from pathlib import Path

import numpy as np
import pandas as pd


def make_tables(seed: int = 0) -> dict[str, pd.DataFrame]:
    rng = np.random.default_rng(seed)

    themes = pd.DataFrame(
        {
            "id": [1, 2, 3, 4, 5, 6, 7],
            "name": ["City", "Police", "Star Wars", "Technic", "Duplo", "Gear", "Friends"],
            "parent_id": [None, 1, None, None, None, None, None],
        }
    )

    common = [f"c{i}" for i in range(10)]  # briques de base (System)
    specific = {t: [f"{t}_{i}" for i in range(15)] for t in ("city", "sw", "tech", "duplo", "fr")}
    root_of_theme = {1: "city", 2: "city", 3: "sw", 4: "tech", 5: "duplo", 6: "city", 7: "fr"}

    sets, inventories, inventory_parts = [], [], []
    inv_id = 0
    for theme_id in themes["id"]:
        key = root_of_theme[theme_id]
        for k in range(20):
            set_num = f"{theme_id}{k:03d}-1"
            year = int(rng.integers(1985, 2025))
            if key == "duplo":
                parts = list(rng.choice(specific["duplo"], size=8, replace=False))
            elif key == "tech":
                parts = list(rng.choice(specific["tech"], size=8, replace=False)) + [common[0]]
            else:
                parts = list(rng.choice(common, size=3, replace=False)) + list(
                    rng.choice(specific[key], size=6, replace=False)
                )
            inv_id += 1
            inventories.append({"id": inv_id, "version": 1, "set_num": set_num})
            quantities = rng.integers(5, 12, size=len(parts))
            for part, q in zip(parts, quantities):
                inventory_parts.append(
                    {
                        "inventory_id": inv_id,
                        "part_num": part,
                        "color_id": int(rng.integers(0, 5)),
                        "quantity": int(q),
                        "is_spare": "f",
                        "img_url": "",
                    }
                )
            sets.append(
                {
                    "set_num": set_num,
                    "name": f"Set {set_num}",
                    "year": year,
                    "theme_id": theme_id,
                    "num_parts": int(quantities.sum()),
                    "img_url": "",
                }
            )

    # Une pièce de rechange Duplo dans un set City : doit être ignorée.
    inventory_parts.append(
        {"inventory_id": 1, "part_num": "duplo_0", "color_id": 0, "quantity": 1,
         "is_spare": "t", "img_url": ""}
    )
    # Une deuxième version d'inventaire pour le premier set City : doit être ignorée.
    inv_id += 1
    inventories.append({"id": inv_id, "version": 2, "set_num": "1000-1"})
    inventory_parts.append(
        {"inventory_id": inv_id, "part_num": "duplo_1", "color_id": 0, "quantity": 1,
         "is_spare": "f", "img_url": ""}
    )

    all_parts = common + [p for ps in specific.values() for p in ps]
    parts = pd.DataFrame(
        {"part_num": all_parts, "name": [f"Pièce {p}" for p in all_parts], "part_cat_id": 1,
         "part_material": "Plastic"}
    )
    part_categories = pd.DataFrame({"id": [1], "name": ["Bricks"]})

    return {
        "themes": themes,
        "sets": pd.DataFrame(sets),
        "inventories": pd.DataFrame(inventories),
        "inventory_parts": pd.DataFrame(inventory_parts),
        "parts": parts,
        "part_categories": part_categories,
    }


def write_tables(directory: str | Path, seed: int = 0) -> Path:
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    for name, df in make_tables(seed).items():
        df.to_csv(directory / f"{name}.csv.gz", index=False)
    return directory
