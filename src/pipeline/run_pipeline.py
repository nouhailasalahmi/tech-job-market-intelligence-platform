"""
src/pipeline/run_pipeline.py
─────────────────────────────
Orchestrateur de la pipeline complète Phase 1 → Phase 2.

Usage :
    # Phase 2 uniquement (données déjà collectées)
    python -m src.pipeline.run_pipeline

    # Phase 1 + Phase 2
    python -m src.pipeline.run_pipeline --collect

    # Avec filtre de date
    python -m src.pipeline.run_pipeline --min-date 2026-09-01
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from src.pipeline.loader import load_raw_adzuna
from src.pipeline.cleaner import run as clean
from src.pipeline.db_loader import load_to_db

logger = logging.getLogger(__name__)


def setup_logging(log_dir: str = "data/logs") -> None:
    from datetime import datetime
    Path(log_dir).mkdir(parents=True, exist_ok=True)
    today = datetime.now().strftime("%Y-%m-%d")
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s — %(message)s",
        handlers=[
            logging.FileHandler(f"{log_dir}/pipeline_{today}.log", encoding="utf-8"),
            logging.StreamHandler(sys.stdout),
        ],
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Pipeline Phase 1 → Phase 2")
    parser.add_argument("--collect", action="store_true", help="Lancer la collecte avant le nettoyage")
    parser.add_argument("--domain", default=None)
    parser.add_argument("--max-pages", type=int, default=20)
    parser.add_argument("--max-days-old", type=int, default=None)
    parser.add_argument("--raw-dir", default="data/raw/adzuna")
    parser.add_argument("--min-date", default=None, help="Ex : 2026-08-01")
    parser.add_argument("--out-csv", default="data/processed/jobs_clean.csv")
    parser.add_argument("--db", default="data/jobs.db")
    args = parser.parse_args()

    setup_logging()
    logger.info("==== AI & Data Job Market Pipeline ====")

    # ── Phase 1 : collecte optionnelle ────────────────────────────
    if args.collect:
        logger.info("--- Phase 1 : Collecte Adzuna ---")
        from src.collectors.adzuna import run as collect
        rc = collect(domain=args.domain, max_pages=args.max_pages, max_days_old=args.max_days_old)
        if rc != 0:
            logger.error("Collecte échouée.")
            return rc

    # ── Phase 2 : nettoyage ───────────────────────────────────────
    logger.info("--- Phase 2 : Chargement des données brutes ---")
    df_raw = load_raw_adzuna(args.raw_dir)
    if df_raw.empty:
        logger.error("Aucune donnée brute trouvée dans %s", args.raw_dir)
        return 1

    logger.info("--- Phase 2 : Nettoyage et structuration ---")
    df_clean = clean(df_raw, min_date=args.min_date)

    # ── Sauvegarde ────────────────────────────────────────────────
    import os
    os.makedirs(str(Path(args.out_csv).parent), exist_ok=True)
    df_clean.to_csv(args.out_csv, index=False, encoding="utf-8-sig")
    logger.info("CSV sauvegardé : %s (%d lignes)", args.out_csv, len(df_clean))

    load_to_db(df_clean, db_path=args.db)
    logger.info("Base SQLite mise à jour : %s", args.db)
    logger.info("==== Pipeline terminee ====")
    return 0


if __name__ == "__main__":
    sys.exit(main())
