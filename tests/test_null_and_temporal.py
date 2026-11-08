"""Tests du modèle nul (curveball) et de la robustesse par période."""

from dataclasses import replace

import numpy as np
import pandas as pd
import pytest

from lego_graph import analysis
from lego_graph.build import prepare, set_part_pairs, select_sets
from lego_graph.config import Params
from lego_graph.null_model import cohesion_vs_null, curveball, share_unchanged
from lego_graph.synthetic import make_tables


@pytest.fixture(scope="module")
def tables():
    return make_tables(seed=0)


@pytest.fixture(scope="module")
def params():
    return Params(year_min=1980, year_max=2030, min_parts=1, min_weight=0.05, betweenness_k=None)


@pytest.fixture(scope="module")
def tables_with_stickers(tables):
    """Les tables synthétiques, plus une planche d'autocollants dans le premier set City."""
    t = {name: df.copy() for name, df in tables.items()}
    t["part_categories"] = pd.concat(
        [t["part_categories"], pd.DataFrame({"id": [58], "name": ["Stickers"]})], ignore_index=True
    )
    t["parts"] = pd.concat(
        [t["parts"], pd.DataFrame({"part_num": ["stk1"], "name": ["Sticker Sheet"], "part_cat_id": [58],
                                   "part_material": ["Plastic"]})],
        ignore_index=True,
    )
    t["inventory_parts"] = pd.concat(
        [t["inventory_parts"], pd.DataFrame({"inventory_id": [1], "part_num": ["stk1"], "color_id": [0],
                                             "quantity": [1], "is_spare": ["f"], "img_url": [""]})],
        ignore_index=True,
    )
    return t


def test_curveball_keeps_set_sizes_and_part_frequencies(tables, params):
    _, _, bip = prepare(tables, params)
    null = curveball(bip, n_rounds=10, seed=1)
    assert (np.asarray(null.matrix.sum(axis=1)) == np.asarray(bip.matrix.sum(axis=1))).all()
    assert (np.asarray(null.matrix.sum(axis=0)) == np.asarray(bip.matrix.sum(axis=0))).all()
    assert null.matrix.max() == 1  # pas de couple (set, pièce) en double
    assert share_unchanged(bip, null) < 0.5  # la matrice a bien été mélangée


def test_curveball_is_reproducible(tables, params):
    _, _, bip = prepare(tables, params)
    a = curveball(bip, n_rounds=5, seed=3).matrix
    b = curveball(bip, n_rounds=5, seed=3).matrix
    assert (a != b).nnz == 0


def test_cohesion_vs_null(tables, params):
    sets, pairs, bip = prepare(tables, params)
    themes, runs = cohesion_vs_null(sets, pairs, bip, params, n_null=3, n_rounds=10, min_sets=5,
                                    log=lambda msg: None)
    assert len(runs) == 4 and runs["run"].iloc[0] == "réel"
    # Même densité que le graphe réel.
    assert (runs["n_edges"] == runs["n_edges"].iloc[0]).all()
    themes = themes.set_index("root_theme")
    # Les thèmes synthétiques ont leurs propres pièces : bien plus cohésifs qu'au hasard.
    assert (themes["internal_share"] > themes["null_max"]).all()
    assert (themes["n_null_ge_real"] == 0).all()
    assert themes["p_value"].eq(1 / 4).all()
    assert runs["modularity_root_themes"].iloc[0] > runs["modularity_root_themes"].iloc[1:].max()


def test_drop_stickers(tables_with_stickers, params):
    sets = select_sets(tables_with_stickers, params)
    kept = set_part_pairs(tables_with_stickers, sets, params)
    dropped = set_part_pairs(tables_with_stickers, sets, replace(params, drop_stickers=True))
    assert "stk1" in set(kept["part"])
    assert "stk1" not in set(dropped["part"])
    assert len(kept) == len(dropped) + 1


def test_exclusive_parts_counts(tables, params):
    sets, pairs, _ = prepare(tables, params)
    excl = analysis.exclusive_parts(pairs, sets)
    assert (excl["n_exclusive"] <= excl["n_parts"]).all()
    assert excl["exclusive_share"].mean() == pytest.approx(analysis.exclusive_part_share(pairs, sets))
    # Les sets Duplo n'ont que des pièces Duplo, toutes exclusives.
    duplo = sets.loc[sets["root_theme"] == "Duplo", "set_num"]
    assert excl[excl["set_num"].isin(duplo)]["exclusive_share"].eq(1).all()


def test_temporal_has_new_columns(tables_with_stickers, params):
    periods = [(1985, 2004), (2005, 2025)]
    df = analysis.temporal(tables_with_stickers, params, periods)
    df_no = analysis.temporal(tables_with_stickers, replace(params, drop_stickers=True), periods)
    for col in ("exclusive_parts_per_set", "parts_per_set", "min_weight", "drop_stickers"):
        assert col in df.columns
    assert not df["drop_stickers"].any() and df_no["drop_stickers"].all()
    # L'autocollant est exclusif (un seul set) : le retirer baisse le nombre de pièces exclusives.
    assert df_no["exclusive_parts_per_set"].sum() < df["exclusive_parts_per_set"].sum()


def test_null_model_script_runs(tmp_path, monkeypatch):
    import sys

    import null_model

    monkeypatch.setattr(sys, "argv", ["null_model.py", "--demo", "--n-null", "2", "--results-dir", str(tmp_path)])
    null_model.main()
    assert (tmp_path / "theme_cohesion_null.csv").exists()
    assert (tmp_path / "null_model_runs.csv").exists()


def test_temporal_robustness_script_runs(tmp_path, monkeypatch):
    import sys

    import temporal_robustness

    monkeypatch.setattr(sys, "argv", ["temporal_robustness.py", "--demo", "--results-dir", str(tmp_path),
                                      "--figures-dir", str(tmp_path)])
    temporal_robustness.main()
    df = pd.read_csv(tmp_path / "temporal_robustness.csv")
    assert set(df["min_weight"]) == {0.05, 0.1} and set(df["drop_stickers"]) == {False, True}
    assert (tmp_path / "temporal_robustness.png").exists()
