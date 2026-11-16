"""Fournisseurs de modèles de langage interchangeables.

Pour ajouter un fournisseur : créer une classe avec une méthode `generate(question, passages)`
et l'enregistrer dans PROVIDERS. Le reste de l'application n'a pas à changer.

- DemoProvider      : aucun service externe ; reformule les passages retrouvés (testé).
- AnthropicProvider : API Messages d'Anthropic via `requests` (non testé ici : aucune clé).
- OpenAIProvider    : API Chat Completions (OpenAI ou compatible) via `requests` (non testé ici).

Les clés API sont lues côté serveur uniquement (config.py / .env).
"""
import requests

SYSTEM_PROMPT = (
    "Tu es l'assistant de Volt Explorer, une application pédagogique et neutre. "
    "Tu réponds en français, UNIQUEMENT à partir des passages numérotés fournis dans le contexte "
    "(extraits du programme officiel de Volt). Règles : "
    "1) cite les passages utilisés avec leurs marqueurs [S1], [S2]… ; "
    "2) n'ajoute aucune information, chiffre ou mesure absents des passages ; "
    "3) si les passages ne répondent pas à la question, dis-le clairement ; "
    "4) présente les mesures comme des propositions de Volt, sans jugement ni opinion ; "
    "5) ne donne jamais de consigne ou de conseil de vote et ne cherche pas à convaincre."
)


def build_user_prompt(question, passages):
    context = "\n\n".join(f"[S{i}] ({p['ref']})\n{p['text']}" for i, p in enumerate(passages, start=1))
    return f"Contexte (passages du programme officiel) :\n\n{context}\n\nQuestion : {question}"


class LLMError(RuntimeError):
    pass


class DemoProvider:
    name = "demo"

    def generate(self, question, passages):
        lines = ["Voici ce que le programme officiel indique sur ce sujet :", ""]
        for i, p in enumerate(passages[:3], start=1):
            lines.append(f"• {p['text']} [S{i}]")
        lines += ["", "(Mode démonstration : cette réponse reprend directement les passages retrouvés, "
                      "sans modèle de langage.)"]
        return "\n".join(lines)


class AnthropicProvider:
    name = "anthropic"

    def __init__(self, api_key, model="", timeout=30):
        self.api_key, self.model, self.timeout = api_key, model or "claude-sonnet-5-5", timeout

    def generate(self, question, passages):
        try:
            r = requests.post(
                "https://api.anthropic.com/v1/messages",
                headers={"x-api-key": self.api_key, "anthropic-version": "2023-06-01",
                         "content-type": "application/json"},
                json={"model": self.model, "max_tokens": 700, "system": SYSTEM_PROMPT,
                      "messages": [{"role": "user", "content": build_user_prompt(question, passages)}]},
                timeout=self.timeout,
            )
            r.raise_for_status()
            return "".join(b.get("text", "") for b in r.json().get("content", [])).strip()
        except (requests.RequestException, ValueError) as exc:
            raise LLMError(f"Appel Anthropic échoué : {exc}") from exc


class OpenAIProvider:
    name = "openai"

    def __init__(self, api_key, model="", base_url="https://api.openai.com/v1", timeout=30):
        self.api_key, self.model = api_key, model or "gpt-4o-mini"
        self.base_url, self.timeout = base_url.rstrip("/"), timeout

    def generate(self, question, passages):
        try:
            r = requests.post(
                f"{self.base_url}/chat/completions",
                headers={"Authorization": f"Bearer {self.api_key}", "content-type": "application/json"},
                json={"model": self.model, "temperature": 0.1,
                      "messages": [{"role": "system", "content": SYSTEM_PROMPT},
                                   {"role": "user", "content": build_user_prompt(question, passages)}]},
                timeout=self.timeout,
            )
            r.raise_for_status()
            return r.json()["choices"][0]["message"]["content"].strip()
        except (requests.RequestException, KeyError, IndexError, ValueError) as exc:
            raise LLMError(f"Appel OpenAI échoué : {exc}") from exc


def get_provider(config):
    """Retourne (fournisseur, notice). Sans clé ou nom inconnu : repli sur le mode démonstration."""
    name = (config.get("LLM_PROVIDER") or "demo").lower()
    timeout = config.get("LLM_TIMEOUT", 30)
    if name == "anthropic":
        if config.get("ANTHROPIC_API_KEY"):
            return AnthropicProvider(config["ANTHROPIC_API_KEY"], config.get("LLM_MODEL", ""), timeout), None
        return DemoProvider(), "Clé ANTHROPIC_API_KEY absente : mode démonstration."
    if name == "openai":
        if config.get("OPENAI_API_KEY"):
            return OpenAIProvider(config["OPENAI_API_KEY"], config.get("LLM_MODEL", ""),
                                  config.get("OPENAI_BASE_URL", "https://api.openai.com/v1"), timeout), None
        return DemoProvider(), "Clé OPENAI_API_KEY absente : mode démonstration."
    if name != "demo":
        return DemoProvider(), f"Fournisseur « {name} » inconnu : mode démonstration."
    return DemoProvider(), None
