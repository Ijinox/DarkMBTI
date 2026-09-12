#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DarkMBTI — édition minimaliste
==============================

Un petit outil d'auto-observation, sans prétention.

- 16 questions, 4 axes, un résultat nuancé.
- Aucune donnée quitte ta machine.
- Aucune étiquette définitive : le résultat est une photo, pas une identité.
- Sauvegarde locale optionnelle (JSON), à toi de la gérer.

Usage :
    python darkmbti.py            # quiz
    python darkmbti.py --save     # quiz + sauvegarde locale
    python darkmbti.py --history  # relire tes sessions passées

Python 3.9+ · Licence MIT · Aucune dépendance.
"""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import List, Tuple

HISTORY_FILE = Path.home() / ".darkmbti_history.json"
MAX_HISTORY = 50


# ------------------------------------------------------------
# Données — 4 questions par axe, formulations neutres
# ------------------------------------------------------------

@dataclass(frozen=True)
class Q:
    axis: str
    text: str
    a: str
    b: str
    pa: str   # pôle A
    pb: str   # pôle B


QUESTIONS: List[Q] = [
    Q("EI", "Après une journée chargée, je me ressource plutôt…",
      "avec du monde", "dans le calme", "E", "I"),
    Q("EI", "Quand je réfléchis à un problème, j'ai tendance à…",
      "en parler autour de moi", "le retourner en silence", "E", "I"),
    Q("EI", "Dans un groupe, je suis plutôt…",
      "celui qui lance les échanges", "celui qui écoute d'abord", "E", "I"),
    Q("EI", "Ce qui me fatigue le plus, c'est…",
      "trop de solitude", "trop de monde", "E", "I"),

    Q("SN", "Quand j'apprends un sujet neuf, je pars de…",
      "ce qui est concret, vérifiable", "ce que ça pourrait vouloir dire", "S", "N"),
    Q("SN", "Je fais plus confiance à…",
      "ce que j'ai vécu", "ce que je pressens", "S", "N"),
    Q("SN", "Dans un projet, ce qui m'attire, c'est…",
      "le faire bien, pas à pas", "imaginer où ça peut mener", "S", "N"),
    Q("SN", "Je remarque d'abord…",
      "les détails autour de moi", "l'ambiance générale", "S", "N"),

    Q("TF", "Quand je dois trancher, je m'appuie sur…",
      "ce qui tient debout logiquement", "ce qui respecte les personnes", "T", "F"),
    Q("TF", "On me dit souvent…",
      "direct", "attentif aux autres", "T", "F"),
    Q("TF", "Ce qui me dérange le plus, c'est…",
      "l'illogisme", "la brutalité", "T", "F"),
    Q("TF", "Face à un désaccord, je cherche d'abord…",
      "à clarifier les faits", "à préserver le lien", "T", "F"),

    Q("JP", "Ce qui me rassure, c'est…",
      "un plan posé", "garder des options ouvertes", "J", "P"),
    Q("JP", "J'avance mieux quand…",
      "je sais où je vais", "je peux ajuster en route", "J", "P"),
    Q("JP", "Ma manière naturelle de travailler, c'est…",
      "structurer puis exécuter", "explorer puis recomposer", "J", "P"),
    Q("JP", "Un changement imprévu me…",
      "dérange un peu", "met en mouvement", "J", "P"),
]


# ------------------------------------------------------------
# Moteur — simple, transparent, sans surprise
# ------------------------------------------------------------

class Quiz:
    AXES = (("EI", "E", "I"), ("SN", "S", "N"),
            ("TF", "T", "F"), ("JP", "J", "P"))

    def __init__(self) -> None:
        self.scores = {p: 0 for _, a, b in self.AXES for p in (a, b)}

    def run(self) -> str:
        for i, q in enumerate(QUESTIONS, 1):
            self._ask(q, i)
        return "".join(
            a if self.scores[a] > self.scores[b] else b
            for _, a, b in self.AXES
        )

    def _ask(self, q: Q, n: int) -> None:
        print(f"\n  {n:2d}/{len(QUESTIONS)}  {q.text}")
        print(f"        1) {q.a}")
        print(f"        2) {q.b}")
        while True:
            try:
                r = input("        > ").strip()
            except (EOFError, KeyboardInterrupt):
                print("\n  Sortie.")
                sys.exit(0)
            if r in ("1", "2"):
                self.scores[q.pa if r == "1" else q.pb] += 1
                return
            print("        (1 ou 2)")

    def strengths(self) -> List[str]:
        """Nuances : quels pôles dominent et à quel point."""
        out = []
        for _, a, b in self.AXES:
            sa, sb = self.scores[a], self.scores[b]
            if sa == sb:
                out.append(f"{a}/{b} — équilibré")
            elif sa == 4 or sb == 4:
                out.append(f"{a if sa > sb else b} — net")
            else:
                out.append(f"{a if sa > sb else b} — léger")
        return out


# ------------------------------------------------------------
# Rendu — sobre, sans jugement
# ------------------------------------------------------------

READING = {
    "EI": ("Energie : plutôt tournée vers l'extérieur.",
           "Energie : plutôt tournée vers l'intérieur."),
    "SN": ("Perception : appui sur le concret et l'observable.",
           "Perception : appui sur les intuitions et les possibles."),
    "TF": ("Décision : priorité à la cohérence logique.",
           "Décision : priorité à l'humain et aux valeurs."),
    "JP": ("Organisation : besoin de cadre posé.",
           "Organisation : besoin de souplesse et d'ouverture."),
}


def render(mbti: str, quiz: Quiz) -> None:
    print("\n" + "─" * 60)
    print(f"  Résultat de cette session : {mbti}")
    print("─" * 60)

    for axis, a, b in Quiz.AXES:
        sa, sb = quiz.scores[a], quiz.scores[b]
        label = READING[axis][0] if sa > sb else READING[axis][1]
        print(f"  • {label}   ({a}:{sa}  {b}:{sb})")

    print("\n  Ceci n'est pas une étiquette — juste une photo du moment.")
    print("  Refais le test dans quelques mois, tu verras ce qui bouge.\n")


# ------------------------------------------------------------
# Historique local (optionnel)
# ------------------------------------------------------------

def save_session(mbti: str, quiz: Quiz) -> None:
    entry = {
        "date": datetime.now().isoformat(timespec="seconds"),
        "result": mbti,
        "scores": dict(quiz.scores),
    }
    history = []
    if HISTORY_FILE.exists():
        try:
            history = json.loads(HISTORY_FILE.read_text(encoding="utf-8"))
            if not isinstance(history, list):
                history = []
        except (json.JSONDecodeError, OSError):
            history = []
    history.append(entry)
    history = history[-MAX_HISTORY:]
    try:
        HISTORY_FILE.write_text(
            json.dumps(history, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        print(f"  Sauvegardé dans {HISTORY_FILE}")
    except OSError as e:
        print(f"  (sauvegarde impossible : {e})")


def show_history() -> None:
    if not HISTORY_FILE.exists():
        print("  Aucun historique.")
        return
    try:
        history = json.loads(HISTORY_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        print("  Historique illisible.")
        return
    print(f"\n  Historique ({len(history)} session(s)) :\n")
    for e in history:
        print(f"    {e.get('date', '?')}  →  {e.get('result', '?')}")
    print()


# ------------------------------------------------------------
# Point d'entrée
# ------------------------------------------------------------

def main() -> int:
    args = sys.argv[1:]

    if "--help" in args or "-h" in args:
        print(__doc__)
        return 0
    if "--history" in args:
        show_history()
        return 0

    print("\nDarkMBTI — auto-observation, pas diagnostic.")
    print("Réponds spontanément. Aucune donnée ne sort de ta machine.")
    input("\n[Entrée] pour commencer…")

    quiz = Quiz()
    mbti = quiz.run()
    render(mbti, quiz)

    if "--save" in args:
        save_session(mbti, quiz)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())