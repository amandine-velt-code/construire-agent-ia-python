"""Outils de recherche de trajets en train — module importable pour les tests."""

import re

DESTINATIONS_VALIDES = {"lyon", "marseille"}


def rechercher_trajets(destination, date):
    """Horaires simulés des trajets vers une destination, à une date."""
    if destination.lower() not in DESTINATIONS_VALIDES:
        return f"Destination inconnue : {destination}. Destinations disponibles : lyon, marseille."
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", date):
        return f"Date invalide : {date}. Format attendu : AAAA-MM-JJ."
    horaires = {
        "lyon": ["07:42", "09:15", "11:38"],
        "marseille": ["06:50", "08:22", "10:05"],
    }
    return horaires[destination.lower()]


def consulter_prix(destination, date):
    """Prix simulé d'un trajet vers une destination, à une date."""
    prix = {"lyon": 65.0, "marseille": 80.0}
    return prix.get(destination.lower(), None)
