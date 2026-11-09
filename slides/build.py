"""Génère deck.html (fichier autonome) à partir des résultats du dépôt.

Les nombres du texte sont des {{clés}} remplacées ici ; les graphiques lisent DATA.
"""
import base64, json, re
from pathlib import Path
import numpy as np, pandas as pd, networkx as nx

REPO = Path(__file__).resolve().parent.parent
HERE = Path(__file__).parent
R = REPO / "results"
NB = " "  # espace fine insécable : séparateur de milliers et avant % : ; ?


def n0(x):  # 9062 -> "9 062"
    return f"{int(round(x)):,}".replace(",", NB)


def dec(x, k=1):  # 0.627 -> "0,63" avec k=2
    return f"{x:.{k}f}".replace(".", ",")


def pct(x, k=0):  # 0.739 -> "74 %"
    return dec(x * 100, k) + NB + "%"


summary = json.load(open(R / "summary.json", encoding="utf-8"))
ext = json.load(open(R / "extensions_summary.json", encoding="utf-8"))["theme_prediction"]
coh = pd.read_csv(R / "theme_cohesion.csv")
edges = pd.read_csv(R / "theme_graph_edges.csv")
parts = pd.read_csv(R / "parts_universality.csv")
sens = pd.read_csv(R / "sensitivity.csv")
comps = pd.read_csv(R / "components.csv")
cmp = pd.read_csv(R / "communities_comparison.csv")
null = pd.read_csv(R / "theme_cohesion_null.csv")
temp = pd.read_csv(R / "temporal.csv")
rob = pd.read_csv(R / "temporal_robustness.csv")
runs = pd.read_csv(R / "null_model_runs.csv")

# --- slide 7 : graphe des thèmes en 3D, thèmes >= 30 sets, 3 liens les plus forts par thème
keep = set(coh.loc[coh.n_sets >= 30, "root_theme"])
e = edges[edges.theme_a.isin(keep) & edges.theme_b.isin(keep)]
sel = set()
for t in keep:
    top = e[(e.theme_a == t) | (e.theme_b == t)].nlargest(3, "weight")
    sel |= {tuple(sorted(p)) for p in zip(top.theme_a, top.theme_b)}
e = e[[tuple(sorted(p)) in sel for p in zip(e.theme_a, e.theme_b)]]
G = nx.Graph()
for r in coh[coh.root_theme.isin(keep)].itertuples():
    G.add_node(r.root_theme, n_sets=int(r.n_sets), share=float(r.internal_share))
for r in e.itertuples():
    G.add_edge(r.theme_a, r.theme_b, w=float(r.weight), lift=float(r.lift))
G.remove_nodes_from(list(nx.isolates(G)))
for _, _, d in G.edges(data=True):
    d["lw"] = float(np.log1p(d["lift"]))
pos = nx.spring_layout(G, dim=3, weight="lw", k=2.2 / np.sqrt(len(G)), iterations=300, seed=42)
P = np.array(list(pos.values())); P = P - P.mean(0)
# Axes principaux : la plus grande étendue à l'horizontale (l'orientation d'un spring layout est arbitraire).
_, _, Vt = np.linalg.svd(P, full_matrices=False); P = P @ Vt.T
P = P / np.abs(P[:, 0]).max() * 11
names = list(G.nodes)
graph = {
    "nodes": [{"name": n, "n": G.nodes[n]["n_sets"], "share": round(G.nodes[n]["share"], 3),
               "p": [round(float(x), 3) for x in P[i]]} for i, n in enumerate(names)],
    "edges": [[names.index(a), names.index(b), round(d["w"], 1)] for a, b, d in G.edges(data=True)],
}

# --- slide 2 : les pièces les plus répandues (ce sont des plaques : on les dessine en 3D)
top4 = parts.head(4)
plates = []
for r in top4.itertuples():
    m = re.fullmatch(r"Plate (\d+) x (\d+)", r.name)
    assert m, f"pièce n° {r.Index + 1} non dessinable : {r.name}"
    a, b = sorted(int(v) for v in m.groups())
    plates.append({"label": f"Plaque {a}×{b}", "w": b, "d": a, "share": round(r.share_of_sets * 100)})
assert [q["w"] for q in plates] == [2, 4, 2, 4], "la scène 3D de la slide 2 range les plaques en 2 colonnes (largeurs 2 et 4)"

