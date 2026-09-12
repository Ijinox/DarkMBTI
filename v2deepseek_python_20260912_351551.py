#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DarkMBTI v2.0
=============

Outil CLI d'évaluation de personnalité inspiré du modèle MBTI, avec :
  - 20 questions (5 par axe : E/I, S/N, T/F, J/P)
  - Moteur de scoring pondéré
  - Base de 16 profils avec forces / faiblesses
  - IA locale légère (Ollama) pour reformuler les questions humainement
  - Garde-fous de sécurité multicouches (sanitisation, rate limit, filtrage)
  - Fallback statique intégral si Ollama est indisponible

⚠️  AVERTISSEMENT ÉTHIQUE ET LÉGAL
-----------------------------------
Ce logiciel est un outil de DÉVELOPPEMENT PERSONNEL.
Il n'est PAS — et ne doit PAS être utilisé comme :
  • un outil de profilage criminel ou de détection de "dangerosité" ;
  • un instrument d'évaluation psychiatrique ou clinique ;
  • un moyen de cibler, discriminer ou surveiller des individus ou
    des groupes, notamment sur des critères religieux, ethniques,
    politiques ou de genre.

Toute utilisation à ces fins serait :
  • scientifiquement invalide (la MBTI n'a aucune valeur prédictive
    sur la dangerosité — voir lettres ouvertes de la communauté
    psychométrique) ;
  • illégale en France (art. 225-1 et 226-1 du Code pénal) ;
  • contraire à l'éthique professionnelle.

