import json
from unittest.mock import patch

from services import llm_providers
from services.document_parser import chunk_text, clean_text
from services.llm_providers import AnthropicProvider, DemoProvider, LLMError, OpenAIProvider, get_provider


def ask(client, question):
    return client.post("/api/assistant", json={"question": question})


def test_status_reports_demo_mode(client):
    s = client.get("/api/assistant/status").get_json()
    assert s["mode"] == "demo" and s["passages"] >= 48


def test_answers_spec_examples_with_sources(client):
    cases = {
        "Que propose Volt concernant l'intelligence artificielle ?": {11, 48},
        "Quelles sont les propositions sur l'environnement ?": {16, 17, 24},
        "Que prévoit le programme concernant les transports ?": {21},
        "Quelles sont les mesures proposées pour l'éducation ?": {34, 35, 36},
    }
    for question, expected_any in cases.items():
        data = ask(client, question).get_json()
        assert data["status"] == "ok", question
        assert data["sources"], question
        ids = {s["proposition_id"] for s in data["sources"]}
        assert ids & expected_any, (question, ids)
        assert "[S1]" in data["answer"]
        for s in data["sources"]:
            assert s["ref"] and s["url"].startswith("https://voltfrance.org/")


def test_irrelevant_question_says_not_found(client):
    for q in ["Quelle est la recette de la tarte aux pommes ?", "Qui a gagné la coupe du monde de football ?"]:
        data = ask(client, q).get_json()
        assert data["status"] == "not_found" and data["sources"] == []
        assert "pas trouvé" in data["answer"]


def test_refuses_vote_recommendation(client):
    for q in ["Pour qui voter aux prochaines élections ?", "Faut-il voter Volt ?", "Quel est le meilleur parti ?"]:
        data = ask(client, q).get_json()
        assert data["status"] == "refused_vote", q
        assert data["sources"] == []


def test_vote_topic_question_is_not_wrongly_refused(client):
    data = ask(client, "Que dit le programme sur le droit de vote à 16 ans ?").get_json()
    assert data["status"] == "ok"
    assert 3 in {s["proposition_id"] for s in data["sources"]}


def test_assistant_input_validation(client):
    assert client.post("/api/assistant", json={}).status_code == 400
    assert client.post("/api/assistant", json={"question": "   "}).status_code == 400
    assert client.post("/api/assistant", json={"question": 12}).status_code == 400
    assert client.post("/api/assistant", json={"question": "a" * 501}).status_code == 400
    assert client.post("/api/assistant", data="pas du json").status_code == 400


def test_unofficial_details_are_not_in_the_index(app):
    rag = app.extensions["rag_service"]
    detail = "Le chiffre de 22 % est celui qui figure explicitement dans le programme."
    assert all(detail not in p["text"] and detail not in p["index_text"] for p in rag.index.passages)


# ---- fournisseurs LLM (sans appel réseau) ----

def test_provider_selection_falls_back_to_demo_without_key():
    p, notice = get_provider({"LLM_PROVIDER": "anthropic", "ANTHROPIC_API_KEY": ""})
    assert isinstance(p, DemoProvider) and "ANTHROPIC_API_KEY" in notice
    p, notice = get_provider({"LLM_PROVIDER": "openai", "OPENAI_API_KEY": ""})
    assert isinstance(p, DemoProvider) and "OPENAI_API_KEY" in notice
    p, notice = get_provider({"LLM_PROVIDER": "inconnu"})
    assert isinstance(p, DemoProvider) and "inconnu" in notice


def test_provider_selection_with_keys():
    p, notice = get_provider({"LLM_PROVIDER": "anthropic", "ANTHROPIC_API_KEY": "k"})
    assert isinstance(p, AnthropicProvider) and notice is None
    p, notice = get_provider({"LLM_PROVIDER": "openai", "OPENAI_API_KEY": "k"})
    assert isinstance(p, OpenAIProvider) and notice is None


def test_anthropic_request_shape_with_mocked_http():
    passages = [{"ref": "réf", "text": "texte"}]

    class Resp:
        def raise_for_status(self): pass
        def json(self): return {"content": [{"type": "text", "text": "Réponse [S1]"}]}

    with patch.object(llm_providers.requests, "post", return_value=Resp()) as post:
        out = AnthropicProvider("secret", "m").generate("Q ?", passages)
    assert out == "Réponse [S1]"
    kwargs = post.call_args.kwargs
    assert kwargs["headers"]["x-api-key"] == "secret"
    assert "[S1]" in kwargs["json"]["messages"][0]["content"]


def test_llm_failure_falls_back_to_demo(app, client):
    class Boom:
        name = "anthropic"
        def generate(self, q, p): raise LLMError("panne")

    app.extensions["rag_service"].provider = Boom()
    data = ask(client, "Que propose le programme sur le charbon ?").get_json()
    assert data["status"] == "ok" and "panne" in data["notice"] and data["sources"]


def test_api_key_never_exposed_in_pages_or_status(app):
    app.config["ANTHROPIC_API_KEY"] = "sk-ultra-secret"
    c = app.test_client()
    blob = c.get("/assistant").get_data(as_text=True) + c.get("/api/assistant/status").get_data(as_text=True)
    blob += c.get("/static/js/assistant.js").get_data(as_text=True)
    assert "sk-ultra-secret" not in blob


# ---- pipeline document ----

def test_chunking_and_cleaning():
    text = clean_text("Une phrase longue. Une autre phrase.\n\n\n\nTroisième phrase ; quatrième.")
    assert "\n\n\n" not in text
    chunks = chunk_text("Phrase un. " * 100, max_chars=200)
    assert len(chunks) > 1 and all(len(c) <= 260 for c in chunks)
