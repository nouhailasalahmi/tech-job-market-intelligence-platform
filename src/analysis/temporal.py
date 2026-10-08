"""
temporal.py  -  Phase 4
Quelles competences montent ou baissent dans le temps ?

Usage :
    python -m src.analysis.temporal
    python -m src.analysis.temporal --min-n 15
"""
from __future__ import annotations

import argparse
import logging
from pathlib import Path

import pandas as pd

from src.analysis.common import DEFAULT_DB, load_all, save_csv

logger = logging.getLogger(__name__)

MIN_SPAN_DAYS = 14   # en dessous, la tendance est peu fiable


def _period_freq(dates: pd.Series) -> str:
    """Mois si les donnees couvrent au moins 2 mois, sinon semaines."""
    span = (dates.max() - dates.min()).days
    return "M" if span >= 60 else "W"


def monthly_share(jobs: pd.DataFrame, job_skills: pd.DataFrame, freq: str | None = None) -> pd.DataFrame:
    """Part (%) des offres de chaque periode qui demandent chaque competence."""
    cols = ["periode", "competence", "n_offres", "part_pct"]
    df = jobs.loc[jobs["date_offre"].notna(), ["id", "date_offre"]]
    if df.empty:
        return pd.DataFrame(columns=cols)

    freq = freq or _period_freq(df["date_offre"])
    df = df.assign(periode=df["date_offre"].dt.to_period(freq).dt.to_timestamp())
    n_per_period = df.groupby("periode")["id"].nunique()

    js = job_skills.merge(df[["id", "periode"]], on="id")
    out = js.groupby(["periode", "competence"])["id"].nunique().reset_index(name="n_offres")
    out["part_pct"] = (out["n_offres"] / out["periode"].map(n_per_period) * 100).round(1)
    return out[cols]


def skill_trends(jobs: pd.DataFrame, job_skills: pd.DataFrame, min_n: int = 10) -> pd.DataFrame | None:
    """Compare la 1re moitie des offres (les plus anciennes) a la 2e moitie.

    Renvoie None s'il n'y a pas au moins 2 dates differentes.
    """
    df = jobs.loc[jobs["date_offre"].notna(), ["id", "date_offre"]].sort_values("date_offre")
    if df["date_offre"].dt.normalize().nunique() < 2:
        return None

    half = len(df) // 2
    df = df.assign(periode=["debut"] * half + ["fin"] * (len(df) - half))
    n = df["periode"].value_counts()

    js = job_skills.merge(df[["id", "periode"]], on="id")
    counts = js.groupby(["competence", "periode"])["id"].nunique().unstack(fill_value=0)
    for col in ("debut", "fin"):
        if col not in counts:
            counts[col] = 0

    out = pd.DataFrame({
        "n_total": counts["debut"] + counts["fin"],
        "part_debut": counts["debut"] / n.get("debut", 1) * 100,
        "part_fin": counts["fin"] / n.get("fin", 1) * 100,
    })
    out["evolution_pts"] = out["part_fin"] - out["part_debut"]
    out = out[out["n_total"] >= min_n].round(1)
    return out.sort_values("evolution_pts", ascending=False).reset_index()


def print_report(trends: pd.DataFrame | None, jobs: pd.DataFrame, min_n: int) -> None:
    dates = jobs["date_offre"].dropna()
    if dates.empty:
        print("\nAucune date exploitable : verifie la colonne date (voir DATE_COL dans common.py).")
        return
    span = (dates.max() - dates.min()).days
    print(f"\nOffres datees : {len(dates)} sur {len(jobs)}  |  du {dates.min():%Y-%m-%d} "
          f"au {dates.max():%Y-%m-%d} ({span} jours)")

    if trends is None:
        print("Une seule date : relance la collecte regulierement pour voir une evolution.")
        return
    if span < MIN_SPAN_DAYS:
        print(f"Attention : moins de {MIN_SPAN_DAYS} jours de donnees, tendance peu fiable.")
    if trends.empty:
        print(f"Aucune competence avec au moins {min_n} offres : baisse --min-n.")
        return

    print("\nEn hausse (part des offres, 1re moitie -> 2e moitie)")
    for _, r in trends.head(10).iterrows():
        print(f"  {r['competence']:<20} {r['part_debut']:>5.1f} % -> {r['part_fin']:>5.1f} %  "
              f"({r['evolution_pts']:+.1f} pts)")
    print("\nEn baisse")
    for _, r in trends.tail(10).iloc[::-1].iterrows():
        print(f"  {r['competence']:<20} {r['part_debut']:>5.1f} % -> {r['part_fin']:>5.1f} %  "
              f"({r['evolution_pts']:+.1f} pts)")


def run(db_path: Path | str = DEFAULT_DB, min_n: int = 10, only_relevant: bool = True) -> pd.DataFrame | None:
    jobs, js = load_all(db_path, only_relevant)
    trends = skill_trends(jobs, js, min_n)
    print_report(trends, jobs, min_n)
    if trends is not None and not trends.empty:
        path = save_csv(trends, "tendances.csv")
        print(f"\nEcrit : {path}")
    return trends


def main() -> None:
    parser = argparse.ArgumentParser(description="Tendances des competences (Phase 4)")
    parser.add_argument("--db", default=str(DEFAULT_DB))
    parser.add_argument("--min-n", type=int, default=10,
                        help="nombre minimum d'offres par competence")
    parser.add_argument("--all", action="store_true", help="inclure les offres non pertinentes")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    run(args.db, args.min_n, only_relevant=not args.all)


if __name__ == "__main__":
    main()