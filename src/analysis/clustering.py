"""
clustering.py  -  Phase 4
Regroupe les offres en grands profils de postes selon leurs competences (KMeans).

Usage :
    python -m src.analysis.clustering            # k choisi automatiquement
    python -m src.analysis.clustering --k 5
"""
from __future__ import annotations

import argparse
import logging
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from sklearn.metrics import silhouette_score

from src.analysis.common import DEFAULT_DB, load_all, save_csv, save_table

logger = logging.getLogger(__name__)

SEED = 42
MIN_OFFERS = 20      # en dessous, un clustering n'a pas de sens


def build_matrix(job_skills: pd.DataFrame, min_skills: int = 2, min_freq: int = 5) -> pd.DataFrame:
    """Matrice offres x competences (0/1). Garde les competences rares hors du calcul."""
    freq = job_skills.groupby("competence")["id"].nunique()
    keep = freq[freq >= min_freq].index
    js = job_skills[job_skills["competence"].isin(keep)]
    if js.empty:
        return pd.DataFrame()
    mat = pd.crosstab(js["id"], js["competence"]).clip(upper=1)
    return mat[mat.sum(axis=1) >= min_skills]


def choose_k(mat: pd.DataFrame, k_min: int = 3, k_max: int = 8) -> tuple[int | None, dict[int, float]]:
    """Teste plusieurs k et garde celui qui a le meilleur score de silhouette."""
    scores: dict[int, float] = {}
    for k in range(k_min, min(k_max, len(mat) - 1) + 1):
        labels = KMeans(n_clusters=k, n_init=10, random_state=SEED).fit_predict(mat)
        if len(set(labels)) > 1:
            scores[k] = float(silhouette_score(mat, labels))
    if not scores:
        return None, scores
    return max(scores, key=scores.get), scores


def fit_clusters(mat: pd.DataFrame, k: int) -> tuple[np.ndarray, np.ndarray]:
    """Renvoie (etiquettes, coordonnees 2D pour un graphique)."""
    labels = KMeans(n_clusters=k, n_init=10, random_state=SEED).fit_predict(mat)
    if min(mat.shape) >= 2:
        coords = PCA(n_components=2, random_state=SEED).fit_transform(mat)
    else:
        coords = np.zeros((len(mat), 2))
    return labels, coords


def describe_clusters(mat: pd.DataFrame, labels: np.ndarray, jobs: pd.DataFrame | None = None,
                      top_n: int = 4, min_presence: float = 0.2) -> pd.DataFrame:
    """Nomme chaque cluster avec ses competences les plus caracteristiques."""
    overall = mat.mean()
    salary = None
    if jobs is not None and "salaire_m" in jobs.columns:
        salary = jobs.drop_duplicates("id").set_index("id")["salaire_m"].reindex(mat.index)

    rows = []
    for c in sorted(set(labels)):
        mask = labels == c
        presence = mat.loc[mask].mean()
        # "caracteristique" = bien plus presente dans ce cluster que dans l'ensemble
        lift = (presence - overall)[presence >= min_presence]
        top = lift.sort_values(ascending=False).head(top_n).index.tolist()
        if not top:
            top = presence.sort_values(ascending=False).head(top_n).index.tolist()

        median = None
        if salary is not None and salary.loc[mask].notna().any():
            median = float(salary.loc[mask].median())
        rows.append({
            "cluster": int(c),
            "n_offres": int(mask.sum()),
            "competences_cles": ", ".join(top),
            "label": f"Profil {int(c) + 1} : " + " / ".join(top[:3]),
            "salaire_median": median,
        })
    return pd.DataFrame(rows)


def print_report(summary: pd.DataFrame, k: int, scores: dict[int, float], n: int) -> None:
    print(f"\nOffres clusterisees : {n}   |   k = {k}")
    if scores:
        print("Silhouette par k    : " + "  ".join(f"{kk}:{s:.2f}" for kk, s in scores.items()))
        print("(plus proche de 1 = groupes bien separes ; < 0.2 = groupes peu nets)")
    print()
    for _, r in summary.sort_values("n_offres", ascending=False).iterrows():
        salary = f"  salaire median {r['salaire_median']:.0f} EUR" if pd.notna(r["salaire_median"]) else ""
        print(f"{r['label']}")
        print(f"   {r['n_offres']} offres{salary}")
        print(f"   competences cles : {r['competences_cles']}")


def run(db_path: Path | str = DEFAULT_DB, k: int | None = None, only_relevant: bool = True,
        min_freq: int = 5, min_skills: int = 2) -> pd.DataFrame | None:
    jobs, js = load_all(db_path, only_relevant)
    mat = build_matrix(js, min_skills, min_freq)
    if len(mat) < MIN_OFFERS:
        print(f"\nSeulement {len(mat)} offres exploitables (minimum {MIN_OFFERS}) : "
              "collecte plus d'offres ou baisse --min-freq / --min-skills.")
        return None

    scores: dict[int, float] = {}
    if k is None:
        k, scores = choose_k(mat)
        if k is None:
            print("\nImpossible de choisir k automatiquement : utilise --k.")
            return None
    k = max(2, min(k, len(mat) - 1))

    labels, coords = fit_clusters(mat, k)
    summary = describe_clusters(mat, labels, jobs)

    label_by_cluster = dict(zip(summary["cluster"], summary["label"]))
    assign = pd.DataFrame({
        "id": mat.index,
        "cluster": labels.astype(int),
        "x": coords[:, 0].round(4),
        "y": coords[:, 1].round(4),
    })
    assign["cluster_label"] = assign["cluster"].map(label_by_cluster)

    save_table(assign, "job_clusters", db_path)
    path = save_csv(summary, "clusters_resume.csv")

    print_report(summary, k, scores, len(mat))
    print(f"\nTable job_clusters mise a jour, resume ecrit : {path}")
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description="Clustering des offres (Phase 4)")
    parser.add_argument("--db", default=str(DEFAULT_DB))
    parser.add_argument("--k", type=int, default=None, help="nombre de groupes (auto sinon)")
    parser.add_argument("--min-freq", type=int, default=5,
                        help="une competence doit apparaitre dans au moins N offres")
    parser.add_argument("--min-skills", type=int, default=2,
                        help="une offre doit avoir au moins N competences")
    parser.add_argument("--all", action="store_true", help="inclure les offres non pertinentes")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    run(args.db, args.k, only_relevant=not args.all,
        min_freq=args.min_freq, min_skills=args.min_skills)


if __name__ == "__main__":
    main()