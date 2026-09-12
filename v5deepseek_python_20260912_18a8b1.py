#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DarkMBTI v5 — Comprendre comment tu fonctionnes (+ rapport .txt)
=================================================================

Un petit outil d'auto-observation, sans prétention.

- 16 questions, 4 axes (E/I, S/N, T/F, J/P)
- Un retour humain, bienveillant, non-jugeant
- Un diagnostic exportable en .txt (lisible, imprimable, gardable)
- Aucune donnée ne quitte ta machine

Usage :
    python darkmbti.py                 # session normale
    python darkmbti.py --save          # + historique JSON local
    python darkmbti.py --report        # + diagnostic .txt
    python darkmbti.py --report --save # les deux
    python darkmbti.py --history       # relire l'historique

Python 3.9+ · Licence MIT · Aucune dépendance.
"""

from __future__ import annotations

import json
import sys
import textwrap
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List

HISTORY_FILE = Path.home() / ".darkmbti_history.json"
MAX_HISTORY = 50
REPORT_DIR = Path.cwd()


# ════════════════════════════════════════════════════════════
# 1. QUESTIONS
# ════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class Q:
    axis: str
    text: str
    a: str
    b: str
    pa: str
    pb: str


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


# ════════════════════════════════════════════════════════════
# 2. RETOUR HUMAIN PAR PÔLE
# ════════════════════════════════════════════════════════════

POLE_FEEDBACK: Dict[str, dict] = {

    "E": {
        "titre": "Tu avances au contact des autres",
        "comment": (
            "Ton énergie monte quand il y a du mouvement, des échanges, "
            "des visages. Tu penses souvent à voix haute — c'est en parlant "
            "que les idées se clarifient pour toi. Le silence prolongé "
            "t'éteint plus qu'il ne te repose."
        ),
        "aide": [
            "Des journées avec des interactions variées",
            "Un entourage vivant, même informel",
            "Pouvoir dire ce que tu penses pour y voir clair",
        ],
        "pesant": [
            "Les longues périodes isolées",
            "Devoir tout garder pour toi",
            "Les environnements trop silencieux ou figés",
        ],
        "conseil": (
            "Apprends à distinguer le bruit dont tu as besoin et le calme "
            "dont tu as vraiment besoin : ce n'est pas la même chose. Et "
            "offre-toi des moments seul, sans culpabilité — ce n'est pas "
            "une trahison de ta nature, c'est du soin."
        ),
    },
    "I": {
        "titre": "Tu avances dans ton monde intérieur",
        "comment": (
            "Tu te recharges dans le calme, la solitude, les moments sans "
            "sollicitation. Ta vie intérieure est riche, tu prends le temps "
            "de digérer avant de répondre. Le contact prolongé te vide, "
            "même quand tu aimes sincèrement les gens."
        ),
        "aide": [
            "Des plages de solitude réelle, sans écran ni obligation",
            "Des relations profondes plutôt que nombreuses",
            "Le droit de ne pas répondre tout de suite",
        ],
        "pesant": [
            "Les sollicitations constantes",
            "Les environnements bruyants ou superficiels",
            "Devoir te justifier d'avoir besoin de silence",
        ],
        "conseil": (
            "Ton besoin de retrait n'est pas une fuite. Mais veille à ne pas "
            "t'y perdre : le monde a besoin de ce que tu vois quand tu es "
            "seul. Choisis bien tes quelques personnes — elles valent plus "
            "que mille contacts."
        ),
    },

    "S": {
        "titre": "Tu t'appuies sur le concret",
        "comment": (
            "Tu fais confiance à ce que tu vois, touches, vérifies. Le réel "
            "te donne des repères solides. Tu avances pas à pas, en "
            "t'appuyant sur l'expérience, et tu repères les détails que "
            "d'autres laissent filer."
        ),
        "aide": [
            "Des projets tangibles, avec des étapes claires",
            "Des exemples concrets plutôt que des théories",
            "Pouvoir vérifier par toi-même",
        ],
        "pesant": [
            "Les discours trop abstraits ou flous",
            "Devoir décider sans informations",
            "Le changement brutal non expliqué",
        ],
        "conseil": (
            "Ta solidité est précieuse. De temps en temps, laisse une petite "
            "place à ce que tu ne peux pas encore prouver — non pour renier "
            "ton ancrage, mais pour laisser entrer un possible que tu "
            "n'avais pas envisagé."
        ),
    },
    "N": {
        "titre": "Tu captes ce qui n'est pas encore dit",
        "comment": (
            "Tu perçois les liens, les ambiances, les directions possibles. "
            "Tu fonctionnes par intuition, par associations, par vision "
            "d'ensemble. Le détail t'intéresse moins que ce qu'il raconte."
        ),
        "aide": [
            "Du temps pour laisser mûrir une idée",
            "Des espaces où l'on peut penser tout haut",
            "Des gens qui supportent l'ambiguïté",
        ],
        "pesant": [
            "Devoir tout justifier par des chiffres",
            "Les tâches purement répétitives",
            "L'impression d'être « dans la lune »",
        ],
        "conseil": (
            "Ton intuition est un vrai guide, mais elle a besoin d'être "
            "incarnée. Note tes idées, reviens-y, confronte-les au réel : "
            "c'est ainsi qu'elles deviennent utiles aux autres, pas "
            "seulement belles pour toi."
        ),
    },

    "T": {
        "titre": "Tu tranches d'abord par la logique",
        "comment": (
            "Ce qui tient, ce qui est cohérent, ce qui est juste au sens "
            "rationnel. Tu ne confonds pas la fermeté avec la dureté : tu "
            "veux simplement que les choses soient vraies."
        ),
        "aide": [
            "Des échanges francs, sans détour",
            "Des critères clairs, posés à l'avance",
            "Des gens qui ne prennent pas la critique pour une attaque",
        ],
        "pesant": [
            "Les décisions prises par affect",
            "Devoir cacher ton avis pour préserver l'ambiance",
            "L'incohérence répétée",
        ],
        "conseil": (
            "Ta clarté est un cadeau, mais elle passe mieux quand elle est "
            "adoucie. Avant de dire une vérité utile, demande-toi : est-ce "
            "le bon moment, la bonne personne, la bonne formulation ? Ce "
            "n'est pas de la compromission, c'est de la précision — dans "
            "le soin de l'autre."
        ),
    },
    "F": {
        "titre": "Tu décides en tenant compte des personnes",
        "comment": (
            "Ce qui compte, c'est l'impact sur les autres, la justesse du "
            "lien, l'humanité de la situation. Tu sens vite ce qui blesse. "
            "Tu ne confonds pas la douceur avec la faiblesse."
        ),
        "aide": [
            "Des environnements où les gens comptent vraiment",
            "Pouvoir dire ce que tu ressens sans te justifier",
            "Du temps pour digérer les tensions",
        ],
        "pesant": [
            "Les milieux cyniques ou brutaux",
            "Devoir trancher sans considération humaine",
            "Les conflits non résolus qui traînent",
        ],
        "conseil": (
            "Ta sensibilité est une force, pas un défaut. Mais apprends à "
            "poser des limites sans culpabilité : prendre soin de toi "
            "n'est pas de l'égoïsme, c'est la condition pour pouvoir "
            "prendre soin des autres longtemps. Dire non, c'est parfois "
            "la forme la plus honnête du oui."
        ),
    },

    "J": {
        "titre": "Tu te sens mieux quand c'est posé",
        "comment": (
            "Tu aimes savoir où tu vas. Tu fermes des portes plutôt que "
            "d'en laisser trop ouvertes, parce que le cadre te libère au "
            "lieu de t'enfermer. Tu tiens tes engagements."
        ),
        "aide": [
            "Des plans clairs et réalistes",
            "Des transitions annoncées",
            "Des gens qui font ce qu'ils disent",
        ],
        "pesant": [
            "L'improvisation permanente",
            "Les changements non expliqués",
            "L'impression de ne jamais boucler",
        ],
        "conseil": (
            "Ton besoin de cadre te sert, mais la vie ne se plie pas "
            "toujours au plan. Garde une petite marge — non pour tout "
            "lâcher, mais pour ne pas souffrir quand le réel fait "
            "autrement. La souplesse n'est pas un abandon, c'est une "
            "manière de durer."
        ),
    },
    "P": {
        "titre": "Tu te sens mieux quand il y a de l'air",
        "comment": (
            "Tu aimes les options, la place pour ajuster, la possibilité "
            "de changer d'avis sans drame. C'est souvent comme ça que tu "
            "fais les meilleurs choix : en voyant venir."
        ),
        "aide": [
            "De la liberté dans l'organisation",
            "Des projets évolutifs",
            "Pouvoir changer d'avis sans que ce soit un échec",
        ],
        "pesant": [
            "Les cadres trop rigides",
            "Les engagements pris trop vite",
            "L'impression d'être coincé",
        ],
        "conseil": (
            "Ton ouverture est une vraie ressource, mais elle peut devenir "
            "une fuite si tu ne refermes jamais rien. Parfois, choisir — "
            "vraiment choisir — t'apporte plus de paix que garder toutes "
            "les portes ouvertes. Une décision tenue vaut mieux que dix "
            "possibilités rêvées."
        ),
    },
}


# ════════════════════════════════════════════════════════════
# 3. MOTEUR
# ════════════════════════════════════════════════════════════

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
            print("        (tape 1 ou 2)")

    def dominant(self, axis: str) -> tuple[str, int, int]:
        _, a, b = next(x for x in self.AXES if x[0] == axis)
        sa, sb = self.scores[a], self.scores[b]
        return (a if sa > sb else b), sa, sb


# ════════════════════════════════════════════════════════════
# 4. RESTITUTION TERMINAL
# ════════════════════════════════════════════════════════════

def _hr(char: str = "─", n: int = 60) -> str:
    return char * n


def _wrap(text: str, indent: str = "  ", width: int = 68) -> str:
    return textwrap.fill(text, width=width,
                         initial_indent=indent,
                         subsequent_indent=indent)


def render_feedback(mbti: str, quiz: Quiz,
                    name: str = "", note: str = "") -> None:
    print("\n" + _hr("═"))
    print("  Ce que tes réponses racontent")
    print(_hr("═"))

    if name:
        print(f"\n  {name}, voici ce qui ressort — sans jugement, sans étiquette.")
    if note:
        print(f"\n  Tu m'as confié : « {note} »")
        print("  Garde ça en tête en lisant la suite.")

    for axis, a, b in Quiz.AXES:
        pole, sa, sb = quiz.dominant(axis)
        fb = POLE_FEEDBACK[pole]

        print("\n" + _hr())
        print(f"  {fb['titre']}   ({a} : {sa}  ·  {b} : {sb})")
        print(_hr())
        print(_wrap(fb["comment"]))

        print("\n  Ce qui t'aide :")
        for item in fb["aide"]:
            print(f"    · {item}")
        print("\n  Ce qui peut te peser :")
        for item in fb["pesant"]:
            print(f"    · {item}")
        print("\n  Un mot pour toi :")
        print(_wrap(fb["conseil"]))

        if sa == sb:
            print(_wrap("\n  (Ici, tes deux côtés se tiennent à égalité — "
                        "c'est une richesse : tu as accès aux deux registres.)"))

    print("\n" + _hr("═"))
    print("  En un mot")
    print(_hr("═"))
    for p in mbti:
        print(f"  · {POLE_FEEDBACK[p]['titre']}")

    print(_wrap(
        "\n  Ces quatre tendances forment ta manière d'avancer. "
        "Elles ne te définissent pas — elles te décrivent dans ce que "
        "tu montres le plus souvent. Rien n'est figé."
    ))
    print(_wrap(
        "\n  Garde ce qui te parle. Laisse le reste. Tu n'as pas à "
        "devenir quelqu'un d'autre — juste à te comprendre un peu "
        "mieux, un pas à la fois."
    ))
    print()


# ════════════════════════════════════════════════════════════
# 5. GÉNÉRATION DU RAPPORT .TXT
# ════════════════════════════════════════════════════════════

REPORT_WIDTH = 74


def _txt_line(char: str = "-", n: int = REPORT_WIDTH) -> str:
    return char * n


def _txt_wrap(text: str, indent: str = "  ") -> str:
    return textwrap.fill(
        text,
        width=REPORT_WIDTH,
        initial_indent=indent,
        subsequent_indent=indent,
    )


def build_report_txt(mbti: str, quiz: Quiz,
                     name: str = "", note: str = "") -> str:
    """Construit le contenu du diagnostic en texte clair."""
    now = datetime.now()
    lines: List[str] = []

    # ─── En-tête ───
    lines.append(_txt_line("="))
    lines.append("  DarkMBTI — Diagnostic d'auto-observation")
    lines.append(_txt_line("="))
    lines.append("")
    if name:
        lines.append(f"  Pour      : {name}")
    lines.append(f"  Date      : {now.strftime('%d/%m/%Y à %H:%M')}")
    lines.append(f"  Résultat  : {mbti}")
    lines.append("")
    lines.append(_txt_wrap(
        "Ce document n'est pas un diagnostic médical ni une étiquette. "
        "C'est une lecture calme de tes réponses, à garder ou à relire "
        "quand tu veux."
    ))
    lines.append("")

    if note:
        lines.append(_txt_line("-"))
        lines.append("  Ce que tu as confié")
        lines.append(_txt_line("-"))
        lines.append(_txt_wrap(f"« {note} »"))
        lines.append("")

    # ─── Les 4 axes ───
    for axis, a, b in Quiz.AXES:
        pole, sa, sb = quiz.dominant(axis)
        fb = POLE_FEEDBACK[pole]

        lines.append(_txt_line("="))
        lines.append(f"  {fb['titre']}")
        lines.append(f"  (score : {a} {sa}  /  {b} {sb})")
        lines.append(_txt_line("="))
        lines.append("")
        lines.append(_txt_wrap(fb["comment"]))
        lines.append("")

        lines.append("  Ce qui t'aide")
        for item in fb["aide"]:
            lines.append(_txt_wrap(f"  - {item}"))
        lines.append("")

        lines.append("  Ce qui peut te peser")
        for item in fb["pesant"]:
            lines.append(_txt_wrap(f"  - {item}"))
        lines.append("")

        lines.append("  Un mot pour toi")
        lines.append(_txt_wrap(fb["conseil"]))
        lines.append("")

        if sa == sb:
            lines.append(_txt_wrap(
                "Note : sur cet axe, tes deux côtés sont à égalité. "
                "C'est une richesse — tu peux jouer des deux registres "
                "selon les situations."
            ))
            lines.append("")

    # ─── Synthèse ───
    lines.append(_txt_line("="))
    lines.append("  En un mot")
    lines.append(_txt_line("="))
    lines.append("")
    for p in mbti:
        lines.append(f"  - {POLE_FEEDBACK[p]['titre']}")
    lines.append("")
    lines.append(_txt_wrap(
        "Ces quatre tendances décrivent ta manière d'avancer, pas ton "
        "identité. Elles peuvent évoluer. Refais ce test dans quelques "
        "mois pour voir ce qui bouge."
    ))
    lines.append("")
    lines.append(_txt_wrap(
        "Garde ce document pour toi. Ce que tu viens de lire est une "
        "carte, pas un destin. Prends soin de toi."
    ))
    lines.append("")

    # ─── Pied de page ───
    lines.append(_txt_line("="))
    lines.append(f"  Généré localement par DarkMBTI v5 — le "
                 f"{now.strftime('%d/%m/%Y à %H:%M')}")
    lines.append("  Aucune donnée n'a quitté ta machine.")
    lines.append(_txt_line("="))
    lines.append("")

    return "\n".join(lines)


def write_report(mbti: str, quiz: Quiz,
                 name: str = "", note: str = "") -> Path | None:
    """Écrit le diagnostic dans un .txt. Retourne le chemin ou None."""
    content = build_report_txt(mbti, quiz, name=name, note=note)

    # Nom de fichier : date + type
    stamp = datetime.now().strftime("%Y-%m-%d_%Hh%M")
    safe_name = ""
    if name:
        # On ne garde que les caractères sûrs pour un nom de fichier
        safe_name = "".join(c for c in name if c.isalnum() or c in "-_")[:20]
        safe_name = f"_{safe_name}" if safe_name else ""

    path = REPORT_DIR / f"darkmbti_{stamp}{safe_name}.txt"

    try:
        path.write_text(content, encoding="utf-8")
        return path
    except OSError as e:
        print(f"  (écriture du rapport impossible : {e})")
        return None


# ════════════════════════════════════════════════════════════
# 6. HISTORIQUE LOCAL (optionnel)
# ════════════════════════════════════════════════════════════

def save_session(mbti: str, quiz: Quiz,
                 name: str = "", note: str = "") -> None:
    entry = {
        "date": datetime.now().isoformat(timespec="seconds"),
        "name": name,
        "note": note,
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
        print(f"  Historique : {HISTORY_FILE}")
    except OSError as e:
        print(f"  (historique impossible : {e})")


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
        date = e.get("date", "?")
        res = e.get("result", "?")
        nm = e.get("name", "")
        suffix = f"  - {nm}" if nm else ""
        print(f"    {date}  ->  {res}{suffix}")
    print()


# ════════════════════════════════════════════════════════════
# 7. POINT D'ENTRÉE
# ════════════════════════════════════════════════════════════

def ask_context() -> tuple[str, str]:
    try:
        name = input("\n  Ton prénom (optionnel, [Entrée] pour passer) : ").strip()
        name = name[:40]
    except (EOFError, KeyboardInterrupt):
        print()
        sys.exit(0)

    note = ""
    if name:
        try:
            note = input(
                "  En une phrase, qu'est-ce qui t'amène ? "
                "(optionnel, [Entrée] pour passer)\n  > "
            ).strip()
            note = note[:200]
        except (EOFError, KeyboardInterrupt):
            print()
            sys.exit(0)
    return name, note


def main() -> int:
    args = sys.argv[1:]

    if "--help" in args or "-h" in args:
        print(__doc__)
        return 0
    if "--history" in args:
        show_history()
        return 0

    print("\n" + _hr("═"))
    print("  DarkMBTI v5 — comprendre comment tu fonctionnes")
    print(_hr("═"))
    print("  Outil d'auto-observation, pas de diagnostic médical.")
    print("  Réponds spontanément : la première réponse est souvent la bonne.")
    print("  Rien ne quitte ta machine.")

    name, note = ask_context()

    try:
        input("\n  [Entrée] pour commencer…")
    except (EOFError, KeyboardInterrupt):
        print()
        return 0

    quiz = Quiz()
    mbti = quiz.run()

    render_feedback(mbti, quiz, name=name, note=note)

    if "--report" in args:
        path = write_report(mbti, quiz, name=name, note=note)
        if path:
            print(f"  Rapport .txt : {path}")
            print("  (ouvre-le avec un éditeur de texte ou imprime-le)\n")

    if "--save" in args:
        save_session(mbti, quiz, name=name, note=note)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())