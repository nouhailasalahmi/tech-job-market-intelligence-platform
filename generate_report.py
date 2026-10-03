"""
generate_report.py
Genere le PDF de rapport du projet AI & Data Job Market Intelligence Platform.
"""

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, PageBreak, KeepTogether
)
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY
from reportlab.platypus import ListFlowable, ListItem
from datetime import datetime

OUTPUT = "Rapport_Phase1_Phase2_JobMarket.pdf"

# ── Couleurs ──────────────────────────────────────────────────────────────────
BLUE_DARK  = colors.HexColor("#1A3C5E")
BLUE_MID   = colors.HexColor("#2E6DA4")
BLUE_LIGHT = colors.HexColor("#D6E4F0")
ACCENT     = colors.HexColor("#E67E22")
GREEN      = colors.HexColor("#27AE60")
GRAY_LIGHT = colors.HexColor("#F2F4F6")
GRAY_MID   = colors.HexColor("#BDC3C7")
WHITE      = colors.white

# ── Styles ────────────────────────────────────────────────────────────────────
styles = getSampleStyleSheet()

title_style = ParagraphStyle("title_style", fontName="Helvetica-Bold",
    fontSize=22, textColor=WHITE, alignment=TA_CENTER, spaceAfter=6)

subtitle_style = ParagraphStyle("subtitle_style", fontName="Helvetica",
    fontSize=13, textColor=BLUE_LIGHT, alignment=TA_CENTER, spaceAfter=4)

meta_style = ParagraphStyle("meta_style", fontName="Helvetica",
    fontSize=10, textColor=BLUE_LIGHT, alignment=TA_CENTER)

h1_style = ParagraphStyle("h1", fontName="Helvetica-Bold",
    fontSize=16, textColor=BLUE_DARK, spaceBefore=14, spaceAfter=6,
    borderPad=4)

h2_style = ParagraphStyle("h2", fontName="Helvetica-Bold",
    fontSize=13, textColor=BLUE_MID, spaceBefore=10, spaceAfter=4)

h3_style = ParagraphStyle("h3", fontName="Helvetica-Bold",
    fontSize=11, textColor=BLUE_DARK, spaceBefore=6, spaceAfter=3)

body_style = ParagraphStyle("body", fontName="Helvetica",
    fontSize=10, textColor=colors.HexColor("#2C3E50"),
    leading=15, alignment=TA_JUSTIFY, spaceAfter=4)

bullet_style = ParagraphStyle("bullet", fontName="Helvetica",
    fontSize=10, textColor=colors.HexColor("#2C3E50"),
    leading=14, leftIndent=16, spaceAfter=2)

code_style = ParagraphStyle("code", fontName="Courier",
    fontSize=9, textColor=colors.HexColor("#1A1A2E"),
    backColor=GRAY_LIGHT, borderPad=6, leading=13,
    leftIndent=10, rightIndent=10, spaceAfter=4)

note_style = ParagraphStyle("note", fontName="Helvetica-Oblique",
    fontSize=9, textColor=colors.HexColor("#7F8C8D"),
    leading=13, leftIndent=10, spaceAfter=4)

label_style = ParagraphStyle("label", fontName="Helvetica-Bold",
    fontSize=9, textColor=WHITE, alignment=TA_CENTER)

# ── Helpers ───────────────────────────────────────────────────────────────────

def spacer(h=0.3):
    return Spacer(1, h * cm)

def hr(color=BLUE_MID, thickness=0.8):
    return HRFlowable(width="100%", thickness=thickness, color=color, spaceAfter=6)

def section_title(text):
    return [
        spacer(0.2),
        hr(BLUE_DARK, 1.5),
        Paragraph(text, h1_style),
        hr(BLUE_MID, 0.5),
        spacer(0.1),
    ]

def subsection(text):
    return Paragraph(text, h2_style)

def subsubsection(text):
    return Paragraph(text, h3_style)

def body(text):
    return Paragraph(text, body_style)

def bullet(text):
    return Paragraph(f"&#8226;  {text}", bullet_style)

def code(text):
    return Paragraph(text.replace(" ", "&nbsp;").replace("\n", "<br/>"), code_style)

def note(text):
    return Paragraph(f"<i>Note : {text}</i>", note_style)

def stat_table(data, col_widths=None):
    """data = list of [label, value] rows"""
    t_data = [["Indicateur", "Valeur"]] + data
    col_widths = col_widths or [11 * cm, 5 * cm]
    t = Table(t_data, colWidths=col_widths)
    t.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, 0),  BLUE_DARK),
        ("TEXTCOLOR",     (0, 0), (-1, 0),  WHITE),
        ("FONTNAME",      (0, 0), (-1, 0),  "Helvetica-Bold"),
        ("FONTSIZE",      (0, 0), (-1, 0),  10),
        ("ROWBACKGROUNDS",(0, 1), (-1, -1), [WHITE, GRAY_LIGHT]),
        ("FONTNAME",      (0, 1), (-1, -1), "Helvetica"),
        ("FONTSIZE",      (0, 1), (-1, -1), 10),
        ("ALIGN",         (1, 0), (1, -1),  "CENTER"),
        ("FONTNAME",      (1, 1), (1, -1),  "Helvetica-Bold"),
        ("TEXTCOLOR",     (1, 1), (1, -1),  BLUE_MID),
        ("GRID",          (0, 0), (-1, -1), 0.4, GRAY_MID),
        ("TOPPADDING",    (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LEFTPADDING",   (0, 0), (-1, -1), 8),
        ("ROUNDEDCORNERS",[3]),
    ]))
    return t

