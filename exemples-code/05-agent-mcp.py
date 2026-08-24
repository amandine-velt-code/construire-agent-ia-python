import asyncio
import json
import os

import requests
from dotenv import load_dotenv
from mcp import Client, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.types import TextContent

load_dotenv()

CHEMIN_SERVEUR = "exemples-code/05-serveur-trains.py"


async def lancer_agent():
    parametres = StdioServerParameters(command="python", args=[CHEMIN_SERVEUR])
    async with Client(stdio_client(parametres)) as client:
        outils = await client.list_tools()
        description_outils = [
            {
                "type": "function",
                "function": {
                    "name": outil.name,
                    "description": outil.description,
                    "parameters": outil.input_schema,
                },
            }
            for outil in outils.tools
        ]
        print("Outils découverts :", [outil.name for outil in outils.tools])

        messages = [
            {
                "role": "user",
                "content": "Je veux aller à Lyon le 25 août 2026. Quels trajets sont disponibles ?",
            }
        ]

        while True:
            reponse = requests.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {os.environ['OPENROUTER_API_KEY']}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": "openrouter/free",
                    "messages": messages,
                    "tools": description_outils,
                },
                timeout=120,
            )

            message = reponse.json()["choices"][0]["message"]
            messages.append(message)

            if not message.get("tool_calls"):
                break

            for appel in message["tool_calls"]:
                nom = appel["function"]["name"]
                arguments = json.loads(appel["function"]["arguments"])
                print("→ le modèle demande", nom, arguments)
                resultat = await client.call_tool(nom, arguments)
                texte = "\n".join(
                    bloc.text for bloc in resultat.content if isinstance(bloc, TextContent)
                )
                if resultat.is_error:
                    texte = f"Erreur : {texte}"
                print("← le serveur exécute :", texte)
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": appel["id"],
                        "content": texte,
                    }
                )

        print("Réponse finale :", message["content"].strip())


if __name__ == "__main__":
    asyncio.run(lancer_agent())
