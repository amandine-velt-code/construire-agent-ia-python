from outils_trajets import consulter_prix, rechercher_trajets


def test_horaires_lyon():
    assert rechercher_trajets("Lyon", "2026-08-25") == ["07:42", "09:15", "11:38"]


def test_destination_inconnue():
    resultat = rechercher_trajets("Bordeaux", "2026-08-25")
    assert "Destination inconnue" in resultat


def test_date_invalide():
    resultat = rechercher_trajets("Lyon", "25/08/2026")
    assert "Date invalide" in resultat


def test_prix_marseille():
    assert consulter_prix("Marseille", "2026-08-26") == 80.0


def test_prix_destination_inconnue():
    assert consulter_prix("Bordeaux", "2026-08-26") is None
