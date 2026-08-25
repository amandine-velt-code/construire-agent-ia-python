"""L'agent produit un récapitulatif structuré et validé : le modèle est
invité à répondre en JSON conforme à un schéma (Pydantic), et le harnais
valide la réponse — en renvoyant l'erreur au modèle si elle ne passe pas."""

import json
import os

import requests
from dotenv import load_dotenv
from pydantic import BaseModel, ValidationError

load_dotenv()

MAX_ITERATIONS = 5
MAX_CORRECTIONS = 2


class Recapitulatif(BaseModel):
    """La forme exacte de la réponse finale de l'agent."""

    destination: str
    date: str
    prix: float | None = None
    statut: str


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


def appeler_modele(messages, schema):
    """Appelle le modèle ; si le modèle tiré refuse le mode structuré (400),
    retente une fois sans lui — le support n'est pas garanti sur tous les
    modèles gratuits."""
    corps = {
        "model": "openrouter/free",
        "messages": messages,
        "tools": DESCRIPTION_OUTILS,
    }
    if schema:
        corps["response_format"] = {
            "type": "json_schema",
            "json_schema": {"name": "recapitulatif", "strict": True, "schema": schema},
        }
    reponse = requests.post(
        "https://openrouter.ai/api/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {os.environ['OPENROUTER_API_KEY']}",
            "Content-Type": "application/json",
        },
        json=corps,
        timeout=120,
    )
    if reponse.status_code == 400 and schema:
        print("Mode structuré refusé par ce modèle : nouvel appel sans schéma.")
        return appeler_modele(messages, schema=None)
    reponse.raise_for_status()
    return reponse.json()


def valider_recapitulatif(texte):
    """Valide la réponse finale contre le schéma ; renvoie (objet, erreur)."""
    try:
        donnees = json.loads(texte)
        return Recapitulatif(**donnees), None
    except (json.JSONDecodeError, ValidationError) as e:
        return None, str(e)


messages = [
    {
        "role": "system",
        "content": (
            "Tu es un assistant de réservation de trains. Quand la demande est "
            "complète, réponds uniquement par un objet JSON conforme au schéma "
            "fourni : destination, date, prix (ou null si inconnu), statut "
            "(\"confirmé\" ou \"annulé\")."
        ),
    },
    {
        "role": "user",
        "content": "Je veux aller à Lyon le 25 août 2026. Réserve-moi le premier trajet et donne-moi le récapitulatif.",
    },
]

corrections = 0

for iteration in range(MAX_ITERATIONS):
    reponse = appeler_modele(messages, Recapitulatif.model_json_schema())
    message = reponse["choices"][0]["message"]
    messages.append(message)

    if not message.get("tool_calls"):
        recapitulatif, erreur = valider_recapitulatif(message["content"])
        if recapitulatif is not None:
            print("Récapitulatif validé :", recapitulatif.model_dump())
            break
        if corrections >= MAX_CORRECTIONS:
            print("Réponse finale invalide après", MAX_CORRECTIONS, "corrections :", erreur)
            break
        corrections += 1
        print("Réponse invalide, renvoyée au modèle :", erreur[:120])
        messages.append(
            {
                "role": "user",
                "content": f"Ta réponse finale était invalide : {erreur}. Réponds avec un JSON conforme au schéma.",
            }
        )
        continue

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
