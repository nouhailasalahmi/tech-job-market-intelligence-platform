"""
skills_extractor.py  -  Phase 3 (NLP)
Trouve les competences dans chaque offre et remplit la table job_skills.

Usage :
    python -m src.analysis.nlp.skills_extractor
    python -m src.analysis.nlp.skills_extractor --all        # inclut les offres non pertinentes
"""
from __future__ import annotations

import argparse
import logging
import sqlite3
from pathlib import Path

import pandas as pd

from src.nlp.normalizer import DEFAULT_TAXONOMY, Skill, load_taxonomy

logger = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parents[3]   # src/analysis/nlp/ -> racine du projet
DEFAULT_DB = ROOT / "data" / "jobs.db"


def extract_skills(text: str, skills: list[Skill]) -> list[Skill]:
    """Renvoie les competences trouvees dans un texte."""
    return [s for s in skills if s.regex.search(text)]


def build_job_skills(df: pd.DataFrame, skills: list[Skill]) -> pd.DataFrame:
    """Une ligne par couple (offre, competence) : colonnes id, competence, categorie."""
    texts = (df["titre_original"].fillna("") + " " + df["description"].fillna("")).tolist()
    rows = []
    for offer_id, text in zip(df["id"], texts):
        for s in extract_skills(text, skills):
            rows.append((offer_id, s.name, s.category))
    return pd.DataFrame(rows, columns=["id", "competence", "categorie"])


def save_job_skills(conn: sqlite3.Connection, skills_df: pd.DataFrame) -> None:
    skills_df.to_sql("job_skills", conn, if_exists="replace", index=False)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_job_skills_id ON job_skills(id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_job_skills_comp ON job_skills(competence)")
    conn.commit()


def print_report(total: int, skills_df: pd.DataFrame, skills: list[Skill]) -> None:
    if total == 0:
        print("\nAucune offre a analyser (verifie la table jobs et le filtre pertinent).")
        return

    with_skill = skills_df["id"].nunique()
    print(f"\nOffres analysees        : {total}")
    print(f"Offres avec >= 1 skill  : {with_skill} ({with_skill / total * 100:.0f} %)")
    print(f"Offres sans competence  : {total - with_skill} ({(total - with_skill) / total * 100:.0f} %)")
    print(f"Competences detectees   : {len(skills_df)} (moyenne {len(skills_df) / total:.1f} par offre)")

    print("\nTop 15 competences")
    for name, n in skills_df["competence"].value_counts().head(15).items():
        print(f"  {name:<20} {n:>5}  ({n / total * 100:.0f} %)")

    print("\nPar categorie (nb d'offres)")
    by_cat = skills_df.groupby("categorie")["id"].nunique().sort_values(ascending=False)
    for cat, n in by_cat.items():
        print(f"  {cat:<20} {n:>5}")

    # Competences jamais trouvees : motif trop strict, ou competence absente des offres
    found = set(skills_df["competence"])
    never = [s.name for s in skills if s.name not in found]
    if never:
        print("\nJamais detectees (motif a verifier) : " + ", ".join(never))


def run(db_path: Path | str = DEFAULT_DB,
        taxonomy_path: Path | str = DEFAULT_TAXONOMY,
        only_relevant: bool = True) -> pd.DataFrame:
    skills = load_taxonomy(taxonomy_path)

    conn = sqlite3.connect(db_path)
    try:
        query = "SELECT id, titre_original, description FROM jobs"
        if only_relevant:
            # pertinent : 1 = titre OK, 2 = titre + description OK (meilleures offres)
            query += " WHERE pertinent >= 1"
        df = pd.read_sql(query, conn)

        skills_df = build_job_skills(df, skills)
        save_job_skills(conn, skills_df)
    finally:
        conn.close()

    print_report(len(df), skills_df, skills)
    return skills_df


def main() -> None:
    parser = argparse.ArgumentParser(description="Extraction des competences (Phase 3)")
    parser.add_argument("--db", default=str(DEFAULT_DB))
    parser.add_argument("--taxonomy", default=str(DEFAULT_TAXONOMY))
    parser.add_argument("--all", action="store_true",
                        help="analyser aussi les offres non pertinentes")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    run(args.db, args.taxonomy, only_relevant=not args.all)


if __name__ == "__main__":
    main()