"""Le chapitre 6 posait le principe sans l'implémenter : une action
irréversible doit s'arrêter avant d'agir. Ici, la réservation est
réellement précédée d'une confirmation humaine — l'agent propose,
l'utilisateur dispose."""

import json
import os

import requests
from dotenv import load_dotenv

load_dotenv()

MAX_ITERATIONS = 5


def rechercher_trajets(destination, date):
    """Horaires simulés des trajets vers une destination, à une date."""
    horaires = {
        "lyon": ["07:42", "09:15", "11:38"],
        "marseille": ["06:50", "08:22", "10:05"],
    }
    return horaires.get(destination.lower(), [])


def consulter_prix(destination, date):
    """Prix simulé d'un trajet vers une destination, à une date."""
    prix = {"lyon": 65.0, "marseille": 80.0}
    return prix.get(destination.lower(), None)


def reserver_trajet(destination, date):
    """La réservation elle-même — appelée seulement après confirmation."""
    return f"Réservation confirmée : {destination} le {date}, référence X7K2."


def demander_confirmation(arguments):
    """Affiche ce qui va être fait, et demande une confirmation explicite.

    Renvoie (decision, arguments_effectifs) — 'oui' exécute tel quel,
    'non' annule, 'modifier' remplace la date proposée.
    """
    print()
    print("Réservation à confirmer :")
    print(f"  destination : {arguments['destination']}")
    print(f"  date        : {arguments['date']}")
    decision = input("Confirmer la réservation ? (oui/non/modifier) ").strip().lower()
    if decision == "modifier":
        nouvelle_date = input("Nouvelle date (AAAA-MM-JJ) : ").strip()
        arguments = dict(arguments, date=nouvelle_date)
        print(f"Réservation modifiée : {arguments['date']} — confirmation requise à nouveau.")
        return demander_confirmation(arguments)
    return decision, arguments


OUTILS = {
    "rechercher_trajets": rechercher_trajets,
    "consulter_prix": consulter_prix,
    "reserver_trajet": reserver_trajet,
}

DESCRIPTION_OUTILS = [
    {
        "type": "function",
        "function": {
            "name": "rechercher_trajets",
            "description": "Recherche les trajets en train disponibles vers une destination, à une date donnée.",
            "parameters": {
                "type": "object",
                "properties": {
                    "destination": {
                        "type": "string",
                        "description": "Ville de destination.",
                    },
                    "date": {
                        "type": "string",
                        "description": "Date du voyage au format AAAA-MM-JJ.",
                    },
                },
                "required": ["destination", "date"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "consulter_prix",
            "description": "Consulte le prix d'un trajet vers une destination, à une date donnée.",
            "parameters": {
                "type": "object",
                "properties": {
                    "destination": {
                        "type": "string",
                        "description": "Ville de destination.",
                    },
                    "date": {
                        "type": "string",
                        "description": "Date du voyage au format AAAA-MM-JJ.",
                    },
                },
                "required": ["destination", "date"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "reserver_trajet",
            "description": "Réserve un trajet vers une destination, à une date donnée. L'utilisateur devra confirmer avant toute exécution.",
            "parameters": {
                "type": "object",
                "properties": {
                    "destination": {
                        "type": "string",
                        "description": "Ville de destination.",
                    },
                    "date": {
                        "type": "string",
                        "description": "Date du voyage au format AAAA-MM-JJ.",
                    },
                },
                "required": ["destination", "date"],
            },
        },
    },
]


def executer_outil(nom, arguments):
    """Exécute la fonction Python demandée par le modèle, après confirmation
    pour les actions irréversibles."""
    if nom not in OUTILS:
        return f"Outil inconnu : {nom}"
    if nom == "reserver_trajet":
        decision, arguments_effectifs = demander_confirmation(arguments)
        if decision != "oui":
            return "Réservation annulée : l'utilisateur a refusé. Informe-le de cette annulation."
        arguments = arguments_effectifs
    return OUTILS[nom](**arguments)


messages = [
    {
        "role": "user",
        "content": "Je veux aller à Lyon le 25 août 2026. Réserve-moi le premier trajet.",
    }
]

for iteration in range(MAX_ITERATIONS):
    reponse = requests.post(
        "https://openrouter.ai/api/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {os.environ['OPENROUTER_API_KEY']}",
            "Content-Type": "application/json",
        },
        json={
            "model": "openrouter/free",
            "messages": messages,
            "tools": DESCRIPTION_OUTILS,
        },
        timeout=120,
    )

    message = reponse.json()["choices"][0]["message"]
    messages.append(message)

    if not message.get("tool_calls"):
        break

    for appel in message["tool_calls"]:
        nom = appel["function"]["name"]
        arguments = json.loads(appel["function"]["arguments"])
        print("→ le modèle demande", nom, arguments)
        resultat = executer_outil(nom, arguments)
        print("← le harnais exécute :", resultat)
        messages.append(
            {
                "role": "tool",
                "tool_call_id": appel["id"],
                "content": json.dumps(resultat, ensure_ascii=False),
            }
        )
else:
    print("Limite d'itérations atteinte : arrêt de la boucle.")

print("Réponse finale :", message["content"].strip())