# --- slide 4 : seuils testés (pondération Jaccard)
sj = sens[sens.weighting == "jaccard"].sort_values("min_weight")
at = sj[sj.min_weight == summary["params"]["min_weight"]].iloc[0]
lo, hi = sj.iloc[0], sj.iloc[-1]

# --- slide 5 : composantes (tailles exactes, lues dans le graphe exporté)
GS = nx.read_gexf(R / "lego_sets.gexf")
cc = sorted(nx.connected_components(GS), key=len, reverse=True)
sizes = [len(c) for c in cc]
giant_themes = len({GS.nodes[n]["root_theme"] for n in cc[0]})
n_themes = len({d["root_theme"] for _, d in GS.nodes(data=True)})
assert len(sizes) == summary["connectivity"]["n_components"] and sizes[0] == summary["connectivity"]["largest_component_size"]
small = [s for s in sizes[2:] if s > 1]
duplo_n = int(re.match(r"Duplo \((\d+)\)", comps.iloc[1].main_themes).group(1))
assert comps.iloc[1]["size"] == sizes[1]

# --- slide 6 : modularités et NMI
cm = summary["communities"]
others = cmp[cmp.algorithm != "thèmes officiels"].nmi_vs_root_theme_non_isolated

# --- slide 8 : cohésion observée contre modèle nul
NULL_THEMES = ["Duplo", "Technic", "Mixels", "DOTS", "City", "Star Wars", "Friends",
               "Harry Potter", "Disney", "Jurassic World"]
nl = null.set_index("root_theme").loc[NULL_THEMES]
lic = nl.loc[["Star Wars", "Harry Potter", "Disney", "Jurassic World"], "ratio_to_null"]
# univers fermés : cohésion >= 0,8 parmi les thèmes d'au moins 30 sets
c30 = coh[coh.n_sets >= 30]
closed = c30[c30.internal_share >= .8].sort_values("internal_share", ascending=False).root_theme.tolist()
assert set(NULL_THEMES[:4]) <= set(closed), "la slide 8 dit « les 4 du haut » : ils doivent tous dépasser 0,8"
closed_other = [t for t in closed if t not in NULL_THEMES[:4]]
assert len(closed_other) == 2, f"la slide 8 cite 2 autres thèmes fermés, il y en a {closed_other}"

# --- slide 9 : évolution
ns = rob[(rob.min_weight == summary["params"]["min_weight"]) & rob.drop_stickers].sort_values("period")

basic, conn, dist, p = summary["basic"], summary["connectivity"], summary["distances"], summary["params"]
deg = summary["top_sets"]["degree"]
btw = summary["top_sets"]["betweenness"]
data = {
    "graph": graph,
    "pred": {"acc": round(ext["accuracy"] * 100, 1), "unw": round(ext["accuracy_unweighted"] * 100, 1),
             "maj": round(ext["majority_baseline"] * 100, 1), "rnd": round(ext["random_baseline"] * 100, 1)},
    "plates": plates,
    "sens": [[float(r.min_weight), int(r.n_edges), int(r.n_isolated), round(float(r.largest_component_share), 4)]
             for r in sj.itertuples()],
    "chosen": float(p["min_weight"]),
    "comps": {"sizes": sizes[:2], "small": small, "isolated": conn["n_isolated_nodes"]},
    "mod": [["Communautés Louvain", cm["modularity_louvain"]], ["Décennies", cm["modularity_decades"]],
            ["Thèmes officiels", cm["modularity_root_themes"]], ["Thèmes mélangés au hasard", cm["modularity_shuffled_themes"]]],
    "null": [{"t": t, "n": int(r.n_sets), "obs": round(r.internal_share, 4), "rnd": round(r.null_mean, 4),
              "max": round(r.null_max, 4)} for t, r in nl.iterrows()],
    "temporal": [{"p": r.period.replace("-", "–"), "excl": round(r.exclusive_part_share * 100, 1),
                  "parts": round(r.parts_per_set)} for r in temp.itertuples()],
}