Auteur  : Adrian Daniel ANTONIAK (consolidation)
Licence : MIT
Python  : >= 3.9
"""

from __future__ import annotations

import argparse
import json
import os
import random
import re
import shutil
import subprocess
import sys
import textwrap
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Final, List, Optional, Tuple


# ============================================================
# MÉTADONNÉES
# ============================================================

__version__: Final[str] = "2.0.0"
__author__: Final[str] = "DarkMBTI Team"


# ============================================================
# AFFICHAGE / COULEURS
# ============================================================

USE_COLOR: bool = sys.stdout.isatty() and os.environ.get("NO_COLOR") is None


def colorize(text: str, code: str) -> str:
    return f"{code}{text}\033[0m" if USE_COLOR else text


class C:
    BOLD = "\033[1m"
    DIM = "\033[2m"
    CYAN = "\033[36m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    RED = "\033[31m"
    MAGENTA = "\033[35m"
    BLUE = "\033[34m"


# ============================================================
# MODÈLES DE DONNÉES
# ============================================================

@dataclass(frozen=True)
class Question:
    axis: str
    text: str
    option_a: str
    option_b: str
    pole_a: str
    pole_b: str


@dataclass(frozen=True)
class Profile:
    name: str
    tagline: str
    description: str
    strengths: Tuple[str, ...]
    weaknesses: Tuple[str, ...]


# ============================================================
# BASE DE QUESTIONS (5 par axe → pas d'égalité possible)
# ============================================================

QUESTIONS: Final[List[Question]] = [
    # --- E / I ---
    Question("EI", "Après une longue journée, je recharge mes batteries en :",
             "passant du temps avec des amis", "restant seul au calme", "E", "I"),
    Question("EI", "Dans une soirée où je ne connais personne :",
             "je vais naturellement vers les gens",
             "j'attends qu'on vienne vers moi", "E", "I"),
    Question("EI", "Je préfère travailler :",
             "en équipe, dans l'effervescence", "seul, au calme", "E", "I"),
    Question("EI", "Quand j'ai un problème, je :",
             "en parle à plusieurs personnes",
             "le rumine intérieurement d'abord", "E", "I"),
    Question("EI", "Les grandes foules me :",
             "énergisent", "fatiguent", "E", "I"),

    # --- S / N ---
    Question("SN", "Je fais plus confiance à :",
             "mon expérience concrète", "mon intuition", "S", "N"),
    Question("SN", "Quand j'apprends quelque chose de nouveau :",
             "j'aime les détails pratiques et les exemples",
             "j'aime la vue d'ensemble et les concepts", "S", "N"),
    Question("SN", "Je remarque plus facilement :",
             "les détails concrets autour de moi",
             "les schémas et connexions cachées", "S", "N"),
    Question("SN", "Je suis plus attiré par :",
             "ce qui est réel, prouvé et actuel",
             "ce qui est possible, futur et théorique", "S", "N"),
    Question("SN", "Dans un projet, je préfère :",
             "suivre une méthode éprouvée",
             "explorer des approches originales", "S", "N"),

    # --- T / F ---
    Question("TF", "Je prends des décisions basées sur :",
             "la logique et l'analyse objective",
             "mes valeurs et l'impact humain", "T", "F"),
    Question("TF", "Face à un conflit, je :",
             "cherche la solution la plus rationnelle",
             "cherche à préserver l'harmonie", "T", "F"),
    Question("TF", "On me décrit plutôt comme :",
             "objectif et franc", "empathique et diplomate", "T", "F"),
    Question("TF", "Il est plus important d'être :",
             "juste", "bienveillant", "T", "F"),
    Question("TF", "Quand un ami a un problème, je :",
             "propose des solutions concrètes",
             "l'écoute et le réconforte", "T", "F"),

    # --- J / P ---
    Question("JP", "Je préfère :",
             "avoir un plan clair à l'avance",
             "voir venir et m'adapter", "J", "P"),
    Question("JP", "Mon espace de travail est :",
             "organisé et rangé", "un peu chaotique mais créatif", "J", "P"),
    Question("JP", "Face à une deadline, je :",
             "m'y prends en avance",
             "travaille sous pression au dernier moment", "J", "P"),
    Question("JP", "Je me sens mieux quand :",
             "les choses sont décidées et fixées",
             "j'ai encore des options ouvertes", "J", "P"),
    Question("JP", "Les plans de dernière minute :",
             "me stressent un peu", "m'excitent", "J", "P"),
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
# GARDE-FOUS OLLAMA
# ============================================================

class OllamaGuard:
    """Constantes de sécurité centralisées. Ne pas assouplir sans audit."""

    MODEL_NAME: Final[str] = "gemma3:1b"
    MODEL_MIN_SIZE_MB: Final[int] = 400
    OLLAMA_BIN: Final[str] = "ollama"

    HOST: Final[str] = "127.0.0.1"
    PORT: Final[int] = 11434
    CONNECT_TIMEOUT: Final[int] = 5
    READ_TIMEOUT: Final[int] = 30

    MAX_NUM_PREDICT: Final[int] = 256
    TEMPERATURE: Final[float] = 0.7
    TOP_P: Final[float] = 0.9
    MAX_CALLS_PER_SESSION: Final[int] = 60
    MIN_INTERVAL_MS: Final[int] = 200

    MAX_INPUT_LEN: Final[int] = 500
    MAX_INPUT_LINES: Final[int] = 5

    MAX_OUTPUT_LEN: Final[int] = 800
    MIN_OUTPUT_LEN: Final[int] = 3

    INJECTION_PATTERNS: Final[tuple] = (
        r"ignore\s+(all\s+)?(previous|prior|above)",
        r"disregard\s+(all\s+)?(rules|instructions)",
        r"you\s+are\s+now\s+",
        r"from\s+now\s+on",
        r"act\s+as\s+(if|a)\s+",
        r"system\s*:\s*",
        r"<\s*\|.*?\|\s*>",
        r"###\s*instruction",
        r"repeat\s+(after\s+)?me",
        r"reveal\s+(your\s+)?(prompt|instructions|system)",
    )
    _INJECTION_RE: Final[re.Pattern] = re.compile(
        "|".join(INJECTION_PATTERNS), re.IGNORECASE | re.DOTALL
    )

    TOXIC_PATTERNS: Final[tuple] = (
        r"\b(kill|tuer|meurtre|suicide|détruire|détruis)\b",
        r"\b(haine|hate|supremacy|suprématie)\b",
        r"\b(arme|weapon|bombe|bomb|explosif|explosive)\b",
        r"\b(drogue|drug|cocaine|héroïne|heroin)\b",
    )
    _TOXIC_RE: Final[re.Pattern] = re.compile(
        "|".join(TOXIC_PATTERNS), re.IGNORECASE
    )


class OllamaUnavailable(Exception):
    """Ollama non joignable ou modèle absent."""


class GuardViolation(Exception):
    """Garde-fou d'entrée ou de sortie déclenché."""


