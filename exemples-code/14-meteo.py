"""L'agent du chapitre 3, avec un outil branché sur une vraie API externe :
la météo d'Open-Meteo (gratuite, sans clé). Les garde-fous du chapitre 6
sont réutilisés : timeout, erreurs transformées en messages."""

import json
import os

import requests
from dotenv import load_dotenv

load_dotenv()

TIMEOUT_METEO = 10
MAX_ITERATIONS = 5

GROUPES_METEO = [
    (0, "ciel dégagé"),
    (1, "plutôt dégagé"),
    (2, "partiellement nuageux"),
    (3, "couvert"),
    (45, "brouillard"),
    (48, "brouillard givrant"),
    (51, "bruine légère"),
    (53, "bruine"),
    (55, "bruine dense"),
    (56, "bruine verglaçante"),
    (57, "bruine verglaçante"),
    (61, "pluie légère"),
    (63, "pluie modérée"),
    (65, "pluie forte"),
    (66, "pluie verglaçante"),
    (67, "pluie verglaçante"),
    (71, "neige légère"),
    (73, "neige modérée"),
    (75, "neige forte"),
    (77, "grains de neige"),
    (80, "averses légères"),
    (81, "averses modérées"),
    (82, "averses fortes"),
    (85, "averses de neige"),
    (86, "averses de neige"),
    (95, "orage"),
    (96, "orage avec grêle"),
    (99, "orage avec grêle"),
]


def traduire_meteo(code):
    """Traduit un code météo WMO en texte français (table simplifiée)."""
    for borne, texte in GROUPES_METEO:
        if code <= borne:
            return texte
    return "temps inconnu"


def meteo(destination):
    """Météo actuelle d'une ville, via l'API Open-Meteo (gratuite, sans clé)."""
    try:
        reponse = requests.get(
            "https://geocoding-api.open-meteo.com/v1/search",
            params={"name": destination, "count": 1, "language": "fr"},
            timeout=TIMEOUT_METEO,
        )
        reponse.raise_for_status()
        resultats = reponse.json().get("results")
        if not resultats:
            return f"Ville inconnue : {destination}. Vérifiez l'orthographe."
        lieu = resultats[0]

        reponse = requests.get(
            "https://api.open-meteo.com/v1/forecast",
            params={
                "latitude": lieu["latitude"],
                "longitude": lieu["longitude"],
                "current": "temperature_2m,weather_code,wind_speed_10m",
                "timezone": "auto",
            },
            timeout=TIMEOUT_METEO,
        )
        reponse.raise_for_status()
        actuel = reponse.json()["current"]
        return (
            f"Météo à {lieu['name']} : {actuel['temperature_2m']} °C, "
            f"{traduire_meteo(actuel['weather_code'])}, vent à "
            f"{actuel['wind_speed_10m']} km/h."
        )
    except (requests.Timeout, requests.ConnectionError, requests.HTTPError) as e:
        return f"Erreur météo : {e}. Réessayez plus tard."


def rechercher_trajets(destination, date):
    """Horaires simulés des trajets vers une destination, à une date."""
    horaires = {
        "lyon": ["07:42", "09:15", "11:38"],
        "marseille": ["06:50", "08:22", "10:05"],
    }
    return horaires.get(destination.lower(), [])


OUTILS = {
    "rechercher_trajets": rechercher_trajets,
    "meteo": meteo,
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
            "name": "meteo",
            "description": "Météo actuelle d'une ville, via une API météo publique (Open-Meteo, gratuite et sans clé).",
            "parameters": {
                "type": "object",
                "properties": {
                    "destination": {
                        "type": "string",
                        "description": "Ville dont on veut la météo.",
                    },
                },
                "required": ["destination"],
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
        "content": "Je veux aller à Lyon le 25 août 2026. Quel temps fera-t-il là-bas, et quels trajets sont disponibles ?",
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
