"""Serveur MCP exposant les outils de recherche de trajets en train."""

from mcp.server import MCPServer

mcp = MCPServer("trajets")


@mcp.tool()
def rechercher_trajets(destination: str, date: str) -> str:
    """Recherche les trajets en train disponibles vers une destination, à une date donnée.

    Args:
        destination: Ville de destination.
        date: Date du voyage au format AAAA-MM-JJ.
    """
    horaires = {
        "lyon": ["07:42", "09:15", "11:38"],
        "marseille": ["06:50", "08:22", "10:05"],
    }
    trajets = horaires.get(destination.lower(), [])
    if not trajets:
        return f"Aucun trajet disponible vers {destination} le {date}."
    return "Horaires disponibles : " + ", ".join(trajets)


@mcp.tool()
def consulter_prix(destination: str, date: str) -> str:
    """Consulte le prix d'un trajet vers une destination, à une date donnée.

    Args:
        destination: Ville de destination.
        date: Date du voyage au format AAAA-MM-JJ.
    """
    prix = {"lyon": 65.0, "marseille": 80.0}
    valeur = prix.get(destination.lower())
    if valeur is None:
        return f"Prix inconnu pour la destination {destination}."
    return f"Le trajet vers {destination} le {date} coûte {valeur} €."


if __name__ == "__main__":
    mcp.run(transport="stdio")