# ============================================================
# CLIENT OLLAMA SÉCURISÉ
# ============================================================

class SecureOllamaClient:
    """
    Client Ollama local avec défense en profondeur.
    Aucun appel réseau sortant, aucun shell=True, fallback permanent.
    """

    def __init__(self, guard: type[OllamaGuard] = OllamaGuard,
                 enable: bool = True) -> None:
        self.g = guard
        self.enabled = enable and self._detect_ollama()
        self._call_count = 0
        self._last_call_ts = 0.0
        self._stats = {"success": 0, "blocked": 0, "fallback": 0, "errors": 0}

    def _detect_ollama(self) -> bool:
        return shutil.which(self.g.OLLAMA_BIN) is not None

    def _model_available(self) -> bool:
        try:
            result = subprocess.run(
                [self.g.OLLAMA_BIN, "list"],
                capture_output=True, text=True, timeout=10, check=False,
            )
            return self.g.MODEL_NAME.split(":")[0] in result.stdout
        except (subprocess.SubprocessError, OSError):
            return False

    def _enforce_rate_limit(self) -> None:
        now = time.monotonic() * 1000
        if now - self._last_call_ts < self.g.MIN_INTERVAL_MS:
            time.sleep((self.g.MIN_INTERVAL_MS - (now - self._last_call_ts)) / 1000)
        if self._call_count >= self.g.MAX_CALLS_PER_SESSION:
            raise GuardViolation(
                f"Limite de {self.g.MAX_CALLS_PER_SESSION} appels atteinte."
            )
        self._call_count += 1
        self._last_call_ts = time.monotonic() * 1000

    @classmethod
    def sanitize_input(cls, text: str) -> str:
        if not isinstance(text, str):
            raise GuardViolation("Entrée non textuelle rejetée.")
        text = text.encode("utf-8", "ignore").decode("utf-8", "ignore")
        text = "".join(c for c in text if c.isprintable() or c in "\n\t ")
        text = text[: cls.g.MAX_INPUT_LEN]
        lines = text.splitlines()[: cls.g.MAX_INPUT_LINES]
        text = "\n".join(lines).strip()
        if len(text) < 1:
            raise GuardViolation("Entrée vide après sanitisation.")
        if cls.g._INJECTION_RE.search(text):
            raise GuardViolation("Pattern d'injection détecté.")
        return text

    @classmethod
    def validate_output(cls, text: str) -> str:
        if not isinstance(text, str):
            raise GuardViolation("Sortie non textuelle.")
        text = text.strip()
        if len(text) < cls.g.MIN_OUTPUT_LEN:
            raise GuardViolation("Sortie trop courte.")
        text = text[: cls.g.MAX_OUTPUT_LEN]
        text = re.sub(r"<[^>]+>", "", text)
        if cls.g._TOXIC_RE.search(text):
            raise GuardViolation("Contenu toxique détecté dans la sortie.")
        return text

    def generate(self, prompt: str, system: str = "") -> Optional[str]:
        if not self.enabled:
            self._stats["fallback"] += 1
            return None
        try:
            self._enforce_rate_limit()
        except GuardViolation:
            self._stats["blocked"] += 1
            return None

        # Sanitisation du prompt interne (défense supplémentaire)
        try:
            prompt = self.sanitize_input(prompt)
        except GuardViolation:
            self._stats["blocked"] += 1
            return None

        full_prompt = (
            f"<|system|>\n{system}\n<|end|>\n"
            f"<|user|>\n{prompt}\n<|end|>\n"
            f"<|assistant|>\n"
        )

        try:
            result = subprocess.run(
                [
                    self.g.OLLAMA_BIN, "run", self.g.MODEL_NAME,
                    "--format", "json",
                    "--options", json.dumps({
                        "num_predict": self.g.MAX_NUM_PREDICT,
                        "temperature": self.g.TEMPERATURE,
                        "top_p": self.g.TOP_P,
                    }),
                ],
                input=full_prompt,
                capture_output=True,
                text=True,
                timeout=self.g.READ_TIMEOUT,
                check=False,
            )
        except subprocess.TimeoutExpired:
            self._stats["errors"] += 1
            return None
        except (subprocess.SubprocessError, OSError):
            self._stats["errors"] += 1
            return None

        if result.returncode != 0:
            self._stats["errors"] += 1
            return None
        raw = result.stdout.strip()
        if not raw:
            self._stats["errors"] += 1
            return None
        try:
            clean = self.validate_output(raw)
        except GuardViolation:
            self._stats["blocked"] += 1
            return None
        self._stats["success"] += 1
        return clean

    def stats(self) -> dict:
        return dict(self._stats)


