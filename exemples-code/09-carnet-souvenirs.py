"""Amorce le carnet de souvenirs : texte + vecteur, et recherche par similarité."""

import json

import numpy as np
from fastembed import TextEmbedding

FICHIER_SOUVENIRS = "souvenirs.json"
MODELE_EMBEDDINGS = "BAAI/bge-small-en-v1.5"

SOUVENIRS_INITIAUX = [
    "L'utilisateur préfère les départs le matin avant 9 heures.",
    "La réservation X7K2 pour Marseille a été annulée le 20 août.",
    "L'utilisateur voyage souvent à Lyon pour le travail.",
]


def cosinus(a, b):
    """Similarité cosinus entre deux vecteurs, de -1 à 1."""
    a, b = np.asarray(a), np.asarray(b)
    return float(a @ b / (np.linalg.norm(a) * np.linalg.norm(b)))


def charger_souvenirs():
    """Charge le carnet de souvenirs, ou renvoie une liste vide."""
    try:
        with open(FICHIER_SOUVENIRS, encoding="utf-8") as fichier:
            return json.load(fichier)
    except FileNotFoundError:
        return []


def sauvegarder_souvenirs(souvenirs):
    """Écrit le carnet complet sur le disque."""
    with open(FICHIER_SOUVENIRS, "w", encoding="utf-8") as fichier:
        json.dump(souvenirs, fichier, ensure_ascii=False, indent=2)


def rechercher_souvenirs(question, souvenirs, embedding, k=3):
    """Renvoie les k souvenirs les plus proches de la question, triés par similarité."""
    v_question = list(embedding.embed([question]))[0]
    scores = [(cosinus(v_question, s["vecteur"]), s["texte"]) for s in souvenirs]
    scores.sort(key=lambda paire: paire[0], reverse=True)
    return scores[:k]


def main():
    embedding = TextEmbedding(model_name=MODELE_EMBEDDINGS)
    souvenirs = charger_souvenirs()

    if not souvenirs:
        print("Carnet vide : amorçage avec les souvenirs initiaux.")
        vecteurs = list(embedding.embed(SOUVENIRS_INITIAUX))
        souvenirs = [
            {"texte": texte, "vecteur": [float(v) for v in vecteur]}
            for texte, vecteur in zip(SOUVENIRS_INITIAUX, vecteurs)
        ]
        sauvegarder_souvenirs(souvenirs)

    question = "Quels trajets pour Lyon demain ?"
    print(f"Question : {question}")
    for score, texte in rechercher_souvenirs(question, souvenirs, embedding):
        print(f"  {score:.4f}  {texte}")


if __name__ == "__main__":
    main()
