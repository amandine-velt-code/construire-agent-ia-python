import os

import requests
from dotenv import load_dotenv

load_dotenv()


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


reponse = requests.post(
    "https://openrouter.ai/api/v1/chat/completions",
    headers={
        "Authorization": f"Bearer {os.environ['OPENROUTER_API_KEY']}",
        "Content-Type": "application/json",
    },
    json={
        "model": "openrouter/free",
        "messages": [
            {
                "role": "user",
                "content": "Je veux aller à Marseille le 26 août 2026. Quel est le prix du premier trajet du matin ?",
            }
        ],
        "tools": [
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
                    "description": "Consulte le prix d'un trajet donné.",
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
        ],
    },
    timeout=120,
)

message = reponse.json()["choices"][0]["message"]
for appel in message["tool_calls"]:
    print("  nom :", appel["function"]["name"])
    print("  arguments :", appel["function"]["arguments"])