# ============================================================
# MOTEUR DU QUIZ (v1 + extension IA)
# ============================================================

class Quiz:
    AXES: Final[Tuple[Tuple[str, str, str], ...]] = (
        ("EI", "E", "I"),
        ("SN", "S", "N"),
        ("TF", "T", "F"),
        ("JP", "J", "P"),
    )

    def __init__(self, questions: List[Question]) -> None:
        self.questions = questions
        self.scores: Dict[str, int] = {
            p: 0 for _, a, b in self.AXES for p in (a, b)
        }

    def run(self) -> str:
        total = len(self.questions)
        for index, question in enumerate(self.questions, start=1):
            self._print_progress(index, total)
            choice = self._ask(question)
            pole = question.pole_a if choice == "A" else question.pole_b
            self.scores[pole] += 1
        return self._compute_type()

    def scores_for(self, pole_a: str, pole_b: str) -> Tuple[int, int]:
        return self.scores[pole_a], self.scores[pole_b]

    def _print_progress(self, index: int, total: int) -> None:
        filled = int((index - 1) / total * 30)
        bar = "█" * filled + "░" * (30 - filled)
        pct = int((index - 1) / total * 100)
        line = f"  [{bar}] {pct:3d}%  (question {index}/{total})"
        print(colorize(line, C.DIM))

    def _ask(self, q: Question) -> str:
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
            print(colorize("  [!] Entrée invalide. Tapez 'A' ou 'B'.", C.RED))

    def _compute_type(self) -> str:
        return "".join(
            a if self.scores[a] >= self.scores[b] else b
            for _, a, b in self.AXES
        )


class AIEnhancedQuiz(Quiz):
    """Quiz v2 avec reformulation humaine via IA locale + fallback."""

    SYSTEM_PROMPT = (
        "Tu es un psychologue bienveillant qui aide à découvrir la "
        "personnalité MBTI. Réponds TOUJOURS en français, en une phrase "
        "courte (max 25 mots). Ne pose JAMAIS de question médicale. "
        "Ne sors JAMAIS du cadre MBTI. Ne juge jamais l'utilisateur."
    )

    def __init__(self, questions, ai: Optional[SecureOllamaClient] = None):
        super().__init__(questions)
        self.ai = ai or SecureOllamaClient()

    def _humanize_question(self, q: Question) -> str:
        if not self.ai.enabled:
            return q.text
        prompt = (
            f"Reformule cette question MBTI de manière naturelle et "
            f"chaleureuse, sans changer son sens : '{q.text}'"
        )
        try:
            out = self.ai.generate(prompt, system=self.SYSTEM_PROMPT)
            if out:
                return out
        except GuardViolation:
            pass
        return q.text

    def _react(self, choice: str, q: Question) -> None:
        if not self.ai.enabled:
            return
        pole = q.pole_a if choice == "A" else q.pole_b
        prompt = (
            f"L'utilisateur vient de choisir une réponse indiquant une "
            f"préférence '{pole}'. Réagis chaleureusement en une phrase."
        )
        try:
            out = self.ai.generate(prompt, system=self.SYSTEM_PROMPT)
            if out:
                print(colorize(f"  💬 {out}", C.CYAN))
        except GuardViolation:
            pass

    def _ask(self, q: Question) -> str:
        display = self._humanize_question(q)
        print()
        print(colorize(f"  ▶ {display}", C.BOLD))
        print(f"      {colorize('A)', C.CYAN)} {q.option_a}")
        print(f"      {colorize('B)', C.CYAN)} {q.option_b}")
        while True:
            try:
                raw = input(colorize("  Choix (A/B) > ", C.YELLOW))
            except (EOFError, KeyboardInterrupt):
                print()
                sys.exit(130)
            choice = raw.strip().upper()
            if choice in ("A", "B"):
                self._react(choice, q)
                return choice
            print(colorize("  [!] Tapez 'A' ou 'B'.", C.RED))


