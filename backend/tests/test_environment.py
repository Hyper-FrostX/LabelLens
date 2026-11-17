import os
from pathlib import Path

from app.config.environment import (
    BACKEND_ENV_FILE,
    load_backend_environment_file,
)


def test_backend_environment_path_is_relative_to_project_directory():
    assert Path(__file__).resolve().parents[1] / ".env" == BACKEND_ENV_FILE


def test_backend_environment_loader_preserves_process_precedence(
    monkeypatch,
    tmp_path,
):
    environment_file = tmp_path / "backend.env"
    environment_file.write_text(
        "LABEL_LENS_ENV_TEST_KEY=from-file\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("LABEL_LENS_ENV_TEST_KEY", "from-process")

    load_backend_environment_file(environment_file)

    assert os.environ["LABEL_LENS_ENV_TEST_KEY"] == "from-process"


def test_missing_backend_environment_file_is_safe(tmp_path):
    load_backend_environment_file(tmp_path / "missing.env")
