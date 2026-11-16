"""API REST : catégories et propositions."""
from flask import Blueprint, jsonify

from database import models
from database.db import get_db

bp = Blueprint("programme_api", __name__, url_prefix="/api")


@bp.get("/categories")
def categories():
    return jsonify(models.list_categories(get_db()))


@bp.get("/propositions/<int:prop_id>")
def proposition(prop_id):
    prop = models.get_proposition(get_db(), prop_id)
    if prop is None:
        return jsonify(error="Proposition introuvable."), 404
    return jsonify(prop)
