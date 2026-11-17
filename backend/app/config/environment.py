from pathlib import Path

from dotenv import load_dotenv

BACKEND_ROOT = Path(__file__).resolve().parents[2]
BACKEND_ENV_FILE = BACKEND_ROOT / ".env"


def load_backend_environment_file(env_file: Path | None = None) -> None:
    load_dotenv(
        dotenv_path=env_file or BACKEND_ENV_FILE,
        override=False,
        encoding="utf-8-sig",
    )
