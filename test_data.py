import json
import sqlite3
from pathlib import Path

DATA = json.loads((Path(__file__).resolve().parent.parent / "data" / "propositions.json").read_text(encoding="utf-8"))


def test_json_integrity():
    props = DATA["propositions"]
    assert [p["id"] for p in props] == list(range(1, len(props) + 1))
    slugs = {c["slug"] for c in DATA["categories"]}
    for p in props:
        assert p["category"] in slugs
        for key in ["title", "summary", "details", "section_ref", "source_url", "source_document"]:
            assert p[key].strip()
        assert p["objectives"] and p["measures"] and p["keywords"]
        assert p["source_url"] == "https://voltfrance.org/storage/pdf/volt-ecp_fr.pdf"
        assert p["page"] is None  # numéros de page non vérifiés : jamais inventés


def test_database_matches_json(app):
    conn = sqlite3.connect(app.config["DATABASE"])
    assert conn.execute("SELECT COUNT(*) FROM propositions").fetchone()[0] == len(DATA["propositions"])
    assert conn.execute("SELECT COUNT(*) FROM categories").fetchone()[0] == len(DATA["categories"])
    conn.close()


def test_every_category_has_at_least_one_proposition(client):
    for c in client.get("/api/categories").get_json():
        assert c["count"] >= 1
