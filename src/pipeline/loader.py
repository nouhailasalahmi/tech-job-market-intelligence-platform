"""
src/pipeline/loader.py
──────────────────────
Chargement des fichiers JSON bruts (Adzuna, futures sources)
vers un DataFrame pandas unifié.
"""

from __future__ import annotations

import glob
import json
import logging
from pathlib import Path

import pandas as pd

logger = logging.getLogger(__name__)


def load_raw_adzuna(raw_dir: str = "data/raw/adzuna") -> pd.DataFrame:
    """
    Charge tous les fichiers JSON Adzuna depuis raw_dir (récursif).

    Retourne un DataFrame avec une colonne supplémentaire `_source_file`
    pour la traçabilité.
    """
    pattern = str(Path(raw_dir) / "**" / "*.json")
    files = glob.glob(pattern, recursive=True)

    if not files:
        logger.warning("Aucun fichier JSON trouvé dans %s", raw_dir)
        return pd.DataFrame()

    rows = []
    for f in files:
        try:
            rec = json.load(open(f, encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as exc:
            logger.warning("Fichier ignoré (%s) : %s", f, exc)
            continue

        offers = rec.get("payload", {}).get("results", [])
        meta = {
            "_source_file": f,
            "_source": rec.get("source", "adzuna"),
            "_country": rec.get("country", "fr"),
            "_domain": rec.get("domain", ""),
            "_role_hint": rec.get("role", ""),
            "_keyword": rec.get("keyword", ""),
            "_collected_at": rec.get("collected_at", ""),
        }
        for offer in offers:
            rows.append({**offer, **meta})

    df = pd.json_normalize(rows)
    logger.info("Chargé %d offres brutes depuis %d fichiers.", len(df), len(files))
    return df
