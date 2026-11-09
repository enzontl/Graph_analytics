import networkx as nx
import pandas as pd
import pytest

from lego_graph import extensions
from lego_graph.build import build_set_graph
from lego_graph.config import Params
from lego_graph.synthetic import make_tables


@pytest.fixture(scope="module")
def G():
    params = Params(year_min=1980, year_max=2030, min_parts=1, min_weight=0.0, betweenness_k=None)
    graph, _, _ = build_set_graph(make_tables(seed=0), params)
    return graph


def test_compare_communities(G):
    df = extensions.compare_communities(G, resolutions=(0.5, 1.0, 2.0), seeds=(42,), log=lambda _: None)
    assert df["algorithm"].iloc[0] == "thèmes officiels"
    assert df["nmi_vs_root_theme"].iloc[0] == pytest.approx(1.0)
    assert set(df.loc[df["algorithm"] == "louvain", "resolution"]) == {0.5, 1.0, 2.0}
    assert df["algorithm"].str.startswith("label propagation").sum() == 2
    assert df["nmi_vs_root_theme"].between(0, 1 + 1e-9).all()
    # Les thèmes synthétiques sont nets : Louvain (γ = 1) les retrouve.
    louvain = df[(df["algorithm"] == "louvain") & (df["resolution"] == 1.0)].iloc[0]
    assert louvain["nmi_vs_root_theme"] > 0.5


def test_theme_graph(G):
    T = extensions.theme_graph(G)
    assert set(T.nodes) == {t for _, t in G.nodes(data="root_theme")}
    # Tout le poids du graphe des sets se retrouve dans les arêtes ou à l'intérieur des thèmes.
    total = G.size(weight="weight")
    internal = sum(w for _, w in T.nodes(data="internal_weight"))
    assert T.size(weight="weight") + internal == pytest.approx(total)
    assert T.degree("Duplo") == 0  # pièces Duplo à part
    assert T.nodes["Duplo"]["internal_share"] == pytest.approx(1.0)
    assert all(d["lift"] > 0 and d["n_links"] >= 1 for _, _, d in T.edges(data=True))


def test_predict_theme(G):
    pred = extensions.predict_theme(G)
    assert len(pred) == G.number_of_nodes()
    assert pred.loc[pred["degree"] == 0, "predicted"].isna().all()
    by_theme = extensions.prediction_by_theme(pred, extensions.predict_theme(G, weighted=False))
    assert by_theme["accuracy"].between(0, 1).all()
    assert by_theme.set_index("root_theme").loc["Duplo", "accuracy"] == pytest.approx(1.0)
    summary = extensions.prediction_summary(pred, by_theme, min_sets=1)
    assert summary["accuracy"] > summary["random_baseline"]


def test_vote_ignores_own_theme():
    G = nx.Graph()
    G.add_node("a", root_theme="City", year=2000)
    G.add_node("b", root_theme="Space", year=2000)
    G.add_node("c", root_theme="Space", year=2000)
    G.add_edge("a", "b", weight=1.0)
    G.add_edge("a", "c", weight=1.0)
    pred = extensions.predict_theme(G).set_index("set_num")
    assert pred.loc["a", "predicted"] == "Space" and not pred.loc["a", "correct"]


def test_extensions_script_runs(tmp_path, monkeypatch):
    import sys

    import run_extensions

    monkeypatch.setattr(sys, "argv", ["run_extensions.py", "--demo", "--resolutions", "1", "2",
                                      "--results-dir", str(tmp_path), "--figures-dir", str(tmp_path)])
    run_extensions.main()
    for name in ("communities_comparison.csv", "theme_graph.gexf", "theme_prediction.csv",
                 "theme_graph.png", "extensions_summary.json"):
        assert (tmp_path / name).exists()
    assert len(pd.read_csv(tmp_path / "communities_comparison.csv")) == 1 + 2 + 1 + 1
