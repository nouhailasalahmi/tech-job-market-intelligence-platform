"""
src/pipeline/db_loader.py
──────────────────────────
Charge le DataFrame nettoyé dans SQLite + crée les index utiles.
"""

from __future__ import annotations

import logging
import sqlite3
from pathlib import Path

import pandas as pd

logger = logging.getLogger(__name__)

DB_PATH = "data/jobs.db"


def load_to_db(df: pd.DataFrame, db_path: str = DB_PATH, table: str = "jobs") -> None:
    """
    Ecrit le DataFrame dans SQLite (remplace la table existante).
    Cree des index sur les colonnes les plus requetees.
    """
    import json as _json
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)

    # SQLite ne supporte pas les colonnes de type list/dict → serialiser en JSON
    df = df.copy()
    for col in df.columns:
        if df[col].apply(lambda x: isinstance(x, (list, dict))).any():
            df[col] = df[col].apply(lambda x: _json.dumps(x, ensure_ascii=False) if isinstance(x, (list, dict)) else x)
    conn = sqlite3.connect(db_path)
    try:
        df.to_sql(table, conn, if_exists="replace", index=False)
        logger.info("Table '%s' écrite : %d lignes.", table, len(df))

        # Index utiles pour les requêtes fréquentes
        indexes = [
            f"CREATE INDEX IF NOT EXISTS idx_{table}_role     ON {table}(role)",
            f"CREATE INDEX IF NOT EXISTS idx_{table}_ville    ON {table}(ville)",
            f"CREATE INDEX IF NOT EXISTS idx_{table}_date     ON {table}(date)",
            f"CREATE INDEX IF NOT EXISTS idx_{table}_pertinent ON {table}(pertinent)",
        ]
        for sql in indexes:
            conn.execute(sql)
        conn.commit()
        logger.info("Index créés.")

        # Mini-vérification
        count = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        logger.info("Vérification DB : %d enregistrements dans '%s'.", count, table)
    finally:
        conn.close()


def query(sql: str, db_path: str = DB_PATH) -> pd.DataFrame:
    """Utilitaire : exécuter une requête SQL et retourner un DataFrame."""
    conn = sqlite3.connect(db_path)
    try:
        return pd.read_sql(sql, conn)
    finally:
        conn.close()
