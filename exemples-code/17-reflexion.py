"""Boucle de réflexion : après sa réponse, l'agent la fait critiquer et la
corrige — mais seulement quand les invariants du chapitre 7 échouent, et
en gardant toujours la meilleure des deux réponses. La réflexion n'est pas
une solution miracle : elle est un deuxième avis, déclenché et mesuré."""

from reflexion_agent import (
    INVARIANTS,
    boucle_agent,
    corriger,
    critiquer,
    verifier_invariants,
)

MAX_REFLEXIONS = 2

QUESTION = "Je veux aller à Marseille le 26 août 2026. Donne-moi le prix du premier trajet du matin ET l'heure de ce trajet."

reponse, _ = boucle_agent(QUESTION)
score_initial = verifier_invariants(reponse)
print("Réponse initiale :", reponse.strip())
print(f"Invariants vérifiés : {score_initial}/{len(INVARIANTS)}")

meilleure = reponse
meilleur_score = score_initial

for essai in range(1, MAX_REFLEXIONS + 1):
    if meilleur_score >= len(INVARIANTS):
        break
    print(f"Réflexion {essai}/{MAX_REFLEXIONS}…")
    critique = critiquer(meilleure, QUESTION)
    if critique.strip().upper() == "OK":
        print("Critique : OK — la réponse est jugée complète, pas de correction.")
        break
    print("Critique :", critique)
    corrigee = corriger(meilleure, critique, QUESTION)
    score = verifier_invariants(corrigee)
    print(f"Réponse corrigée ({score}/{len(INVARIANTS)}) :", corrigee.strip())
    if score > meilleur_score:
        meilleure, meilleur_score = corrigee, score
    else:
        print("La correction n'améliore pas : la réponse initiale est conservée.")
        break

print()
print("Réponse finale :", meilleure.strip())
print(f"Invariants : {meilleur_score}/{len(INVARIANTS)}")
