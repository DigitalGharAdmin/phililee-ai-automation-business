"""Test configuration in subprocesses without reading the real project .env."""

import os
from pathlib import Path
import shutil
import subprocess
import sys

import pytest


@pytest.mark.parametrize("file_present,process_values", [
    (False, {}),
    (True, {}),
    (True, {"OPENAI_API_KEY": "process-placeholder", "OPENAI_MODEL": "process-model"}),
    (True, {"OPENAI_API_KEY": "", "OPENAI_MODEL": "process-model"}),
])
def test_isolated_environment_loading(tmp_path, file_present, process_values):
    project = tmp_path / "project"
    shutil.copytree(Path(__file__).resolve().parents[1] / "app", project / "app",
                    ignore=shutil.ignore_patterns("__pycache__"))
    if file_present:
        (project / ".env").write_text(
            "OPENAI_API_KEY=file-placeholder\nOPENAI_MODEL=file-model\n",
            encoding="utf-8",
        )
    # A neighboring .env must never be discovered or loaded.
    (tmp_path / ".env").write_text("OPENAI_API_KEY=wrong-project\n", encoding="utf-8")
    env = os.environ.copy()
    for key in ["OPENAI_API_KEY", "OPENAI_MODEL", "PYTHON_DOTENV_DISABLED"]:
        env.pop(key, None)
    env.update(process_values)
    env["DATABASE_URL"] = "sqlite:///:memory:"
    env["PYTHONPATH"] = str(project)
    expected_key = process_values.get("OPENAI_API_KEY", "file-placeholder" if file_present else "")
    expected_model = process_values.get("OPENAI_MODEL", "file-model" if file_present else "gpt-4.1-mini")
    code = f"""
from app import settings
assert settings.OPENAI_API_KEY == {expected_key!r}, 'key precedence mismatch'
assert settings.OPENAI_MODEL == {expected_model!r}, 'model precedence mismatch'
from app.api import app
from fastapi.testclient import TestClient
with TestClient(app) as client:
    assert client.get('/').status_code == 200
assert '/leads/qualify-ai' in app.openapi()['paths']
"""
    result = subprocess.run([sys.executable, "-c", code], cwd=tmp_path, env=env,
                            capture_output=True, text=True, timeout=30)
    assert result.returncode == 0, "Isolated configuration/startup check failed"
