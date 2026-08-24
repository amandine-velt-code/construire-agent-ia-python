"""Agent observé : chaque appel au modèle et chaque outil devient un événement
structuré (attributs gen_ai.*, conventions OpenTelemetry GenAI), avec durée,
tokens et coût estimé — et un budget en dollars qui coupe la session."""

import json
import os
import sys
import time

import requests
from dotenv import load_dotenv
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor, SpanExporter

load_dotenv()

FICHIER_TRACES = "traces.jsonl"
BUDGET_DOLLARS = float(sys.argv[1]) if len(sys.argv) > 1 else 0.50
MAX_ITERATIONS = 5

# Prix d'exemple par million de tokens (entrée / sortie) — remplacez par les
# prix affichés sur openrouter.ai/models pour vos modèles réels.
PRIX_PAR_MILLION = {
    "entree": 0.25,
    "sortie": 1.00,
}


class ExporteurJSONL(SpanExporter):
    """Écrit chaque span comme une ligne JSON dans traces.jsonl."""

    def __init__(self, chemin):
        self.chemin = chemin

    def export(self, spans):
        with open(self.chemin, "a", encoding="utf-8") as fichier:
            for span in spans:
                fichier.write(
                    json.dumps(
                        {
                            "name": span.name,
                            "attributes": {k: v for k, v in span.attributes.items()},
                            "duration_ms": (span.end_time - span.start_time) / 1_000_000,
                        },
                        ensure_ascii=False,
                    )
                    + "\n"
                )
        return None

    def shutdown(self):
        pass


def estimer_tokens(texte):
    """Estimation grossière : 1 token ≈ 4 caractères (mécanisme du chapitre 4)."""
    return len(texte) // 4


def estimer_cout(prompt_tokens, completion_tokens):
    """Coût estimé d'un appel, en dollars, à partir des prix d'exemple."""
    return (
        prompt_tokens / 1_000_000 * PRIX_PAR_MILLION["entree"]
        + completion_tokens / 1_000_000 * PRIX_PAR_MILLION["sortie"]
    )


def rechercher_trajets(destination, date):
    """Horaires simulés des trajets vers une destination, à une date."""
    horaires = {
        "lyon": ["07:42", "09:15", "11:38"],
        "marseille": ["06:50", "08:22", "10:05"],
    }
    return horaires.get(destination.lower(), [])


def consulter_prix(destination, date):
    """Prix simulé d'un trajet vers une destination, à une date."""
    prix = {"lyon": 65.0, "marseille": 80.0}
    return prix.get(destination.lower(), None)


OUTILS = {
    "rechercher_trajets": rechercher_trajets,
    "consulter_prix": consulter_prix,
}

DESCRIPTION_OUTILS = [
    {
        "type": "function",
        "function": {
            "name": "rechercher_trajets",
            "description": "Recherche les trajets en train disponibles vers une destination, à une date donnée.",
            "parameters": {
                "type": "object",
                "properties": {
                    "destination": {
                        "type": "string",
                        "description": "Ville de destination.",
                    },
                    "date": {
                        "type": "string",
                        "description": "Date du voyage au format AAAA-MM-JJ.",
                    },
                },
                "required": ["destination", "date"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "consulter_prix",
            "description": "Consulte le prix d'un trajet vers une destination, à une date donnée.",
            "parameters": {
                "type": "object",
                "properties": {
                    "destination": {
                        "type": "string",
                        "description": "Ville de destination.",
                    },
                    "date": {
                        "type": "string",
                        "description": "Date du voyage au format AAAA-MM-JJ.",
                    },
                },
                "required": ["destination", "date"],
            },
        },
    },
]


def executer_outil(nom, arguments):
    """Exécute la fonction Python demandée par le modèle."""
    if nom not in OUTILS:
        return f"Outil inconnu : {nom}"
    return OUTILS[nom](**arguments)


def appeler_modele(messages, tracer):
    """Appelle le modèle dans un span chat, et renvoie (réponse, durée)."""
    debut = time.perf_counter()
    reponse = requests.post(
        "https://openrouter.ai/api/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {os.environ['OPENROUTER_API_KEY']}",
            "Content-Type": "application/json",
        },
        json={
            "model": "openrouter/free",
            "messages": messages,
            "tools": DESCRIPTION_OUTILS,
        },
        timeout=120,
    )
    duree = time.perf_counter() - debut

    donnees = reponse.json()
    usage = donnees.get("usage", {})
    with tracer.start_as_current_span("chat") as span:
        span.set_attribute("gen_ai.operation.name", "chat")
        span.set_attribute("gen_ai.provider.name", "openrouter")
        span.set_attribute("gen_ai.request.model", donnees.get("model", "openrouter/free"))
        span.set_attribute("gen_ai.usage.input_tokens", usage.get("prompt_tokens", 0))
        span.set_attribute("gen_ai.usage.output_tokens", usage.get("completion_tokens", 0))
        span.set_attribute("gen_ai.response.finish_reasons", [donnees["choices"][0].get("finish_reason", "")])
        span.set_attribute("app.duration_s", round(duree, 3))
    return donnees, duree


# Instrumentation.
provider = TracerProvider()
provider.add_span_processor(SimpleSpanProcessor(ExporteurJSONL(FICHIER_TRACES)))
trace.set_tracer_provider(provider)
tracer = trace.get_tracer("agent-trains")

messages = [
    {
        "role": "user",
        "content": "Je veux aller à Lyon le 25 août 2026. Quels trajets sont disponibles ?",
    }
]

cout_total = 0.0
appels = 0

for iteration in range(MAX_ITERATIONS):
    tokens_entree = estimer_tokens(json.dumps(messages, ensure_ascii=False))
    cout_prochain = estimer_cout(tokens_entree, 200)
    if cout_total + cout_prochain > BUDGET_DOLLARS:
        print(f"Coupe-circuit : budget dépassé ({cout_total:.4f} $ cumulés, "
              f"{cout_prochain:.4f} $ estimés pour le prochain appel). Arrêt.")
        break

    donnees, duree = appeler_modele(messages, tracer)
    appels += 1
    message = donnees["choices"][0]["message"]
    usage = donnees.get("usage", {})
    cout_appel = estimer_cout(usage.get("prompt_tokens", 0), usage.get("completion_tokens", 0))
    cout_total += cout_appel
    print(f"Appel {appels} : {duree:.2f} s, {cout_appel:.5f} $ (total {cout_total:.5f} $)")
    messages.append(message)

    if not message.get("tool_calls"):
        print("Réponse finale :", message["content"].strip())
        break

    for appel in message["tool_calls"]:
        nom = appel["function"]["name"]
        arguments = json.loads(appel["function"]["arguments"])
        debut = time.perf_counter()
        resultat = executer_outil(nom, arguments)
        duree_outil = time.perf_counter() - debut
        with tracer.start_as_current_span("execute_tool") as span:
            span.set_attribute("gen_ai.operation.name", "execute_tool")
            span.set_attribute("gen_ai.tool.name", nom)
            span.set_attribute("app.duration_s", round(duree_outil, 3))
        print(f"→ le modèle demande {nom} ({duree_outil:.3f} s)")
        messages.append(
            {
                "role": "tool",
                "tool_call_id": appel["id"],
                "content": json.dumps(resultat, ensure_ascii=False),
            }
        )
else:
    print(f"Limite d'itérations atteinte ({MAX_ITERATIONS}) : arrêt de la boucle.")

print(f"Session : {appels} appels au modèle, {cout_total:.5f} $ estimés — traces dans {FICHIER_TRACES}.")