def file_table(rows):
    """rows = [[fichier, phase, role]]"""
    header = [
        Paragraph("Fichier", label_style),
        Paragraph("Phase", label_style),
        Paragraph("Role", label_style),
    ]
    t_data = [header] + [
        [Paragraph(r[0], ParagraphStyle("c", fontName="Courier", fontSize=9, textColor=BLUE_DARK)),
         Paragraph(r[1], ParagraphStyle("c", fontName="Helvetica-Bold", fontSize=9, textColor=ACCENT, alignment=TA_CENTER)),
         Paragraph(r[2], ParagraphStyle("c", fontName="Helvetica", fontSize=9, textColor=colors.HexColor("#2C3E50"), leading=13))]
        for r in rows
    ]
    col_widths = [5.5 * cm, 2.5 * cm, 8.5 * cm]
    t = Table(t_data, colWidths=col_widths)
    t.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, 0),  BLUE_DARK),
        ("ROWBACKGROUNDS",(0, 1), (-1, -1), [WHITE, GRAY_LIGHT]),
        ("GRID",          (0, 0), (-1, -1), 0.4, GRAY_MID),
        ("VALIGN",        (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING",    (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
        ("LEFTPADDING",   (0, 0), (-1, -1), 8),
    ]))
    return t

# ── Cover page ────────────────────────────────────────────────────────────────

