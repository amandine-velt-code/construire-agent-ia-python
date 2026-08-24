"""Orchestrateur : l'agent principal délègue une partie de la tâche à un
agent spécialisé — l'agent agenda, appelé comme s'il était un outil."""

import json
import os

import requests
from dotenv import load_dotenv

load_dotenv()

MAX_ITERATIONS = 5


# --- L'agent spécialisé : l'agenda. Sa propre boucle, ses propres outils. ---

OUTILS_AGENDA = {
    "ajouter_evenement": lambda titre, date: f"Événement ajouté à l'agenda : {titre} le {date}.",
}

DESCRIPTION_AGENDA = [
    {
        "type": "function",
        "function": {
            "name": "ajouter_evenement",
            "description": "Ajoute un événement à l'agenda de l'utilisateur.",
            "parameters": {
                "type": "object",
                "properties": {
                    "titre": {
                        "type": "string",
                        "description": "Titre de l'événement.",
                    },
                    "date": {
                        "type": "string",
                        "description": "Date de l'événement au format AAAA-MM-JJ.",
                    },
                },
                "required": ["titre", "date"],
            },
        },
    }
]


def agent_agenda(question):
    """Mini-boucle : un agent qui ne sait que son agenda, et répond seul."""
    messages = [{"role": "user", "content": question}]
    for _ in range(3):
        reponse = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {os.environ['OPENROUTER_API_KEY']}",
                "Content-Type": "application/json",
            },
            json={
                "model": "openrouter/free",
                "messages": messages,
                "tools": DESCRIPTION_AGENDA,
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
            print(f"  [agenda] → {nom} {arguments}")
            resultat = OUTILS_AGENDA[nom](**arguments)
            print(f"  [agenda] ← {resultat}")
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": appel["id"],
                    "content": json.dumps(resultat, ensure_ascii=False),
                }
            )

    return "L'agent agenda n'a pas abouti dans la limite d'itérations."


# --- L'agent principal : la boucle du chapitre 3, l'agenda en outil. ---


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


OUTILS = {
    "rechercher_trajets": rechercher_trajets,
    "consulter_prix": consulter_prix,
    "deleguer_a_agenda": agent_agenda,
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
            "name": "deleguer_a_agenda",
            "description": "Délègue à l'agent agenda : lui demande d'ajouter ou de consulter des événements dans l'agenda de l'utilisateur. Passe-lui la demande complète, formulée en français.",
            "parameters": {
                "type": "object",
                "properties": {
                    "question": {
                        "type": "string",
                        "description": "La demande à confier à l'agent agenda.",
                    }
                },
                "required": ["question"],
            },
        },
    },
]


def executer_outil(nom, arguments):
    """Exécute la fonction Python demandée par le modèle."""
    if nom not in OUTILS:
        return f"Outil inconnu : {nom}"
    return OUTILS[nom](**arguments)


messages = [
    {
        "role": "user",
        "content": "Je veux aller à Lyon le 25 août 2026, réserve-moi un trajet et ajoute la réservation à mon agenda.",
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
