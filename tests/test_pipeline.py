from dataclasses import replace

import networkx as nx
import pytest

from lego_graph import analysis
from lego_graph.build import TooManyEdges, build_set_graph, select_sets, set_part_pairs, theme_table
from lego_graph.config import Params
from lego_graph.synthetic import make_tables


@pytest.fixture(scope="module")
def tables():
    return make_tables(seed=0)


@pytest.fixture(scope="module")
def params():
    return Params(year_min=1980, year_max=2030, min_parts=1, min_weight=0.0, betweenness_k=None)


def test_theme_roots(tables):
    themes = theme_table(tables["themes"]).set_index("id")
    assert themes.loc[2, "root_name"] == "City"  # Police -> City
    assert themes.loc[3, "root_name"] == "Star Wars"


def test_excluded_themes_removed(tables, params):
    sets = select_sets(tables, params)
    assert "Gear" not in set(sets["root_theme"])


def test_spares_and_later_versions_ignored(tables, params):
    sets = select_sets(tables, params)
    pairs = set_part_pairs(tables, sets, params)
    first_city = pairs[pairs["set_num"] == "1000-1"]["part"]
    assert not first_city.str.startswith("duplo").any()


def test_graph_is_simple_undirected_weighted(tables, params):
    G, _, _ = build_set_graph(tables, params)
    assert not G.is_directed() and not G.is_multigraph()
    assert all("weight" in d and d["weight"] > 0 for _, _, d in G.edges(data=True))
    assert nx.number_of_selfloops(G) == 0


def test_duplo_is_separate_component(tables, params):
    G, _, _ = build_set_graph(tables, params)
    for comp in nx.connected_components(G):
        themes = {G.nodes[n]["root_theme"] for n in comp}
        assert "Duplo" not in themes or themes == {"Duplo"}


@pytest.mark.parametrize("weighting,threshold", [("count", 1), ("jaccard", 0.05), ("idf", 0.5)])
def test_weightings_run(tables, params, weighting, threshold):
    G, _, _ = build_set_graph(tables, replace(params, weighting=weighting, min_weight=threshold))
    assert G.number_of_edges() > 0


def test_top_k_reduces_edges(tables, params):
    G_all, _, _ = build_set_graph(tables, params)
    G_k, _, _ = build_set_graph(tables, replace(params, top_k=3))
    assert 0 < G_k.number_of_edges() < G_all.number_of_edges()


def test_jaccard_matches_definition(tables, params):
    G, pairs, _ = build_set_graph(tables, params)
    parts = pairs.groupby("set_num")["part"].apply(set)
    u, v, d = next(iter(G.edges(data=True)))
    expected = len(parts[u] & parts[v]) / len(parts[u] | parts[v])
    assert d["weight"] == pytest.approx(expected)


def test_idf_matches_definition(tables, params):
    import math

    p = replace(params, weighting="idf", min_weight=0.0)
    G, pairs, _ = build_set_graph(tables, p)
    n_sets = pairs["set_num"].nunique()
    doc_freq = pairs.groupby("part")["set_num"].nunique()
    parts = pairs.groupby("set_num")["part"].apply(set)
    for u, v, d in list(G.edges(data=True))[:20]:
        expected = sum(max(math.log(n_sets / doc_freq[q]), 1e-9) for q in parts[u] & parts[v])
        assert d["weight"] == pytest.approx(expected)
        assert d["shared"] == len(parts[u] & parts[v])


def test_too_many_edges_stops_early(tables, params):
    with pytest.raises(TooManyEdges):
        build_set_graph(tables, replace(params, weighting="count", min_weight=1), max_edges=10)


def test_full_analysis(tables, params):
    G, pairs, sets = build_set_graph(tables, params)
    conn, comps = analysis.connectivity(G)
    assert conn["n_components"] >= 2  # au moins Duplo à part
    dist = analysis.distances(G)
    assert dist["radius"] <= dist["diameter"] <= 2 * dist["radius"]
    cent = analysis.centralities(G, params)
    assert len(cent) == G.number_of_nodes()
    summary, assignment, table = analysis.communities(G, params)
    # Les thèmes synthétiques sont nets : les communautés doivent les retrouver.
    assert summary["nmi_vs_root_theme"] > 0.5
    assert summary["modularity_shuffled_themes"] < summary["modularity_root_themes"]
    assert 0 <= analysis.exclusive_part_share(pairs, sets) <= 1
    cohesion = analysis.theme_cohesion(G, min_sets=1).set_index("root_theme")
    assert cohesion.loc["Duplo", "internal_share"] == pytest.approx(1.0)  # pièces Duplo à part
    assert cohesion["internal_share"].between(0, 1 + 1e-9).all()
    universal = analysis.part_universality(pairs, sets, tables["parts"])
    sig = analysis.signature_parts(pairs, sets, universal, min_sets=2)
    duplo = sig[sig["root_theme"] == "Duplo"]
    assert len(duplo) and duplo["part"].str.startswith("duplo").all() and (duplo["specificity"] == 1).all()
    temporal = analysis.temporal(tables, params, [(1985, 2004), (2005, 2025)])
    assert len(temporal) == 2


def test_weighted_clustering_matches_networkx(tables, params):
    G, _, _ = build_set_graph(tables, replace(params, min_weight=0.05))
    G.add_node("isolated")
    assert analysis.average_clustering_weighted(G) == pytest.approx(
        nx.average_clustering(G, weight="weight")
    )


def test_sensitivity_script_runs(tmp_path, monkeypatch):
    import sys

    import sensitivity

    monkeypatch.setattr(sys, "argv", ["sensitivity.py", "--demo", "--results-dir", str(tmp_path)])
    sensitivity.main()
    assert (tmp_path / "sensitivity.csv").exists()
