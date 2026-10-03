"""
src/pipeline/cleaner.py
────────────────────────
Phase 2 — Data Preparation complète.

Étapes :
  1. Sélection et renommage des colonnes
  2. Dédoublonnage (par id, puis fuzzy sur titre+entreprise)
  3. Nettoyage du texte (HTML, espaces)
  4. Normalisation des dates + filtre période
  5. Extraction région / ville depuis zone[]
  6. Normalisation des salaires → mensuel
  7. Normalisation des titres → rôle canonique + niveau
  8. Langue de la description (fr / en / other)
  9. Score de pertinence Data/IA
  10. Rapport de qualité
"""

from __future__ import annotations

import hashlib
import logging
import re
from typing import Optional

import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)


# ══════════════════════════════════════════════════════════════════════════════
# 1. COLONNES UTILES
# ══════════════════════════════════════════════════════════════════════════════

_COLUMNS_MAP = {
    "id":                        "id",
    "title":                     "titre_original",
    "company.display_name":      "entreprise",
    "location.display_name":     "lieu",
    "location.area":             "zone",
    "category.label":            "categorie",
    "contract_type":             "type_contrat",
    "contract_time":             "temps_travail",
    "salary_min":                "salaire_min",
    "salary_max":                "salaire_max",
    "created":                   "date",
    "description":               "description",
    "redirect_url":              "lien",
    "latitude":                  "latitude",
    "longitude":                 "longitude",
    # méta collecte
    "_source":                   "source",
    "_country":                  "pays",
    "_domain":                   "domaine",
    "_role_hint":                "role_hint",
    "_keyword":                  "keyword_collecte",
    "_collected_at":             "collecte_at",
}


def _select_columns(df: pd.DataFrame) -> pd.DataFrame:
    present = {k: v for k, v in _COLUMNS_MAP.items() if k in df.columns}
    return df[list(present.keys())].rename(columns=present)


# ══════════════════════════════════════════════════════════════════════════════
# 2. DÉDOUBLONNAGE
# ══════════════════════════════════════════════════════════════════════════════

def _fingerprint(row: pd.Series) -> str:
    """Clé de déduplication : id Adzuna OU hash(titre+entreprise+5 premiers mots desc)."""
    if pd.notna(row.get("id")):
        return str(row["id"])
    titre = str(row.get("titre_original", ""))[:80]
    entreprise = str(row.get("entreprise", ""))[:40]
    desc_head = " ".join(str(row.get("description", "")).split()[:5])
    raw = f"{titre}|{entreprise}|{desc_head}".lower()
    return hashlib.md5(raw.encode()).hexdigest()


def deduplicate(df: pd.DataFrame) -> pd.DataFrame:
    before = len(df)
    # 1) doublons exacts sur id
    df = df.drop_duplicates(subset="id", keep="first")
    # 2) doublons sémantiques (même offre republiée)
    df = df.copy()
    df["_fp"] = df.apply(_fingerprint, axis=1)
    df = df.drop_duplicates(subset="_fp", keep="first").drop(columns=["_fp"])
    logger.info("Dedup : %d -> %d lignes (-%d)", before, len(df), before - len(df))
    return df


# ══════════════════════════════════════════════════════════════════════════════
# 3. NETTOYAGE TEXTE
# ══════════════════════════════════════════════════════════════════════════════

_HTML_TAG = re.compile(r"<[^>]+>")
_WHITESPACE = re.compile(r"\s+")


def _clean_text(text) -> str:
    if not isinstance(text, str) or not text.strip():
        return ""
    text = _HTML_TAG.sub(" ", text)
    text = _WHITESPACE.sub(" ", text)
    return text.strip()


def clean_texts(df: pd.DataFrame) -> pd.DataFrame:
    df["titre_original"] = df["titre_original"].apply(_clean_text)
    df["description"] = df["description"].apply(_clean_text)
    df["entreprise"] = df["entreprise"].apply(_clean_text)
    return df


# ══════════════════════════════════════════════════════════════════════════════
# 4. DATES
# ══════════════════════════════════════════════════════════════════════════════

