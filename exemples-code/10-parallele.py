"""Boucle du chapitre 3 : les appels d'outils indépendants s'exécutent en parallèle."""

import json
import os
import time
from concurrent.futures import ThreadPoolExecutor

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


def executer_appel(appel):
    """Exécute un appel d'outil et renvoie (appel, résultat, durée)."""
    nom = appel["function"]["name"]
    arguments = json.loads(appel["function"]["arguments"])
    debut = time.perf_counter()
    resultat = executer_outil(nom, arguments)
    duree = time.perf_counter() - debut
    return appel, resultat, duree


messages = [
    {
        "role": "user",
        "content": "Je veux aller à Marseille le 26 août 2026. Quel est le prix du premier trajet du matin ?",
    }
]

for iteration in range(MAX_ITERATIONS):
    debut_tour = time.perf_counter()
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
        print("Réponse finale :", message["content"].strip())
        break

    with ThreadPoolExecutor() as pool:
        paires = list(pool.map(executer_appel, message["tool_calls"]))

    for appel, resultat, duree in paires:
        nom = appel["function"]["name"]
        print(f"→ le modèle demande {nom} ({duree:.3f} s)")
        messages.append(
            {
                "role": "tool",
                "tool_call_id": appel["id"],
                "content": json.dumps(resultat, ensure_ascii=False),
            }
        )

    print(f"← tour terminé en {time.perf_counter() - debut_tour:.3f} s")
else:
    print(f"Limite d'itérations atteinte ({MAX_ITERATIONS}) : arrêt de la boucle.")
