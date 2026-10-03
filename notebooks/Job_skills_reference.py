import sqlite3
import pandas as pd

# Compétences à chercher (mot -> motif de recherche)
SKILLS = {
    "Python": r"\bpython\b",
    "SQL": r"\bsql\b",
    "Java": r"\bjava\b",
    "JavaScript": r"\bjavascript\b",
    "C++": r"c\+\+",
    "Scala": r"\bscala\b",
    "Spark": r"\bspark\b",
    "Hadoop": r"\bhadoop\b",
    "Kafka": r"\bkafka\b",
    "Airflow": r"\bairflow\b",
    "dbt": r"\bdbt\b",
    "Docker": r"\bdocker\b",
    "Kubernetes": r"\bkubernetes\b|\bk8s\b",
    "Git": r"\bgit\b",
    "Linux": r"\blinux\b",
    "AWS": r"\baws\b",
    "Azure": r"\bazure\b",
    "GCP": r"\bgcp\b|google cloud",
    "Snowflake": r"\bsnowflake\b",
    "Databricks": r"\bdatabricks\b",
    "Power BI": r"power\s?bi",
    "Excel": r"\bexcel\b",
    "Pandas": r"\bpandas\b",
    "Scikit-learn": r"scikit[- ]?learn|sklearn",
    "TensorFlow": r"\btensorflow\b",
    "PyTorch": r"\bpytorch\b",
    "Machine Learning": r"machine learning",
    "Deep Learning": r"deep learning",
    "NLP": r"\bnlp\b",
    "LLM": r"\bllm\b|\bllms\b",
    "MLOps": r"\bmlops\b",
}
# R, Go et Tableau sont volontairement absents : on les confondrait
# avec des mots courants ("R&D", "go", "tableau de bord").

conn = sqlite3.connect("data/jobs.db")
df = pd.read_sql("SELECT id, titre, description FROM jobs WHERE pertinent = 1", conn)
texte = (df["titre"].fillna("") + " " + df["description"].fillna("")).str.lower()

# Une ligne par couple (offre, compétence trouvée)
lignes = []
for competence, motif in SKILLS.items():
    trouve = texte.str.contains(motif, regex=True)
    lignes += [(offre_id, competence) for offre_id in df.loc[trouve, "id"]]

skills_df = pd.DataFrame(lignes, columns=["id", "competence"])
skills_df.to_sql("job_skills", conn, if_exists="replace", index=False)

# Résultat : top 15
total = len(df)
top = skills_df["competence"].value_counts().head(15)
print(f"Offres analysées : {total}\n")
for competence, nombre in top.items():
    print(f"{competence:<18} {nombre:>5}  ({nombre / total * 100:.0f} %)")

conn.close()