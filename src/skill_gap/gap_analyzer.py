"""
gap_analyzer.py  -  Phase 5
Compare mes competences (config/my_profile.yaml) a la demande du marche.

Usage :
    python -m src.analysis.skill_gap.gap_analyzer
    python -m src.analysis.skill_gap.gap_analyzer --profile config/my_profile.yaml --all
"""
from __future__ import annotations

import argparse
import logging
from pathlib import Path

import pandas as pd
import yaml

from src.analysis.analyse_salaire import salary_by_skill
from src.analysis.common import DEFAULT_DB, ROOT, load_all, save_csv

logger = logging.getLogger(__name__)

DEFAULT_PROFILE = ROOT / "config" / "my_profile.yaml"
GOOD_COVERAGE = 0.7     # une offre est "bien couverte" si je connais >= 70 % de ses competences


def load_profile(path: Path | str = DEFAULT_PROFILE) -> list[str]:
    """Lit la liste `competences:` du YAML."""
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Profil introuvable : {path} (cree config/my_profile.yaml)")
    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    items = data.get("competences") or []
    return [str(s).strip() for s in items if s is not None and str(s).strip()]


def market_demand(jobs: pd.DataFrame, job_skills: pd.DataFrame) -> pd.DataFrame:
    """Part des offres qui demandent chaque competence."""
    total = jobs["id"].nunique()
    demand = (job_skills.groupby(["competence", "categorie"])["id"].nunique()
              .reset_index(name="n_offres"))
    demand["demande_pct"] = (demand["n_offres"] / total * 100).round(1) if total else 0.0
    return demand.sort_values("n_offres", ascending=False).reset_index(drop=True)


def compute_gap(demand: pd.DataFrame, profile: list[str]) -> pd.DataFrame:
    """Ajoute la colonne `possede` (True si la competence est dans mon profil)."""
    mine = {p.lower() for p in profile}
    out = demand.copy()
    out["possede"] = out["competence"].str.lower().isin(mine)
    return out


def unknown_in_profile(demand: pd.DataFrame, profile: list[str]) -> list[str]:
    """Noms du profil qui ne correspondent a aucune competence detectee (faute de frappe ?)."""
    known = set(demand["competence"].str.lower())
    return [p for p in profile if p.lower() not in known]


def coverage_per_offer(job_skills: pd.DataFrame, profile: list[str]) -> pd.Series:
    """Pour chaque offre : part de ses competences que je possede (0 a 1)."""
    mine = {p.lower() for p in profile}
    owned = job_skills["competence"].str.lower().isin(mine)
    return owned.groupby(job_skills["id"]).mean()


def add_salary_premium(gap: pd.DataFrame, jobs: pd.DataFrame, job_skills: pd.DataFrame) -> pd.DataFrame:
    """Ajoute `prime_vs_median` (EUR/mois) quand assez d'offres ont un salaire."""
    sal = salary_by_skill(jobs, job_skills, min_n=3)[["competence", "prime_vs_median"]]
    return gap.merge(sal, on="competence", how="left")


def print_report(gap: pd.DataFrame, coverage: pd.Series, unknown: list[str], n_profile: int) -> None:
    print(f"\nCompetences dans mon profil : {n_profile}")
    if unknown:
        print("Jamais detectees dans les offres (faute de frappe, ou competence absente de la taxonomie ?) : "
              + ", ".join(unknown))

    if len(coverage):
        good = (coverage >= GOOD_COVERAGE).mean() * 100
        print(f"Couverture moyenne des offres : {coverage.mean() * 100:.0f} %")
        print(f"Offres ou je connais >= {GOOD_COVERAGE * 100:.0f} % des competences : {good:.0f} %")

    print("\nTop 10 competences demandees que je n'ai pas")
    missing = gap[~gap["possede"]].head(10)
    if missing.empty:
        print("  Aucune : ton profil couvre tout ce qui est detecte.")
    for _, r in missing.iterrows():
        premium = ""
        if "prime_vs_median" in gap and pd.notna(r.get("prime_vs_median")):
            premium = f"  salaire {r['prime_vs_median']:+.0f} EUR"
        print(f"  {r['competence']:<20} {r['demande_pct']:>5.1f} % des offres{premium}")

    print("\nMes competences les plus demandees")
    for _, r in gap[gap["possede"]].head(5).iterrows():
        print(f"  {r['competence']:<20} {r['demande_pct']:>5.1f} % des offres")


def run(db_path: Path | str = DEFAULT_DB,
        profile_path: Path | str = DEFAULT_PROFILE,
        only_relevant: bool = True) -> pd.DataFrame:
    profile = load_profile(profile_path)
    jobs, js = load_all(db_path, only_relevant)

    demand = market_demand(jobs, js)
    gap = add_salary_premium(compute_gap(demand, profile), jobs, js)
    coverage = coverage_per_offer(js, profile)

    print_report(gap, coverage, unknown_in_profile(demand, profile), len(profile))
    path = save_csv(gap, "skill_gap.csv")
    print(f"\nEcrit : {path}")
    return gap


def main() -> None:
    parser = argparse.ArgumentParser(description="Skill gap (Phase 5)")
    parser.add_argument("--db", default=str(DEFAULT_DB))
    parser.add_argument("--profile", default=str(DEFAULT_PROFILE))
    parser.add_argument("--all", action="store_true", help="inclure les offres non pertinentes")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    run(args.db, args.profile, only_relevant=not args.all)


if __name__ == "__main__":
    main()