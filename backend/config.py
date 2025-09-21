import os
from pathlib import Path


class Settings:
    """Application configuration with sane defaults for local dev.

    Uses environment variables when available.
    """

    # Base directories
    PROJECT_ROOT: Path = Path(__file__).resolve().parent.parent
    DATA_DIR: Path = Path(os.getenv("OVO_DATA_DIR", PROJECT_ROOT / "uploads"))

    # Database
    raw_db_url = os.getenv(
        "DATABASE_URL",
        f"sqlite:///{(PROJECT_ROOT / 'ovo.db').as_posix()}",
    )
    # Normalize Render-style Postgres DSNs
    if raw_db_url.startswith("postgres://"):
        raw_db_url = raw_db_url.replace("postgres://", "postgresql+psycopg2://", 1)
    elif raw_db_url.startswith("postgresql://") and "+psycopg2" not in raw_db_url:
        raw_db_url = raw_db_url.replace("postgresql://", "postgresql+psycopg2://", 1)
    DATABASE_URL: str = raw_db_url

    # Answer Keys
    KEYS_DIR: Path = Path(os.getenv("OVO_KEYS_DIR", PROJECT_ROOT / "sheets" / "Keys"))
    KEY_SET_A_PATH: Path = Path(os.getenv("OVO_KEY_SET_A", KEYS_DIR / "KeySetA.csv"))
    KEY_SET_B_PATH: Path = Path(os.getenv("OVO_KEY_SET_B", KEYS_DIR / "KeySetB.csv"))

    # API
    ALLOWED_ORIGINS: list[str] = (
        os.getenv("OVO_ALLOWED_ORIGINS", "http://localhost:8501,http://127.0.0.1:8501")
        .split(",")
    )


settings = Settings()


