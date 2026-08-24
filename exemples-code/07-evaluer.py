"""Évaluation légère de l'agent : vérifie des invariants sur plusieurs runs."""

import sys

from agent_trajets import repondre

NOMBRE_RUNS = int(sys.argv[1]) if len(sys.argv) > 1 else 3

QUESTION = "Je veux aller à Lyon le 25 août 2026. Quels trajets sont disponibles ?"

INVARIANTS = [
    ("la réponse mentionne la destination", lambda r: "Lyon" in r),
    (
        "la réponse mentionne au moins un horaire",
        lambda r: any(horaire in r for horaire in ["07:42", "09:15", "11:38"]),
    ),
]

succes = 0
total = NOMBRE_RUNS * len(INVARIANTS)

for run in range(1, NOMBRE_RUNS + 1):
    print(f"Run {run}/{NOMBRE_RUNS} :")
    reponse = repondre(QUESTION)
    print("  réponse :", reponse)
    for nom, verifie in INVARIANTS:
        ok = verifie(reponse)
        print(f"  invariant « {nom} » : {'OK' if ok else 'ÉCHEC'}")
        succes += ok

print(f"Résultat : {succes}/{total} invariants vérifiés")