T = {
    "n_sets": n0(basic["n_nodes"]), "n_edges": n0(basic["n_edges"]),
    "years": f"{p['year_min']}–{p['year_max']}", "min_parts": str(p["min_parts"]),
    "thr": dec(p["min_weight"], 2),
    # pièces
    "parts_n": n0(len(parts)), "parts_one": pct((parts.n_root_themes == 1).mean()),
    "parts_ge100": str(int((parts.n_root_themes >= 100).sum())),
    # seuil
    "thr_n": str(len(sj)), "thr_lo": dec(lo.min_weight, 2), "thr_hi": dec(hi.min_weight, 2),
    "giant_at": pct(at.largest_component_share), "iso_at": n0(at.n_isolated), "edges_at": n0(at.n_edges),
    "giant_lo": pct(lo.largest_component_share), "edges_lo": dec(lo.n_edges / 1e6, 1) + " millions",
    "giant_hi": pct(hi.largest_component_share), "edges_hi": n0(hi.n_edges),
    # structure
    "density": pct(basic["density"], 2), "mean_deg": n0(basic["mean_degree"]),
    "n_comp": n0(conn["n_components"]), "n_iso": n0(conn["n_isolated_nodes"]),
    "giant_n": n0(conn["largest_component_size"]), "giant_pct": pct(conn["largest_component_share"]),
    "duplo_comp": n0(sizes[1]), "duplo_in": n0(duplo_n),
    "small_n": n0(len(small)), "small_sets": n0(sum(small)),
    "giant_themes": str(giant_themes), "n_themes": str(n_themes), "tg_n": str(len(G)),
    "n_draws": str(int((runs.run != "réel").sum())),
    "diam": str(dist["diameter"]), "mean_dist": dec(dist["mean_distance_estimate"], 1),
    "deg1": deg[0]["name"], "deg1_n": n0(deg[0]["degree"]), "deg2": deg[1]["name"], "deg3": deg[2]["name"],
    "btw1": btw[0]["name"], "btw2": btw[1]["name"],
    # communautés
    "nmi": dec(cm["nmi_vs_root_theme_non_isolated"], 2),
    "nmi_lo": dec(others.min(), 2), "nmi_hi": dec(others.max(), 2),
    "n_res": str(int((cmp.algorithm == "louvain").sum())),
    "n_lp": str(int(cmp.algorithm.str.startswith("label propagation").sum())),
    # modèle nul
    "null_all": str(int((null.n_null_ge_real == 0).sum())), "null_n": str(len(null)),
    "n_closed": str(len(closed)), "coh_n": str(len(c30)), "closed_other": " et ".join(closed_other),
    "lic_lo": dec(lic.min(), 0), "lic_hi": dec(lic.max(), 0),
    # évolution
    "ex_first": pct(temp.exclusive_part_share.iloc[0], 1), "ex_last": pct(temp.exclusive_part_share.iloc[-1], 1),
    "ns_first": pct(ns.exclusive_part_share.iloc[0], 1), "ns_last": pct(ns.exclusive_part_share.iloc[-1], 1),
}

tpl = (HERE / "template.html").read_text(encoding="utf-8")
tpl = re.sub(r"\{\{(\w+)\}\}", lambda m: T[m.group(1)], tpl)  # KeyError si une clé manque
tpl = tpl.replace("/*FONT*/", base64.b64encode((HERE / "archivo.woff2").read_bytes()).decode())
html = (tpl.replace("/*THREE*/", (HERE / "three.min.js").read_text(encoding="utf-8"))
           .replace("/*DATA*/", "const DATA=" + json.dumps(data, ensure_ascii=False) + ";"))
out = HERE / "deck.html"
out.write_text(html, encoding="utf-8")
print(out, f"{out.stat().st_size/1e6:.2f} Mo", len(G), "thèmes", G.number_of_edges(), "liens")
for k in ("parts_one", "giant_at", "edges_lo", "nmi", "nmi_lo", "nmi_hi", "lic_lo", "lic_hi", "ns_first", "ns_last",
          "small_n", "small_sets", "giant_themes", "n_themes", "tg_n", "n_draws", "years", "density", "mean_dist",
          "n_closed", "coh_n", "closed_other", "n_res", "n_lp", "parts_n", "parts_ge100", "deg1", "btw1", "ex_first", "ex_last"):
    print(f"  {k} = {T[k]}")
print("  null obs :", [(d["t"], d["obs"]) for d in data["null"]])
print("  mod :", data["mod"])
print("  plates :", data["plates"])
print("  temporal :", data["temporal"])
assert "{{" not in html, "motif {{ resté dans la page"
