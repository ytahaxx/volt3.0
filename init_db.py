"""Recrée la base SQLite depuis data/propositions.json.

Usage :  python scripts/init_db.py
À lancer après avoir modifié le JSON (la base n'est créée automatiquement qu'au premier lancement).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config import Config  # noqa: E402
from database.db import init_db  # noqa: E402

if __name__ == "__main__":
    Path(Config.DATABASE).unlink(missing_ok=True)
    init_db(Config.DATABASE, Config.PROPOSITIONS_JSON)
    print(f"Base recréée : {Config.DATABASE}")
