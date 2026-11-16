"""Requêtes sur les propositions et catégories (lecture seule)."""
import json


def _row_to_proposition(row):
    d = dict(row)
    for key in ("objectives", "measures", "keywords"):
        d[key] = json.loads(d[key])
    return d


def list_categories(db):
    rows = db.execute(
        """SELECT c.slug, c.label, c.icon, c.description, COUNT(p.id) AS count
           FROM categories c LEFT JOIN propositions p ON p.category = c.slug
           GROUP BY c.slug ORDER BY c.label COLLATE NOCASE"""
    ).fetchall()
    return [dict(r) for r in rows]


def get_category(db, slug):
    row = db.execute("SELECT slug,label,icon,description FROM categories WHERE slug=?", (slug,)).fetchone()
    return dict(row) if row else None


def list_all_propositions(db):
    rows = db.execute("SELECT * FROM propositions ORDER BY id").fetchall()
    return [_row_to_proposition(r) for r in rows]


def get_proposition(db, prop_id):
    row = db.execute("SELECT * FROM propositions WHERE id=?", (prop_id,)).fetchone()
    return _row_to_proposition(row) if row else None


def list_parts(db):
    """Structure du document : parties > sections > propositions (dans l'ordre du document)."""
    rows = db.execute("SELECT id,title,part,section,position FROM propositions ORDER BY id").fetchall()
    parts = []
    for r in rows:
        if not parts or parts[-1]["title"] != r["part"]:
            parts.append({"title": r["part"], "sections": []})
        sections = parts[-1]["sections"]
        if not sections or sections[-1]["title"] != r["section"]:
            sections.append({"title": r["section"], "propositions": []})
        sections[-1]["propositions"].append({"id": r["id"], "title": r["title"]})
    return parts


def distinct_filters(db):
    cats = list_categories(db)
    subs = db.execute(
        "SELECT DISTINCT category, subcategory FROM propositions ORDER BY subcategory COLLATE NOCASE"
    ).fetchall()
    types = db.execute("SELECT DISTINCT type FROM propositions ORDER BY type COLLATE NOCASE").fetchall()
    return {
        "categories": [{"slug": c["slug"], "label": c["label"], "count": c["count"]} for c in cats],
        "subcategories": [{"category": r["category"], "label": r["subcategory"]} for r in subs],
        "types": [r["type"] for r in types],
    }
