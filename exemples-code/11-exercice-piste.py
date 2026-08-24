"""Piste de l'exercice du chapitre 11 : lire les traces après coup.

Le script principal exécute la session instrumentée ; celui-ci lit le
fichier traces.jsonl produit et restitue la session — une première forme
de ce que fait un backend d'observabilité.
"""

import json
import sys


def restituer_sessions(chemin):
    """Lit traces.jsonl et regroupe les événements par ordre d'apparition."""
    evenements = []
    with open(chemin, encoding="utf-8") as fichier:
        for ligne in fichier:
            evenements.append(json.loads(ligne))
    return evenements


if len(sys.argv) < 2:
    print("Usage : uv run python exemples-code/11-exercice-piste.py chemin/des/traces.jsonl")
    sys.exit(1)

evenements = restituer_sessions(sys.argv[1])
print(f"{len(evenements)} événements dans {sys.argv[1]} :")
for evenement in evenements:
    attributs = evenement["attributes"]
    nom = attributs.get("gen_ai.tool.name") or attributs.get("gen_ai.request.model", evenement["name"])
    print(f"  {evenement['name']:14s} {nom:30s} "
          f"{evenement['duration_ms']:9.1f} ms")
