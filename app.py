
"""Point d'entrée de Volt Explorer (fabrique d'application Flask).

Lancer en local : python app.py → http://127.0.0.1:5000
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from flask import Flask, jsonify, render_template, request  # noqa: E402

from config import Config  # noqa: E402
from database import models  # noqa: E402
from database.db import close_db, connect, init_db  # noqa: E402
from routes import assistant, main, programme, quiz, search  # noqa: E402
from services.quiz_service import QuizService  # noqa: E402
from services.rag_service import RagService  # noqa: E402


def create_app(config_object=Config, overrides=None):
    app = Flask(__name__)
    app.config.from_object(config_object)

    if overrides:
        app.config.update(overrides)

    # Initialisation de la base de données
    if not Path(app.config["DATABASE"]).exists():
        init_db(
            app.config["DATABASE"],
            app.config["PROPOSITIONS_JSON"]
        )

    app.teardown_appcontext(close_db)

    # Chargement des propositions
    conn = connect(app.config["DATABASE"])
    try:
        propositions = models.list_all_propositions(conn)
    finally:
        conn.close()

    # Initialisation des services
    app.extensions["quiz_service"] = QuizService(
        app.config["QUIZ_JSON"]
    )

    app.extensions["rag_service"] = RagService(
        propositions,
        app.config
    )

    # Enregistrement des Blueprints
    for module in (main, programme, search, quiz, assistant):
        app.register_blueprint(module.bp)

    # Gestion des erreurs 404
    @app.errorhandler(404)
    def not_found(_e):
        if request.path.startswith("/api/"):
            return jsonify(error="Ressource introuvable."), 404
        return render_template("404.html"), 404

    # Gestion des erreurs 405
    @app.errorhandler(405)
    def method_not_allowed(_e):
        if request.path.startswith("/api/"):
            return jsonify(error="Méthode non autorisée."), 405
        return render_template("404.html"), 405

    # Gestion des erreurs 500
    @app.errorhandler(500)
    def server_error(_e):
        if request.path.startswith("/api/"):
            return jsonify(error="Erreur interne du serveur."), 500
        return render_template("404.html", error500=True), 500

    return app


# ==========================================
# INSTANCE FLASK PRINCIPALE POUR VERCEL
# ==========================================

app = create_app()


# ==========================================
# LANCEMENT LOCAL
# ==========================================

if __name__ == "__main__":
    app.run(
        host="127.0.0.1",
        port=int(os.getenv("PORT", "5000")),
        debug=os.getenv("FLASK_DEBUG", "0") == "1"
    )
