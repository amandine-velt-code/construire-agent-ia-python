"""La boucle de réflexion du chapitre 17, en module réutilisable : la boucle
du chapitre 3, la vérification par invariants (chapitre 7), la critique et
la correction."""

import json
import os

import requests
from dotenv import load_dotenv

load_dotenv()

MAX_ITERATIONS = 5

INVARIANTS = [
    ("la réponse mentionne la destination", lambda r: "Marseille" in r),
    (
        "la réponse mentionne l'heure du premier trajet",
        lambda r: "06:50" in r,
    ),
    (
        "la réponse mentionne le prix",
        lambda r: "80" in r,
    ),
]


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


def boucle_agent(question):
    """La boucle du chapitre 3 ; renvoie la réponse finale du modèle."""
    messages = [{"role": "user", "content": question}]
    for _ in range(MAX_ITERATIONS):
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
            return message["content"].strip(), messages

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

    return "Limite d'itérations atteinte : pas de réponse finale.", messages


def verifier_invariants(reponse):
    """Compte les invariants vérifiés par la réponse (mécanisme du chapitre 7)."""
    return sum(1 for _, verifie in INVARIANTS if verifie(reponse))


def critiquer(reponse, question):
    """Demande au modèle d'évaluer la réponse ; 'OK' ou une critique précise."""
    appel = requests.post(
        "https://openrouter.ai/api/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {os.environ['OPENROUTER_API_KEY']}",
            "Content-Type": "application/json",
        },
        json={
            "model": "openrouter/free",
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "Tu évalues une réponse d'assistant. Si elle répond complètement "
                        "à la question — destination, heure et prix cités — réponds "
                        "uniquement : OK. Sinon, critique ce qui manque ou ce qui est "
                        "faux, en une phrase."
                    ),
                },
                {"role": "user", "content": f"Question : {question}\nRéponse : {reponse}"},
            ],
        },
        timeout=120,
    )
    return appel.json()["choices"][0]["message"]["content"].strip()


def corriger(reponse, critique, question):
    """Demande au modèle une version corrigée de la réponse."""
    appel = requests.post(
        "https://openrouter.ai/api/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {os.environ['OPENROUTER_API_KEY']}",
            "Content-Type": "application/json",
        },
        json={
            "model": "openrouter/free",
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "Tu corriges ta réponse précédente en tenant compte de la "
                        "critique. Cite la destination, l'heure et le prix demandés."
                    ),
                },
                {
                    "role": "user",
                    "content": f"Question : {question}\nRéponse précédente : {reponse}\nCritique : {critique}",
                },
            ],
        },
        timeout=120,
    )
    return appel.json()["choices"][0]["message"]["content"].strip()
