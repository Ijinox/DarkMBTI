#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DarkMBTI v1.0
=============

Outil CLI d'évaluation de personnalité inspiré du modèle MBTI.

- 20 questions (5 par axe : E/I, S/N, T/F, J/P)
- Moteur de scoring pondéré
- Base de 16 profils avec forces / faiblesses
- Rendu terminal sans dépendance externe

Auteur  : Expert Cybersécurité & Python
Licence : MIT
Python  : >= 3.9
"""

from __future__ import annotations

import argparse
import os
import sys
import textwrap
from dataclasses import dataclass
from typing import Dict, List, Tuple, Final

# ============================================================
# MÉTADONNÉES
# ============================================================

__version__: Final[str] = "1.0.0"
__author__: Final[str] = "DarkMBTI Team"

# Toggle couleur : uniquement si la sortie est un TTY (pas de pollution
# des pipes / fichiers redirigés).
USE_COLOR: bool = sys.stdout.isatty() and os.environ.get("NO_COLOR") is None


def colorize(text: str, code: str) -> str:
    """Applique une séquence ANSI si les couleurs sont activées."""
    return f"{code}{text}\033[0m" if USE_COLOR else text


class C:
    """Codes ANSI regroupés."""
    BOLD = "\033[1m"
    DIM = "\033[2m"
    CYAN = "\033[36m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    RED = "\033[31m"
    MAGENTA = "\033[35m"
    BLUE = "\033[34m"


# ============================================================
# MODÈLES DE DONNÉES (immuables → thread-safe, hashables)
# ============================================================

@dataclass(frozen=True)
class Question:
    """Une question binaire associée à un axe MBTI."""
    axis: str            # "EI", "SN", "TF", "JP"
    text: str
    option_a: str
    option_b: str
    pole_a: str          # lettre du pôle A (ex: "E")
    pole_b: str          # lettre du pôle B (ex: "I")


@dataclass(frozen=True)
class Profile:
    """Profil MBTI associé à un code 4 lettres."""
    name: str
    tagline: str
    description: str
    strengths: Tuple[str, ...]
    weaknesses: Tuple[str, ...]


# ============================================================
# BASE DE QUESTIONS (5 par axe → jamais d'égalité)
# ============================================================

QUESTIONS: Final[List[Question]] = [
    # --- E / I : source d'énergie ---
    Question("EI",
             "Après une longue journée, je recharge mes batteries en :",
             "passant du temps avec des amis", "restant seul au calme",
             "E", "I"),
    Question("EI",
             "Dans une soirée où je ne connais personne :",
             "je vais naturellement vers les gens",
             "j'attends qu'on vienne vers moi",
             "E", "I"),
    Question("EI",
             "Je préfère travailler :",
             "en équipe, dans l'effervescence",
             "seul, au calme",
             "E", "I"),
    Question("EI",
             "Quand j'ai un problème, je :",
             "en parle à plusieurs personnes",
             "le rumine intérieurement d'abord",
             "E", "I"),
    Question("EI",
             "Les grandes foules me :",
             "énergisent", "fatiguent",
             "E", "I"),

    # --- S / N : perception ---
    Question("SN",
             "Je fais plus confiance à :",
             "mon expérience concrète",
             "mon intuition",
             "S", "N"),
    Question("SN",
             "Quand j'apprends quelque chose de nouveau :",
             "j'aime les détails pratiques et les exemples",
             "j'aime la vue d'ensemble et les concepts",
             "S", "N"),
    Question("SN",
             "Je remarque plus facilement :",
             "les détails concrets autour de moi",
             "les schémas et connexions cachées",
             "S", "N"),
    Question("SN",
             "Je suis plus attiré par :",
             "ce qui est réel, prouvé et actuel",
             "ce qui est possible, futur et théorique",
             "S", "N"),
    Question("SN",
             "Dans un projet, je préfère :",
             "suivre une méthode éprouvée",
             "explorer des approches originales",
             "S", "N"),

    # --- T / F : décision ---
    Question("TF",
             "Je prends des décisions basées sur :",
             "la logique et l'analyse objective",
             "mes valeurs et l'impact humain",
             "T", "F"),
    Question("TF",
             "Face à un conflit, je :",
             "cherche la solution la plus rationnelle",
             "cherche à préserver l'harmonie",
             "T", "F"),
    Question("TF",
             "On me décrit plutôt comme :",
             "objectif et franc",
             "empathique et diplomate",
             "T", "F"),
    Question("TF",
             "Il est plus important d'être :",
             "juste", "bienveillant",
             "T", "F"),
    Question("TF",
             "Quand un ami a un problème, je :",
             "propose des solutions concrètes",
             "l'écoute et le réconforte",
             "T", "F"),

    # --- J / P : style de vie ---
    Question("JP",
             "Je préfère :",
             "avoir un plan clair à l'avance",
             "voir venir et m'adapter",
             "J", "P"),
    Question("JP",
             "Mon espace de travail est :",
             "organisé et rangé",
             "un peu chaotique mais créatif",
             "J", "P"),
    Question("JP",
             "Face à une deadline, je :",
             "m'y prends en avance",
             "travaille sous pression au dernier moment",
             "J", "P"),
    Question("JP",
             "Je me sens mieux quand :",
             "les choses sont décidées et fixées",
             "j'ai encore des options ouvertes",
             "J", "P"),
    Question("JP",
             "Les plans de dernière minute :",
             "me stressent un peu",
             "m'excitent",
             "J", "P"),
]


# ============================================================
# BASE DES 16 PROFILS MBTI
# ============================================================

PROFILES: Final[Dict[str, Profile]] = {
    "INTJ": Profile(
        "L'Architecte", "Stratège visionnaire, architecte de systèmes",
        "Rare et analytique, l'INTJ combine intuition et logique pour "
        "bâtir des plans à long terme. Indépendant, il remet tout en "
        "question et cherche constamment à optimiser.",
        ("Vision stratégique", "Indépendance intellectuelle",
         "Détermination", "Hautes exigences", "Apprentissage rapide"),
        ("Arrogance perçue", "Peut paraître froid",
         "Difficulté à déléguer", "Impatience face à l'incompétence",
         "Néglige la dimension émotionnelle"),
    ),
    "INFJ": Profile(
        "L'Avocat", "Idéaliste discret, guide des autres",
        "Rare et intuitif, l'INFJ allie empathie profonde et vision. "
        "Il cherche du sens et aide les autres à révéler leur potentiel.",
        ("Empathie profonde", "Vision inspirante", "Intégrité",
         "Créativité", "Dévouement"),
        ("Sensibilité excessive", "Perfectionnisme",
         "Difficulté à dire non", "Épuisement émotionnel",
         "Idéalisme parfois déçu"),
    ),
    "ISTJ": Profile(
        "Le Logisticien", "Pilier fiable, gardien des traditions",
        "Pratique, factuel et fiable, l'ISTJ excelle dans l'organisation "
        "et le respect des engagements.",
        ("Fiabilité", "Sens du devoir", "Organisation",
         "Patience", "Attention aux détails"),
        ("Rigidité", "Résistance au changement",
         "Difficulté à exprimer ses émotions",
         "Jugement rapide", "Peut être trop conventionnel"),
    ),
    "ISFJ": Profile(
        "Le Défenseur", "Protecteur dévoué et chaleureux",
        "Chaleureux et consciencieux, l'ISFJ prend soin des autres avec "
        "discrétion et loyauté.",
        ("Loyauté", "Altruisme", "Patience",
         "Sens du détail", "Fiabilité"),
        ("Difficulté à s'affirmer", "Néglige ses propres besoins",
         "Résistance au changement", "Prend trop sur soi",
         "Très sensible aux critiques"),
    ),
    "ISTP": Profile(
        "Le Virtuose", "Artisan pragmatique et curieux",
        "Expérimentateur né, l'ISTP aime comprendre comment les choses "
        "fonctionnent et résoudre des problèmes concrets.",
        ("Pragmatisme", "Calme sous pression", "Habileté technique",
         "Autonomie", "Résolution de problèmes"),
        ("Détachement émotionnel", "Ennui facile",
         "Imprévisibilité", "Difficulté à s'engager",
         "Peut paraître insensible"),
    ),
    "ISFP": Profile(
        "L'Aventurier", "Artiste sensible et libre",
        "Créatif et sensible, l'ISFP vit selon ses valeurs et cherche "
        "la beauté dans l'instant présent.",
        ("Créativité", "Empathie", "Souplesse", "Passion",
         "Sens esthétique"),
        ("Évitement des conflits", "Difficulté à planifier",
         "Sensible aux critiques", "Imprévisibilité",
         "Manque d'ambition long terme"),
    ),
    "INTP": Profile(
        "Le Logicien", "Penseur analytique, explorateur d'idées",
        "Curieux et analytique, l'INTP adore démonter les concepts et "
        "explorer des théories.",
        ("Analyse profonde", "Créativité intellectuelle",
         "Objectivité", "Honnêteté", "Adaptabilité"),
        ("Procrastination", "Difficulté à finaliser",
         "Détachement émotionnel", "Impatience sociale",
         "Vit trop dans sa tête"),
    ),
    "INFP": Profile(
        "Le Médiateur", "Idéaliste poétique, cœur sensible",
        "Rêveur idéaliste, l'INFP cherche du sens et reste fidèle à ses "
        "valeurs profondes.",
        ("Empathie", "Créativité", "Idéalisme", "Loyauté",
         "Ouverture d'esprit"),
        ("Trop idéaliste", "Difficulté avec le concret",
         "Évitement des conflits", "Auto-critique sévère",
         "Difficulté à s'affirmer"),
    ),
    "ENTJ": Profile(
        "Le Commandant", "Leader né, stratège ambitieux",
        "Leader charismatique, l'ENTJ mobilise les autres vers des "
        "objectifs ambitieux.",
        ("Leadership", "Détermination", "Vision stratégique",
         "Efficacité", "Confiance en soi"),
        ("Autoritarisme", "Impatience", "Intolérance",
         "Néglige les émotions", "Trop exigeant"),
    ),
    "ENFJ": Profile(
        "Le Protagoniste", "Leader inspirant et bienveillant",
        "Charismatique et altruiste, l'ENFJ inspire les autres et œuvre "
        "pour le bien commun.",
        ("Charisme", "Empathie", "Communication",
         "Altruisme", "Organisation"),
        ("Difficulté à dire non", "Trop idéaliste",
         "Sensible aux critiques", "Néglige ses besoins",
         "Manipulation involontaire"),
    ),
    "ESTJ": Profile(
        "Le Directeur", "Administrateur rigoureux et fiable",
        "Organisé et direct, l'ESTJ aime structurer et faire avancer les "
        "choses efficacement.",
        ("Organisation", "Leadership", "Fiabilité",
         "Franchise", "Sens des responsabilités"),
        ("Rigidité", "Manque de tact", "Résistance au changement",
         "Jugement hâtif", "Difficulté avec les émotions"),
    ),
    "ESFJ": Profile(
        "Le Consul", "Coordinateur chaleureux et sociable",
        "Sociable et consciencieux, l'ESFJ aime aider et maintenir "
        "l'harmonie du groupe.",
        ("Altruisme", "Loyauté", "Organisation",
         "Communication", "Empathie"),
        ("Besoin d'approbation", "Sensible aux critiques",
         "Évitement des conflits", "Néglige ses besoins",
         "Peut être envahissant"),
    ),
    "ESTP": Profile(
        "L'Entrepreneur", "Aventurier énergique et pragmatique",
        "Audacieux et vif, l'ESTP vit dans l'instant et excelle dans "
        "l'action.",
        ("Audace", "Pragmatisme", "Sociabilité",
         "Réactivité", "Négociation"),
        ("Imprudence", "Impatience", "Manque de planification",
         "Sensible à l'ennui", "Peut être insensible"),
    ),
    "ESFP": Profile(
        "L'Amuseur", "Animateur spontané et joyeux",
        "Spontané et chaleureux, l'ESFP apporte joie et énergie partout "
        "où il passe.",
        ("Sociabilité", "Enthousiasme", "Empathie",
         "Spontanéité", "Sens pratique"),
        ("Imprévisibilité", "Difficulté à planifier",
         "Évitement des conflits", "Sensible au stress",
         "Manque de concentration"),
    ),
    "ENTP": Profile(
        "L'Innovateur", "Débatteur brillant et inventif",
        "Inventif et provocateur, l'ENTP adore explorer des idées et "
        "défier les conventions.",
        ("Créativité", "Vivacité d'esprit", "Adaptabilité",
         "Charisme", "Vision"),
        ("Argumentatif", "Difficulté à finaliser",
         "Impatience", "Manque de suivi",
         "Peut blesser sans le vouloir"),
    ),
    "ENFP": Profile(
        "L'Inspirateur", "Esprit libre enthousiaste et créatif",
        "Enthousiaste et créatif, l'ENFP inspire les autres et explore "
        "sans cesse de nouvelles possibilités.",
        ("Enthousiasme", "Créativité", "Empathie",
         "Communication", "Adaptabilité"),
        ("Dispersion", "Difficulté à finir",
         "Sensibilité émotionnelle", "Désorganisation",
         "Besoin d'approbation"),
    ),
}


# ============================================================
# MOTEUR DU QUIZ
# ============================================================

class Quiz:
    """
    Moteur d'évaluation MBTI.

    Le quiz est piloté par une liste de Question. Le scoring est un simple
    compteur par pôle. Comme chaque axe comporte un nombre impair de
    questions, aucun match nul n'est possible.
    """

    AXES: Final[Tuple[Tuple[str, str, str], ...]] = (
        ("EI", "E", "I"),
        ("SN", "S", "N"),
        ("TF", "T", "F"),
        ("JP", "J", "P"),
    )

    def __init__(self, questions: List[Question]) -> None:
        self.questions = questions
        self.scores: Dict[str, int] = {p: 0 for _, a, b in self.AXES for p in (a, b)}

    # ---------- API publique ----------

    def run(self) -> str:
        """Pose toutes les questions et retourne le type MBTI (ex: 'INTJ')."""
        total = len(self.questions)
        for index, question in enumerate(self.questions, start=1):
            self._print_progress(index, total)
            choice = self._ask(question)
            pole = question.pole_a if choice == "A" else question.pole_b
            self.scores[pole] += 1
        return self._compute_type()

    def scores_for(self, pole_a: str, pole_b: str) -> Tuple[int, int]:
        """Retourne (score_a, score_b) pour un axe donné."""
        return self.scores[pole_a], self.scores[pole_b]

    # ---------- Interne ----------

    def _print_progress(self, index: int, total: int) -> None:
        filled = int((index - 1) / total * 30)
        bar = "█" * filled + "░" * (30 - filled)
        pct = int((index - 1) / total * 100)
        line = f"  [{bar}] {pct:3d}%  (question {index}/{total})"
        print(colorize(line, C.DIM))

    def _ask(self, q: Question) -> str:
        """Pose une question, valide l'entrée, borne strictement à A/B."""
        print()
        print(colorize(f"  ▶ {q.text}", C.BOLD))
        print(f"      {colorize('A)', C.CYAN)} {q.option_a}")
        print(f"      {colorize('B)', C.CYAN)} {q.option_b}")

        while True:
            try:
                raw = input(colorize("  Choix (A/B) > ", C.YELLOW))
            except (EOFError, KeyboardInterrupt):
                print()
                print(colorize("\n  [!] Interruption — sortie propre.", C.RED))
                sys.exit(130)

            choice = raw.strip().upper()
            if choice in ("A", "B"):
                return choice
            # Pas d'echo, pas d'eval, message clair.
            print(colorize("  [!] Entrée invalide. Tapez 'A' ou 'B'.", C.RED))

    def _compute_type(self) -> str:
        result = []
        for _, a, b in self.AXES:
            result.append(a if self.scores[a] >= self.scores[b] else b)
        return "".join(result)


