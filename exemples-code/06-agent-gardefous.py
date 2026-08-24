import json
import os
import sys
import time

import requests
from dotenv import load_dotenv

load_dotenv()

MAX_ITERATIONS = int(sys.argv[1]) if len(sys.argv) > 1 else 5
BUDGET_TOKENS = 20_000
MAX_TENTATIVES_API = 3
ATTENTE_ENTRE_TENTATIVES = 2


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


def estimer_tokens(messages):
    """Estimation grossière du nombre de tokens d'un historique : 1 token ≈ 4 caractères."""
    caracteres = sum(len(m["content"]) for m in messages if isinstance(m["content"], str))
    return caracteres // 4


def appeler_modele(messages):
    """Appelle le modèle, avec reprise limitée sur les erreurs réseau."""
    for tentative in range(1, MAX_TENTATIVES_API + 1):
        try:
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
            reponse.raise_for_status()
            return reponse.json()
        except (requests.Timeout, requests.ConnectionError, requests.HTTPError) as e:
            print(f"Erreur réseau (tentative {tentative}/{MAX_TENTATIVES_API}) : {e}")
            if tentative < MAX_TENTATIVES_API:
                time.sleep(ATTENTE_ENTRE_TENTATIVES)
    raise RuntimeError(f"Le modèle n'a pas répondu après {MAX_TENTATIVES_API} tentatives.")


messages = [
    {
        "role": "user",
        "content": "Je veux aller à Lyon le 25 août 2026. Quels trajets sont disponibles ?",
    }
]

for iteration in range(MAX_ITERATIONS):
    if estimer_tokens(messages) > BUDGET_TOKENS:
        print("Budget de tokens dépassé : l'historique est trop grand, on s'arrête.")
        break

    reponse = appeler_modele(messages)
    message = reponse["choices"][0]["message"]
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
