"""API REST : quiz."""
from flask import Blueprint, current_app, jsonify, request

bp = Blueprint("quiz_api", __name__, url_prefix="/api/quiz")


def _svc():
    return current_app.extensions["quiz_service"]


@bp.get("")
def questions():
    level = request.args.get("level", "tous")
    svc = _svc()
    if level != "tous" and level not in svc.level_slugs():
        return jsonify(error="Niveau inconnu."), 400
    qs = svc.get_questions(level)
    return jsonify(levels=svc.levels, level=level, count=len(qs), questions=qs)


@bp.post("/answer")
def answer():
    body = request.get_json(silent=True)
    if not isinstance(body, dict):
        return jsonify(error="Un objet JSON est requis."), 400
    try:
        return jsonify(_svc().check_answer(body.get("question_id"), body.get("choice")))
    except KeyError:
        return jsonify(error="Question inconnue."), 404
    except ValueError:
        return jsonify(error="Choix invalide."), 400


@bp.post("/score")
def score():
    body = request.get_json(silent=True)
    if not isinstance(body, dict):
        return jsonify(error="Un objet JSON est requis."), 400
    answers = body.get("answers")
    if not isinstance(answers, list):
        return jsonify(error="Le champ « answers » doit être une liste."), 400
    try:
        return jsonify(_svc().score(answers))
    except ValueError:
        return jsonify(error="Réponse invalide."), 400