# ============================================================
# RENDU DU RÉSULTAT
# ============================================================

def _wrap(text: str, width: int = 68, indent: str = "  ") -> str:
    return textwrap.fill(text, width=width, initial_indent=indent,
                         subsequent_indent=indent)


def _bar(score_a: int, score_b: int, pole_a: str, pole_b: str,
         width: int = 24) -> str:
    """Petite visualisation 'A ●———○ B'."""
    total = score_a + score_b
    ratio = score_a / total if total else 0.5
    pos = int(ratio * (width - 1))
    track = list("─" * width)
    track[pos] = "●"
    return f"  {pole_a} {''.join(track)} {pole_b}   ({score_a} / {score_b})"


def render_result(mbti: str, quiz: Quiz) -> None:
    profile = PROFILES.get(mbti)
    if profile is None:
        print(colorize(f"\n  [!] Profil inconnu : {mbti}", C.RED))
        return

    sep = "═" * 70
    print()
    print(colorize(sep, C.MAGENTA))
    print(colorize(f"  RÉSULTAT : {mbti} — {profile.name}", C.BOLD + C.MAGENTA))
    print(colorize(f"  {profile.tagline}", C.DIM))
    print(colorize(sep, C.MAGENTA))
    print()

    print(colorize("  Description", C.BOLD + C.CYAN))
    print(_wrap(profile.description))
    print()

    print(colorize("  Détail par axe", C.BOLD + C.CYAN))
    for _, a, b in Quiz.AXES:
        sa, sb = quiz.scores_for(a, b)
        print(_bar(sa, sb, a, b))
    print()

    print(colorize("  Forces", C.BOLD + C.GREEN))
    for s in profile.strengths:
        print(f"    ✔ {s}")
    print()

    print(colorize("  Faiblesses", C.BOLD + C.RED))
    for w in profile.weaknesses:
        print(f"    ✘ {w}")
    print()


