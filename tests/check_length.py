import json
from pathlib import Path

racine = Path(__file__).resolve().parent.parent
dossier = racine / "data" / "raw" / "adzuna"

fichiers = list(dossier.rglob("*.json"))
print("Fichiers JSON (pages):", len(fichiers))

lengths = []
ids = []
for f in fichiers:
    with open(f, encoding="utf-8") as file:
        data = json.load(file)
    for offre in data["payload"]["results"]:
        lengths.append(len(offre.get("description", "")))
        ids.append(offre.get("id"))

print("Offres (avec doublons):", len(lengths))
print("Offres uniques (id)   :", len(set(ids)))
print("Longueur max          :", max(lengths))
print("Longueur moyenne      :", round(sum(lengths) / len(lengths)))
