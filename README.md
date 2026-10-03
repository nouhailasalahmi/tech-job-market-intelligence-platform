# AI & Data Job Market Intelligence Platform

## Architecture

```
.
├── config/
│   ├── keywords.yaml          # Mots-clés de collecte par domaine
│   └── skills_taxonomy.yaml   # Taxonomie des compétences (Phase 3)
│
├── data/
│   ├── raw/adzuna/            # JSON bruts horodatés (YYYY-MM-DD/)
│   ├── processed/
│   │   └── jobs_clean.csv     # Données nettoyées Phase 2
│   ├── logs/                  # Logs de collecte et pipeline
│   └── jobs.db                # SQLite — tables jobs, job_skills
│
├── src/
│   ├── collectors/
│   │   └── adzuna.py          # Phase 1 — Collecte API Adzuna
│   ├── pipeline/
│   │   ├── loader.py          # Chargement JSON bruts → DataFrame
│   │   ├── cleaner.py         # Phase 2 — Nettoyage complet
│   │   ├── db_loader.py       # Écriture SQLite + index
│   │   └── run_pipeline.py    # Orchestrateur CLI
│   ├── nlp/                   # Phase 3 (à venir)
│   ├── analysis/              # Phase 4 (à venir)
│   ├── skill_gap/             # Phase 6 (à venir)
│   └── dashboard/             # Phase 7 (à venir)
│
├── notebooks/                 # EDA Jupyter
├── tests/
├── requirements.txt
└── README.md
```

## Lancement rapide

### Installer les dépendances
```bash
pip install -r requirements.txt
```

### Phase 2 uniquement (données déjà collectées)
```bash
python -m src.pipeline.run_pipeline
```

### Phase 1 + Phase 2
```bash
python -m src.pipeline.run_pipeline --collect --domain ai_data --max-pages 10
```

### Avec filtre de date
```bash
python -m src.pipeline.run_pipeline --min-date 2026-08-01
```

## Phases

| Phase | Module | Statut |
|-------|--------|--------|
| 1 — Collecte | `src/collectors/adzuna.py` | ✅ |
| 2 — Préparation | `src/pipeline/cleaner.py` | ✅ |
| 3 — NLP | `src/nlp/` | 🔲 |
| 4 — Data Science | `src/analysis/` | 🔲 |
| 5 — Temporel | `src/analysis/temporal.py` | 🔲 |
| 6 — Skill Gap | `src/skill_gap/` | 🔲 |
| 7 — Dashboard | `src/dashboard/` | 🔲 |

## Variables d'environnement

```bash
ADZUNA_APP_ID=<ton_app_id>
ADZUNA_APP_KEY=<ta_app_key>
```

Crée un fichier `.env` à la racine du projet.
