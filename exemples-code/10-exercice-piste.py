"""Piste de l'exercice du chapitre 10 : un modèle différent par tâche.

Le résumé de conversation (tâche simple) passe par un modèle épinglé via
l'environnement — le lecteur choisit un modèle gratuit rapide dans
openrouter.ai/models ; la boucle principale reste sur le routeur. Les durées
s'affichent pour comparer.
"""

import json
import os
import sys
import time

import requests
from dotenv import load_dotenv

load_dotenv()

MODELE_SIMPLE = os.getenv("MODELE_SIMPLE", "openrouter/free")
MODELE_PRINCIPAL = os.getenv("MODELE_PRINCIPAL", "openrouter/free")


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


def resumer_conversation(messages):
    """Résume la conversation avec le modèle simple, et chronomètre."""
    texte = "\n".join(
        f"{m['role']} : {m['content']}" for m in messages if isinstance(m["content"], str)
    )
    debut = time.perf_counter()
    reponse = requests.post(
        "https://openrouter.ai/api/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {os.environ['OPENROUTER_API_KEY']}",
            "Content-Type": "application/json",
        },
        json={
            "model": MODELE_SIMPLE,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "Tu résumes une conversation entre un utilisateur et un assistant. "
                        "Conserve chaque fait important : demandes, dates, destinations, prix, décisions. "
                        "Rédige en français, sans répétition."
                    ),
                },
                {"role": "user", "content": f"Résume cette conversation :\n{texte}"},
            ],
        },
        timeout=120,
    )
    duree = time.perf_counter() - debut
    contenu = reponse.json()["choices"][0]["message"]["content"].strip()
    print(f"Résumé ({MODELE_SIMPLE}) en {duree:.2f} s : {contenu[:60]}…")
    return contenu


if len(sys.argv) < 2:
    print('Usage : uv run python exemples-code/10-exercice-piste.py "votre question"')
    sys.exit(1)

messages = [{"role": "user", "content": sys.argv[1]}]

for iteration in range(5):
    debut = time.perf_counter()
    reponse = requests.post(
        "https://openrouter.ai/api/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {os.environ['OPENROUTER_API_KEY']}",
            "Content-Type": "application/json",
        },
        json={
            "model": MODELE_PRINCIPAL,
            "messages": messages,
            "tools": DESCRIPTION_OUTILS,
        },
        timeout=120,
    )

    message = reponse.json()["choices"][0]["message"]
    messages.append(message)
    print(f"Appel au modèle terminé en {time.perf_counter() - debut:.2f} s")

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

# La tâche simple passe par le modèle simple.
resumer_conversation(messages)
