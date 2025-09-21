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
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        f"sqlite:///{(PROJECT_ROOT / 'ovo.db').as_posix()}",
    )

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


