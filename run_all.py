"""
run_all.py  -  lance toute la chaine en une commande

Usage (depuis la racine du projet) :
    python run_all.py                    # collecte + pipeline + NLP + analyses
    python run_all.py --skip-collect     # sans appeler les API (donnees deja collectees)
    python run_all.py --skip-analysis    # s'arrete apres l'extraction des competences
    python run_all.py --keep-going       # continue meme si une etape echoue

Chaque etape est lancee comme `python -m <module>`. Si un module porte un autre
nom chez toi, modifie la liste STEPS ci-dessous.
"""
from __future__ import annotations

import argparse
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent

# (groupe, titre, module)
STEPS = [
    ("collect",  "Collecte Adzuna",            "src.collectors.collect_adzuna"),
    ("collect",  "Collecte France Travail",    "src.collectors.francetravail"),
    ("pipeline", "Nettoyage + SQLite",         "src.analysis.pipeline.run_pipeline"),
    ("nlp",      "Extraction des competences", "src.analysis.nlp.skills_extractor"),
    ("analysis", "Salaires",                   "src.analysis.analyse_salaire"),
    ("analysis", "Clustering",                 "src.analysis.clustering"),
    ("analysis", "Tendances",                  "src.analysis.temporal"),
    ("analysis", "Skill gap",                  "src.analysis.skill_gap.gap_analyzer"),
]


def run_step(title: str, module: str) -> bool:
    print(f"\n{'=' * 70}\n>>> {title}   (python -m {module})\n{'=' * 70}", flush=True)
    start = time.perf_counter()
    result = subprocess.run([sys.executable, "-m", module], cwd=ROOT)
    elapsed = time.perf_counter() - start
    ok = result.returncode == 0
    print(f"--- {'OK' if ok else 'ECHEC (code ' + str(result.returncode) + ')'} en {elapsed:.1f} s", flush=True)
    return ok


def main() -> int:
    parser = argparse.ArgumentParser(description="Lance toute la chaine du projet")
    parser.add_argument("--skip-collect", action="store_true", help="ne pas appeler les API")
    parser.add_argument("--skip-analysis", action="store_true", help="s'arreter apres le NLP")
    parser.add_argument("--keep-going", action="store_true", help="continuer apres une erreur")
    args = parser.parse_args()

    skipped = set()
    if args.skip_collect:
        skipped.add("collect")
    if args.skip_analysis:
        skipped.add("analysis")

    failed: list[str] = []
    for group, title, module in STEPS:
        if group in skipped:
            print(f"(etape ignoree : {title})")
            continue
        if not run_step(title, module):
            failed.append(title)
            if not args.keep_going:
                print(f"\nArret : l'etape '{title}' a echoue (relance avec --keep-going pour continuer).")
                return 1

    print("\n" + "=" * 70)
    if failed:
        print("Termine avec des erreurs : " + ", ".join(failed))
        return 1
    print("Tout est termine. Dashboard :  streamlit run src/dashboard/app.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())