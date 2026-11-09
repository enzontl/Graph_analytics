<p align="center"><img src="assets/brick.svg" alt="Deux briques LEGO en ASCII qui s'emboîtent" width="200"></p>

# Les thèmes LEGO sont-ils de vrais univers ? Analyse en graphe du catalogue LEGO

Projet de Graph Analytics 2026, Albert School.

**Membres du groupe :** Enzo, Keira, Amandine

## Question

Les thèmes LEGO (City, Star Wars, Technic, Friends…) forment-ils des univers
séparés, chacun avec ses propres pièces, ou partagent-ils tous les mêmes
briques ? Et LEGO s'est-il spécialisé au fil du temps ?

Hypothèse testée : depuis les années 2000 et la multiplication des licences,
les sets utiliseraient des pièces de plus en plus spécifiques, si bien que les
thèmes seraient plus séparés dans le graphe qu'avant.

## Résultats principaux

Graphe par défaut : sets de 1990 à 2025 d'au moins 50 pièces, poids de Jaccard
≥ 0,25. Tous les chiffres viennent de `results/` (données du 2026-11-06).

- **Le graphe :** 9 062 sets et 317 495 arêtes (densité 0,0077, degré moyen 70).
  Il n'est pas connexe : 1 640 composantes, dont 1 462 sets isolés. La plus
  grande composante regroupe 74 % des sets. Son diamètre est de 16 et son
  rayon de 8 ; la distance moyenne est d'environ 3,8.
- **Les communautés ne sont pas les thèmes.** Louvain trouve une partition de
  modularité 0,63, contre 0,28 pour les thèmes officiels et ≈ 0 pour des thèmes
  mélangés au hasard. Un découpage par décennie (0,36) structure le graphe
  **mieux** que les thèmes. La NMI communautés/thèmes vaut 0,45 (sets isolés
  exclus). Les grandes communautés mélangent plusieurs thèmes d'une même époque.
- **Autre algorithme** (`communities_comparison.csv`). La label propagation
  donne des résultats proches de Louvain : 1 814 communautés, modularité 0,58 et
  NMI 0,49 (asynchrone, pondérée) ; 1 805 communautés, 0,58 et 0,47
  (semi-synchrone, non pondérée). Louvain à résolution 1 (nos résultats) : 1 677
  communautés, 0,63 et 0,45. Quand on augmente la résolution de Louvain
  (0,5 → 4), la NMI monte (0,43 → 0,54) et la modularité baisse (0,61 → 0,48),
  mais c'est surtout parce qu'il y a plus de communautés : on ne conclut pas
  que les thèmes sont mieux retrouvés. Les NMI de tous les algorithmes
  restent entre 0,43 et 0,54.
- **Quelques thèmes sont de vrais univers.** Part des liens d'un thème qui
  restent dans le thème (`theme_cohesion.csv`) : Duplo 0,91, Technic 0,85,
  Mixels 0,81, DOTS 0,81, Brickheadz 0,77. Les thèmes sous licence sont surtout
  des étiquettes : Harry Potter 0,10, Disney 0,07, Super Heroes DC 0,06,
  Jurassic World 0,03.
  La médiane est de 0,29 sur 57 thèmes.