# ============================================================
# INTERFACE CLI
# ============================================================

BANNER = r"""
  ╔══════════════════════════════════════════════════════════════╗
  ║                    DarkMBTI  v1.0.0                         ║
  ║        Découvre ton type de personnalité MBTI               ║
  ║        20 questions · 16 profils · 100 % offline            ║
  ╚══════════════════════════════════════════════════════════════╝
"""


def print_banner() -> None:
    print(colorize(BANNER, C.MAGENTA))


def parse_args(argv: List[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="darkmbti",
        description="DarkMBTI — évaluation de personnalité MBTI en CLI.",
        epilog="Aucune donnée n'est transmise : tout est local.",
    )
    parser.add_argument("-v", "--version", action="version",
                        version=f"DarkMBTI {__version__}")
    parser.add_argument("--no-color", action="store_true",
                        help="Désactiver la coloration ANSI.")
    parser.add_argument("--list", action="store_true",
                        help="Lister les 16 profils et quitter.")
    return parser.parse_args(argv)


def cmd_list_profiles() -> None:
    print(colorize("\n  Les 16 profils MBTI\n", C.BOLD + C.CYAN))
    for code in sorted(PROFILES):
        p = PROFILES[code]
        print(f"    {colorize(code, C.BOLD)} — {p.name:<18} {colorize('— ' + p.tagline, C.DIM)}")
    print()


def main(argv: List[str] | None = None) -> int:
    global USE_COLOR
    args = parse_args(argv if argv is not None else sys.argv[1:])
    if args.no_color:
        USE_COLOR = False

    if args.list:
        cmd_list_profiles()
        return 0

    print_banner()
    print(colorize(
        "  Ce test est un outil de réflexion, pas un diagnostic clinique.\n"
        "  Répondez spontanément : la première réponse est souvent la bonne.\n",
        C.DIM,
    ))

    try:
        input(colorize("  [Entrée] pour commencer…", C.YELLOW))
    except (EOFError, KeyboardInterrupt):
        print()
        return 130

    quiz = Quiz(QUESTIONS)
    try:
        mbti = quiz.run()
    except KeyboardInterrupt:
        print(colorize("\n  [!] Interruption.", C.RED))
        return 130

    render_result(mbti, quiz)
    print(colorize("  Merci d'avoir utilisé DarkMBTI. — v" + __version__,
                   C.DIM))
    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())