def cover_page():
    elements = []
    # Blue header band (simulated via a 1-row table)
    cover_data = [[Paragraph(
        "AI &amp; Data Job Market<br/>Intelligence Platform",
        ParagraphStyle("ct", fontName="Helvetica-Bold", fontSize=26,
                       textColor=WHITE, alignment=TA_CENTER, leading=34))]]
    cover_table = Table(cover_data, colWidths=[17 * cm])
    cover_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), BLUE_DARK),
        ("TOPPADDING",    (0, 0), (-1, -1), 30),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 30),
        ("LEFTPADDING",   (0, 0), (-1, -1), 20),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 20),
        ("ROUNDEDCORNERS",[6]),
    ]))
    elements.append(spacer(2))
    elements.append(cover_table)
    elements.append(spacer(0.6))

    # Subtitle band
    sub_data = [[Paragraph(
        "Rapport de Projet — Phases 1 &amp; 2",
        ParagraphStyle("cs", fontName="Helvetica-Bold", fontSize=14,
                       textColor=BLUE_DARK, alignment=TA_CENTER))]]
    sub_table = Table(sub_data, colWidths=[17 * cm])
    sub_table.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, -1), BLUE_LIGHT),
        ("TOPPADDING",    (0, 0), (-1, -1), 12),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
        ("ROUNDEDCORNERS",[4]),
    ]))
    elements.append(sub_table)
    elements.append(spacer(1.5))

    # Info box
    info = [
        ["Date", datetime.now().strftime("%d %B %Y")],
        ["Domaine", "Data Science / NLP / Machine Learning"],
        ["Source de donnees", "API Adzuna (France)"],
        ["Offres collectees", "6 691 offres brutes"],
        ["Offres apres nettoyage", "4 545 offres uniques"],
        ["Base de donnees", "SQLite — data/jobs.db"],
    ]
    info_data = [[
        Paragraph(r[0], ParagraphStyle("il", fontName="Helvetica-Bold", fontSize=10, textColor=BLUE_DARK)),
        Paragraph(r[1], ParagraphStyle("iv", fontName="Helvetica", fontSize=10, textColor=colors.HexColor("#2C3E50")))
    ] for r in info]
    info_table = Table(info_data, colWidths=[6 * cm, 11 * cm])
    info_table.setStyle(TableStyle([
        ("ROWBACKGROUNDS", (0, 0), (-1, -1), [WHITE, GRAY_LIGHT]),
        ("GRID",           (0, 0), (-1, -1), 0.4, GRAY_MID),
        ("TOPPADDING",     (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING",  (0, 0), (-1, -1), 7),
        ("LEFTPADDING",    (0, 0), (-1, -1), 10),
    ]))
    elements.append(info_table)
    elements.append(spacer(2))
    elements.append(hr(ACCENT, 2))
    elements.append(PageBreak())
    return elements

# ── Table of contents ─────────────────────────────────────────────────────────

def toc():
    elements = []
    elements += section_title("Table des matieres")
    toc_items = [
        ("1.", "Contexte et Problematique"),
        ("2.", "Architecture du Projet"),
        ("3.", "Phase 1 — Collecte des Donnees"),
        ("4.", "Phase 2 — Preparation des Donnees"),
        ("5.", "Description de chaque Fichier"),
        ("6.", "Resultats et Statistiques"),
        ("7.", "Points d'Attention et Prochaines Etapes"),
    ]
    for num, item in toc_items:
        toc_row = Table(
            [[Paragraph(num, ParagraphStyle("tn", fontName="Helvetica-Bold", fontSize=11, textColor=BLUE_MID)),
              Paragraph(item, ParagraphStyle("ti", fontName="Helvetica", fontSize=11, textColor=BLUE_DARK))]],
            colWidths=[1.2 * cm, 15 * cm]
        )
        toc_row.setStyle(TableStyle([
            ("TOPPADDING",    (0,0),(-1,-1), 5),
            ("BOTTOMPADDING", (0,0),(-1,-1), 5),
            ("LINEBELOW",     (0,0),(-1,-1), 0.3, GRAY_MID),
        ]))
        elements.append(toc_row)
    elements.append(spacer(0.5))
    elements.append(PageBreak())
    return elements

# ── Section 1 : Contexte ──────────────────────────────────────────────────────

def section_contexte():
    elements = []
    elements += section_title("1. Contexte et Problematique")
    elements.append(body(
        "Le marche de l'emploi dans les domaines de la Data et de l'Intelligence Artificielle "
        "evolue rapidement, avec l'apparition de nouvelles technologies, de nouveaux metiers et "
        "de nouvelles competences recherchees par les entreprises. Les offres d'emploi constituent "
        "une source importante d'informations sur ces evolutions, mais elles sont nombreuses, "
        "heterogenes et principalement disponibles sous forme de donnees textuelles difficiles "
        "a exploiter directement."
    ))
    elements.append(spacer(0.3))
    elements.append(subsection("Problematique"))
    pb_data = [[Paragraph(
        "Comment exploiter automatiquement les donnees issues des offres d'emploi "
        "afin d'identifier, analyser et suivre l'evolution des metiers, competences "
        "et technologies recherches dans les domaines de la Data et de l'IA ?",
        ParagraphStyle("pb", fontName="Helvetica-Oblique", fontSize=11,
                       textColor=BLUE_DARK, alignment=TA_CENTER, leading=17))]]
    pb_table = Table(pb_data, colWidths=[17 * cm])
    pb_table.setStyle(TableStyle([
        ("BACKGROUND",    (0,0),(-1,-1), BLUE_LIGHT),
        ("TOPPADDING",    (0,0),(-1,-1), 14),
        ("BOTTOMPADDING", (0,0),(-1,-1), 14),
        ("LEFTPADDING",   (0,0),(-1,-1), 16),
        ("RIGHTPADDING",  (0,0),(-1,-1), 16),
        ("ROUNDEDCORNERS",[5]),
        ("BOX",           (0,0),(-1,-1), 1.5, BLUE_MID),
    ]))
    elements.append(pb_table)
    elements.append(spacer(0.4))
    elements.append(subsection("Objectif global"))
    elements.append(body(
        "Concevoir et developper une plateforme intelligente d'analyse du marche de l'emploi "
        "dans les domaines de la Data et de l'IA, capable de :"
    ))
    goals = [
        "Collecter automatiquement des offres d'emploi depuis differentes sources",
        "Nettoyer, structurer et enrichir les donnees brutes",
        "Extraire les competences, technologies et metiers via NLP",
        "Analyser les tendances, co-occurrences et salaires via Data Science",
        "Detecter les competences emergentes par analyse temporelle",
        "Permettre une analyse de l'ecart de competences (Skill Gap Analysis)",
        "Visualiser les resultats dans un dashboard interactif",
    ]
    for g in goals:
        elements.append(bullet(g))
    elements.append(spacer(0.3))
    elements.append(subsection("Extension prevue"))
    elements.append(body(
        "La plateforme est concue pour demarrer sur le domaine AI/Data, puis etre etendue "
        "progressivement a : Software Engineering, Cloud, DevOps, Cybersecurity — sans "
        "refonte de l'architecture."
    ))
    return elements

# ── Section 2 : Architecture ──────────────────────────────────────────────────

def section_architecture():
    elements = []
    elements.append(PageBreak())
    elements += section_title("2. Architecture du Projet")
    elements.append(body(
        "Le projet suit une architecture modulaire organisee en packages Python independants, "
        "chaque package correspondant a une phase du projet. Cette organisation permet d'ajouter "
        "de nouveaux modules sans toucher au code existant."
    ))
    elements.append(spacer(0.3))

    arch_text = (
        "Tech job Market intelligent plateforme/<br/>"
        "&nbsp;&nbsp;&nbsp;&nbsp;config/<br/>"
        "&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;keywords.yaml<br/>"
        "&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;skills_taxonomy.yaml<br/>"
        "&nbsp;&nbsp;&nbsp;&nbsp;data/<br/>"
        "&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;raw/adzuna/YYYY-MM-DD/*.json<br/>"
        "&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;processed/jobs_clean.csv<br/>"
        "&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;logs/<br/>"
        "&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;jobs.db<br/>"
        "&nbsp;&nbsp;&nbsp;&nbsp;src/<br/>"
        "&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;collectors/adzuna.py<br/>"
        "&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;pipeline/loader.py<br/>"
        "&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;pipeline/cleaner.py<br/>"
        "&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;pipeline/db_loader.py<br/>"
        "&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;pipeline/run_pipeline.py<br/>"
        "&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;nlp/&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;(Phase 3 - a venir)<br/>"
        "&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;analysis/&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;(Phase 4 - a venir)<br/>"
        "&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;skill_gap/&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;(Phase 6 - a venir)<br/>"
        "&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;dashboard/&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;(Phase 7 - a venir)<br/>"
        "&nbsp;&nbsp;&nbsp;&nbsp;notebooks/<br/>"
        "&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;Job_skills_reference.py<br/>"
        "&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;analyse_salaire_reference.py<br/>"
        "&nbsp;&nbsp;&nbsp;&nbsp;requirements.txt<br/>"
        "&nbsp;&nbsp;&nbsp;&nbsp;README.md"
    )
    arch_data = [[Paragraph(arch_text, ParagraphStyle("arch",
        fontName="Courier", fontSize=9, textColor=colors.HexColor("#1A1A2E"),
        leading=14))]]
    arch_table = Table(arch_data, colWidths=[17 * cm])
    arch_table.setStyle(TableStyle([
        ("BACKGROUND",    (0,0),(-1,-1), GRAY_LIGHT),
        ("TOPPADDING",    (0,0),(-1,-1), 12),
        ("BOTTOMPADDING", (0,0),(-1,-1), 12),
        ("LEFTPADDING",   (0,0),(-1,-1), 14),
        ("BOX",           (0,0),(-1,-1), 0.8, BLUE_MID),
        ("ROUNDEDCORNERS",[4]),
    ]))
    elements.append(arch_table)
    elements.append(spacer(0.4))

    # Phases overview table
    elements.append(subsection("Vue d'ensemble des phases"))
    phases = [
        ["Phase 1", "Collecte",          "Operationnelle", "src/collectors/"],
        ["Phase 2", "Preparation",       "Operationnelle", "src/pipeline/"],
        ["Phase 3", "NLP",               "A venir",        "src/nlp/"],
        ["Phase 4", "Data Science",      "A venir",        "src/analysis/"],
        ["Phase 5", "Analyse temporelle","A venir",        "src/analysis/temporal.py"],
        ["Phase 6", "Skill Gap",         "A venir",        "src/skill_gap/"],
        ["Phase 7", "Dashboard",         "A venir",        "src/dashboard/"],
    ]
    ph_header = [
        Paragraph("Phase", label_style),
        Paragraph("Nom", label_style),
        Paragraph("Statut", label_style),
        Paragraph("Module", label_style),
    ]
    ph_data = [ph_header] + [
        [Paragraph(r[0], ParagraphStyle("c", fontName="Helvetica-Bold", fontSize=9, textColor=BLUE_DARK, alignment=TA_CENTER)),
         Paragraph(r[1], ParagraphStyle("c", fontName="Helvetica", fontSize=9)),
         Paragraph(r[2], ParagraphStyle("c", fontName="Helvetica-Bold", fontSize=9,
             textColor=GREEN if r[2]=="Operationnelle" else GRAY_MID, alignment=TA_CENTER)),
         Paragraph(r[3], ParagraphStyle("c", fontName="Courier", fontSize=9, textColor=BLUE_MID))]
        for r in phases
    ]
    ph_table = Table(ph_data, colWidths=[2.5*cm, 4*cm, 4*cm, 6.5*cm])
    ph_table.setStyle(TableStyle([
        ("BACKGROUND",    (0,0),(-1,0),  BLUE_DARK),
        ("ROWBACKGROUNDS",(0,1),(-1,-1), [WHITE, GRAY_LIGHT]),
        ("GRID",          (0,0),(-1,-1), 0.4, GRAY_MID),
        ("TOPPADDING",    (0,0),(-1,-1), 6),
        ("BOTTOMPADDING", (0,0),(-1,-1), 6),
        ("LEFTPADDING",   (0,0),(-1,-1), 8),
        ("VALIGN",        (0,0),(-1,-1), "MIDDLE"),
    ]))
    elements.append(ph_table)
    return elements

# ── Section 3 : Phase 1 ───────────────────────────────────────────────────────

def section_phase1():
    elements = []
    elements.append(PageBreak())
    elements += section_title("3. Phase 1 — Collecte des Donnees")
    elements.append(body(
        "La phase de collecte consiste a recuperer automatiquement des offres d'emploi "
        "depuis l'API Adzuna. Le collecteur est concu pour etre robuste (retry automatique, "
        "gestion des erreurs reseau), parametre (mots-cles depuis un fichier YAML) et "
        "extensible (d'autres sources pourront etre ajoutees)."
    ))
    elements.append(spacer(0.3))
    elements.append(subsection("Source : API Adzuna"))
    elements.append(body(
        "Adzuna est une plateforme d'agrégation d'offres d'emploi qui expose une API REST "
        "publique. Pour la France, les requetes sont envoyees a :"
    ))
    elements.append(code("https://api.adzuna.com/v1/api/jobs/fr/search/{page}"))
    elements.append(spacer(0.2))
    params = [
        ["Parametre", "Valeur", "Description"],
        ["results_per_page", "50", "Offres par page (maximum API)"],
        ["sort_by", "date", "Tri par date de publication"],
        ["max_days_old", "optionnel", "Filtre sur l'anciennete des offres"],
        ["what", "mot-cle", "Terme de recherche (data scientist, etc.)"],
    ]
    p_header = [Paragraph(h, label_style) for h in params[0]]
    p_data = [p_header] + [
        [Paragraph(r[i], ParagraphStyle("c", fontName="Courier" if i<2 else "Helvetica",
            fontSize=9, textColor=BLUE_DARK if i<2 else colors.HexColor("#2C3E50")))
         for i in range(3)]
        for r in params[1:]
    ]
    p_table = Table(p_data, colWidths=[4*cm, 3*cm, 10*cm])
    p_table.setStyle(TableStyle([
        ("BACKGROUND",    (0,0),(-1,0),  BLUE_MID),
        ("ROWBACKGROUNDS",(0,1),(-1,-1), [WHITE, GRAY_LIGHT]),
        ("GRID",          (0,0),(-1,-1), 0.4, GRAY_MID),
        ("TOPPADDING",    (0,0),(-1,-1), 6),
        ("BOTTOMPADDING", (0,0),(-1,-1), 6),
        ("LEFTPADDING",   (0,0),(-1,-1), 8),
    ]))
    elements.append(p_table)
    elements.append(spacer(0.3))
    elements.append(subsection("Mots-cles collectes (config/keywords.yaml)"))
    kws = [
        "data scientist", "data analyst", "data engineer",
        "machine learning engineer", "MLOps", "intelligence artificielle",
        "NLP engineer", "LLM engineer", "data architect", "business intelligence"
    ]
    for kw in kws:
        elements.append(bullet(kw))
    elements.append(spacer(0.3))
    elements.append(subsection("Mecanismes de robustesse"))
    robustesses = [
        ("Retry automatique", "4 tentatives avec backoff exponentiel (2s, 4s, 8s, 16s) en cas de timeout ou coupure reseau"),
        ("Gestion HTTP 429", "Rate limiting : attente avant de reessayer si l'API signale trop de requetes"),
        ("Pause entre appels", "2.5 secondes entre chaque page (~25 req/min, sous la limite API)"),
        ("Deduplication", "Suivi des IDs deja vus pour eviter les doublons entre mots-cles"),
        ("Logs horodates", "Fichier de log par date dans data/logs/"),
        ("Stockage JSON brut", "Chaque page sauvegardee dans data/raw/adzuna/YYYY-MM-DD/ avec metadonnees"),
    ]
    for titre, desc in robustesses:
        elements.append(Paragraph(
            f"<b>{titre}</b> : {desc}",
            ParagraphStyle("rb", fontName="Helvetica", fontSize=10,
                           textColor=colors.HexColor("#2C3E50"), leading=14,
                           leftIndent=12, spaceAfter=4)
        ))
    elements.append(spacer(0.3))
    elements.append(subsection("Chiffres de collecte"))
    elements.append(stat_table([
        ["Fichiers JSON generes", "134 fichiers"],
        ["Offres brutes totales", "6 691 offres"],
        ["Doublons detectes", "1 969 doublons (−29%)"],
        ["Offres uniques apres dedup", "4 722 offres"],
        ["Periode couverte", "Aout 2026 → Octobre 2026"],
        ["Source", "Adzuna France uniquement (extensible)"],
    ]))
    return elements

# ── Section 4 : Phase 2 ───────────────────────────────────────────────────────

def section_phase2():
    elements = []
    elements.append(PageBreak())
    elements += section_title("4. Phase 2 — Preparation des Donnees")
    elements.append(body(
        "La phase de preparation transforme les donnees brutes JSON en un DataFrame structure, "
        "nettoye et enrichi, pret pour les analyses NLP et Data Science. Elle comporte 8 etapes "
        "sequentielles appliquees dans un pipeline."
    ))
    elements.append(spacer(0.3))

    etapes = [
        ("Etape 1", "Selection des colonnes",
         "Extraction des 19 colonnes utiles depuis les JSON Adzuna + ajout des metadonnees "
         "de collecte (source, domaine, mot-cle, pays, date de collecte)."),
        ("Etape 2", "Nettoyage des textes",
         "Suppression des balises HTML, normalisation des espaces multiples "
         "dans les champs titre, description et entreprise."),
        ("Etape 3", "Deduplication",
         "Deux niveaux : (1) deduplication exacte sur l'ID Adzuna, "
         "(2) deduplication semantique par empreinte MD5 sur titre+entreprise+debut de description "
         "pour detecter les offres re-publiees. Resultat : −1 969 doublons (−29%)."),
        ("Etape 4", "Parsing des dates",
         "Conversion UTC → naive datetime, filtrage des offres anterieures a une date seuil "
         "(configurable via --min-date), suppression des dates manquantes."),
        ("Etape 5", "Normalisation des localisations",
         "Extraction de region et ville depuis le tableau zone[] d'Adzuna. "
         "Filtrage des arrondissements. Canonicalisation des noms de villes (ex: 'sophia-antipolis' → 'Sophia Antipolis'). "
         "Detection du teletravail dans le titre et la description."),
        ("Etape 6", "Normalisation des salaires",
         "Conversion automatique annuel/mensuel/horaire → mensuel. Cas speciaux alternance/stage. "
         "Validation : salaire fiable entre 1 250 et 16 600 EUR/mois."),
        ("Etape 7", "Normalisation des titres",
         "Detection du role canonique par regex (Data Scientist, ML Engineer, LLM/GenAI Engineer, etc.) "
         "et du niveau d'experience (Junior, Senior, Lead, Stage, Alternance, Manager)."),
        ("Etape 8", "Langue + Score de pertinence",
         "Detection de la langue (FR/EN) par heuristique sur mots courants. "
         "Score de pertinence Data/IA : 0 = hors sujet, 1 = titre pertinent, 2 = titre+description pertinents."),
    ]

    for num, titre, desc in etapes:
        row_data = [[
            Paragraph(num, ParagraphStyle("en", fontName="Helvetica-Bold", fontSize=9,
                textColor=WHITE, alignment=TA_CENTER)),
            Paragraph(f"<b>{titre}</b><br/>{desc}",
                ParagraphStyle("ed", fontName="Helvetica", fontSize=9,
                    textColor=colors.HexColor("#2C3E50"), leading=13))
        ]]
        row_table = Table(row_data, colWidths=[2.5*cm, 14.5*cm])
        row_table.setStyle(TableStyle([
            ("BACKGROUND",    (0,0),(0,0),  BLUE_MID),
            ("BACKGROUND",    (1,0),(1,0),  GRAY_LIGHT if etapes.index((num,titre,desc))%2==0 else WHITE),
            ("VALIGN",        (0,0),(-1,-1),"TOP"),
            ("TOPPADDING",    (0,0),(-1,-1), 8),
            ("BOTTOMPADDING", (0,0),(-1,-1), 8),
            ("LEFTPADDING",   (0,0),(-1,-1), 8),
            ("LINEBELOW",     (0,0),(-1,-1), 0.4, GRAY_MID),
        ]))
        elements.append(row_table)

    elements.append(spacer(0.4))
    elements.append(subsection("Rapport qualite — resultats"))
    elements.append(stat_table([
        ["Offres apres nettoyage complet", "4 545"],
        ["Offres pertinentes Data/IA (score >= 1)", "2 794 (61%)"],
        ["Haute pertinence (score >= 2)", "1 721 (38%)"],
        ["Offres avec salaire mensuel calcule", "1 057 (23%)"],
        ["Salaires fiables (1 250-16 600 EUR/mois)", "954 (21%)"],
        ["Offres avec ville precise", "3 982 (88%)"],
        ["Offres en teletravail detectees", "60 (1.3%)"],
        ["Descriptions en francais", "4 047 (89%)"],
        ["Descriptions en anglais", "498 (11%)"],
        ["Ville manquante", "12.4%"],
        ["Salaire manquant", "76.7% (normal : Adzuna FR peu de salaires)"],
        ["Type de contrat manquant", "54.7%"],
    ]))
    return elements

# ── Section 5 : Fichiers ──────────────────────────────────────────────────────

def section_fichiers():
    elements = []
    elements.append(PageBreak())
    elements += section_title("5. Description de chaque Fichier")

    # Config files
    elements.append(subsection("Fichiers de configuration"))
    elements.append(file_table([
        ["config/keywords.yaml",
         "Config",
         "Liste des mots-cles de collecte organises par domaine (ai_data, software, cloud...). "
         "Chaque entree contient : query (terme de recherche), domain et role. "
         "Extensible sans toucher au code."],
        ["config/skills_taxonomy.yaml",
         "Config",
         "Taxonomie complete des competences techniques classees par categorie : "
         "langages, data engineering, cloud, devops/mlops, machine learning, librairies, "
         "visualisation, bases de donnees. Chaque competence liste ses patterns regex "
         "pour la normalisation (Phase 3 NLP)."],
    ]))
    elements.append(spacer(0.4))

    # Collectors
    elements.append(subsection("src/collectors/"))
    elements.append(file_table([
        ["src/collectors/adzuna.py",
         "Phase 1",
         "Collecteur principal. Charge les mots-cles depuis keywords.yaml, "
         "interroge l'API Adzuna page par page, gere les retries/rate-limiting, "
         "sauvegarde chaque page en JSON horodate avec metadonnees (source, domain, role, keyword). "
         "Utilisable en CLI : python -m src.collectors.adzuna --domain ai_data"],
    ]))
    elements.append(spacer(0.4))

    # Pipeline
    elements.append(subsection("src/pipeline/"))
    elements.append(file_table([
        ["src/pipeline/loader.py",
         "Phase 2",
         "Charge tous les fichiers JSON bruts depuis data/raw/adzuna/ (recursif) "
         "en un seul DataFrame pandas. Ajoute les colonnes de traçabilite (_source_file, "
         "_domain, _keyword, _collected_at). Robuste aux fichiers corrompus."],
        ["src/pipeline/cleaner.py",
         "Phase 2",
         "Pipeline de nettoyage en 8 etapes (voir Section 4). "
         "Modules independants : deduplicate(), clean_texts(), parse_dates(), "
         "normalize_locations(), normalize_salaries(), normalize_titles(), "
         "detect_language(), score_relevance(). "
         "Genere un rapport qualite detaille a chaque execution."],
        ["src/pipeline/db_loader.py",
         "Phase 2",
         "Ecrit le DataFrame nettoye dans SQLite (data/jobs.db, table 'jobs'). "
         "Cree automatiquement des index sur role, ville, date et pertinent "
         "pour accelerer les requetes du dashboard. "
         "Serialise les colonnes de type list en JSON pour compatibilite SQLite."],
        ["src/pipeline/run_pipeline.py",
         "Phase 2",
         "Orchestrateur CLI de la pipeline complete. "
         "Options : --collect (lance Phase 1 avant Phase 2), --min-date, "
         "--domain, --max-pages, --out-csv, --db. "
         "Enchaîne : loader → cleaner → CSV → SQLite."],
    ]))
    elements.append(spacer(0.4))

    # Notebooks
    elements.append(subsection("notebooks/ (references)"))
    elements.append(file_table([
        ["notebooks/Job_skills_reference.py",
         "Ref P3",
         "Version initiale de l'extraction de competences par regex (37 competences). "
         "Servira de reference pour coder src/nlp/ en Phase 3. "
         "Genere la table job_skills dans SQLite."],
        ["notebooks/analyse_salaire_reference.py",
         "Ref P4",
         "Analyse exploratoire du salaire median par competence. "
         "Servira de reference pour src/analysis/ en Phase 4. "
         "Necessite la table job_skills."],
    ]))
    elements.append(spacer(0.4))

    # Other files
    elements.append(subsection("Fichiers racine"))
    elements.append(file_table([
        ["requirements.txt",
         "Projet",
         "Toutes les dependances Python pour les 7 phases : requests, pandas, numpy, "
         "spacy, langdetect, rapidfuzz, scikit-learn, plotly, streamlit, pyyaml."],
        [".env",
         "Config",
         "Variables d'environnement : ADZUNA_APP_ID et ADZUNA_APP_KEY. "
         "Non versionne (dans .gitignore)."],
        ["README.md",
         "Doc",
         "Documentation principale : architecture, commandes de lancement, "
         "tableau d'avancement des phases."],
    ]))
    return elements

# ── Section 6 : Resultats ─────────────────────────────────────────────────────

def section_resultats():
    elements = []
    elements.append(PageBreak())
    elements += section_title("6. Resultats et Statistiques")
    elements.append(subsection("Distribution des roles detectes"))
    roles_data = [
        ["Autre (hors domaine)", "2 563", "56.4%"],
        ["Data Engineer",        "533",   "11.7%"],
        ["Data Analyst",         "499",   "11.0%"],
        ["Data Scientist",       "437",    "9.6%"],
        ["AI Engineer",          "294",    "6.5%"],
        ["LLM / GenAI Engineer", "75",     "1.7%"],
        ["ML Engineer",          "60",     "1.3%"],
        ["MLOps Engineer",       "50",     "1.1%"],
        ["Data Architect",       "25",     "0.6%"],
        ["Data Manager",          "9",     "0.2%"],
    ]
    r_header = [Paragraph(h, label_style) for h in ["Role", "Nb offres", "Part"]]
    r_data = [r_header] + [
        [Paragraph(r[i], ParagraphStyle("c", fontName="Helvetica-Bold" if i==0 else "Helvetica",
            fontSize=10, textColor=BLUE_DARK if i==0 else colors.HexColor("#2C3E50"),
            alignment=TA_CENTER if i>0 else TA_LEFT)) for i in range(3)]
        for r in roles_data
    ]
    r_table = Table(r_data, colWidths=[9*cm, 4*cm, 4*cm])
    r_table.setStyle(TableStyle([
        ("BACKGROUND",    (0,0),(-1,0),  BLUE_DARK),
        ("ROWBACKGROUNDS",(0,1),(-1,-1), [WHITE, GRAY_LIGHT]),
        ("GRID",          (0,0),(-1,-1), 0.4, GRAY_MID),
        ("TOPPADDING",    (0,0),(-1,-1), 7),
        ("BOTTOMPADDING", (0,0),(-1,-1), 7),
        ("LEFTPADDING",   (0,0),(-1,-1), 8),
    ]))
    elements.append(r_table)
    elements.append(spacer(0.4))
    elements.append(subsection("Distribution des niveaux d'experience"))
    niveaux_data = [
        ["Unspecified",  "2 522", "55.5%"],
        ["Manager",      "594",   "13.1%"],
        ["Stage",        "552",   "12.1%"],
        ["Senior",       "518",   "11.4%"],
        ["Lead",         "172",    "3.8%"],
        ["Alternance",   "141",    "3.1%"],
        ["Junior",        "46",    "1.0%"],
    ]
    n_header = [Paragraph(h, label_style) for h in ["Niveau", "Nb offres", "Part"]]
    n_data = [n_header] + [
        [Paragraph(r[i], ParagraphStyle("c", fontName="Helvetica-Bold" if i==0 else "Helvetica",
            fontSize=10, textColor=BLUE_DARK if i==0 else colors.HexColor("#2C3E50"),
            alignment=TA_CENTER if i>0 else TA_LEFT)) for i in range(3)]
        for r in niveaux_data
    ]
    n_table = Table(n_data, colWidths=[9*cm, 4*cm, 4*cm])
    n_table.setStyle(TableStyle([
        ("BACKGROUND",    (0,0),(-1,0),  BLUE_DARK),
        ("ROWBACKGROUNDS",(0,1),(-1,-1), [WHITE, GRAY_LIGHT]),
        ("GRID",          (0,0),(-1,-1), 0.4, GRAY_MID),
        ("TOPPADDING",    (0,0),(-1,-1), 7),
        ("BOTTOMPADDING", (0,0),(-1,-1), 7),
        ("LEFTPADDING",   (0,0),(-1,-1), 8),
    ]))
    elements.append(n_table)
    elements.append(spacer(0.4))
    elements.append(subsection("Top 5 des villes"))
    villes_data = [
        ["Paris",          "1 151", "25.3%"],
        ["Lyon",           "71",     "1.6%"],
        ["Hauts-de-Seine", "57",     "1.3%"],
        ["Loire-Atlantique","57",    "1.3%"],
        ["Bordeaux",       "45",     "1.0%"],
    ]
    v_header = [Paragraph(h, label_style) for h in ["Ville", "Nb offres", "Part"]]
    v_data = [v_header] + [
        [Paragraph(r[i], ParagraphStyle("c", fontName="Helvetica-Bold" if i==0 else "Helvetica",
            fontSize=10, textColor=BLUE_DARK if i==0 else colors.HexColor("#2C3E50"),
            alignment=TA_CENTER if i>0 else TA_LEFT)) for i in range(3)]
        for r in villes_data
    ]
    v_table = Table(v_data, colWidths=[9*cm, 4*cm, 4*cm])
    v_table.setStyle(TableStyle([
        ("BACKGROUND",    (0,0),(-1,0),  BLUE_DARK),
        ("ROWBACKGROUNDS",(0,1),(-1,-1), [WHITE, GRAY_LIGHT]),
        ("GRID",          (0,0),(-1,-1), 0.4, GRAY_MID),
        ("TOPPADDING",    (0,0),(-1,-1), 7),
        ("BOTTOMPADDING", (0,0),(-1,-1), 7),
        ("LEFTPADDING",   (0,0),(-1,-1), 8),
    ]))
    elements.append(v_table)
    return elements

# ── Section 7 : Prochaines etapes ─────────────────────────────────────────────

def section_next():
    elements = []
    elements.append(PageBreak())
    elements += section_title("7. Points d'Attention et Prochaines Etapes")
    elements.append(subsection("Points a ameliorer identifies"))
    points = [
        ("Villes mal normalisees",
         "Les arrondissements de type '1er-Arrondissement' passent encore dans la table ville. "
         "A corriger : mapper tout arrondissement vers 'Paris'."),
        ("56% en role 'Autre'",
         "Plus de la moitie des offres ne correspondent a aucun pattern de role. "
         "Ces offres ont des titres trop generiques. En Phase 3, le NLP (spaCy + classification) "
         "permettra d'en recuperer une partie."),
        ("76.7% de salaires manquants",
         "Normal pour Adzuna France : peu d'entreprises publient les salaires. "
         "L'analyse salariale sera basee sur les ~954 offres avec salaires fiables."),
        ("Encodage console Windows",
         "La console Windows (cp1252) ne supporte pas certains caracteres Unicode. "
         "Les logs utilisent donc de l'ASCII pur — les fichiers log (UTF-8) sont corrects."),
    ]
    for titre, desc in points:
        pt_data = [[
            Paragraph("!", ParagraphStyle("ic", fontName="Helvetica-Bold", fontSize=14,
                textColor=ACCENT, alignment=TA_CENTER)),
            Paragraph(f"<b>{titre}</b><br/>{desc}",
                ParagraphStyle("pd", fontName="Helvetica", fontSize=10,
                    textColor=colors.HexColor("#2C3E50"), leading=13))
        ]]
        pt_table = Table(pt_data, colWidths=[1*cm, 16*cm])
        pt_table.setStyle(TableStyle([
            ("BACKGROUND",    (0,0),(-1,-1), colors.HexColor("#FEF9E7")),
            ("VALIGN",        (0,0),(-1,-1), "TOP"),
            ("TOPPADDING",    (0,0),(-1,-1), 8),
            ("BOTTOMPADDING", (0,0),(-1,-1), 8),
            ("LEFTPADDING",   (0,0),(-1,-1), 8),
            ("LINEBELOW",     (0,0),(-1,-1), 0.5, ACCENT),
            ("BOX",           (0,0),(-1,-1), 0.5, ACCENT),
            ("ROUNDEDCORNERS",[3]),
        ]))
        elements.append(pt_table)
        elements.append(spacer(0.2))

    elements.append(spacer(0.3))
    elements.append(subsection("Prochaines etapes — Phase 3 : NLP"))
    next_steps = [
        "Extraction des competences depuis les descriptions via les patterns de skills_taxonomy.yaml",
        "Normalisation des formulations ('ML' = 'Machine Learning', 'sklearn' = 'Scikit-learn')",
        "Classification automatique des metiers (pour les 2 563 offres en 'Autre')",
        "Extraction des entites nommees : technologies, certifications, niveaux d'etudes",
        "Creation de la table job_skills dans SQLite avec categorie de competence",
    ]
    for step in next_steps:
        elements.append(bullet(step))

    elements.append(spacer(0.3))
    elements.append(subsection("Commandes de lancement"))
    cmds = [
        ("# Lancer Phase 2 uniquement (donnees deja collectees)",
         "venv\\Scripts\\python.exe -m src.pipeline.run_pipeline --min-date 2026-08-01"),
        ("# Lancer Phase 1 + Phase 2 (nouvelle collecte)",
         "venv\\Scripts\\python.exe -m src.pipeline.run_pipeline --collect --domain ai_data"),
    ]
    for comment, cmd in cmds:
        elements.append(code(f"{comment}<br/>{cmd}"))
        elements.append(spacer(0.1))

    elements.append(spacer(0.5))
    elements.append(hr(ACCENT, 1.5))
    elements.append(Paragraph(
        "Rapport genere automatiquement le " + datetime.now().strftime("%d/%m/%Y a %H:%M"),
        ParagraphStyle("footer", fontName="Helvetica-Oblique", fontSize=9,
            textColor=GRAY_MID, alignment=TA_CENTER)
    ))
    return elements

# ── Main ──────────────────────────────────────────────────────────────────────

def build_pdf():
    doc = SimpleDocTemplate(
        OUTPUT,
        pagesize=A4,
        rightMargin=2*cm, leftMargin=2*cm,
        topMargin=2*cm, bottomMargin=2*cm,
        title="AI & Data Job Market Intelligence — Rapport Phases 1 & 2",
        author="Pipeline auto-genere",
    )

    elements = []
    elements += cover_page()
    elements += toc()
    elements += section_contexte()
    elements += section_architecture()
    elements += section_phase1()
    elements += section_phase2()
    elements += section_fichiers()
    elements += section_resultats()
    elements += section_next()

    doc.build(elements)
    print(f"PDF genere : {OUTPUT}")

if __name__ == "__main__":
    build_pdf()