- **Graphe des thèmes** (`theme_graph.gexf`, `figures/theme_graph.png`).
  127 thèmes, 2 487 liens, 7 thèmes sans aucun lien (tous très petits : 2 à 19
  sets, par exemple Bluey ou Scala). Les liens les plus lourds passent par Star Wars et
  Creator (Creator–Star Wars, Star Wars–Icons) mais ils sont peu
  informatifs : leur `lift` est proche de 1 (1,10 et 1,38), ce qu'on attend
  d'un thème qui a énormément de liens. Les couples les plus liés par rapport au hasard
  (`lift`, thèmes d'au moins 30 sets) sont des thèmes proches par l'univers :
  Castle–Pirates (56), Pirates–Adventurers (45), Train–Town (20),
  Bionicle–Hero Factory (15).
- **Deviner le thème d'un set par ses voisins** (`theme_prediction.csv`).
  Chaque voisin vote pour son thème : on devine juste pour **63,9 %** des sets
  reliés (7 600 sets) et 53,6 % en comptant les sets isolés comme des échecs,
  contre 8,4 % en prédisant toujours Star Wars et 3,1 % au hasard. Les mieux
  devinés : Technic 100 %, Town 93 %, Duplo 88 %, Star Wars 86 %, Friends 83 %.
  Les moins bien devinés sont des thèmes-étiquettes, presque toujours
  confondus avec Star Wars : LEGO Ideas 0 %, Icons 5 %, LEGO Exclusive 5 %,
  Monkie Kid 9 %. Cela rejoint la cohésion : les univers fermés se devinent,
  pas les étiquettes.
- **Modèle nul** (`theme_cohesion_null.csv`, `null_model_runs.csv`). Si l'on
  mélange les pièces entre les sets (tailles des sets et fréquences des pièces
  conservées, 10 tirages), environ 180 paires de sets seulement atteignent le
  seuil 0,25, contre 317 495 en réalité. À densité égale, la modularité des
  thèmes tombe à 0,005 (contre 0,28) et les **57 thèmes sont plus cohésifs que
  dans chacun des 10 tirages**. Cela nuance le point précédent : les thèmes
  sous licence restent 2 à 4 fois plus cohésifs qu'au hasard (Harry Potter
  3,9, Disney 2,2, Super Heroes DC 2,1, Jurassic World 2,6). Ce sont des
  univers faibles plutôt que de simples étiquettes. Les thèmes à système de
  pièces propre sont loin devant (Technic 18, Duplo 11). Rapport médian : 19.
- **Les pièces :** 77 % des 28 856 pièces n'apparaissent que dans un thème, et
  51 pièces apparaissent dans 100 thèmes ou plus (`figures/parts_themes.png`).
  Les pièces « signature » (`signature_parts.csv`) sont des pièces mécaniques
  pour Technic, une autre échelle pour Duplo, des moules propres pour Super
  Mario et des pièces imprimées pour Star Wars et Friends.
- **Évolution :** l'hypothèse n'est pas confirmée. La part de pièces d'un set
  exclusives à son thème passe de 8,9 % (années 1990) à 4,4 % (années 2010 et
  2020). Ce résultat ne dépend pas du seuil et résiste aux autres paramètres
  (taille minimale, couleur, thèmes exclus). La baisse de la modularité des
  thèmes par décennie (0,52 → 0,17), elle, **dépend du seuil** : à 0,35 elle
  remonte (0,54 → 0,47 → 0,67 → 0,62, `temporal_robustness.csv`). Il ne faut
  donc pas la présenter comme une tendance.
- **Robustesse de l'évolution** (`temporal_robustness.csv`,
  `figures/temporal_robustness.png`). Sans les autocollants, la part de pièces
  exclusives passe de 8,3 % à 4,0 % : ils n'expliquent pas la baisse. En
  nombre, la baisse est plus faible et n'est pas régulière : 4,6 pièces
  exclusives par set dans les années 1990, 2,9 dans les années 2010 et 3,8
  dans les années 2020. Dans le même temps, les sets passent de 57 à 103
  pièces distinctes en moyenne. La part baisse donc surtout parce que les sets
  grossissent avec des pièces partagées entre thèmes.

| Période | Modularité des thèmes (seuil 0,25) | Modularité des thèmes (seuil 0,35) | NMI (sans isolés) | Pièces exclusives au thème | Pièces exclusives par set |
|---|---|---|---|---|---|
| 1990–1999 | 0,52 | 0,54 | 0,70 | 8,9 % | 4,6 |
| 2000–2009 | 0,31 | 0,47 | 0,52 | 9,0 % | 4,2 |
| 2010–2019 | 0,32 | 0,67 | 0,45 | 4,4 % | 2,9 |
| 2020–2025 | 0,17 | 0,62 | 0,42 | 4,4 % | 3,8 |

Ces résultats concordent avec Bartneck et Moltchanova (2018), qui montrent sur
les données BrickLink 1955–2015 que les nouvelles pièces sont de moins en moins
réutilisées.

Le graphe des sets dans Gephi, coloré par communauté Louvain
(`figures/gephi_communities.png`) puis par thème racine
(`figures/gephi_root_themes.png`), avec la même disposition.

## Données

