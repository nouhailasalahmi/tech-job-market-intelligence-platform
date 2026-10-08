"""
common.py  -  fonctions partagees par les analyses (Phases 4 a 6)

- charge les offres (table jobs) et les competences (table job_skills)
- detecte automatiquement les colonnes salaire et date, meme si leur nom change
"""
from __future__ import annotations

import logging
import sqlite3
from pathlib import Path

import pandas as pd

logger = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parents[2]      # src/analysis/ -> racine du projet
DEFAULT_DB = ROOT / "data" / "jobs.db"
PROCESSED_DIR = ROOT / "data" / "processed"

# --- A ADAPTER SI LA DETECTION AUTOMATIQUE SE TROMPE -------------------------
SALARY_COL: str | None = None          # ex : "salaire_mensuel"
DATE_COL: str | None = None            # ex : "date_publication"
SALARY_MIN, SALARY_MAX = 800, 20000    # euros / mois : le reste est ignore (aberrant)
# -----------------------------------------------------------------------------

_SALARY_WORDS = ("salaire", "salary")
_SALARY_EXCLUDE = ("predict", "is_", "devise", "currency", "period", "unite", "unit", "flag")


# ------------------------------------------------------------------ colonnes --
def _auto_salary(df: pd.DataFrame) -> tuple[pd.Series | None, str]:
    """Devine la colonne de salaire mensuel. Renvoie (serie, nom utilise)."""
    cands: dict[str, pd.Series] = {}
    for c in df.columns:
        low = c.lower()
        if any(w in low for w in _SALARY_WORDS) and not any(x in low for x in _SALARY_EXCLUDE):
            s = pd.to_numeric(df[c], errors="coerce")
            if s.notna().any():
                cands[c] = s
    if not cands:
        return None, ""

    monthly = {c: s for c, s in cands.items() if "mens" in c.lower() or "month" in c.lower()}
    pool = monthly or cands

    # 1) une colonne "moyenne" deja calculee
    for c, s in pool.items():
        if any(k in c.lower() for k in ("moy", "mean", "avg", "mid")):
            return s, c

    # 2) colonnes min + max -> milieu de la fourchette
    mins = [c for c in pool if "min" in c.lower()]
    maxs = [c for c in pool if "max" in c.lower()]
    if mins and maxs:
        mid = pd.concat([pool[mins[0]], pool[maxs[0]]], axis=1).mean(axis=1)
        return mid, f"{mins[0]} + {maxs[0]}"

    # 3) premiere colonne disponible
    c = next(iter(pool))
    return pool[c], c


def detect_salary(df: pd.DataFrame, col: str | None = None) -> pd.Series:
    """Serie des salaires mensuels (NaN si inconnu ou aberrant)."""
    name = col or SALARY_COL
    if name:
        raw, used = pd.to_numeric(df[name], errors="coerce"), name
    else:
        raw, used = _auto_salary(df)

    if raw is None:
        logger.warning("Aucune colonne de salaire trouvee : analyses de salaires vides")
        return pd.Series(float("nan"), index=df.index)

    logger.info("Colonne salaire utilisee : %s", used)
    return raw.where(raw.between(SALARY_MIN, SALARY_MAX))


def detect_date(df: pd.DataFrame, col: str | None = None) -> pd.Series:
    """Serie de dates (NaT si inconnu). Prefere la date de publication."""
    name = col or DATE_COL
    if name is None:
        cands = [c for c in df.columns
                 if "date" in c.lower() or c.lower() in ("created", "published", "created_at")]
        order = ("public", "creat", "post", "collect")
        name = next((c for k in order for c in cands if k in c.lower()),
                    cands[0] if cands else None)

    if name is None or name not in df.columns:
        return pd.Series(pd.NaT, index=df.index, dtype="datetime64[ns]")

    logger.info("Colonne date utilisee : %s", name)
    dates = pd.to_datetime(df[name], errors="coerce", utc=True, format="mixed")
    return dates.dt.tz_localize(None)


# ------------------------------------------------------------------- lecture --
def _connect(db_path: Path | str) -> sqlite3.Connection:
    path = Path(db_path)
    if not path.exists():       # sqlite3.connect creerait un fichier vide sinon
        raise FileNotFoundError(f"Base introuvable : {path} (lance d'abord le pipeline)")
    return sqlite3.connect(path)


def load_jobs(db_path: Path | str = DEFAULT_DB, only_relevant: bool = True) -> pd.DataFrame:
    """Offres + 2 colonnes calculees : salaire_m (EUR/mois) et date_offre."""
    conn = _connect(db_path)
    try:
        df = pd.read_sql("SELECT * FROM jobs", conn)
    finally:
        conn.close()

    if only_relevant and "pertinent" in df.columns:
        df = df[df["pertinent"] >= 1]
    df = df.reset_index(drop=True)
    df["salaire_m"] = detect_salary(df)
    df["date_offre"] = detect_date(df)
    return df


def load_job_skills(db_path: Path | str = DEFAULT_DB) -> pd.DataFrame:
    """Table job_skills : une ligne par (offre, competence)."""
    conn = _connect(db_path)
    try:
        df = pd.read_sql("SELECT id, competence, categorie FROM job_skills", conn)
    except (pd.errors.DatabaseError, sqlite3.OperationalError) as exc:
        raise RuntimeError(
            "Table job_skills introuvable : lance d'abord "
            "python -m src.analysis.nlp.skills_extractor"
        ) from exc
    finally:
        conn.close()
    return df.drop_duplicates(["id", "competence"]).reset_index(drop=True)


def load_all(db_path: Path | str = DEFAULT_DB,
             only_relevant: bool = True) -> tuple[pd.DataFrame, pd.DataFrame]:
    """(offres, competences) avec les competences filtrees sur les offres gardees."""
    jobs = load_jobs(db_path, only_relevant)
    skills = load_job_skills(db_path)
    skills = skills[skills["id"].isin(jobs["id"])].reset_index(drop=True)
    return jobs, skills


def load_table(name: str, db_path: Path | str = DEFAULT_DB) -> pd.DataFrame | None:
    """Lit une table quelconque, ou renvoie None si elle n'existe pas."""
    if not name.isidentifier():
        raise ValueError(f"Nom de table invalide : {name}")
    conn = _connect(db_path)
    try:
        return pd.read_sql(f"SELECT * FROM {name}", conn)
    except (pd.errors.DatabaseError, sqlite3.OperationalError):
        return None
    finally:
        conn.close()


# ------------------------------------------------------------------ ecriture --
def save_table(df: pd.DataFrame, name: str, db_path: Path | str = DEFAULT_DB) -> None:
    conn = _connect(db_path)
    try:
        df.to_sql(name, conn, if_exists="replace", index=False)
        conn.commit()
    finally:
        conn.close()


def save_csv(df: pd.DataFrame, filename: str) -> Path:
    """Ecrit dans data/processed/ (utf-8-sig : s'ouvre correctement dans Excel)."""
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    path = PROCESSED_DIR / filename
    df.to_csv(path, index=False, encoding="utf-8-sig")
    return path