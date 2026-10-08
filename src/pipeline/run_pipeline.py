"""
src/analysis/pipeline/run_pipeline.py
─────────────────────────────────────
Orchestrateur de la pipeline complète Phase 1 → Phase 2.
Sources : Adzuna + France Travail.

Usage :
    # Phase 2 uniquement (données déjà collectées)
    python -m src.analysis.pipeline.run_pipeline

    # Phase 1 (Adzuna + France Travail) + Phase 2
    python -m src.analysis.pipeline.run_pipeline --collect

    # Collecter une seule source
    python -m src.analysis.pipeline.run_pipeline --collect --source adzuna
    python -m src.analysis.pipeline.run_pipeline --collect --source francetravail --jours 7

    # Avec filtre de date
    python -m src.analysis.pipeline.run_pipeline --collect --min-date 2026-09-01
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
from pathlib import Path

import pandas as pd

from src.pipeline.loader import load_raw_adzuna, load_raw_francetravail
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


def collect_sources(args: argparse.Namespace) -> bool:
    """
    Lance la collecte des sources demandées.
    Une source qui échoue n'arrête pas l'autre.
    Retourne True si au moins une source a réussi.
    """
    results: dict[str, bool] = {}

    if args.source in ("adzuna", "all"):
        logger.info("--- Phase 1 : Collecte Adzuna ---")
        try:
            from src.collectors.adzuna import run as collect_adzuna
            rc = collect_adzuna(
                domain=args.domain,
                max_pages=args.max_pages,
                max_days_old=args.max_days_old,
            )
            results["Adzuna"] = (rc == 0)
        except Exception:
            logger.exception("Collecte Adzuna : exception inattendue")
            results["Adzuna"] = False

    if args.source in ("francetravail", "all"):
        logger.info("--- Phase 1 : Collecte France Travail ---")
        try:
            from src.collectors.collect_francetravail import run as collect_ft
            rc = collect_ft(jours=args.jours)
            results["France Travail"] = (rc == 0)
        except Exception:
            logger.exception("Collecte France Travail : exception inattendue")
            results["France Travail"] = False

    for name, ok in results.items():
        if ok:
            logger.info("Collecte %s : OK", name)
        else:
            logger.error("Collecte %s : ÉCHEC", name)

    return any(results.values())


def main() -> int:
    parser = argparse.ArgumentParser(description="Pipeline Phase 1 → Phase 2")
    parser.add_argument("--collect", action="store_true",
                        help="Lancer la collecte (Adzuna + France Travail) avant le nettoyage")
    parser.add_argument("--source", choices=["adzuna", "francetravail", "all"], default="all",
                        help="Source(s) à collecter avec --collect (défaut : all)")
    parser.add_argument("--domain", default=None, help="Adzuna : domaine ciblé")
    parser.add_argument("--max-pages", type=int, default=20, help="Adzuna : pages max")
    parser.add_argument("--max-days-old", type=int, default=None, help="Adzuna : ancienneté max")
    parser.add_argument("--jours", type=int, default=31, choices=[1, 3, 7, 14, 31],
                        help="France Travail : offres publiées depuis X jours")
    parser.add_argument("--raw-dir", default="data/raw/adzuna",
                        help="Dossier des JSON Adzuna")
    parser.add_argument("--ft-dir", default="data/raw/francetravail",
                        help="Dossier des JSON France Travail")
    parser.add_argument("--min-date", default=None, help="Ex : 2026-08-01")
    parser.add_argument("--out-csv", default="data/processed/jobs_clean.csv")
    parser.add_argument("--db", default="data/jobs.db")
    args = parser.parse_args()

    setup_logging()
    logger.info("==== AI & Data Job Market Pipeline ====")

    # ── Phase 1 : collecte optionnelle ────────────────────────────
    if args.collect:
        if not collect_sources(args):
            logger.error("Aucune source n'a pu être collectée.")
            return 1

    # ── Phase 2 : chargement des deux sources ─────────────────────
    logger.info("--- Phase 2 : Chargement des données brutes ---")
    df_adz = load_raw_adzuna(args.raw_dir)
    df_ft = load_raw_francetravail(args.ft_dir)
    logger.info("Sources : Adzuna=%d, France Travail=%d", len(df_adz), len(df_ft))

    df_raw = pd.concat([df_adz, df_ft], ignore_index=True)
    if df_raw.empty:
        logger.error("Aucune donnée brute trouvée (%s, %s)", args.raw_dir, args.ft_dir)
        return 1

    # Ids Adzuna (nombres) et France Travail (texte "ft_...") : tout en texte
    df_raw["id"] = df_raw["id"].astype(str)

    # ── Phase 2 : nettoyage ───────────────────────────────────────
    logger.info("--- Phase 2 : Nettoyage et structuration ---")
    df_clean = clean(df_raw, min_date=args.min_date)

    # ── Sauvegarde ────────────────────────────────────────────────
    os.makedirs(str(Path(args.out_csv).parent), exist_ok=True)
    df_clean.to_csv(args.out_csv, index=False, encoding="utf-8-sig")
    logger.info("CSV sauvegardé : %s (%d lignes)", args.out_csv, len(df_clean))

    load_to_db(df_clean, db_path=args.db)
    logger.info("Base SQLite mise à jour : %s", args.db)
    logger.info("==== Pipeline terminée ====")
    return 0


if __name__ == "__main__":
    sys.exit(main())