# Données

Les données viennent des téléchargements CSV de Rebrickable :
<https://rebrickable.com/downloads/>

## Téléchargement automatique

Depuis la racine du dépôt :

```bash
python download_data.py
```

## Téléchargement manuel

Si le script échoue, téléchargez ces fichiers depuis la page ci-dessus et
placez-les tels quels (sans les décompresser) dans `data/raw/` :

- `themes.csv.gz`
- `sets.csv.gz`
- `inventories.csv.gz`
- `inventory_parts.csv.gz`
- `parts.csv.gz`
- `part_categories.csv.gz`

Notez la date de téléchargement dans `data/raw/DOWNLOAD_DATE.txt` : les
fichiers sont mis à jour en continu.

## Dans le dépôt

Le sujet demande d'inclure les données si c'est pratique. Si les fichiers
font moins de 100 Mo chacun (limite de GitHub), committez-les. Sinon,
déposez-les sur un Google Drive et mettez le lien ici.
