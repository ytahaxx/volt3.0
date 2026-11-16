"""API REST : assistant RAG."""
from flask import Blueprint, current_app, jsonify, request

bp = Blueprint("assistant_api", __name__, url_prefix="/api/assistant")

MAX_QUESTION_LENGTH = 500


@bp.get("/status")
def status():
    rag = current_app.extensions["rag_service"]
    return jsonify(mode=rag.mode, notice=rag.notice, passages=len(rag.index.passages))


@bp.post("")
def ask():
    body = request.get_json(silent=True)
    if not isinstance(body, dict) or not isinstance(body.get("question"), str):
        return jsonify(error="Le champ « question » est requis."), 400
    question = body["question"].strip()
    if not question:
        return jsonify(error="La question est vide."), 400
    if len(question) > MAX_QUESTION_LENGTH:
        return jsonify(error=f"Question trop longue (maximum {MAX_QUESTION_LENGTH} caractères)."), 400
    return jsonify(current_app.extensions["rag_service"].answer(question))
