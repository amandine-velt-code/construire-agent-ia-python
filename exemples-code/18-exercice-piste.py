"""Piste de l'exercice du chapitre 18 : mesurer l'effet de la réflexion.

Le chapitre 7 a construit un harnais d'évaluation par invariants ; celui-ci
l'applique à la réflexion : plusieurs questions, et le bilan avant/après —
la réflexion n'est pas présentée comme automatiquement meilleure, elle est
mesurée."""

from reflexion_agent import (
    INVARIANTS,
    boucle_agent,
    corriger,
    critiquer,
    verifier_invariants,
)

QUESTIONS = [
    "Je veux aller à Lyon le 25 août 2026. Donne-moi le prix du premier trajet du matin ET l'heure de ce trajet.",
    "Je veux aller à Marseille le 26 août 2026. Donne-moi l'heure du dernier trajet et son prix.",
]

total_avant = 0
total_apres = 0

for question in QUESTIONS:
    reponse, _ = boucle_agent(question)
    score_initial = verifier_invariants(reponse)
    total_avant += score_initial
    if score_initial >= len(INVARIANTS):
        print("Réponse complète d'emblée — pas de réflexion nécessaire.")
        total_apres += score_initial
        continue
    critique = critiquer(reponse, question)
    if critique.strip().upper() == "OK":
        total_apres += score_initial
        continue
    corrigee = corriger(reponse, critique, question)
    score = verifier_invariants(corrigee)
    total_apres += max(score, score_initial)
    print(f"Avant : {score_initial}/{len(INVARIANTS)} — après : {score}/{len(INVARIANTS)}")

print(
    f"Bilan : {total_avant} invariants sans réflexion, {total_apres} avec — "
    f"sur {len(QUESTIONS) * len(INVARIANTS)} possibles"
)
