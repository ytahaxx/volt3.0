"""Régression : les paramètres de Config étaient accidentellement hors de la classe."""
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent


@pytest.mark.parametrize("vercel", [False, True])
def test_config_exposes_all_settings(vercel):
    env = dict(os.environ)
    env.pop("VERCEL", None)
    env.pop("DATABASE_PATH", None)
    if vercel:
        env["VERCEL"] = "1"
    code = """
from pathlib import Path
from config import Config
keys = ('DATABASE', 'PROPOSITIONS_JSON', 'QUIZ_JSON', 'PROGRAMME_PDF',
        'LLM_PROVIDER', 'LLM_MODEL', 'LLM_TIMEOUT', 'RAG_TOP_K', 'RAG_MIN_SCORE')
assert all(hasattr(Config, key) for key in keys)
assert Path(Config.PROPOSITIONS_JSON).is_file()
assert Path(Config.QUIZ_JSON).is_file()
assert Config.DATABASE.startswith('/tmp/') if VERCEL else '/database/' in Config.DATABASE.replace('\\\\', '/')
""".replace('VERCEL', str(vercel))
    result = subprocess.run([sys.executable, '-c', code], cwd=ROOT, env=env,
                            capture_output=True, text=True, timeout=15)
    assert result.returncode == 0, result.stderr
