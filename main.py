"""Pages HTML (rendu côté serveur avec Jinja)."""
from flask import Blueprint, abort, current_app, render_template, send_from_directory

from database import models
from database.db import get_db

bp = Blueprint("main", __name__)


@bp.get("/sw.js")
def service_worker():
    """Servi à la racine pour que le service worker contrôle tout le site (scope « / »)."""
    resp = send_from_directory(current_app.static_folder, "sw.js", mimetype="application/javascript")
    resp.headers["Cache-Control"] = "no-cache"
    return resp


@bp.get("/")
def index():
    db = get_db()
    return render_template("index.html", categories=models.list_categories(db),
                           total=len(models.list_all_propositions(db)))


@bp.get("/programme")
def programme():
    db = get_db()
    props = models.list_all_propositions(db)
    return render_template("programme.html", parts=models.list_parts(db),
                           source=props[0] if props else None, total=len(props))


@bp.get("/thematiques")
def categories():
    return render_template("categories.html", categories=models.list_categories(get_db()))


@bp.get("/thematiques/<slug>")
def category(slug):
    db = get_db()
    cat = models.get_category(db, slug)
    if cat is None:
        abort(404)
    props = [p for p in models.list_all_propositions(db) if p["category"] == slug]
    return render_template("category.html", category=cat, propositions=props)


@bp.get("/proposition/<int:prop_id>")
def proposition(prop_id):
    db = get_db()
    prop = models.get_proposition(db, prop_id)
    if prop is None:
        abort(404)
    cat = models.get_category(db, prop["category"])
    return render_template("proposition.html", p=prop, category=cat)


@bp.get("/explorer")
def explorer():
    return render_template("explorer.html")


@bp.get("/favoris")
def favoris():
    return render_template("favoris.html")


@bp.get("/quiz")
def quiz():
    return render_template("quiz.html")


@bp.get("/assistant")
def assistant():
    return render_template("assistant.html")


@bp.get("/a-propos")
def about():
    return render_template("about.html")
