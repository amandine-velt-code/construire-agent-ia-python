import os

import requests
from dotenv import load_dotenv

load_dotenv()

reponse = requests.post(
    "https://openrouter.ai/api/v1/chat/completions",
    headers={
        "Authorization": f"Bearer {os.environ['OPENROUTER_API_KEY']}",
        "Content-Type": "application/json",
    },
    json={
        "model": "openrouter/free",
        "messages": [
            {
                "role": "user",
                "content": "Quelle est la capitale du Japon ? Réponds en une phrase.",
            }
        ],
    },
    timeout=120,
)

message = reponse.json()["choices"][0]["message"]
print(message["content"].strip())
