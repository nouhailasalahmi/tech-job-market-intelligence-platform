"""
normalizer.py  -  Phase 3 (NLP)
Charge config/skills_taxonomy.yaml et compile une regex par competence.
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from pathlib import Path

import yaml

logger = logging.getLogger(__name__)

# Fichier situe dans src/analysis/nlp/normalizer.py -> racine = parents[3]
ROOT = Path(__file__).resolve().parents[3]
DEFAULT_TAXONOMY = ROOT / "config" / "skills_taxonomy.yaml"


@dataclass(frozen=True)
class Skill:
    name: str          # nom canonique, ex: "Scikit-learn"
    category: str      # ex: "libraries"
    regex: re.Pattern  # toutes les variantes combinees


def load_taxonomy(path: Path | str = DEFAULT_TAXONOMY) -> list[Skill]:
    """Lit le YAML et renvoie une liste de Skill pretes a chercher."""
    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}

    skills: list[Skill] = []
    seen: set[str] = set()

    for category, entries in data.items():
        for name, patterns in (entries or {}).items():
            name = str(name)
            if name in seen:
                logger.warning("Competence en double ignoree : %s", name)
                continue

            # Correction 1 : un motif ecrit en simple texte (et non en liste)
            if isinstance(patterns, str):
                patterns = [patterns]

            valid = []
            for p in patterns or []:
                # Correction 2 : ignorer null (None) et motifs vides, convertir le reste en texte
                if p is None:
                    continue
                p = str(p).strip()
                if not p:
                    continue
                try:
                    re.compile(p)
                except re.error as exc:
                    logger.warning("Motif invalide pour %s (%s) : %s", name, p, exc)
                    continue
                valid.append(f"(?:{p})")

            if not valid:
                logger.warning("Aucun motif valide pour %s : ignoree", name)
                continue

            # Correction 3 : proteger la compilation de la regex combinee
            try:
                regex = re.compile("|".join(valid), re.IGNORECASE)
            except re.error as exc:
                logger.warning("Regex combinee invalide pour %s : %s", name, exc)
                continue

            skills.append(Skill(name=name, category=str(category), regex=regex))
            seen.add(name)

    logger.info("Taxonomie chargee : %d competences", len(skills))
    return skills