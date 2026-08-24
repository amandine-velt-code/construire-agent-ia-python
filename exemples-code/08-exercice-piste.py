import asyncio
import os

from dotenv import load_dotenv
from mcp import Client
from mcp.types import TextContent

load_dotenv()

URL_SERVEUR = os.getenv("AGENT_URL", "http://127.0.0.1:8000/mcp")


async def main():
    async with Client(URL_SERVEUR) as client:
        outils = await client.list_tools()
        print("Connecté à", URL_SERVEUR)
        print("Outils disponibles :", [outil.name for outil in outils.tools])
        resultat = await client.call_tool(
            "rechercher_trajets", {"destination": "Lyon", "date": "2026-08-25"}
        )
        for bloc in resultat.content:
            if isinstance(bloc, TextContent):
                print("Résultat :", bloc.text)


if __name__ == "__main__":
    asyncio.run(main())
