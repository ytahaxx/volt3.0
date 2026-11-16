"""API REST : recherche, filtres et tri."""
from flask import Blueprint, jsonify, request

from database import models
from database.db import get_db
from services.search_service import VALID_SORTS, search

bp = Blueprint("search_api", __name__, url_prefix="/api")

LIST_FIELDS = ("id", "title", "category", "category_label", "subcategory", "type", "summary", "section_ref")


@bp.get("/filters")
def filters():
    return jsonify(models.distinct_filters(get_db()))


@bp.get("/propositions")
def propositions():
    """Paramètres : q, category, subcategory, type, sort (relevance|alpha|alpha_desc|document), ids=1,2,3."""
    db = get_db()
    sort = request.args.get("sort", "")
    if sort and sort not in VALID_SORTS:
        return jsonify(error=f"Tri invalide. Valeurs possibles : {', '.join(sorted(VALID_SORTS))}."), 400

    ids = None
    raw_ids = request.args.get("ids")
    if raw_ids is not None:
        try:
            ids = [int(x) for x in raw_ids.split(",") if x.strip()]
        except ValueError:
            return jsonify(error="Paramètre ids invalide."), 400

    labels = {c["slug"]: c["label"] for c in models.list_categories(db)}
    category = request.args.get("category", "")
    if category and category not in labels:
        return jsonify(error="Catégorie inconnue."), 400

    results, terms = search(
        models.list_all_propositions(db),
        q=request.args.get("q", "")[:200],
        category=category,
        subcategory=request.args.get("subcategory", ""),
        ptype=request.args.get("type", ""),
        sort=sort,
        ids=ids,
        category_labels=labels,
    )
    return jsonify(count=len(results), terms=terms,
                   results=[{k: p[k] for k in LIST_FIELDS} for p in results])
