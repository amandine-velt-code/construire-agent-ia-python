import json
import os
import sys

import requests
from dotenv import load_dotenv

load_dotenv()

MAX_ITERATIONS = int(sys.argv[1]) if len(sys.argv) > 1 else 5


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
    try:
        return OUTILS[nom](**arguments)
    except Exception as e:
        return f"Erreur d'exécution : {e}"


dernier_appel = None

messages = [
    {
        "role": "user",
        "content": "Je veux aller à Lyon le 25 août 2026. Quels trajets sont disponibles ?",
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
        print("Réponse finale :", message["content"].strip())
        break

    for appel in message["tool_calls"]:
        nom = appel["function"]["name"]
        try:
            arguments = json.loads(appel["function"]["arguments"])
        except json.JSONDecodeError as e:
            print("Arguments mal formés, renvoyés au modèle :", e)
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": appel["id"],
                    "content": f"Erreur : les arguments ne sont pas du JSON valide ({e}). Corrige.",
                }
            )
            continue
        if (nom, arguments) == dernier_appel:
            print("Appel répété détecté :", nom, arguments)
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": appel["id"],
                    "content": "Erreur : cet appel a déjà été exécuté à l'itération précédente, "
                    "avec les mêmes arguments. Utilise son résultat déjà obtenu, ou change d'approche.",
                }
            )
            continue
        dernier_appel = (nom, arguments)
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
    print(f"Limite d'itérations atteinte ({MAX_ITERATIONS}) : arrêt de la boucle.")
