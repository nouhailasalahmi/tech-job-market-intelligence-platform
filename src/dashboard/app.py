"""
app.py  -  Phase 6 : dashboard Streamlit

Lancer depuis la racine du projet :
    streamlit run src/dashboard/app.py
"""
from __future__ import annotations

import sys
from pathlib import Path

# Permet "from src...." meme quand Streamlit lance le script par son chemin
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pandas as pd                      # noqa: E402
import plotly.express as px              # noqa: E402
import streamlit as st                   # noqa: E402

from src.analysis import common          # noqa: E402
from src.analysis.analyse_salaire import salary_by_skill, salary_overview   # noqa: E402
from src.skill_gap.gap_analyzer import (                           # noqa: E402
    DEFAULT_PROFILE, coverage_per_offer, load_profile, market_demand,
)
from src.analysis.temporal import monthly_share, skill_trends               # noqa: E402

st.set_page_config(page_title="Tech Job Market", page_icon="📊", layout="wide")


@st.cache_data(show_spinner="Chargement des offres...")
def load_data(only_relevant: bool) -> tuple[pd.DataFrame, pd.DataFrame]:
    return common.load_all(only_relevant=only_relevant)


@st.cache_data(show_spinner=False)
def load_clusters() -> pd.DataFrame | None:
    return common.load_table("job_clusters")


# ------------------------------------------------------------------ sidebar --
st.sidebar.title("📊 Tech Job Market")
only_relevant = st.sidebar.checkbox("Uniquement les offres pertinentes", value=True)
if not only_relevant:
    st.sidebar.caption("Les compétences ne sont extraites que pour les offres analysées par "
                       "`skills_extractor` : lance-le avec `--all` pour couvrir toutes les offres.")
if st.sidebar.button("Recharger les données"):
    st.cache_data.clear()

try:
    jobs, js = load_data(only_relevant)
except (FileNotFoundError, RuntimeError) as exc:
    st.error(str(exc))
    st.stop()

if jobs.empty:
    st.warning("Aucune offre à afficher : vérifie la table jobs et le filtre « pertinent ».")
    st.stop()

demand = market_demand(jobs, js)
overview = salary_overview(jobs)

# --------------------------------------------------------------------- KPIs --
st.title("Marché de l'emploi Tech : compétences, salaires, tendances")

k1, k2, k3, k4 = st.columns(4)
k1.metric("Offres analysées", f"{len(jobs):,}")
k2.metric("Avec ≥ 1 compétence", f"{js['id'].nunique() / len(jobs) * 100:.0f} %")
k3.metric("Avec salaire", f"{overview['part_pct']} %")
k4.metric("Salaire médian", f"{overview['mediane']:,.0f} €/mois" if overview["mediane"] else "n/a")

tab_over, tab_skills, tab_sal, tab_gap, tab_cluster, tab_trend = st.tabs(
    ["Vue d'ensemble", "Compétences", "Salaires", "Skill gap", "Profils de postes", "Tendances"]
)

# ------------------------------------------------------------ vue d'ensemble --
with tab_over:
    st.subheader("Top 15 des compétences demandées")
    top = demand.head(15).sort_values("demande_pct")
    fig = px.bar(top, x="demande_pct", y="competence", color="categorie", orientation="h",
                 labels={"demande_pct": "% des offres", "competence": "", "categorie": "Catégorie"})
    st.plotly_chart(fig)

    st.subheader("Offres par catégorie de compétences")
    by_cat = (js.groupby("categorie")["id"].nunique().sort_values(ascending=False)
              .reset_index(name="n_offres"))
    st.plotly_chart(px.bar(by_cat, x="categorie", y="n_offres",
                           labels={"categorie": "", "n_offres": "Nombre d'offres"}))

# --------------------------------------------------------------- compétences --
with tab_skills:
    cats = sorted(demand["categorie"].unique())
    cat = st.selectbox("Catégorie", cats)
    sub = demand[demand["categorie"] == cat].sort_values("demande_pct")
    st.plotly_chart(px.bar(sub, x="demande_pct", y="competence", orientation="h",
                           labels={"demande_pct": "% des offres", "competence": ""}))
    st.dataframe(sub.sort_values("demande_pct", ascending=False), hide_index=True)

