"""
src/analysis/pipeline/loader.py
───────────────────────────────
Chargement des fichiers JSON bruts (Adzuna, France Travail)
vers un DataFrame pandas unifié.

Principe : chaque source est convertie vers le MEME format de colonnes
(celui d'Adzuna aplati par json_normalize). Le cleaner n'a donc pas
besoin de savoir d'où vient l'offre.

Adzuna : un fichier par offre -> data/raw/adzuna/{id}.json
    {
      ...champs de l'offre (id, title, description, ...),
      "_meta": {"source", "country", "domain", "role", "keyword", "collected_at"}
    }
L'ancien format (un fichier par page, avec "payload") reste lisible,
pour ne rien casser avant la conversion.
"""

from __future__ import annotations

import glob
import json
import logging
import re
from pathlib import Path

import pandas as pd

logger = logging.getLogger(__name__)


# ══════════════════════════════════════════════════════════════════════════════
# ADZUNA
# ══════════════════════════════════════════════════════════════════════════════

def _adzuna_meta(meta: dict, source_file: str) -> dict:
    """Métadonnées de collecte, avec les noms de colonnes attendus par le cleaner."""
    return {
        "_source_file": source_file,
        "_source": meta.get("source", "adzuna"),
        "_country": meta.get("country", "fr"),
        "_domain": meta.get("domain", ""),
        "_role_hint": meta.get("role", ""),
        "_keyword": meta.get("keyword", ""),
        "_collected_at": meta.get("collected_at", ""),
    }


def load_raw_adzuna(raw_dir: str = "data/raw/adzuna") -> pd.DataFrame:
    """
    Charge tous les fichiers JSON Adzuna depuis raw_dir (récursif).

    Deux formats acceptés :
      - NOUVEAU : un fichier par offre (clé "id" + "_meta")
      - ANCIEN  : un fichier par page (clé "payload" -> "results")

    Retourne un DataFrame avec une colonne `_source_file` pour la traçabilité.
    """
    pattern = str(Path(raw_dir) / "**" / "*.json")
    files = glob.glob(pattern, recursive=True)

    if not files:
        logger.warning("Aucun fichier JSON trouvé dans %s", raw_dir)
        return pd.DataFrame()

    rows = []
    for f in files:
        try:
            with open(f, encoding="utf-8") as fh:
                rec = json.load(fh)
        except (json.JSONDecodeError, OSError) as exc:
            logger.warning("Fichier ignoré (%s) : %s", f, exc)
            continue

        if "payload" in rec:                          # ancien format : une page = plusieurs offres
            meta = _adzuna_meta(rec, f)
            for offer in rec.get("payload", {}).get("results", []):
                rows.append({**offer, **meta})
        elif "id" in rec:                             # nouveau format : une offre
            offer = {k: v for k, v in rec.items() if k != "_meta"}
            rows.append({**offer, **_adzuna_meta(rec.get("_meta", {}), f)})
        else:
            logger.warning("Format inconnu, fichier ignoré : %s", f)

    if not rows:
        return pd.DataFrame()

    df = pd.json_normalize(rows)
    logger.info("Chargé %d offres Adzuna depuis %d fichiers.", len(df), len(files))
    return df


# ══════════════════════════════════════════════════════════════════════════════
# FRANCE TRAVAIL
# ══════════════════════════════════════════════════════════════════════════════

# Region de chaque departement (le libelle France Travail ne donne que le departement)
_REGIONS = {
    "Île-de-France": ["75", "77", "78", "91", "92", "93", "94", "95"],
    "Auvergne-Rhône-Alpes": ["01", "03", "07", "15", "26", "38", "42", "43", "63", "69", "73", "74"],
    "Bourgogne-Franche-Comté": ["21", "25", "39", "58", "70", "71", "89", "90"],
    "Bretagne": ["22", "29", "35", "56"],
    "Centre-Val de Loire": ["18", "28", "36", "37", "41", "45"],
    "Corse": ["2A", "2B"],
    "Grand Est": ["08", "10", "51", "52", "54", "55", "57", "67", "68", "88"],
    "Hauts-de-France": ["02", "59", "60", "62", "80"],
    "Normandie": ["14", "27", "50", "61", "76"],
    "Nouvelle-Aquitaine": ["16", "17", "19", "23", "24", "33", "40", "47", "64", "79", "86", "87"],
    "Occitanie": ["09", "11", "12", "30", "31", "32", "34", "46", "48", "65", "66", "81", "82"],
    "Pays de la Loire": ["44", "49", "53", "72", "85"],
    "Provence-Alpes-Côte d'Azur": ["04", "05", "06", "13", "83", "84"],
}
_DEPT_TO_REGION = {d: region for region, depts in _REGIONS.items() for d in depts}

