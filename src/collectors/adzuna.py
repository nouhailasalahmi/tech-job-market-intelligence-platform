"""
src/collectors/adzuna.py
────────────────────────
Collecteur d'offres d'emploi via l'API Adzuna.
Refactorisé depuis collect_adzuna.py (racine) vers l'architecture modulaire.

Usage (CLI):
    python -m src.collectors.adzuna
    python -m src.collectors.adzuna --domain ai_data --max-pages 10 --max-days-old 30
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import requests
import yaml

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# ── Constantes ────────────────────────────────────────────────────────────────

BASE_URL = "https://api.adzuna.com/v1/api/jobs/{country}/search/{page}"
RESULTS_PER_PAGE = 50
PAUSE_BETWEEN_CALLS = 2.5   # secondes (~25 req/min max)
TIMEOUT = 90
DEFAULT_MAX_PAGES = 20       # 20 × 50 = 1 000 offres max par mot-clé
DEFAULT_COUNTRY = "fr"

CONFIG_PATH = Path(__file__).parents[2] / "config" / "keywords.yaml"

# ── Utilitaires ───────────────────────────────────────────────────────────────

logger = logging.getLogger(__name__)


def slugify(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")


def load_keywords(domain: Optional[str] = None) -> list[dict]:
    """Charge les mots-clés depuis config/keywords.yaml."""
    with open(CONFIG_PATH, encoding="utf-8") as f:
        config = yaml.safe_load(f)

    entries = []
    for dom, kws in config.items():
        if dom.startswith("_"):
            continue  # commentaires YAML commentés
        if domain and dom != domain:
            continue
        entries.extend(kws)
    return entries


# ── Réseau ────────────────────────────────────────────────────────────────────

def _with_retries(func, retries: int = 4):
    for attempt in range(retries):
        try:
            return func()
        except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as exc:
            wait = 2 ** (attempt + 1)
            logger.warning("Réseau (%s). Retry dans %ss (%d/%d)", type(exc).__name__, wait, attempt + 1, retries)
            time.sleep(wait)
    raise RuntimeError("Serveur inaccessible après plusieurs tentatives.")


def _fetch_page(
    session: requests.Session,
    app_id: str,
    app_key: str,
    keyword: str,
    page: int,
    country: str,
    max_days_old: Optional[int],
    retries: int = 4,
) -> requests.Response:
    params = {
        "app_id": app_id,
        "app_key": app_key,
        "what": keyword,
        "results_per_page": RESULTS_PER_PAGE,
        "sort_by": "date",
        "content-type": "application/json",
    }
    if max_days_old:
        params["max_days_old"] = max_days_old

    url = BASE_URL.format(country=country, page=page)

    for attempt in range(retries):
        resp = _with_retries(lambda: session.get(url, params=params, timeout=TIMEOUT))
        if resp.status_code == 200:
            return resp
        if resp.status_code in (401, 403):
            logger.error("Accès refusé (%s) : vérifier ADZUNA_APP_ID / ADZUNA_APP_KEY.", resp.status_code)
            resp.raise_for_status()
        if resp.status_code == 429 or resp.status_code >= 500:
            wait = 2 ** (attempt + 1)
            logger.warning("HTTP %s, retry dans %ss", resp.status_code, wait)
            time.sleep(wait)
            continue
        resp.raise_for_status()

    raise RuntimeError(f"Échec après {retries} tentatives (keyword={keyword}, page={page})")


# ── Collecte ──────────────────────────────────────────────────────────────────

def collect_keyword(
    session: requests.Session,
    app_id: str,
    app_key: str,
    entry: dict,
    out_dir: Path,
    max_pages: int,
    country: str,
    max_days_old: Optional[int],
    seen_ids: set,
    stats: dict,
) -> None:
    keyword = entry["query"]
    domain = entry.get("domain", "unknown")
    role = entry.get("role", "")

    for page in range(1, max_pages + 1):
        resp = _fetch_page(session, app_id, app_key, keyword, page, country, max_days_old)
        payload = resp.json()
        offers = payload.get("results", [])

        if not offers:
            logger.info("[%s] page %d : aucun résultat.", keyword, page)
            break

        record = {
            "source": "adzuna",
            "country": country,
            "domain": domain,
            "role": role,
            "keyword": keyword,
            "collected_at": datetime.now(timezone.utc).isoformat(),
            "page": page,
            "payload": payload,
        }
        path = out_dir / f"{slugify(keyword)}_{page:03d}.json"
        path.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")

        new = sum(1 for o in offers if str(o.get("id")) not in seen_ids)
        seen_ids.update(str(o.get("id")) for o in offers)
        stats[keyword] = stats.get(keyword, 0) + len(offers)

        logger.info(
            "[%s] page %d : %d offres (%d nouvelles) — API total : %s",
            keyword, page, len(offers), new, payload.get("count"),
        )

        if len(offers) < RESULTS_PER_PAGE:
            break
        time.sleep(PAUSE_BETWEEN_CALLS)


def run(
    domain: Optional[str] = None,
    max_pages: int = DEFAULT_MAX_PAGES,
    max_days_old: Optional[int] = None,
    country: str = DEFAULT_COUNTRY,
    out: str = "data",
) -> int:
    app_id = os.getenv("ADZUNA_APP_ID")
    app_key = os.getenv("ADZUNA_APP_KEY")
    if not app_id or not app_key:
        print("Définis ADZUNA_APP_ID et ADZUNA_APP_KEY (.env ou variables d'env).")
        return 1

    today = datetime.now().strftime("%Y-%m-%d")
    root = Path(out)
    out_dir = root / "raw" / "adzuna" / today
    log_dir = root / "logs"
    out_dir.mkdir(parents=True, exist_ok=True)
    log_dir.mkdir(parents=True, exist_ok=True)

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        handlers=[
            logging.FileHandler(log_dir / f"collect_adzuna_{today}.log", encoding="utf-8"),
            logging.StreamHandler(sys.stdout),
        ],
    )

    keywords = load_keywords(domain)
    logger.info("Collecte Adzuna — %d mots-clés, pays=%s", len(keywords), country)

    session = requests.Session()
    seen_ids: set = set()
    stats: dict = {}

    for entry in keywords:
        try:
            collect_keyword(session, app_id, app_key, entry, out_dir, max_pages, country, max_days_old, seen_ids, stats)
        except Exception as exc:
            logger.error("[%s] échec : %s", entry["query"], exc)

    logger.info("Terminé. Offres par mot-clé : %s", stats)
    logger.info("Offres uniques : %d", len(seen_ids))
    return 0


# ── CLI ───────────────────────────────────────────────────────────────────────

def main() -> int:
    parser = argparse.ArgumentParser(description="Collecte Adzuna")
    parser.add_argument("--domain", default=None, help="Filtrer par domaine (ex: ai_data)")
    parser.add_argument("--country", default=DEFAULT_COUNTRY)
    parser.add_argument("--max-pages", type=int, default=DEFAULT_MAX_PAGES)
    parser.add_argument("--max-days-old", type=int, default=None)
    parser.add_argument("--out", default="data")
    args = parser.parse_args()
    return run(
        domain=args.domain,
        max_pages=args.max_pages,
        max_days_old=args.max_days_old,
        country=args.country,
        out=args.out,
    )


if __name__ == "__main__":
    sys.exit(main())