def parse_dates(df: pd.DataFrame, min_date: Optional[str] = None) -> pd.DataFrame:
    df["date"] = pd.to_datetime(df["date"], utc=True, errors="coerce").dt.tz_localize(None)
    before = len(df)
    df = df.dropna(subset=["date"])
    if min_date:
        df = df[df["date"] >= min_date]
        logger.info("Filtre date >= %s : %d -> %d lignes", min_date, before, len(df))
    return df


# ══════════════════════════════════════════════════════════════════════════════
# 5. LOCALISATION
# ══════════════════════════════════════════════════════════════════════════════

# Correspondance ville → forme canonique (cas courants France)
_CITY_ALIASES = {
    "paris":            "Paris",
    "lyon":             "Lyon",
    "marseille":        "Marseille",
    "bordeaux":         "Bordeaux",
    "toulouse":         "Toulouse",
    "nantes":           "Nantes",
    "lille":            "Lille",
    "strasbourg":       "Strasbourg",
    "montpellier":      "Montpellier",
    "rennes":           "Rennes",
    "nice":             "Nice",
    "grenoble":         "Grenoble",
    "sophia antipolis": "Sophia Antipolis",
    "sophia-antipolis": "Sophia Antipolis",
    "aix-en-provence":  "Aix-en-Provence",
    "aix en provence":  "Aix-en-Provence",
    "remote":           "Télétravail",
    "full remote":      "Télétravail",
    "télétravail":      "Télétravail",
}

_ARRONDISSEMENT = re.compile(r"\d+[eè]?[mr]?[es]?\s+arrondissement", re.I)


def _extract_location(zone) -> pd.Series:
    """
    Extrait (region, ville) depuis le tableau zone[] d'Adzuna.
    zone = ["France", "Île-de-France", "Paris", "8ème Arrondissement"]
    """
    if not isinstance(zone, list):
        return pd.Series({"region": None, "ville": None})

    parts = [p for p in zone if not _ARRONDISSEMENT.search(str(p))]
    region = parts[1] if len(parts) >= 2 else None
    ville_raw = parts[-1] if len(parts) >= 3 else None
    # Canonicalisation
    if ville_raw:
        ville = _CITY_ALIASES.get(ville_raw.lower(), ville_raw)
    else:
        ville = None
    return pd.Series({"region": region, "ville": ville})


def normalize_locations(df: pd.DataFrame) -> pd.DataFrame:
    loc = df["zone"].apply(_extract_location)
    df["region"] = loc["region"]
    df["ville"] = loc["ville"]
    # Télétravail : détecter aussi depuis titre/description
    tele_pattern = re.compile(r"t[eé]l[eé]travail|full.?remote|remote.?first|100\s*%\s*remote", re.I)
    df["teletravail"] = (
        df["titre_original"].str.contains(tele_pattern, regex=True, na=False)
        | df["description"].str.contains(tele_pattern, regex=True, na=False)
        | (df["ville"] == "Télétravail")
    )
    return df


# ══════════════════════════════════════════════════════════════════════════════
# 6. SALAIRES
# ══════════════════════════════════════════════════════════════════════════════

def _to_monthly(s) -> Optional[float]:
    """Convertit n'importe quelle valeur Adzuna en salaire mensuel €."""
    if pd.isna(s) or s < 1:
        return None
    if s < 1_000:          # horaire ou journée – ambigu
        return None
    if s < 10_000:         # déjà mensuel
        return float(s)
    if s <= 300_000:       # annuel → mensuel
        return float(s) / 12
    return None            # aberrant


def normalize_salaries(df: pd.DataFrame) -> pd.DataFrame:
    df["salaire_mensuel_min"] = df["salaire_min"].apply(_to_monthly).round(0)
    df["salaire_mensuel_max"] = df["salaire_max"].apply(_to_monthly).round(0)

    # Alternance / stage : montant entre 300–999 € = mensuel
    alt = df["titre_original"].str.lower().str.contains(r"alternance|stage|apprenti", regex=True, na=False)
    petit = df["salaire_min"].between(300, 999.99)
    df.loc[alt & petit, "salaire_mensuel_min"] = df["salaire_min"]
    df.loc[alt & petit, "salaire_mensuel_max"] = df["salaire_max"]

    # Salaire fiable : entre 1 250 et 16 600 €/mois
    df["salaire_fiable"] = df["salaire_mensuel_min"].between(1_250, 16_600)
    df = df.drop(columns=["salaire_min", "salaire_max"], errors="ignore")
    return df


