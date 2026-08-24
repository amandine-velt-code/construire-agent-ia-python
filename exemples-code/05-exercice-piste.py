import asyncio

from mcp import Client, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.types import TextContent

CHEMIN_SERVEUR = "exemples-code/05-serveur-trains.py"


async def main():
    parametres = StdioServerParameters(command="python", args=[CHEMIN_SERVEUR])
    async with Client(stdio_client(parametres)) as client:
        outils = await client.list_tools()
        print("Outils découverts :", [outil.name for outil in outils.tools])
        for outil in outils.tools:
            print(f"- {outil.name} : {outil.description}")
            print("  paramètres :", list(outil.input_schema.get("properties", {}).keys()))
        resultat = await client.call_tool(
            "rechercher_trajets", {"destination": "Lyon", "date": "2026-08-25"}
        )
        for bloc in resultat.content:
            if isinstance(bloc, TextContent):
                print("Résultat :", bloc.text)


if __name__ == "__main__":
    asyncio.run(main())