# ============================================================
# RENDU DU RÉSULTAT
# ============================================================

def _wrap(text: str, width: int = 68, indent: str = "  ") -> str:
    return textwrap.fill(text, width=width,
                         initial_indent=indent, subsequent_indent=indent)


def _bar(score_a: int, score_b: int, pole_a: str, pole_b: str,
         width: int = 24) -> str:
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
# DISCLAIMER OBLIGATOIRE
# ============================================================

DISCLAIMER = """
⚠️  AVERTISSEMENT — À LIRE

DarkMBTI est un outil de développement personnel, PAS un outil de
profilage, de surveillance ou d'évaluation de dangerosité.

• Les corrélations entre type MBTI et comportements sont statistiques,
  non prédictives au niveau individuel.
• Aucun type n'est "dangereux" en soi.
• Utiliser cet outil pour cibler des individus ou des groupes
  (religieux, ethniques, politiques, etc.) serait illégal et contraire
  à l'éthique.
• La MBTI n'est pas un outil de profilage criminel validé par la
  communauté scientifique.

Ressources :
  • France — 3114 (prévention du suicide)
  • Urgences : 15 / 112
  • Violences faites aux femmes : 3919
  • Signalement en ligne : https://www.internet-signalement.gouv.fr
"""


# ============================================================
# INTERFACE CLI
# ============================================================

BANNER = r"""
  ╔══════════════════════════════════════════════════════════════╗
  ║                    DarkMBTI  v2.0.0                         ║
  ║        Découvre ton type de personnalité MBTI               ║
  ║        20 questions · 16 profils · IA locale optionnelle    ║
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
    parser.add_argument("--no-ai", action="store_true",
                        help="Désactiver l'IA locale (mode statique).")
    parser.add_argument("--list", action="store_true",
                        help="Lister les 16 profils et quitter.")
    parser.add_argument("--stats", action="store_true",
                        help="Afficher les stats de sécurité de l'IA.")
    return parser.parse_args(argv)


def cmd_list_profiles() -> None:
    print(colorize("\n  Les 16 profils MBTI\n", C.BOLD + C.CYAN))
    for code in sorted(PROFILES):
        p = PROFILES[code]
        print(f"    {colorize(code, C.BOLD)} — {p.name:<18} "
              f"{colorize('— ' + p.tagline, C.DIM)}")
    print()


def main(argv: Optional[List[str]] = None) -> int:
    global USE_COLOR
    args = parse_args(argv if argv is not None else sys.argv[1:])
    if args.no_color:
        USE_COLOR = False

    if args.list:
        cmd_list_profiles()
        return 0

    print_banner()
    print(colorize(DISCLAIMER, C.DIM))

    ai = None if args.no_ai else SecureOllamaClient()

    if args.stats:
        if ai:
            print(colorize("  IA locale : ACTIVÉE" if ai.enabled
                           else "  IA locale : INDISPONIBLE (fallback statique)",
                           C.CYAN))
        else:
            print(colorize("  IA locale : DÉSACTIVÉE (--no-ai)", C.CYAN))
        return 0

    if ai:
        state = "activée" if ai.enabled else "indisponible (fallback statique)"
        print(colorize(f"  IA locale : {state}", C.DIM))

    print(colorize(
        "\n  Répondez spontanément : la première réponse est souvent la bonne.\n",
        C.DIM,
    ))

    try:
        input(colorize("  [Entrée] pour commencer…", C.YELLOW))
    except (EOFError, KeyboardInterrupt):
        print()
        return 130

    quiz = AIEnhancedQuiz(QUESTIONS, ai=ai)
    try:
        mbti = quiz.run()
    except KeyboardInterrupt:
        print(colorize("\n  [!] Interruption.", C.RED))
        return 130

    render_result(mbti, quiz)

    if ai and ai.enabled:
        s = ai.stats()
        print(colorize(
            f"  [IA] {s['success']} succès · {s['blocked']} bloqués · "
            f"{s['errors']} erreurs · {s['fallback']} fallbacks",
            C.DIM,
        ))

    print(colorize(f"  Merci d'avoir utilisé DarkMBTI. — v{__version__}", C.DIM))
    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())