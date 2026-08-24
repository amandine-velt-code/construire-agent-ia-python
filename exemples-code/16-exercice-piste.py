"""Piste de l'exercice du chapitre 16 : mesurer la latence perçue.

Le script du chapitre affiche les mots au fil de l'eau ; celui-ci
chronomètre le premier token (TTFT) et le temps total sur une question
textuelle simple — la latence perçue, comparée à la latence réelle du
chapitre 10."""

import json
import os
import time

import requests
from dotenv import load_dotenv

load_dotenv()

POINT_TERMINAISON = "https://openrouter.ai/api/v1/chat/completions"


def appeler_modele_stream_chrono(messages):
    """Comme le chapitre 16, avec chronométrage du premier token."""
    debut = time.perf_counter()
    premier_token = None
    reponse = requests.post(
        POINT_TERMINAISON,
        headers={
            "Authorization": f"Bearer {os.environ['OPENROUTER_API_KEY']}",
            "Content-Type": "application/json",
        },
        json={
            "model": "openrouter/free",
            "messages": messages,
            "stream": True,
        },
        timeout=120,
        stream=True,
    )
    reponse.raise_for_status()

    texte = ""
    for ligne in reponse.iter_lines():
        if not ligne or not ligne.startswith(b"data: "):
            continue
        donnees = ligne[6:]
        if donnees == b"[DONE]":
            break
        chunk = json.loads(donnees)
        delta = chunk.get("choices", [{}])[0].get("delta", {})
        if delta.get("content"):
            if premier_token is None:
                premier_token = time.perf_counter() - debut
            texte += delta["content"]
            print(delta["content"], end="", flush=True)
    total = time.perf_counter() - debut
    print()
    print(f"Premier token : {premier_token:.2f} s — réponse complète : {total:.2f} s")
    return texte


messages = [
    {
        "role": "user",
        "content": "Quelle est la capitale du Japon ? Réponds en une phrase.",
    }
]

texte = appeler_modele_stream_chrono(messages)
print("Réponse finale :", texte.strip())
