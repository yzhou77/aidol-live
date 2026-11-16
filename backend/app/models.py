"""Core domain models shared by the room engine, providers and API layer."""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Any


@dataclass(frozen=True)
class VoiceStyle:
    """Hints for browser-side text-to-speech (Web Speech API)."""

    pitch: float = 1.0
    rate: float = 1.0


@dataclass(frozen=True)
class Anchor:
    """An AI streamer with a fixed persona."""

    id: str
    name: str
    persona: str  # one-paragraph character description fed to the LLM
    talent: str  # what this anchor "performs" (sing / jokes / poems ...)
    catchphrase: str
    color: str  # UI accent color
    voice: VoiceStyle = field(default_factory=VoiceStyle)

    def public(self) -> dict[str, Any]:
        data = asdict(self)
        data.pop("persona")
        return data


@dataclass(frozen=True)
class Gift:
    id: str
    name: str
    emoji: str
    value: int  # price in virtual coins == PK points

    def public(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class Fan:
    name: str
    coins: int
    total_spent: int = 0
    visits: int = 0
    last_message: str | None = None

    @property
    def is_returning(self) -> bool:
        return self.visits > 1


class LineKind(str, Enum):
    """Why an anchor is speaking. Providers use this to pick tone/template."""

    GREET = "greet"  # a viewer entered the room
    REPLY = "reply"  # answering a chat message
    THANKS = "thanks"  # thanking a gift
    PERFORM = "perform"  # doing a short show (triggered by big gifts / idle time)
    IDLE = "idle"  # keeping the room warm when nobody talks
    PK_START = "pk_start"
    PK_WIN = "pk_win"
    PK_LOSE = "pk_lose"  # accepting the (harmless) PK penalty
    PK_TIE = "pk_tie"


@dataclass
class LineRequest:
    """Everything a provider needs to write one line for one anchor."""

    anchor: Anchor
    kind: LineKind
    fan: Fan | None = None
    message: str | None = None
    gift: Gift | None = None
    gift_count: int = 1
    opponent: Anchor | None = None
    recent_chat: list[str] = field(default_factory=list)
