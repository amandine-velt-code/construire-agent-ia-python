"""Piste de l'exercice du chapitre 7.

1. Tests de normalisation (majuscules, espaces) : ils ne passent qu'après
   avoir adapté outils_trajets.py, par exemple avec
   `destination = destination.strip().lower()`.
2. Invariant d'évaluation à ajouter aux INVARIANTS de 07-evaluer.py.
"""

from outils_trajets import rechercher_trajets


def test_destination_en_majuscules():
    assert rechercher_trajets("LYON", "2026-08-25") == ["07:42", "09:15", "11:38"]


def test_destination_avec_espaces():
    assert rechercher_trajets(" Lyon ", "2026-08-25") == ["07:42", "09:15", "11:38"]


INVARIANT_AUCUN_TRAJET = (
    "la réponse n'affirme pas qu'aucun trajet n'est disponible",
    lambda r: "aucun" not in r,
)
