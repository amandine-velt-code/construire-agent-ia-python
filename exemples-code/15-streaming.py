"""La boucle du chapitre 3 en streaming : la réponse du modèle est lue au
fil de l'eau (SSE), les premiers mots s'affichent avant la fin, et les
appels d'outils sont réassemblés depuis leurs fragments."""

import json
import os

import requests
from dotenv import load_dotenv

load_dotenv()

MAX_ITERATIONS = 5
POINT_TERMINAISON = "https://openrouter.ai/api/v1/chat/completions"


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


def accumuler_outils(fragments, appels):
    """Concatène les fragments d'appels d'outils, groupés par index.

    Le premier fragment d'un index porte l'identifiant et le nom ; les
    suivants ne portent que des morceaux des arguments, qu'il faut
    concaténer — jamais remplacer.
    """
    for fragment in fragments:
        index = fragment["index"]
        appel = appels.setdefault(
            index, {"id": None, "type": "function", "function": {"name": None, "arguments": ""}}
        )
        if fragment.get("id"):
            appel["id"] = fragment["id"]
        fonction = fragment.get("function", {})
        if fonction.get("name"):
            appel["function"]["name"] = fonction["name"]
        appel["function"]["arguments"] += fonction.get("arguments", "")
    return appels


def appeler_modele_stream(messages):
    """Appelle le modèle en streaming ; renvoie (texte, tool_calls, usage)."""
    reponse = requests.post(
        POINT_TERMINAISON,
        headers={
            "Authorization": f"Bearer {os.environ['OPENROUTER_API_KEY']}",
            "Content-Type": "application/json",
        },
        json={
            "model": "openrouter/free",
            "messages": messages,
            "tools": DESCRIPTION_OUTILS,
            "stream": True,
            "stream_options": {"include_usage": True},
        },
        timeout=120,
        stream=True,
    )
    reponse.raise_for_status()

    texte = ""
    appels = {}
    usage = None
    for ligne in reponse.iter_lines():
        if not ligne or not ligne.startswith(b"data: "):
            continue
        donnees = ligne[6:]
        if donnees == b"[DONE]":
            break
        chunk = json.loads(donnees)
        if chunk.get("usage"):
            usage = chunk["usage"]
        choix = chunk.get("choices", [{}])[0]
        delta = choix.get("delta", {})
        if delta.get("content"):
            texte += delta["content"]
            print(delta["content"], end="", flush=True)
        if delta.get("tool_calls"):
            accumuler_outils(delta["tool_calls"], appels)
        if choix.get("finish_reason"):
            print()
    return texte, list(appels.values()), usage


messages = [
    {
        "role": "user",
        "content": "Je veux aller à Lyon le 25 août 2026. Quels trajets sont disponibles ?",
    }
]

for iteration in range(MAX_ITERATIONS):
    texte, tool_calls, usage = appeler_modele_stream(messages)
    if usage:
        print(f"(tokens : {usage.get('prompt_tokens', 0)} entrée, {usage.get('completion_tokens', 0)} sortie)")

    if not tool_calls:
        print("Réponse finale :", texte.strip())
        break

    message = {"role": "assistant", "content": None, "tool_calls": tool_calls}
    messages.append(message)

    for appel in tool_calls:
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
