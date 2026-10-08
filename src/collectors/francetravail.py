"""
collect_francetravail.py  -  Collecte des offres via l'API France Travail
Ecrit un fichier JSON par offre dans data/raw/francetravail/

Prerequis :
    pip install requests python-dotenv
    .env  ->  FT_CLIENT_ID=...   FT_CLIENT_SECRET=...

Usage :
    python -m src.collectors.collect_francetravail
    python -m src.collectors.collect_francetravail --jours 31
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import requests
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = ROOT / "data" / "raw" / "francetravail"

TOKEN_URL = "https://entreprise.francetravail.fr/connexion/oauth2/access_token?realm=/partenaire"
SEARCH_URL = "https://api.francetravail.io/partenaire/offresdemploi/v2/offres/search"
SCOPE = "api_offresdemploiv2 o2dsoffre"

PAGE_SIZE = 150      # maximum d'offres par requete
MAX_RESULTS = 1150   # l'API ne permet pas d'aller au-dela (fenetre 0-1149)

KEYWORDS = [
    "data scientist",
    "data analyst",
    "data engineer",
    "machine learning",
    "MLOps",
    "intelligence artificielle",
    "business intelligence",
    "IA generative",
]


def get_token() -> str:
    """Demande un jeton d'acces (valable environ 25 minutes)."""
    load_dotenv(ROOT / ".env", override=True)
    client_id = os.getenv("FT_CLIENT_ID")
    client_secret = os.getenv("FT_CLIENT_SECRET")
    if not client_id or not client_secret:
        raise SystemExit("FT_CLIENT_ID / FT_CLIENT_SECRET manquants dans le fichier .env")

    r = requests.post(
        TOKEN_URL,
        data={
            "grant_type": "client_credentials",
            "client_id": client_id,
            "client_secret": client_secret,
            "scope": SCOPE,
        },
        timeout=30,
    )
    if not r.ok:
        raise SystemExit(f"Erreur {r.status_code} : {r.text}")
    return r.json()["access_token"]


def search_keyword(token: str, keyword: str, days: int) -> list[dict]:
    """Recupere toutes les offres pour un mot-cle (pagination par tranches de 150)."""
    headers = {"Authorization": f"Bearer {token}"}
    offers: list[dict] = []

    for start in range(0, MAX_RESULTS, PAGE_SIZE):
        params = {
            "motsCles": keyword,
            "publieeDepuis": days,
            "range": f"{start}-{min(start + PAGE_SIZE - 1, MAX_RESULTS - 1)}",
        }
        r = requests.get(SEARCH_URL, headers=headers, params=params, timeout=30)

        if r.status_code == 204:          # aucun resultat
            break
        r.raise_for_status()              # 200 et 206 (contenu partiel) sont acceptes

        batch = r.json().get("resultats", [])
        offers.extend(batch)
        if len(batch) < PAGE_SIZE:        # derniere page
            break
        time.sleep(0.3)                   # on reste poli avec l'API

    return offers


def save_offers(offers: list[dict], keyword: str, seen: set[str]) -> int:
    """Ecrit un JSON par offre. Ignore les doublons deja vus pendant ce lancement."""
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    now = datetime.now(timezone.utc).isoformat()
    new = 0

    for offer in offers:
        offer_id = offer.get("id")
        if not offer_id or offer_id in seen:
            continue
        seen.add(offer_id)

        offer["keyword_collecte"] = keyword
        offer["collecte_at"] = now
        path = OUT_DIR / f"{offer_id}.json"
        path.write_text(json.dumps(offer, ensure_ascii=False, indent=2), encoding="utf-8")
        new += 1

    return new


def run(jours: int = 31) -> int:
    """Point d'entree appelable depuis la pipeline. Retourne 0 si succes."""
    try:
        token = get_token()
    except SystemExit as e:               # get_token() utilise SystemExit
        logger.error("Authentification France Travail echouee : %s", e)
        return 1

    seen: set[str] = set()
    for kw in KEYWORDS:
        try:
            offers = search_keyword(token, kw, jours)
        except requests.RequestException:
            logger.exception("Erreur sur le mot-cle '%s'", kw)
            continue                      # on passe au mot-cle suivant
        new = save_offers(offers, kw, seen)
        logger.info("%-28s %4d trouvees, %4d nouvelles", kw, len(offers), new)

    logger.info("Total : %d offres uniques dans %s", len(seen), OUT_DIR)
    return 0 if seen else 1


def main() -> int:
    parser = argparse.ArgumentParser(description="Collecte France Travail")
    parser.add_argument("--jours", type=int, default=31, choices=[1, 3, 7, 14, 31],
                        help="offres publiees depuis X jours")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    return run(args.jours)


if __name__ == "__main__":
    sys.exit(main())