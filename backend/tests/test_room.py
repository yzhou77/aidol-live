import asyncio

import pytest

from app.llm import build_messages
from app.models import LineKind, LineRequest
from app.personas import DEFAULT_ANCHORS
from app.room import RoomError

from .conftest import Inbox


def run(coro):
    return asyncio.run(coro)


def test_join_sends_state_and_greeting(room):
    inbox = Inbox()
    run(room.join("c1", "Alice", inbox))
    state = inbox.of("state")[0]
    assert state["you"]["coins"] == 2000
    assert len(state["anchors"]) == 4
    assert "persona" not in state["anchors"][0]  # prompts stay server-side
    speech = inbox.of("speech")
    assert speech and speech[0]["kind"] == "greet"
    assert "Alice" in speech[0]["text"]


def test_duplicate_or_bad_names_rejected(room):
    run(room.join("c1", "Alice", Inbox()))
    with pytest.raises(RoomError):
        run(room.join("c2", "Alice", Inbox()))
    with pytest.raises(RoomError):
        run(room.join("c3", "   ", Inbox()))
    with pytest.raises(RoomError):
        run(room.join("c4", "x" * 17, Inbox()))


def test_chat_naming_an_anchor_gets_that_anchor(room):
    inbox = Inbox()
    run(room.join("c1", "Alice", inbox))
    run(room.chat("c1", "Hi Luna, I am a bit tired today"))
    assert inbox.of("chat")[-1] == {"type": "chat", "fan": "Alice", "text": "Hi Luna, I am a bit tired today"}
    reply = inbox.of("speech")[-1]
    assert reply["kind"] == "reply" and reply["anchorId"] == "luna"


def test_chat_requires_join(room):
    with pytest.raises(RoomError):
        run(room.chat("nobody", "hi"))


def test_gift_deducts_coins_and_thanks(room):
    inbox = Inbox()
    run(room.join("c1", "Alice", inbox))
    run(room.gift("c1", "jay", "flower", 2))
    assert inbox.of("wallet")[-1]["coins"] == 2000 - 104
    gift = inbox.of("gift")[-1]
    assert gift["value"] == 104 and gift["anchorId"] == "jay"
    assert inbox.of("speech")[-1]["kind"] == "thanks"
    assert inbox.of("leaderboard")[-1]["items"] == [{"name": "Alice", "total": 104}]


def test_big_gift_triggers_performance(room):
    inbox = Inbox()
    run(room.join("c1", "Alice", inbox))
    run(room.gift("c1", "lulu", "car", 1))
    kinds = [e["kind"] for e in inbox.of("speech")]
    assert kinds[-2:] == ["thanks", "perform"]


def test_gift_validation(room):
    run(room.join("c1", "Alice", Inbox()))
    for args in [("nope", "heart", 1), ("lulu", "nope", 1), ("lulu", "heart", 0), ("lulu", "heart", 100)]:
        with pytest.raises(RoomError):
            run(room.gift("c1", *args))
    with pytest.raises(RoomError):
        run(room.gift("c1", "lulu", "rocket", 2))  # 2628 > 2000 coins


def test_full_pk_round(room, clock):
    a, b = Inbox(), Inbox()
    run(room.join("c1", "Alice", a))
    run(room.join("c2", "Bob", b))
    run(room.start_pk("lulu", "jay"))
    with pytest.raises(RoomError):
        run(room.start_pk("luna", "max"))  # one PK at a time

    run(room.gift("c1", "lulu", "candy", 3))  # 30
    run(room.gift("c2", "jay", "flower", 1))  # 52
    run(room.gift("c1", "luna", "flower", 1))  # not in PK -> no points
    assert room.pk.scores == {"lulu": 30, "jay": 52}

    clock.advance(30)
    run(room.tick())
    assert a.of("pk")[-1]["remaining"] == 30

    clock.advance(31)
    run(room.tick())
    end = a.of("pk_end")[-1]
    assert end["winner"] == "jay" and end["mvp"] == "Bob"
    kinds = [(e["anchorId"], e["kind"]) for e in a.of("speech")[-2:]]
    assert kinds == [("jay", "pk_win"), ("lulu", "pk_lose")]
    assert room.pk is None


def test_pk_tie(room, clock):
    inbox = Inbox()
    run(room.join("c1", "Alice", inbox))
    run(room.start_pk("luna", "max", duration_s=5))
    clock.advance(6)
    run(room.tick())
    assert inbox.of("pk_end")[-1]["winner"] is None
    assert inbox.of("speech")[-1]["kind"] == "pk_tie"


def test_idle_chatter_only_after_silence(room, clock):
    inbox = Inbox()
    run(room.join("c1", "Alice", inbox))
    before = len(inbox.of("speech"))
    clock.advance(10)
    run(room.tick())
    assert len(inbox.of("speech")) == before
    clock.advance(15)
    run(room.tick())
    assert len(inbox.of("speech")) == before + 1
    assert inbox.of("speech")[-1]["kind"] in {"idle", "perform"}


def test_returning_fan_greeted_by_favorite_anchor(room):
    run(room.join("c1", "Alice", Inbox()))
    run(room.gift("c1", "max", "flower", 1))
    run(room.chat("c1", "See you next time"))
    run(room.leave("c1"))

    inbox = Inbox()
    run(room.join("c1b", "Alice", inbox))
    greet = inbox.of("speech")[0]
    assert greet["anchorId"] == "max"
    assert inbox.of("state")[0]["you"]["visits"] == 2


def test_dead_connections_are_dropped(room):
    async def broken(_event):
        raise ConnectionError

    run(room.join("c1", "Alice", Inbox()))
    room.viewers["c1"].send = broken
    run(room.broadcast({"type": "system", "text": "x"}))
    assert "c1" not in room.viewers


def test_prompt_contains_persona_guardrails_and_memory(fans):
    fan = fans.record_visit("Alice")
    fans.record_message("Alice", "I am job hunting lately")
    fan = fans.record_visit("Alice")
    msgs = build_messages(
        LineRequest(anchor=DEFAULT_ANCHORS[2], kind=LineKind.GREET, fan=fan)
    )
    system, user = msgs[0]["content"], msgs[1]["content"]
    assert "Luna" in system and "AI host" in system and "Never pressure" in system
    assert "Returning viewer" in user and "I am job hunting lately" in user
