"""Runtime settings read from environment variables (see .env.example)."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def load_dotenv(path: str | Path = Path(__file__).resolve().parent.parent / ".env") -> None:
    """Minimal .env loader (KEY=VALUE lines). Real environment variables win."""
    path = Path(path)
    if not path.is_file():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def _int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, default))
    except ValueError:
        return default


@dataclass(frozen=True)
class Settings:
    # "mock" works offline; "openai" talks to any OpenAI-compatible endpoint.
    llm_provider: str = "mock"
    llm_base_url: str = "https://api.openai.com/v1"
    llm_api_key: str = ""
    llm_model: str = "gpt-4o-mini"
    llm_timeout_s: int = 20

    db_path: str = "data/fans.db"
    starting_coins: int = 2000
    pk_duration_s: int = 90
    idle_after_s: int = 25  # anchors start small talk after this much silence
    auto_pk_every_s: int = 300  # 0 disables automatic PK rounds

    @classmethod
    def from_env(cls) -> "Settings":
        load_dotenv()
        return cls(
            llm_provider=os.getenv("LLM_PROVIDER", "mock").lower(),
            llm_base_url=os.getenv("LLM_BASE_URL", cls.llm_base_url).rstrip("/"),
            llm_api_key=os.getenv("LLM_API_KEY", ""),
            llm_model=os.getenv("LLM_MODEL", cls.llm_model),
            llm_timeout_s=_int("LLM_TIMEOUT_S", cls.llm_timeout_s),
            db_path=os.getenv("DB_PATH", cls.db_path),
            starting_coins=_int("STARTING_COINS", cls.starting_coins),
            pk_duration_s=_int("PK_DURATION_S", cls.pk_duration_s),
            idle_after_s=_int("IDLE_AFTER_S", cls.idle_after_s),
            auto_pk_every_s=_int("AUTO_PK_EVERY_S", cls.auto_pk_every_s),
        )
