import sqlite3
import pandas as pd

conn = sqlite3.connect("data/jobs.db")

# Offres avec une compétence ET un salaire fiable
df = pd.read_sql("""
    SELECT s.competence, j.salaire_mensuel_min
    FROM job_skills s
    JOIN jobs j ON j.id = s.id
    WHERE j.salaire_fiable = 1
""", conn)

# Salaire de référence : toutes les offres data / IA avec salaire fiable
reference = pd.read_sql("""
    SELECT salaire_mensuel_min FROM jobs
    WHERE pertinent = 1 AND salaire_fiable = 1
""", conn)["salaire_mensuel_min"].median()

# Résumé par compétence (on garde celles avec au moins 10 offres)
resume = (
    df.groupby("competence")["salaire_mensuel_min"]
    .agg(offres="count", mediane="median", moyenne="mean")
    .query("offres >= 10")
    .round(0)
    .sort_values("mediane", ascending=False)
)

print(f"Salaire médian de référence (data / IA) : {reference:.0f} €/mois\n")
print(resume.to_string())

conn.close()