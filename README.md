# 📊 Tech Job Market Intelligence Platform

Plateforme d'analyse du marché de l'emploi tech : collecte d'offres multi-sources, extraction automatique des compétences par NLP, analyses (salaires, clusters, tendances) et dashboard interactif.

🔗 **Démo en ligne :** [Ouvrir le dashboard](https://tech-job-market-intelligence-platform-ckmsrpabdqnu22ppud5dqj.streamlit.app/)

---

## 🎯 Objectifs

- Centraliser les offres tech issues de plusieurs sources (**Adzuna**, **France Travail**)
- Identifier les compétences les plus demandées
- Analyser les salaires (mensuels), les profils et l'évolution dans le temps
- Mesurer l'écart entre un profil et les compétences du marché (*skill gap*)

## 🧱 Stack technique

Python · pandas · SQLite · NLP (extraction par taxonomie) · scikit-learn · Streamlit · APIs REST · Git/GitHub

## 🔄 Fonctionnement

```
APIs (Adzuna, France Travail)
        ↓  collecte
   JSON bruts (data/raw/)
        ↓  nettoyage
   SQLite (data/jobs.db)
        ↓  NLP
   Compétences (table job_skills)
        ↓  analyses
   Dashboard Streamlit
```

## 📁 Structure du projet

```
├── config/
│   ├── keywords.yaml          # Mots-clés de collecte par domaine
│   └── skills_taxonomy.yaml   # Taxonomie des compétences (9 catégories)
│
├── data/
│   ├── raw/                   # JSON bruts (adzuna/, francetravail/)
│   ├── processed/
│   │   └── jobs_clean.csv     # Données nettoyées
│   ├── logs/                  # Logs de collecte et pipeline
│   └── jobs.db                # SQLite — tables jobs, job_skills
│
├── src/
│   ├── collectors/
│   │   ├── adzuna.py          # Collecte API Adzuna
│   │   └── francetravail.py   # Collecte API France Travail
│   ├── pipeline/
│   │   ├── loader.py          # Chargement JSON bruts → DataFrame
│   │   ├── cleaner.py         # Nettoyage complet
│   │   ├── db_loader.py       # Écriture SQLite + index
│   │   └── run_pipeline.py    # Orchestrateur CLI
│   ├── analysis/
│   │   ├── nlp/               # Extraction des compétences
│   │   ├── skill_gap/         # Analyse d'écart de compétences
│   │   ├── analyse_salaire.py # Analyse des salaires
│   │   ├── clustering.py      # Clustering des offres
│   │   └── temporal.py        # Évolution dans le temps
│   └── dashboard/
│       └── app.py             # Dashboard Streamlit
│
├── notebooks/                 # EDA Jupyter
├── tests/
├── requirements.txt
└── README.md
```

## 🚀 Installation et utilisation

```bash
# 1. Cloner le dépôt
git clone https://github.com/nouhailasalahmi/tech-job-market-intelligence-platform.git
cd tech-job-market-intelligence-platform

# 2. Installer les dépendances
pip install -r requirements.txt

# 3. (Optionnel) Relancer le pipeline de collecte et nettoyage
python -m src.pipeline.run_pipeline --collect

# 4. Extraire les compétences
python -m src.analysis.nlp.skills_extractor

# 5. Lancer le dashboard
streamlit run src/dashboard/app.py
```

> Les clés API (Adzuna, France Travail) se placent dans un fichier `.env` (non versionné).

## ✅ Avancement

| Phase | Contenu | Statut |
|---|---|---|
| 1 | Collecte (Adzuna, France Travail) | ✅ |
| 2 | Nettoyage + base SQLite | ✅ |
| 3 | NLP : extraction des compétences | ✅ |
| 4 | Analyses : salaires, clustering, temporel | ✅ |
| 5 | Skill gap | ✅ |
| 6 | Dashboard Streamlit (déployé) | ✅ |

## 👩‍💻 Auteure

**Nouha** — Étudiante ingénieure Smart ICT (Data Science & IA), INPT Rabat
