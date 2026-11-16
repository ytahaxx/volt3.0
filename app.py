"""Point d'entrée de Volt Explorer (fabrique d'application Flask).

Lancer en local : python app.py → http://127.0.0.1:5000

Robustesse au déploiement : si le dépôt a été téléversé « à plat » sur GitHub
(tous les fichiers à la racine, sans les dossiers routes/, services/,
database/, templates/, static/, data/), l'arborescence est reconstruite
automatiquement dans /tmp au démarrage.
"""

import os
import re
import shutil
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent

_PACKAGES = {
    "routes": {"main.py", "quiz.py", "programme.py", "search.py", "assistant.py"},
    "services": {"llm_providers.py", "rag_service.py", "text_utils.py",
                 "document_parser.py", "quiz_service.py", "search_service.py"},
    "database": {"db.py", "models.py"},
}
_JS = {"app.js", "search.js", "quiz.js", "assistant.js"}


def _canonical(name):
    """« style (4).css » → « style.css » (doublons créés par l'upload GitHub)."""
    return re.sub(r" \(\d+\)(?=\.[^.]+$)", "", name)


def _destination(name):
    if name in ("config.py",):
        return name
    for pkg, files in _PACKAGES.items():
        if name in files:
            return f"{pkg}/{name}"
    if name.endswith(".html"):
        return f"templates/{name}"
    if name == "style.css":
        return "static/css/style.css"
    if name in _JS:
        return f"static/js/{name}"
    if name in ("sw.js", "manifest.webmanifest"):
        return f"static/{name}"
    if name.endswith(".png"):
        return f"static/images/{name}"
    if name in ("propositions.json", "quiz.json"):
        return f"data/{name}"
    return None


def _project_root():
    if (HERE / "database" / "db.py").exists() and (HERE / "templates").is_dir():
        return HERE  # arborescence normale
    target = Path(tempfile.gettempdir()) / "volt_explorer_src"
    if not (target / "database" / "db.py").exists():
        shutil.rmtree(target, ignore_errors=True)
        for f in sorted(HERE.iterdir()):
            if not f.is_file():
                continue
            canon = _canonical(f.name)
            dest = _destination(canon)
            if dest is None:
                continue
            out = target / dest
            if canon != f.name and out.exists():
                continue  # garder la version sans « (n) »
            out.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(f, out)
        for pkg in _PACKAGES:
            (target / pkg / "__init__.py").touch()
    return target


ROOT = _project_root()
sys.path.insert(0, str(ROOT))

from flask import Flask, jsonify, render_template, request  # noqa: E402

from config import Config  # noqa: E402
from database import models  # noqa: E402
from database.db import close_db, connect, init_db  # noqa: E402
from routes import assistant, main, programme, quiz, search  # noqa: E402
from services.quiz_service import QuizService  # noqa: E402
from services.rag_service import RagService  # noqa: E402


def create_app(config_object=Config, overrides=None):
    app = Flask(__name__, root_path=str(ROOT))
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