# ------------------------------------------------------------------ salaires --
with tab_sal:
    if overview["avec_salaire"] == 0:
        st.info("Aucun salaire exploitable. Vérifie SALARY_COL dans src/analysis/common.py.")
    else:
        if overview["part_pct"] < 30:
            st.warning(f"Seulement {overview['part_pct']} % des offres ont un salaire : "
                       "les moyennes sont à prendre avec prudence.")
        min_n = st.slider("Nombre minimum d'offres avec salaire par compétence", 1, 30, 5)
        by_skill = salary_by_skill(jobs, js, min_n)

        st.subheader("Distribution des salaires mensuels")
        st.plotly_chart(px.histogram(jobs.dropna(subset=["salaire_m"]), x="salaire_m", nbins=30,
                                     labels={"salaire_m": "€/mois"}))

        st.subheader("Compétences les mieux payées")
        if by_skill.empty:
            st.info("Pas assez d'offres avec salaire : baisse le seuil.")
        else:
            best = by_skill.head(15).sort_values("salaire_median")
            st.plotly_chart(px.bar(best, x="salaire_median", y="competence", orientation="h",
                                   color="categorie",
                                   labels={"salaire_median": "Salaire médian (€/mois)",
                                           "competence": "", "categorie": "Catégorie"}))
            st.dataframe(by_skill, hide_index=True)

# ----------------------------------------------------------------- skill gap --
with tab_gap:
    st.subheader("Mon profil face au marché")
    options = sorted(demand["competence"])
    try:
        profile = {p.lower() for p in load_profile(DEFAULT_PROFILE)}
    except FileNotFoundError:
        profile = set()
    mine = st.multiselect("Mes compétences", options,
                          default=[o for o in options if o.lower() in profile])

    gap = demand.assign(possede=demand["competence"].isin(mine))
    coverage = coverage_per_offer(js, mine)
    g1, g2 = st.columns(2)
    g1.metric("Couverture moyenne des offres", f"{coverage.mean() * 100:.0f} %" if len(coverage) else "n/a")
    g2.metric("Offres où je connais ≥ 70 %",
              f"{(coverage >= 0.7).mean() * 100:.0f} %" if len(coverage) else "n/a")

    missing = gap[~gap["possede"]].head(10).sort_values("demande_pct")
    st.markdown("**Top 10 des compétences demandées qui me manquent**")
    if missing.empty:
        st.success("Ton profil couvre toutes les compétences détectées.")
    else:
        st.plotly_chart(px.bar(missing, x="demande_pct", y="competence", orientation="h",
                               color="categorie",
                               labels={"demande_pct": "% des offres", "competence": "",
                                       "categorie": "Catégorie"}))

# ------------------------------------------------------------------ clusters --
with tab_cluster:
    clusters = load_clusters()
    if clusters is None or clusters.empty:
        st.info("Lance d'abord : python -m src.analysis.clustering")
    else:
        st.subheader("Grands profils de postes (KMeans sur les compétences)")
        st.plotly_chart(px.scatter(clusters, x="x", y="y", color="cluster_label",
                                   hover_data=["id"], labels={"cluster_label": "Profil"}))

        chosen = st.selectbox("Détail d'un profil", sorted(clusters["cluster_label"].unique()))
        ids = clusters.loc[clusters["cluster_label"] == chosen, "id"]
        sub = js[js["id"].isin(ids)]
        presence = (sub.groupby("competence")["id"].nunique() / len(ids) * 100)
        presence = presence.sort_values(ascending=False).head(10).sort_values()
        st.caption(f"{len(ids)} offres dans ce profil")
        st.plotly_chart(px.bar(presence.reset_index(name="pct"), x="pct", y="competence",
                               orientation="h",
                               labels={"pct": "% des offres du profil", "competence": ""}))

# ----------------------------------------------------------------- tendances --
with tab_trend:
    dated = jobs["date_offre"].dropna()
    if dated.dt.normalize().nunique() < 2:
        st.info("Une seule date dans les données : relance la collecte régulièrement "
                "pour voir une évolution.")
    else:
        span = (dated.max() - dated.min()).days
        st.caption(f"Offres du {dated.min():%d/%m/%Y} au {dated.max():%d/%m/%Y} ({span} jours)")
        if span < 14:
            st.warning("Moins de 14 jours de données : tendance peu fiable.")

        chosen = st.multiselect("Compétences à suivre", sorted(demand["competence"]),
                                default=demand["competence"].head(5).tolist())
        share = monthly_share(jobs, js)
        share = share[share["competence"].isin(chosen)]
        if not share.empty:
            st.plotly_chart(px.line(share, x="periode", y="part_pct", color="competence",
                                    markers=True,
                                    labels={"periode": "", "part_pct": "% des offres de la période",
                                            "competence": "Compétence"}))

        trends = skill_trends(jobs, js, min_n=10)
        if trends is not None and not trends.empty:
            c1, c2 = st.columns(2)
            c1.markdown("**En hausse**")
            c1.dataframe(trends.head(8), hide_index=True)
            c2.markdown("**En baisse**")
            c2.dataframe(trends.tail(8).iloc[::-1], hide_index=True)