- **Source :** base de données Rebrickable, téléchargements CSV
  (<https://rebrickable.com/downloads/>). Rebrickable est une base
  communautaire du catalogue LEGO (sets, pièces, inventaires, thèmes).
- **Tables utilisées :** `themes`, `sets`, `inventories`, `inventory_parts`,
  `parts`, `part_categories`.
- **Date de téléchargement :** 2026-11-06 (`data/raw/DOWNLOAD_DATE.txt`). Les
  fichiers sont mis à jour en continu, les chiffres dépendent donc de la date.
- **Conditions d'utilisation :** d'après les conditions de Rebrickable
  (<https://rebrickable.com/terms/>, section 5), les données du catalogue
  peuvent être utilisées « pour n'importe quel usage », via l'API ou la page
  Downloads, et le téléchargement automatique n'est autorisé que depuis cette
  page (ce que fait `download_data.py`). Rebrickable demande de citer la
  source : **données issues de Rebrickable**.
  LEGO® est une marque du groupe LEGO, qui ne parraine ni n'approuve ce projet.
- Voir [`data/README.md`](data/README.md) pour le téléchargement.

## Réutilisation de code et outils d'IA

- **Code existant :** aucun code d'une analyse existante de ces données n'a
  été repris. Le projet utilise les bibliothèques NetworkX, pandas, NumPy,
  SciPy, scikit-learn et matplotlib.
- **Outils d'IA :** le code (chargement, construction du graphe, fonctions
  d'analyse, tests) et la recherche d'études existantes ont été réalisés avec l'aide de Claude Code (Anthropic).

## Modèle de graphe

1. **Graphe biparti sets–pièces.** Un set est relié à chaque pièce qu'il
   contient (pièces de rechange exclues ; pour un set à plusieurs versions
   d'inventaire, on garde la première).
2. **Projection sur les sets.** Deux sets sont reliés s'ils partagent des
   pièces. Le graphe obtenu est **non orienté**, **simple** (pas d'arêtes
   multiples ni de boucles) et **pondéré**.

Choix de modélisation, tous réglables (`lego_graph/config.py` ou options de
`run_analysis.py`) :

| Choix | Valeur par défaut | Option |
|---|---|---|
| Période | 1990–2025 | `--year-min`, `--year-max` |
| Taille minimale d'un set | 50 pièces | `--min-parts` |
| Thèmes exclus | Gear, Books, Key Chain, Bulk Bricks, Service Packs, Supplemental, Collectible Minifigures | `exclude_themes` dans `config.py` |
| Une pièce = | une forme (`part_num`), toutes couleurs confondues | `--with-color` |
| Pièces trop fréquentes | conservées | `--max-part-share 0.2` les retire |
| Autocollants (catégorie « Stickers ») | conservés | `--drop-stickers` les retire |
| Poids d'une arête | Jaccard = pièces partagées / pièces de l'un ou l'autre set | `--weighting count\|jaccard\|idf` |
| Seuil | arête gardée si poids ≥ 0,25 | `--min-weight` |
| Squelette k plus proches voisins | désactivé | `--top-k` |

Les minifigurines ne sont pas comptées : leurs pièces sont dans des
inventaires séparés.

**Pourquoi 0,25 ?** Sous 0,15 environ, presque toutes les paires de sets sont
reliées (plus de 5 millions d'arêtes) et le graphe ne dit plus rien. Le
tableau `results/sensitivity.csv` (produit par `sensitivity.py`) montre la
connectivité et les communautés pour les seuils de 0,15 à 0,4.
`results/sensitivity_coarse.csv` est un premier balayage plus large, fait
avec une ancienne grille de `sensitivity.py` : le script actuel ne le
régénère pas.

## Installation

Le projet utilise [uv](https://docs.astral.sh/uv/). Les dépendances sont
dans `pyproject.toml` et leurs versions exactes sont figées dans `uv.lock`.

```bash
uv sync
```

## Exécution

Téléchargement des données (déjà présentes dans `data/raw/` ; sinon voir
`data/README.md`) :

```bash
uv run python download_data.py
```

Analyse complète avec les paramètres par défaut (environ 3 min 30) :

```bash
uv run python run_analysis.py
```

Étude de sensibilité au seuil et à la pondération :

```bash
uv run python sensitivity.py
```

Modèle nul pour la cohésion des thèmes (10 graphes nuls, environ 2 min) :

```bash
uv run python null_model.py
```

Robustesse de l'évolution par période, aux seuils 0,25 et 0,35, avec et
sans autocollants (moins d'une minute) :

```bash
uv run python temporal_robustness.py
```

Analyses complémentaires (autre algorithme de communautés, graphe des thèmes,
thème deviné par les voisins) :

```bash
uv run python run_extensions.py
uv run python run_extensions.py --n-seeds 3   # stabilité selon la graine
```

Exemple avec d'autres paramètres :

```bash
uv run python run_analysis.py --weighting idf --min-weight 120 --resolution 1.2
```

Pour tester sans les vraies données (jeu synthétique, résultats sans
signification), puis lancer les tests :

```bash
uv run python run_analysis.py --demo --min-parts 1 --year-min 1980 --min-weight 0.05
uv run python null_model.py --demo
uv run python temporal_robustness.py --demo
uv run python run_extensions.py --demo
uv run pytest
```

## Fichiers produits

| Contenu | Fichier |
|---|---|
| Nombre de nœuds et d'arêtes, densité, clustering | `results/summary.json` → `basic` |
| Connectivité, composantes | `summary.json` → `connectivity`, `results/components.csv` |
| Diamètre, rayon, distance moyenne (plus grande composante) | `summary.json` → `distances` |
| Centralités (degré, degré pondéré, betweenness, vecteur propre) | `results/centralities.csv`, `summary.json` → `top_sets` |
| Pièces universelles (degré dans le biparti) | `results/parts_universality.csv`, `figures/parts_themes.png` |
| Pièces signature de chaque thème | `results/signature_parts.csv` |
| Communautés Louvain et comparaison avec les thèmes (modularité, NMI, ARI) | `summary.json` → `communities`, `results/communities_summary.csv`, `results/communities_assignment.csv`, `figures/communities_vs_themes.png` |
| Louvain à plusieurs résolutions et label propagation, comparés aux thèmes (modularité, NMI, ARI) | `results/communities_comparison.csv` (`run_extensions.py`) |
| Cohésion de chaque thème | `results/theme_cohesion.csv` |
| Cohésion de chaque thème comparée au modèle nul | `results/theme_cohesion_null.csv`, `results/null_model_runs.csv` (`null_model.py`) |
| Graphe des thèmes (un nœud par thème racine) | `results/theme_graph.gexf`, `results/theme_graph_edges.csv`, `figures/theme_graph.png` (`run_extensions.py`) |
| Thème deviné par vote des voisins, réussite par thème | `results/theme_prediction.csv`, `results/theme_prediction_sets.csv`, `results/extensions_summary.json` (`run_extensions.py`) |
| Évolution par décennie | `results/temporal.csv`, `figures/temporal.png` |
| Évolution par décennie aux seuils 0,25 et 0,35, avec et sans autocollants | `results/temporal_robustness.csv`, `figures/temporal_robustness.png` (`temporal_robustness.py`) |
| Distribution des degrés | `figures/degree_distribution.png` |
| Sensibilité au seuil | `results/sensitivity.csv` |
| Graphe pour Gephi (avec communautés) | `results/lego_sets.gexf` (≈ 80 Mo, non versionné : relancer `run_analysis.py`) |
| Images Gephi du graphe des sets, colorées par communauté et par thème | `figures/gephi_communities.png`, `figures/gephi_root_themes.png` |
| Slides de l'oral (HTML autonome, flèches pour avancer, F pour le plein écran ; PDF de 10 pages) | `slides/deck.html`, `slides/deck.pdf` (régénérer le HTML depuis `results/` : `uv run python slides/build.py`) |

## Méthodes et conventions

- **Diamètre et rayon** : calculés exactement sur la plus grande composante
  connexe, avec `usebounds=True` de NetworkX (Takes et Kosters, 2011). La
  distance est le nombre d'arêtes (non pondérée). La distance moyenne est
  estimée à partir de 200 sources tirées au hasard.
- **Clustering** : moyenne du clustering pondéré d'Onnela et al. (2005),
  calculée avec des matrices creuses (même valeur que NetworkX, testé).
- **Betweenness** : distance d'une arête = 1 / poids (un lien fort rapproche
  deux sets). Elle est estimée sur 500 sources tirées au hasard (`--betweenness-k`).
- **Vecteur propre** : calculé sur la plus grande composante, pondéré.
- **Communautés** : Louvain pondéré (Blondel et al., 2008), graine 42.
  On compare la partition trouvée aux thèmes racines avec la NMI et l'ARI,
  calculées aussi sans les sets isolés (chacun forme sa propre communauté,
  ce qui gonfle la NMI). La modularité des thèmes est comparée à deux repères :
  des thèmes mélangés au hasard (mêmes tailles) et un découpage par décennie.
- **Autre algorithme** (`run_extensions.py`) : Louvain aux résolutions 0,5,
  1, 2 et 4, et label propagation (Raghavan et al., 2007) en deux versions :
  asynchrone pondérée, graine fixée, et semi-synchrone non pondérée,
  déterministe. La modularité est toujours calculée à la résolution 1 pour
  rester comparable d'une ligne à l'autre. Une résolution plus haute donne
  plus de communautés, ce qui peut à lui seul faire monter la NMI : la
  colonne `n_communities` aide à la lire. La ligne « thèmes officiels » sert
  de repère (NMI = 1 par définition).
- **Cohésion d'un thème** : `internal_share` = 2 × poids des arêtes internes /
  somme des degrés pondérés des sets du thème. 1 = univers fermé.
  `expected_share` est la valeur attendue si les liens ignoraient les thèmes.
- **Graphe des thèmes** : un nœud par thème racine. Poids d'une arête = somme
  des poids Jaccard des arêtes entre sets des deux thèmes ; `n_links` = nombre
  de ces arêtes ; `lift` = ce poids divisé par le poids attendu si les liens
  ignoraient les thèmes (volume_a × volume_b / volume total, comme dans la
  modularité). La figure ne garde que les thèmes d'au moins 30 sets et, pour
  chacun, ses 3 liens les plus forts.
- **Thème deviné** : chaque voisin vote pour son thème racine avec le poids
  de l'arête (`accuracy_unweighted` : un voisin = une voix). Le thème du set
  lui-même n'est pas utilisé. `accuracy` est calculée sur les sets non isolés,
  `accuracy_all` compte les sets isolés comme des échecs. Repères : toujours
  prédire le thème le plus fréquent, et tirer au hasard selon les fréquences
  des thèmes (somme des p²).
- **Pièces signature** : `specificity` = part des sets contenant la pièce qui
  sont du thème ; `coverage` = part des sets du thème qui la contiennent.
- **Spécialisation** : `exclusive_part_share` est la part moyenne des pièces
  d'un set qu'on ne trouve dans aucun autre thème racine du catalogue
  1990–2025. Elle ne dépend pas du seuil de la projection.
  `exclusive_parts_per_set` donne le même indicateur en nombre de pièces, et
  `parts_per_set` le nombre moyen de pièces distinctes par set : une part peut
  baisser seulement parce que les sets grossissent.
- **Modèle nul** (`null_model.py`) : on mélange la matrice sets × pièces avec
  l'algorithme *curveball* (Strona et al., 2014), 20 tours par graphe. Chaque
  set garde exactement son nombre de pièces et chaque pièce son nombre de
  sets ; seul le lien entre pièces et thèmes est cassé. On refait la
  projection 10 fois (graines 42 à 51). Au seuil 0,25, un graphe nul n'a
  presque pas d'arêtes : on garde donc ses arêtes les plus fortes, autant que
  dans le graphe réel (même densité), puis on calcule la même cohésion que
  pour le graphe réel. `theme_cohesion_null.csv` donne, par thème, la
  moyenne et l'écart-type au hasard (`null_mean`, `null_std`), le rapport
  `ratio_to_null`, le `z_score` et une p-valeur empirique
  (1 + tirages au moins aussi cohésifs) / (1 + tirages). Avec 10 tirages, la
  plus petite p-valeur possible est 1/11 ≈ 0,09 : on s'appuie donc sur le
  nombre de thèmes au-dessus de tous les tirages (`n_null_ge_real` = 0) et sur
  le rapport. Le `z_score` est donné à titre indicatif : avec 10 tirages et un
  écart-type estimé sur 10 valeurs, il atteint des valeurs énormes (jusqu'à
  405) qui ne se lisent pas comme une probabilité. Le rapport est lui aussi
  gonflé quand la cohésion au hasard est presque nulle (Belville 225).
- **Autocollants** : `--drop-stickers` retire les pièces de la catégorie
  Rebrickable « Stickers » avant de construire le graphe.
- **Images Gephi** : `results/lego_sets.gexf` ouvert dans Gephi, sets isolés
  retirés (filtre *Degree Range* ≥ 1), disposition ForceAtlas2 (LinLog,
  répulsion approchée), couleur par partition `community` puis `root_theme`.

## Limites

- Le seuil change fortement le graphe : seuls les résultats qui tiennent sur
  plusieurs seuils sont présentés comme des conclusions.
- Une pièce imprimée a son propre numéro et une planche d'autocollants compte
  comme une pièce : les deux gonflent les pièces exclusives. Les autocollants
  peuvent être retirés (`--drop-stickers`) et changent peu les résultats ; les
  pièces imprimées restent comptées à part.
- Le modèle nul ne compte que 10 tirages : la p-valeur empirique ne descend
  pas sous 1/11. Le graphe nul est comparé à densité égale (mêmes nombres
  d'arêtes) et non au même seuil, où il serait presque vide.
- La modularité d'une projection ignore une partie de la structure biparti
  (Barber, 2007).
- La label propagation asynchrone dépend de l'ordre de visite des nœuds :
  d'une graine à l'autre, la partition peut changer (`--n-seeds`).

## Références

- Bartneck, C. et Moltchanova, E. (2018). Expanding the LEGO universe:
  exponential growth of LEGO parts. *PLOS ONE*.
- Blondel, V. et al. (2008). Fast unfolding of communities in large networks.
  *J. Stat. Mech.*
- Raghavan, U. N., Albert, R. et Kumara, S. (2007). Near linear time algorithm
  to detect community structures in large-scale networks. *Physical Review E*.
- Onnela, J.-P. et al. (2005). Intensity and coherence of motifs in weighted
  complex networks. *Physical Review E*.
- Takes, F. et Kosters, W. (2011). Determining the diameter of small world
  networks. *CIKM*.
- Barber, M. (2007). Modularity and community detection in bipartite networks.
  *Physical Review E*.
- Strona, G., Nappo, D., Boccacci, F., Fattorini, S. et San-Miguel-Ayanz, J.
  (2014). A fast and unbiased procedure to randomize ecological binary
  matrices with fixed row and column totals. *Nature Communications*.

## Reproductibilité

Toutes les étapes aléatoires utilisent une graine fixe (`--seed`, 42 par
défaut). Les résultats de Louvain peuvent varier d'une version de NetworkX à
l'autre : `uv.lock` fige les versions exactes, `uv sync` réinstalle donc
les mêmes. Même avec les mêmes versions, Louvain peut changer d'une machine à
l'autre quand deux choix sont presque à égalité (écarts d'arrondi au
quinzième chiffre). Avec le même code, une seconde machine a obtenu pour
2000–2009 une NMI de 0,52 au lieu de 0,53 (modularité Louvain 0,6692 au lieu
de 0,6693) ; les autres périodes et le graphe complet sont identiques. Le
tableau ci-dessus reprend la valeur de `results/temporal.csv`.

## Structure

```
lego_graph/
  config.py     paramètres de modélisation
  load.py       lecture des CSV Rebrickable
  build.py      biparti sets-pièces et projection pondérée
  analysis.py   mesures (connectivité, distances, centralités, pièces, communautés, temps)
  null_model.py modèle nul (mélange curveball) et cohésion comparée au hasard
  extensions.py autre algorithme de communautés, graphe des thèmes, thème deviné
  figures.py    figures du rapport
  synthetic.py  jeu de données synthétique pour les tests
download_data.py
run_analysis.py
sensitivity.py
null_model.py           modèle nul de la cohésion des thèmes
temporal_robustness.py  évolution par période selon le seuil et les autocollants
run_extensions.py       label propagation, graphe des thèmes, thème deviné
tests/          tests du pipeline (pytest)
assets/         image du README
data/raw/       données téléchargées
results/        tableaux et résumé produits
figures/        figures produites
slides/         slides de l'oral : build.py remplit template.html avec les chiffres de results/
pyproject.toml  dépendances (uv)
uv.lock         versions exactes des dépendances
```
