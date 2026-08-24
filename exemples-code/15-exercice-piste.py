"""Piste de l'exercice du chapitre 15 : valider la sortie d'un vrai outil.

L'outil météo du chapitre 14 renvoie du texte libre. Ici, il renvoie une
structure validée par Pydantic — la validation attrape les champs absents
d'une vraie API avant qu'ils ne polluent la conversation.
"""

import json
import os

import requests
from dotenv import load_dotenv
from pydantic import BaseModel, ValidationError

load_dotenv()

TIMEOUT_METEO = 10
MAX_ITERATIONS = 5


class Meteo(BaseModel):
    """La forme validée du retour de l'outil météo."""

    ville: str
    temperature: float
    description: str
    vent_kmh: float | None = None


def meteo_validee(destination):
    """Météo actuelle d'une ville, renvoyée sous forme validée par Pydantic."""
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
        donnees = {
            "ville": lieu["name"],
            "temperature": actuel["temperature_2m"],
            "description": traduire_meteo(actuel["weather_code"]),
            "vent_kmh": actuel["wind_speed_10m"],
        }
        valide = Meteo(**donnees)
        return json.dumps(valide.model_dump(), ensure_ascii=False)
    except (requests.Timeout, requests.ConnectionError, requests.HTTPError) as e:
        return f"Erreur météo : {e}. Réessayez plus tard."
    except ValidationError as e:
        return f"Réponse de l'API invalide : {e}"


def traduire_meteo(code):
    """Traduit un code météo WMO en texte français (table simplifiée)."""
    groupes = [
        (0, "ciel dégagé"),
        (1, "plutôt dégagé"),
        (2, "partiellement nuageux"),
        (3, "couvert"),
        (45, "brouillard"),
        (61, "pluie légère"),
        (63, "pluie modérée"),
        (65, "pluie forte"),
        (80, "averses"),
        (95, "orage"),
    ]
    for borne, texte in groupes:
        if code <= borne:
            return texte
    return "temps inconnu"


OUTILS = {
    "meteo": meteo_validee,
}

DESCRIPTION_OUTILS = [
    {
        "type": "function",
        "function": {
            "name": "meteo",
            "description": "Météo actuelle d'une ville, via l'API Open-Meteo (gratuite et sans clé).",
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
        "content": "Quel temps fait-il à Marseille en ce moment ?",
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
