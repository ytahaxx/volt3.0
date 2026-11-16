"""Accès SQLite (bibliothèque standard `sqlite3`).

Choix technique : SQLAlchemy n'était pas installé dans l'environnement de développement
et l'installation de paquets y était bloquée. La couche d'accès est donc isolée dans
`database/` (db.py = connexion/initialisation, models.py = requêtes) : migrer vers
SQLAlchemy ou PostgreSQL ne demandera de réécrire que ces deux fichiers.
"""
import json
import sqlite3
from pathlib import Path

from flask import current_app, g

SCHEMA = """
CREATE TABLE IF NOT EXISTS categories (
    slug TEXT PRIMARY KEY,
    label TEXT NOT NULL,
    icon TEXT NOT NULL DEFAULT '',
    description TEXT NOT NULL DEFAULT ''
);
CREATE TABLE IF NOT EXISTS propositions (
    id INTEGER PRIMARY KEY,
    title TEXT NOT NULL,
    category TEXT NOT NULL REFERENCES categories(slug),
    subcategory TEXT NOT NULL,
    type TEXT NOT NULL,
    summary TEXT NOT NULL,
    details TEXT NOT NULL,
    objectives TEXT NOT NULL,      -- JSON (liste)
    measures TEXT NOT NULL,        -- JSON (liste)
    keywords TEXT NOT NULL,        -- JSON (liste)
    part TEXT NOT NULL,
    section TEXT NOT NULL,
    position INTEGER NOT NULL,
    section_ref TEXT NOT NULL,
    source_document TEXT NOT NULL,
    source_url TEXT NOT NULL,
    page INTEGER
);
CREATE INDEX IF NOT EXISTS idx_prop_category ON propositions(category);
"""


def connect(path):
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def get_db():
    if "db" not in g:
        g.db = connect(current_app.config["DATABASE"])
    return g.db


def close_db(_exc=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db(path, propositions_json):
    """Crée le schéma et (ré)charge les données depuis le JSON vérifié."""
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    data = json.loads(Path(propositions_json).read_text(encoding="utf-8"))
    conn = connect(path)
    try:
        conn.executescript(SCHEMA)
        conn.execute("DELETE FROM propositions")
        conn.execute("DELETE FROM categories")
        conn.executemany(
            "INSERT INTO categories(slug,label,icon,description) VALUES (?,?,?,?)",
            [(c["slug"], c["label"], c["icon"], c["description"]) for c in data["categories"]],
        )
        conn.executemany(
            """INSERT INTO propositions(id,title,category,subcategory,type,summary,details,
               objectives,measures,keywords,part,section,position,section_ref,
               source_document,source_url,page)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            [
                (
                    p["id"], p["title"], p["category"], p["subcategory"], p["type"],
                    p["summary"], p["details"],
                    json.dumps(p["objectives"], ensure_ascii=False),
                    json.dumps(p["measures"], ensure_ascii=False),
                    json.dumps(p["keywords"], ensure_ascii=False),
                    p["part"], p["section"], p["position"], p["section_ref"],
                    p["source_document"], p["source_url"], p.get("page"),
                )
                for p in data["propositions"]
            ],
        )
        conn.commit()
    finally:
        conn.close()
