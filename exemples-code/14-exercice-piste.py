"""Piste de l'exercice du chapitre 14 : une prévision à trois jours, en plus
de la météo actuelle — le même outil, un autre paramètre de l'API."""

import json
import os

import requests
from dotenv import load_dotenv

load_dotenv()

TIMEOUT_METEO = 10
MAX_ITERATIONS = 5


def meteo_prevision(destination):
    """Températures prévues (max/min) des trois prochains jours d'une ville."""
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
                "daily": "temperature_2m_max,temperature_2m_min",
                "forecast_days": 3,
                "timezone": "auto",
            },
            timeout=TIMEOUT_METEO,
        )
        reponse.raise_for_status()
        quotidien = reponse.json()["daily"]
        lignes = []
        for date, maxi, mini in zip(
            quotidien["time"], quotidien["temperature_2m_max"], quotidien["temperature_2m_min"]
        ):
            lignes.append(f"{date} : de {mini} à {maxi} °C")
        return f"Prévision à {lieu['name']} : " + ", ".join(lignes)
    except (requests.Timeout, requests.ConnectionError, requests.HTTPError) as e:
        return f"Erreur météo : {e}. Réessayez plus tard."


OUTILS = {
    "meteo_prevision": meteo_prevision,
}

DESCRIPTION_OUTILS = [
    {
        "type": "function",
        "function": {
            "name": "meteo_prevision",
            "description": "Prévision météo (températures min/max) des trois prochains jours d'une ville, via l'API Open-Meteo.",
            "parameters": {
                "type": "object",
                "properties": {
                    "destination": {
                        "type": "string",
                        "description": "Ville dont on veut la prévision.",
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
        "content": "Je pars à Marseille dans trois jours. Quel temps est-il prévu là-bas ?",
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