# ══════════════════════════════════════════════════════════════════════════════
# 7. NORMALISATION DES TITRES
# ══════════════════════════════════════════════════════════════════════════════

# Ordre : plus spécifique d'abord
_ROLE_PATTERNS: list[tuple[str, str]] = [
    ("LLM / GenAI Engineer",  r"llm|gen.?ai|generative.?ai"),
    ("NLP Engineer",          r"\bnlp\b.*(engineer|ingénieur)|traitement.*(langage|nlp)"),
    ("MLOps Engineer",        r"\bmlops\b"),
    ("ML Engineer",           r"machine.?learning.*(engineer|ingénieur)|ml.*(engineer|ingénieur)"),
    ("AI Engineer",           r"(ai|ia).*(engineer|ingénieur)|(engineer|ingénieur).*(ai|ia)"),
    ("Data Architect",        r"data.*(architect|architecte)|architecte.*donn"),
    ("Data Engineer",         r"data.*(engineer|ingénieur)|ingénieur.*donn"),
    ("Data Scientist",        r"data.?scien|scientifique.*donn"),
    ("Data Analyst",          r"data.?anal|analyste.*(donn|data)"),
    ("BI Developer",          r"business.?intelligen|\bbi\b.*(develop|analyst)"),
    ("Data Manager",          r"data.?manager|responsable.*donn"),
]

_LEVEL_PATTERNS: list[tuple[str, str]] = [
    ("Stage",       r"\bstage\b|\bstagiaire\b|\binternship\b"),
    ("Alternance",  r"\balternance\b|\bapprentissage\b|\bapprentis?\b"),
    ("Junior",      r"\bjunior\b|\bjr\b|\bdébutant\b|\b0.?[àa].?2.?ans?\b"),
    ("Senior",      r"\bsenior\b|\bsr\b|\bconfirmé\b|\bexpérimenté\b|\b5\+?\s*ans?\b"),
    ("Lead",        r"\blead\b|\bprincipal\b|\bstaff\b"),
    ("Manager",     r"\bmanager\b|\bdirecteur\b|\bhead.?of\b|\bvp\b"),
    ("Mid",         r"\bmid\b|\bmedior\b"),   # fallback générique
]


def _detect_role(titre: str) -> str:
    t = titre.lower()
    for role, pattern in _ROLE_PATTERNS:
        if re.search(pattern, t):
            return role
    return "Autre"


def _detect_level(titre: str) -> str:
    t = titre.lower()
    for level, pattern in _LEVEL_PATTERNS:
        if re.search(pattern, t):
            return level
    return "Unspecified"


def normalize_titles(df: pd.DataFrame) -> pd.DataFrame:
    """
    Crée deux nouvelles colonnes :
      - `role`   : rôle canonique (ex: "Data Scientist")
      - `niveau` : niveau d'expérience (ex: "Senior", "Junior", "Stage"…)
    """
    df["role"] = df["titre_original"].apply(_detect_role)
    df["niveau"] = df["titre_original"].apply(_detect_level)
    logger.info("Rôles détectés :\n%s", df["role"].value_counts().to_string())
    logger.info("Niveaux détectés :\n%s", df["niveau"].value_counts().to_string())
    return df


# ══════════════════════════════════════════════════════════════════════════════
# 8. LANGUE
# ══════════════════════════════════════════════════════════════════════════════

def detect_language(df: pd.DataFrame) -> pd.DataFrame:
    """
    Heuristique légère (sans dépendance externe) :
    compte les mots-clés français typiques dans les 200 premiers caractères.
    """
    _FR_WORDS = re.compile(r"\b(le|la|les|de|du|des|et|en|au|aux|un|une|nous|vous|est|sont|pour|avec|dans)\b", re.I)

    def _lang(desc: str) -> str:
        sample = str(desc)[:200]
        return "fr" if len(_FR_WORDS.findall(sample)) >= 3 else "en"

    df["langue"] = df["description"].apply(_lang)
    return df


# ══════════════════════════════════════════════════════════════════════════════
# 9. SCORE DE PERTINENCE DATA / IA
# ══════════════════════════════════════════════════════════════════════════════

