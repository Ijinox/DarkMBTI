# DarkMBTI

> Un petit outil d'auto-observation, sans prétention.

DarkMBTI est un questionnaire en ligne de commande qui t'aide à mettre des
mots sur ta manière de fonctionner. Il ne te dit pas qui tu es. Il te
renvoie, calmement, ce que tu viens de répondre — et pourquoi ça peut
t'être utile de le savoir.

## Ce que c'est

- Un quiz de 16 questions, 4 axes (E/I, S/N, T/F, J/P)
- Un retour humain, bienveillant, non-jugeant
- Un journal libre, que tu écris pour toi
- Un rapport `.txt` que tu peux garder, imprimer, relire dans six mois
- Tout est local. Rien ne quitte ta machine.

## Ce que ce n'est PAS

- Un diagnostic médical ou psychiatrique
- Un outil de profilage, de recrutement, de surveillance
- Un instrument pour évaluer la "dangerosité" de qui que ce soit
- Une étiquette définitive posée sur une personne

Le MBTI n'est pas un modèle validé scientifiquement pour prédire des
comportements. Il décrit des préférences, pas des risques. DarkMBTI assume
cette limite et ne prétend rien de plus.

## Installation

Aucune dépendance externe. Python 3.9 ou plus récent, c'est tout.

```bash
git clone https://github.com/<ton-compte>/darkmbti.git
cd darkmbti
python darkmbti.py
```

## Utilisation

```bash
python darkmbti.py                              # session simple
python darkmbti.py --journal                    # + saisie d'une note
python darkmbti.py --report                     # + rapport .txt
python darkmbti.py --save                       # + historique JSON
python darkmbti.py --journal --report --save    # tout activé
python darkmbti.py --history                    # relire sessions et notes
python darkmbti.py --help                       # aide
python darkmbti.py --version                    # version
```

### Options

| Option | Effet |
|---|---|
| `--journal` | Propose d'écrire une note libre après le quiz |
| `--report` | Génère un diagnostic `.txt` à côté du script |
| `--save` | Enregistre la session dans `~/.darkmbti_history.json` |
| `--history` | Affiche sessions passées + journal |
| `--no-pause` | Ne pas attendre à la fin (utile en script) |
| `--version` | Affiche la version |
| `--help` | Affiche l'aide |

## Où sont mes données ?

Trois emplacements, tous sur ta machine :

| Fichier | Contenu |
|---|---|
| `~/.darkmbti_history.json` | Tes sessions passées (résultats, scores) |
| `~/.darkmbti_journal.json` | Tes notes de journal |
| `darkmbti_<date>.txt` (dans le dossier du script) | Ton rapport imprimable |

Aucun envoi réseau. Aucun serveur. Aucun compte. Tu peux supprimer ces
fichiers d'un `rm` et tout disparaît.

## Structure du projet

```
darkmbti/
├── darkmbti.py          # script unique, autonome
├── README.md
├── LICENSE
├── CHANGELOG.md
├── CONTRIBUTING.md
└── examples/
    └── rapport_exemple.txt
```

## Licence

MIT — voir [LICENSE](LICENSE).

## Avertissement

Ce logiciel est un outil de développement personnel. Il ne doit **pas**
être utilisé pour du profilage, du recrutement discriminatoire, de la
surveillance, ou toute forme d'évaluation d'autrui sans consentement
éclairé. De tels usages seraient contraires à son intention, à la loi
française (articles 225-1 et 226-1 du Code pénal), et à l'éthique la
plus élémentaire.

Si tu vas mal, parle à quelqu'un. En France :

- **3114** — prévention du suicide
- **15** ou **112** — urgences
- **3919** — violences faites aux femmes
- **[internet-signalement.gouv.fr](https://www.internet-signalement.gouv.fr)** — signalements en ligne