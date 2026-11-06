"""Chargement des fichiers CSV de Rebrickable."""

from pathlib import Path

import pandas as pd

# Tables utilisées par l'analyse (téléchargements Rebrickable).
TABLES = (
    "themes",
    "sets",
    "inventories",
    "inventory_parts",
    "parts",
    "part_categories",
)

# Colonnes indispensables : on vérifie qu'elles sont présentes au chargement.
REQUIRED_COLUMNS = {
    "themes": {"id", "name", "parent_id"},
    "sets": {"set_num", "name", "year", "theme_id", "num_parts"},
    "inventories": {"id", "version", "set_num"},
    "inventory_parts": {"inventory_id", "part_num", "color_id", "quantity", "is_spare"},
    "parts": {"part_num", "name", "part_cat_id"},
    "part_categories": {"id", "name"},
}


def _find_file(data_dir: Path, name: str) -> Path:
    for suffix in (".csv.gz", ".csv"):
        path = data_dir / f"{name}{suffix}"
        if path.exists():
            return path
    raise FileNotFoundError(
        f"Fichier {name}.csv.gz introuvable dans {data_dir}. "
        "Lancez `python download_data.py` ou téléchargez-le à la main "
        "(voir data/README.md)."
    )


def load_tables(data_dir: str | Path) -> dict[str, pd.DataFrame]:
    """Charge toutes les tables nécessaires depuis `data_dir`."""
    data_dir = Path(data_dir)
    tables = {}
    for name in TABLES:
        df = pd.read_csv(_find_file(data_dir, name), low_memory=False)
        missing = REQUIRED_COLUMNS[name] - set(df.columns)
        if missing:
            raise ValueError(f"{name}: colonnes manquantes {sorted(missing)}")
        tables[name] = df
    return tables
