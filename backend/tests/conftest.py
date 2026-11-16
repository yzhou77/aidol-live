import random

import pytest

from app.config import Settings
from app.fans import FanStore
from app.llm import MockProvider
from app.personas import DEFAULT_ANCHORS, DEFAULT_GIFTS
from app.room import Room


class FakeClock:
    def __init__(self, start: float = 1000.0) -> None:
        self.now = start

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


class Inbox:
    """Collects events sent to one viewer."""

    def __init__(self) -> None:
        self.events: list[dict] = []

    async def __call__(self, event: dict) -> None:
        self.events.append(event)

    def of(self, kind: str) -> list[dict]:
        return [e for e in self.events if e["type"] == kind]


@pytest.fixture
def clock() -> FakeClock:
    return FakeClock()


@pytest.fixture
def settings() -> Settings:
    return Settings(starting_coins=2000, pk_duration_s=60, idle_after_s=20, auto_pk_every_s=0)


@pytest.fixture
def fans(settings: Settings):
    store = FanStore(":memory:", starting_coins=settings.starting_coins)
    yield store
    store.close()


@pytest.fixture
def room(fans: FanStore, settings: Settings, clock: FakeClock) -> Room:
    return Room(
        "test",
        DEFAULT_ANCHORS,
        DEFAULT_GIFTS,
        MockProvider(seed=1),
        fans,
        settings,
        clock=clock,
        rng=random.Random(1),
    )