_PERTINENCE_TITLE = re.compile(
    r"data|donn[eé]|machine.?learning|mlops|\bia\b|\bai\b|intelligence.?artificielle"
    r"|\bml\b|\bbi\b|analytique|analytique|scientist|analyst|engineer.*data|data.*engineer",
    re.I,
)
_PERTINENCE_DESC = re.compile(
    r"data|machine.?learning|deep.?learning|nlp|\bllm\b|pandas|scikit|tensorflow|pytorch|spark",
    re.I,
)


def score_relevance(df: pd.DataFrame) -> pd.DataFrame:
    """
    pertinent = 1 si le titre correspond
    pertinent = 2 si titre + description correspondent (haute pertinence)
    """
    titre_ok = df["titre_original"].str.contains(_PERTINENCE_TITLE, regex=True, na=False)
    desc_ok = df["description"].str.contains(_PERTINENCE_DESC, regex=True, na=False)
    df["pertinent"] = 0
    df.loc[titre_ok, "pertinent"] = 1
    df.loc[titre_ok & desc_ok, "pertinent"] = 2
    return df


# ══════════════════════════════════════════════════════════════════════════════
# 10. RAPPORT DE QUALITÉ
# ══════════════════════════════════════════════════════════════════════════════

def quality_report(df: pd.DataFrame) -> str:
    total = len(df)
    sep = "-" * 50
    lines = [
        sep,
        "  RAPPORT QUALITE - Phase 2",
        sep,
        f"  Offres totales         : {total}",
        f"  Pertinentes (score>=1) : {(df['pertinent'] >= 1).sum()}",
        f"  Haute pertinence (>=2) : {(df['pertinent'] == 2).sum()}",
        f"  Avec salaire mensuel   : {df['salaire_mensuel_min'].notna().sum()}",
        f"  Salaires fiables       : {df['salaire_fiable'].sum()}",
        f"  Avec ville precise     : {df['ville'].notna().sum()}",
        f"  En teletravail         : {df['teletravail'].sum()}",
        f"  Langue FR              : {(df['langue'] == 'fr').sum()}",
        f"  Langue EN              : {(df['langue'] == 'en').sum()}",
        f"  Periode : {df['date'].min().date()} -> {df['date'].max().date()}",
        "",
        "  Valeurs manquantes (%)",
    ]
    for col in ["entreprise", "lieu", "ville", "region", "salaire_mensuel_min", "description", "type_contrat"]:
        if col in df.columns:
            pct = df[col].isna().mean() * 100
            lines.append(f"    {col:<25} {pct:5.1f}%")
    lines += [
        "",
        "  Roles detectes (top 10)",
    ]
    for role, cnt in df["role"].value_counts().head(10).items():
        lines.append(f"    {role:<30} {cnt:>5}")
    lines.append(sep)
    return "\n".join(lines)


# ══════════════════════════════════════════════════════════════════════════════
# PIPELINE PRINCIPAL
# ══════════════════════════════════════════════════════════════════════════════

def run(df: pd.DataFrame, min_date: Optional[str] = None) -> pd.DataFrame:
    """
    Applique toutes les étapes de nettoyage Phase 2.

    Parameters
    ----------
    df : DataFrame brut sorti du loader
    min_date : str, ex. "2026-01-01" — filtre les offres plus anciennes

    Returns
    -------
    DataFrame nettoyé, prêt pour Phase 3 (NLP)
    """
    logger.info("=== Phase 2 — Data Preparation ===")

    logger.info("Étape 1/8 : sélection des colonnes...")
    df = _select_columns(df)

    logger.info("Étape 2/8 : nettoyage des textes...")
    df = clean_texts(df)

    logger.info("Étape 3/8 : dédoublonnage...")
    df = deduplicate(df)

    logger.info("Étape 4/8 : parsing des dates...")
    df = parse_dates(df, min_date=min_date)

    logger.info("Étape 5/8 : normalisation des localisations...")
    df = normalize_locations(df)

    logger.info("Étape 6/8 : normalisation des salaires...")
    df = normalize_salaries(df)

    logger.info("Étape 7/8 : normalisation des titres (rôle + niveau)...")
    df = normalize_titles(df)

    logger.info("Étape 8/8 : langue + score de pertinence...")
    df = detect_language(df)
    df = score_relevance(df)

    report = quality_report(df)
    logger.info("\n%s", report)
    print(report)

    return df
