"""L'agent de recherche de trajets : la boucle du chapitre 3, en module réutilisable."""

import json
import os

import requests
from dotenv import load_dotenv

from outils_trajets import consulter_prix, rechercher_trajets

load_dotenv()

OUTILS = {
    "rechercher_trajets": rechercher_trajets,
    "consulter_prix": consulter_prix,
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
]


def executer_outil(nom, arguments):
    """Exécute la fonction Python demandée par le modèle."""
    if nom not in OUTILS:
        return f"Outil inconnu : {nom}"
    return OUTILS[nom](**arguments)


def repondre(question, max_iterations=5):
    """Exécute la boucle d'agent et renvoie la réponse finale du modèle."""
    messages = [{"role": "user", "content": question}]
    for _ in range(max_iterations):
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
            return message["content"].strip()

        for appel in message["tool_calls"]:
            nom = appel["function"]["name"]
            arguments = json.loads(appel["function"]["arguments"])
            resultat = executer_outil(nom, arguments)
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": appel["id"],
                    "content": json.dumps(resultat, ensure_ascii=False),
                }
            )

    return "Limite d'itérations atteinte : pas de réponse finale."
