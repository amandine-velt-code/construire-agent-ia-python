"""Piste de l'exercice du chapitre 17 : tester le garde d'approbation.

Le pattern de test des agents à confirmation humaine, tel que documenté
par la pratique : on ne mocke pas l'humain, on reprend la session avec une
décision scriptée. Ici, le garde du chapitre est testé avec les trois
décisions, enchaînées — sans clavier, sans modèle.
"""


def demander_confirmation(arguments, decisions):
    """Le garde du chapitre 17, avec des décisions scriptées au lieu du clavier.

    Renvoie (decision, arguments_effectifs).
    """
    while decisions:
        decision = decisions.pop(0)
        if decision == "modifier":
            arguments = dict(arguments, date=input_date_modifiee())
            continue
        return decision, arguments
    return "non", arguments


def input_date_modifiee():
    return "2026-08-26"


def test_oui():
    decision, arguments = demander_confirmation(
        {"destination": "Lyon", "date": "2026-08-25"}, ["oui"]
    )
    assert decision == "oui"
    assert arguments["date"] == "2026-08-25"
    print("oui → exécute tel quel :", arguments)


def test_non():
    decision, arguments = demander_confirmation(
        {"destination": "Lyon", "date": "2026-08-25"}, ["non"]
    )
    assert decision == "non"
    print("non → annule :", arguments)


def test_modifier():
    decision, arguments = demander_confirmation(
        {"destination": "Lyon", "date": "2026-08-25"}, ["modifier", "oui"]
    )
    assert decision == "oui"
    assert arguments["date"] == "2026-08-26"
    print("modifier → nouvelle date confirmée :", arguments)


if __name__ == "__main__":
    test_oui()
    test_non()
    test_modifier()
    print("Trois chemins du garde d'approbation vérifiés.")
