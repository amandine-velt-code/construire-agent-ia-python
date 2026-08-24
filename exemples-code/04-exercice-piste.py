import json
import os
import sys

import requests
from dotenv import load_dotenv

load_dotenv()

FICHIER_HISTORIQUE = "historique.json"
BUDGET_TOKENS = int(sys.argv[2]) if len(sys.argv) > 2 else 50


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


def charger_historique():
    """Charge l'historique sauvegardé, ou renvoie une liste vide."""
    try:
        with open(FICHIER_HISTORIQUE, encoding="utf-8") as fichier:
            return json.load(fichier)
    except FileNotFoundError:
        return []


def sauvegarder_historique(messages):
    """Écrit l'historique complet sur le disque."""
    with open(FICHIER_HISTORIQUE, "w", encoding="utf-8") as fichier:
        json.dump(messages, fichier, ensure_ascii=False, indent=2)


def estimer_tokens(messages):
    """Estimation grossière du nombre de tokens d'un historique : 1 token ≈ 4 caractères."""
    caracteres = sum(len(m["content"]) for m in messages if isinstance(m["content"], str))
    return caracteres // 4


def resumer(messages_a_resumer):
    """Demande au modèle un résumé de l'historique, en conservant les faits mot pour mot."""
    texte = "\n".join(
        f"{m['role']} : {m['content']}" for m in messages_a_resumer if isinstance(m["content"], str)
    )
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
                    "role": "system",
                    "content": (
                        "Tu résumes une conversation entre un utilisateur et un assistant. "
                        "Conserve mot pour mot chaque date, destination, horaire et prix cités. "
                        "Rédige en français, sans répétition."
                    ),
                },
                {"role": "user", "content": f"Résume cette conversation :\n{texte}"},
            ],
        },
        timeout=120,
    )
    return reponse.json()["choices"][0]["message"]["content"].strip()


def reduire_si_necessaire(messages):
    """Remplace les messages anciens par un résumé si le budget est dépassé."""
    if estimer_tokens(messages) <= BUDGET_TOKENS:
        return messages
    dernier_tour = 0
    for i, message in enumerate(messages):
        if message["role"] == "user":
            dernier_tour = i
    if dernier_tour == 0:
        return messages
    vieux = messages[:dernier_tour]
    recents = messages[dernier_tour:]
    resume = resumer(vieux)
    print(f"Contexte trop grand : {len(vieux)} messages remplacés par un résumé.")
    print("Résumé :", resume)
    return [{"role": "system", "content": f"Résumé de la conversation précédente : {resume}"}] + recents


if len(sys.argv) < 2:
    print('Usage : uv run python exemples-code/04-exercice-piste.py "votre question" [budget_tokens]')
    sys.exit(1)

messages = charger_historique()
messages.append({"role": "user", "content": sys.argv[1]})
messages = reduire_si_necessaire(messages)

while True:
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

sauvegarder_historique(messages)
print("Réponse finale :", message["content"].strip())
