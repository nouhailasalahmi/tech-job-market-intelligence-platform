"""
analyse_salaire.py  -  Phase 4
Salaires mensuels par competence et par categorie.

Usage :
    python -m src.analysis.analyse_salaire
    python -m src.analysis.analyse_salaire --min-n 10 --all
"""
from __future__ import annotations

import argparse
import logging
from pathlib import Path

import pandas as pd

from src.analysis.common import DEFAULT_DB, load_all, save_csv

logger = logging.getLogger(__name__)

SKILL_COLUMNS = ["competence", "categorie", "n_offres", "salaire_median",
                 "salaire_moyen", "p25", "p75", "prime_vs_median"]


def salary_overview(jobs: pd.DataFrame) -> dict:
    """Chiffres globaux : combien d'offres ont un salaire, et lequel."""
    s = jobs["salaire_m"].dropna()
    total = len(jobs)
    has = len(s) > 0
    return {
        "offres": total,
        "avec_salaire": len(s),
        "part_pct": round(len(s) / total * 100, 1) if total else 0.0,
        "mediane": float(s.median()) if has else None,
        "moyenne": float(s.mean()) if has else None,
        "p25": float(s.quantile(0.25)) if has else None,
        "p75": float(s.quantile(0.75)) if has else None,
    }


def salary_by_skill(jobs: pd.DataFrame, job_skills: pd.DataFrame, min_n: int = 5) -> pd.DataFrame:
    """Salaire mensuel median des offres qui demandent chaque competence."""
    sal = jobs.loc[jobs["salaire_m"].notna(), ["id", "salaire_m"]]
    merged = job_skills.merge(sal, on="id")
    if merged.empty:
        return pd.DataFrame(columns=SKILL_COLUMNS)

    out = (merged.groupby(["competence", "categorie"])["salaire_m"]
           .agg(n_offres="count", salaire_median="median", salaire_moyen="mean",
                p25=lambda s: s.quantile(0.25), p75=lambda s: s.quantile(0.75))
           .reset_index())
    out = out[out["n_offres"] >= min_n].copy()
    out["prime_vs_median"] = out["salaire_median"] - sal["salaire_m"].median()
    out = out.sort_values("salaire_median", ascending=False).round(0)
    return out.reset_index(drop=True)[SKILL_COLUMNS]


def salary_by_category(jobs: pd.DataFrame, job_skills: pd.DataFrame) -> pd.DataFrame:
    """Salaire median des offres qui contiennent au moins une competence de la categorie."""
    sal = jobs.loc[jobs["salaire_m"].notna(), ["id", "salaire_m"]]
    pairs = job_skills[["id", "categorie"]].drop_duplicates().merge(sal, on="id")
    if pairs.empty:
        return pd.DataFrame(columns=["categorie", "n_offres", "salaire_median", "salaire_moyen"])
    out = (pairs.groupby("categorie")["salaire_m"]
           .agg(n_offres="count", salaire_median="median", salaire_moyen="mean")
           .round(0).reset_index())
    return out.sort_values("salaire_median", ascending=False).reset_index(drop=True)


def print_report(ov: dict, by_skill: pd.DataFrame, by_cat: pd.DataFrame, min_n: int) -> None:
    print(f"\nOffres analysees        : {ov['offres']}")
    print(f"Offres avec salaire     : {ov['avec_salaire']} ({ov['part_pct']} %)")
    if ov["mediane"] is None:
        print("\nAucun salaire exploitable : verifie la colonne salaire (voir SALARY_COL dans common.py).")
        return

    print(f"Salaire mensuel median  : {ov['mediane']:.0f} EUR  (moyenne {ov['moyenne']:.0f}, "
          f"50 % des offres entre {ov['p25']:.0f} et {ov['p75']:.0f})")
    if ov["part_pct"] < 30:
        print("Attention : moins de 30 % des offres ont un salaire, les moyennes sont fragiles.")

    print(f"\nTop 10 competences les mieux payees (au moins {min_n} offres avec salaire)")
    if by_skill.empty:
        print("  Pas assez de donnees : baisse --min-n.")
    for _, r in by_skill.head(10).iterrows():
        print(f"  {r['competence']:<20} {r['salaire_median']:>7.0f} EUR  "
              f"({r['prime_vs_median']:+.0f})  n={int(r['n_offres'])}")

    print("\nPar categorie")
    for _, r in by_cat.iterrows():
        print(f"  {r['categorie']:<20} {r['salaire_median']:>7.0f} EUR  n={int(r['n_offres'])}")


def run(db_path: Path | str = DEFAULT_DB, min_n: int = 5, only_relevant: bool = True) -> pd.DataFrame:
    jobs, js = load_all(db_path, only_relevant)
    ov = salary_overview(jobs)
    by_skill = salary_by_skill(jobs, js, min_n)
    by_cat = salary_by_category(jobs, js)

    print_report(ov, by_skill, by_cat, min_n)
    if not by_skill.empty:
        path = save_csv(by_skill, "salaires_par_competence.csv")
        print(f"\nEcrit : {path}")
    return by_skill


def main() -> None:
    parser = argparse.ArgumentParser(description="Analyse des salaires (Phase 4)")
    parser.add_argument("--db", default=str(DEFAULT_DB))
    parser.add_argument("--min-n", type=int, default=5,
                        help="nombre minimum d'offres avec salaire par competence")
    parser.add_argument("--all", action="store_true", help="inclure les offres non pertinentes")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    run(args.db, args.min_n, only_relevant=not args.all)


if __name__ == "__main__":
    main()