_PLACE = re.compile(r"^\s*(\d{2,3}|2A|2B)\s*-\s*(.+?)\s*$", re.I)   # "75 - PARIS 08"
_TRAILING_NUMBER = re.compile(r"\s+\d+$")                            # " 08" (arrondissement)

_AMOUNT = re.compile(r"(\d+(?:[.,]\d+)?)\s*euros?", re.I)
_MONTHS_PART = re.compile(r"sur\s+[\d.,]+\s*mois", re.I)             # "sur 12,0 mois"

_CONTRACT = {"CDI": "permanent", "CDD": "contract", "MIS": "contract"}
_WORK_TIME = {"temps plein": "full_time", "temps partiel": "part_time"}


def _parse_place(lieu: dict) -> tuple[str | None, str | None]:
    """'75 - PARIS 08' -> ('Île-de-France', 'Paris'). Ville seulement si une commune est precisee."""
    m = _PLACE.match(lieu.get("libelle") or "")
    if not m:
        return None, None
    region = _DEPT_TO_REGION.get(m.group(1).upper())
    ville = None
    if lieu.get("commune"):   # sans commune, le libelle ne contient que le departement
        ville = _TRAILING_NUMBER.sub("", m.group(2)).title()
    return region, ville


def _parse_salary(libelle: str | None) -> tuple[float | None, float | None]:
    """
    Extrait (min, max) du texte libre de France Travail.
    Les montants sont gardes tels quels (annuel ou mensuel) : le cleaner
    les convertit en mensuel comme pour Adzuna. Horaire / illisible -> (None, None).
    """
    if not libelle:
        return None, None
    txt = libelle.lower()
    if "annuel" not in txt and "mensuel" not in txt:
        return None, None
    amounts = [float(a.replace(",", ".")) for a in _AMOUNT.findall(_MONTHS_PART.sub("", txt))]
    if not amounts:
        return None, None
    return min(amounts), max(amounts)


def _convert_ft_offer(o: dict, source_file: str) -> dict:
    """Une offre France Travail -> memes colonnes qu'une offre Adzuna aplatie."""
    lieu = o.get("lieuTravail") or {}
    region, ville = _parse_place(lieu)
    if ville:
        zone = ["France", region, ville]
    elif region:
        zone = ["France", region]
    else:
        zone = ["France"]

    sal_min, sal_max = _parse_salary((o.get("salaire") or {}).get("libelle"))
    offer_id = o.get("id")
    default_url = f"https://candidat.francetravail.fr/offres/recherche/detail/{offer_id}"

    return {
        "id": f"ft_{offer_id}",                      # prefixe : evite une collision avec Adzuna
        "title": o.get("intitule"),
        "company.display_name": (o.get("entreprise") or {}).get("nom"),
        "location.display_name": lieu.get("libelle"),
        "location.area": zone,
        "category.label": o.get("romeLibelle"),
        "contract_type": _CONTRACT.get(o.get("typeContrat")),
        "contract_time": _WORK_TIME.get((o.get("dureeTravailLibelleConverti") or "").lower()),
        "salary_min": sal_min,
        "salary_max": sal_max,
        "created": o.get("dateCreation"),
        "description": o.get("description"),
        "redirect_url": (o.get("origineOffre") or {}).get("urlOrigine") or default_url,
        "latitude": lieu.get("latitude"),
        "longitude": lieu.get("longitude"),
        # meta collecte
        "_source": "francetravail",
        "_country": "fr",
        "_domain": "",
        "_role_hint": "",
        "_keyword": o.get("keyword_collecte", ""),
        "_collected_at": o.get("collecte_at", ""),
        "_source_file": source_file,
    }


def load_raw_francetravail(raw_dir: str = "data/raw/francetravail") -> pd.DataFrame:
    """Charge les JSON France Travail (un fichier par offre) au format commun."""
    files = glob.glob(str(Path(raw_dir) / "*.json"))
    if not files:
        logger.warning("Aucun fichier JSON trouvé dans %s", raw_dir)
        return pd.DataFrame()

    rows = []
    for f in files:
        try:
            with open(f, encoding="utf-8") as fh:
                offer = json.load(fh)
        except (json.JSONDecodeError, OSError) as exc:
            logger.warning("Fichier ignoré (%s) : %s", f, exc)
            continue
        rows.append(_convert_ft_offer(offer, f))

    if not rows:
        return pd.DataFrame()

    df = pd.DataFrame(rows)
    for col in ("salary_min", "salary_max", "latitude", "longitude"):
        df[col] = pd.to_numeric(df[col], errors="coerce")

    logger.info("Chargé %d offres France Travail depuis %d fichiers.", len(df), len(files))
    return df