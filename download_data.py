"""Télécharge les tables Rebrickable utiles dans data/raw/.

Si le téléchargement automatique échoue, télécharger les fichiers à la main
depuis https://rebrickable.com/downloads/ (voir data/README.md).
"""

import sys
import urllib.request
from datetime import date
from pathlib import Path

from lego_graph.load import TABLES

BASE_URL = "https://cdn.rebrickable.com/media/downloads/{name}.csv.gz"
DEST = Path("data/raw")


def main() -> None:
    DEST.mkdir(parents=True, exist_ok=True)
    failed = []
    for name in TABLES:
        url = BASE_URL.format(name=name)
        target = DEST / f"{name}.csv.gz"
        print(f"{url} -> {target}")
        request = urllib.request.Request(url, headers={"User-Agent": "lego-graph-student-project"})
        try:
            with urllib.request.urlopen(request, timeout=120) as response:
                target.write_bytes(response.read())
        except Exception as exc:  # noqa: BLE001
            print(f"  échec : {exc}")
            failed.append(name)

    if failed:
        print(f"\nÉchec pour : {', '.join(failed)}. Voir data/README.md.")
        sys.exit(1)
    # Date écrite seulement si toutes les tables viennent du même téléchargement.
    (DEST / "DOWNLOAD_DATE.txt").write_text(f"Téléchargé le {date.today().isoformat()}\n")
    print("\nTerminé. Notez la date de téléchargement dans le rapport (DOWNLOAD_DATE.txt).")


if __name__ == "__main__":
    main()
