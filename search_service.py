"""Recherche par mot-clé et filtrage des propositions.

Recherche volontairement simple et déterministe (sans IA) : insensible à la casse et aux
accents, tous les mots saisis doivent être présents (ET), avec un score de pertinence
pondéré (titre > mots-clés > résumé > reste).
"""
import re

from services.text_utils import normalize

VALID_SORTS = {"relevance", "alpha", "alpha_desc", "document"}


def _haystack_parts(p):
    return {
        "title": normalize(p["title"]),
        "keywords": normalize(" ".join(p["keywords"])),
        "summary": normalize(p["summary"]),
        "rest": normalize(
            " ".join([p["details"], " ".join(p["measures"]), " ".join(p["objectives"]),
                      p["subcategory"], p["type"], p["section"]])
        ),
    }


def _term_in(term, text):
    if len(term) <= 3:  # « ia », « ue » : mot entier uniquement, pour éviter les faux positifs
        return re.search(rf"(?<![a-z0-9]){re.escape(term)}(?![a-z0-9])", text) is not None
    return term in text


def score_proposition(p, terms):
    parts = _haystack_parts(p)
    weights = {"title": 5, "keywords": 3, "summary": 2, "rest": 1}
    total = 0
    for term in terms:
        term_score = sum(w for key, w in weights.items() if _term_in(term, parts[key]))
        if term_score == 0:
            return 0  # opérateur ET
        total += term_score
    return total


def search(propositions, q="", category="", subcategory="", ptype="", sort="", ids=None, category_labels=None):
    """Retourne la liste filtrée/triée de propositions (dicts)."""
    items = propositions
    if category_labels:
        items = [dict(p, category_label=category_labels.get(p["category"], "")) for p in items]
    if ids is not None:
        wanted = set(ids)
        items = [p for p in items if p["id"] in wanted]
    if category:
        items = [p for p in items if p["category"] == category]
    if subcategory:
        items = [p for p in items if normalize(p["subcategory"]) == normalize(subcategory)]
    if ptype:
        items = [p for p in items if normalize(p["type"]) == normalize(ptype)]

    terms = [t for t in normalize(q).replace("'", " ").split() if t]
    scored = []
    for p in items:
        s = score_proposition(p, terms) if terms else 1
        if s > 0:
            scored.append((s, p))

    sort = sort if sort in VALID_SORTS else ("relevance" if terms else "document")
    if sort == "relevance":
        scored.sort(key=lambda sp: (-sp[0], sp[1]["id"]))
    elif sort == "alpha":
        scored.sort(key=lambda sp: normalize(sp[1]["title"]))
    elif sort == "alpha_desc":
        scored.sort(key=lambda sp: normalize(sp[1]["title"]), reverse=True)
    else:
        scored.sort(key=lambda sp: sp[1]["id"])
    return [p for _, p in scored], terms
