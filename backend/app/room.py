"""The live room engine.

A Room owns the cast of AI anchors, the connected viewers, the PK battle and
the idle-chatter loop. It is transport-agnostic: each viewer is registered with
an async ``send(event: dict)`` callable, so the same engine works behind
WebSockets in production and behind a list collector in tests.
"""

from __future__ import annotations

import asyncio
import logging
import random
import time
from collections import deque
from dataclasses import dataclass
from typing import Any, Awaitable, Callable

from .config import Settings
from .fans import FanStore, InsufficientCoins
from .llm import LineProvider
from .models import Anchor, Fan, Gift, LineKind, LineRequest
from .personas import PERFORM_THRESHOLD
from .pk import PKBattle

log = logging.getLogger(__name__)

Send = Callable[[dict[str, Any]], Awaitable[None]]

MAX_NAME_LEN = 16
MAX_CHAT_LEN = 100
MAX_GIFT_COUNT = 99


class RoomError(Exception):
    """A user-facing validation error."""


@dataclass
class Viewer:
    name: str
    send: Send


class Room:
    def __init__(
        self,
        room_id: str,
        anchors: list[Anchor],
        gifts: list[Gift],
        provider: LineProvider,
        fans: FanStore,
        settings: Settings,
        clock: Callable[[], float] = time.monotonic,
        rng: random.Random | None = None,
    ) -> None:
        if len(anchors) < 2:
            raise ValueError("a group live room needs at least two anchors")
        self.room_id = room_id
        self.anchors = {a.id: a for a in anchors}
        self.gifts = {g.id: g for g in gifts}
        self.provider = provider
        self.fans = fans
        self.settings = settings
        self.clock = clock
        self.rng = rng or random.Random()

        self.viewers: dict[str, Viewer] = {}
        self.recent_chat: deque[str] = deque(maxlen=20)
        self.popularity: dict[str, int] = {a.id: 0 for a in anchors}
        self.last_spoke: dict[str, float] = {a.id: 0.0 for a in anchors}
        now = clock()
        self.last_activity = now
        self.last_pk_end = now
        self.pk: PKBattle | None = None

    # ------------------------------------------------------------------ io
    async def _send(self, viewer: Viewer, event: dict[str, Any]) -> bool:
        try:
            await viewer.send(event)
            return True
        except Exception:  # connection already gone
            return False

    async def broadcast(self, event: dict[str, Any]) -> None:
        dead = []
        for conn_id, viewer in list(self.viewers.items()):
            if not await self._send(viewer, event):
                dead.append(conn_id)
        for conn_id in dead:
            self.viewers.pop(conn_id, None)

    def snapshot(self) -> dict[str, Any]:
        now = self.clock()
        return {
            "type": "state",
            "roomId": self.room_id,
            "anchors": [a.public() for a in self.anchors.values()],
            "gifts": [g.public() for g in self.gifts.values()],
            "pk": self.pk.snapshot(now) if self.pk else None,
            "viewers": len(self.viewers),
            "popularity": dict(self.popularity),
            "leaderboard": self.fans.leaderboard(),
        }

    # -------------------------------------------------------------- speech
    async def speak(self, anchor: Anchor, req: LineRequest) -> str:
        req.recent_chat = list(self.recent_chat)
        text = await self.provider.generate(req)
        now = self.clock()
        self.last_spoke[anchor.id] = now
        self.last_activity = now
        self.recent_chat.append(f"{anchor.name}: {text}")
        await self.broadcast(
            {"type": "speech", "anchorId": anchor.id, "kind": req.kind.value, "text": text}
        )
        return text

    def pick_anchor(self, text: str = "") -> Anchor:
        """Whoever is named in the message, else whoever has been quiet longest."""
        lowered = text.lower()
        for a in self.anchors.values():
            if a.name.lower() in lowered:
                return a
        quietest = min(self.last_spoke.values())
        candidates = [aid for aid, t in self.last_spoke.items() if t == quietest]
        return self.anchors[self.rng.choice(sorted(candidates))]

    # ------------------------------------------------------------- viewers
    async def join(self, conn_id: str, name: str, send: Send) -> Fan:
        name = (name or "").strip()
        if not name or len(name) > MAX_NAME_LEN:
            raise RoomError(f"Nickname must be 1-{MAX_NAME_LEN} characters")
        if any(v.name == name for v in self.viewers.values()):
            raise RoomError("That nickname is already in the room, please pick another")

        fan = self.fans.record_visit(name)
        viewer = Viewer(name=name, send=send)
        self.viewers[conn_id] = viewer
        await self._send(viewer, {**self.snapshot(), "you": _fan_public(fan)})
        await self.broadcast({"type": "system", "text": f"{name} joined the room"})
        await self.broadcast({"type": "viewers", "count": len(self.viewers)})

        fav = self.fans.favorite_anchor(name)
        # A returning supporter is greeted by the anchor they backed most.
        greeter = (self.anchors.get(fav) if fav else None) or self.pick_anchor()
        await self.speak(greeter, LineRequest(anchor=greeter, kind=LineKind.GREET, fan=fan))
        return fan

    async def leave(self, conn_id: str) -> None:
        viewer = self.viewers.pop(conn_id, None)
        if viewer:
            await self.broadcast({"type": "viewers", "count": len(self.viewers)})

    def _viewer(self, conn_id: str) -> Viewer:
        viewer = self.viewers.get(conn_id)
        if viewer is None:
            raise RoomError("Please join the room first")
        return viewer

    # ---------------------------------------------------------------- chat
    async def chat(self, conn_id: str, text: str) -> None:
        viewer = self._viewer(conn_id)
        text = (text or "").strip()[:MAX_CHAT_LEN]
        if not text:
            return
        fan = self.fans.get(viewer.name)  # read before overwriting last_message
        self.fans.record_message(viewer.name, text)
        self.recent_chat.append(f"{viewer.name}: {text}")
        self.last_activity = self.clock()
        await self.broadcast({"type": "chat", "fan": viewer.name, "text": text})

        anchor = self.pick_anchor(text)
        await self.speak(anchor, LineRequest(anchor=anchor, kind=LineKind.REPLY, fan=fan, message=text))

    # --------------------------------------------------------------- gifts
    async def gift(self, conn_id: str, anchor_id: str, gift_id: str, count: int = 1) -> None:
        viewer = self._viewer(conn_id)
        anchor = self.anchors.get(anchor_id)
        gift = self.gifts.get(gift_id)
        if anchor is None:
            raise RoomError("Unknown anchor")
        if gift is None:
            raise RoomError("Unknown gift")
        if not isinstance(count, int) or not 1 <= count <= MAX_GIFT_COUNT:
            raise RoomError(f"Gift count must be between 1 and {MAX_GIFT_COUNT}")

        total = gift.value * count
        try:
            fan = self.fans.spend(viewer.name, anchor.id, total)
        except InsufficientCoins:
            raise RoomError("Not enough virtual coins (this project uses virtual coins only, no real payments)") from None

        now = self.clock()
        self.popularity[anchor.id] += total
        self.last_activity = now
        await self._send(viewer, {"type": "wallet", "coins": fan.coins})
        await self.broadcast(
            {
                "type": "gift",
                "fan": viewer.name,
                "anchorId": anchor.id,
                "giftId": gift.id,
                "count": count,
                "value": total,
                "popularity": self.popularity[anchor.id],
            }
        )
        if self.pk and self.pk.add_points(anchor.id, viewer.name, total, now):
            await self.broadcast({"type": "pk", **self.pk.snapshot(now)})
        await self.broadcast({"type": "leaderboard", "items": self.fans.leaderboard()})

        await self.speak(
            anchor,
            LineRequest(anchor=anchor, kind=LineKind.THANKS, fan=fan, gift=gift, gift_count=count),
        )
        if gift.value >= PERFORM_THRESHOLD:
            await self.speak(anchor, LineRequest(anchor=anchor, kind=LineKind.PERFORM, fan=fan))

    # ------------------------------------------------------------------ PK
    async def start_pk(self, anchor_a: str, anchor_b: str, duration_s: int | None = None) -> PKBattle:
        if self.pk and not self.pk.finished:
            raise RoomError("A PK battle is already in progress")
        if anchor_a not in self.anchors or anchor_b not in self.anchors:
            raise RoomError("Unknown anchor")
        if anchor_a == anchor_b:
            raise RoomError("A PK battle needs two different anchors")

        now = self.clock()
        self.pk = PKBattle(
            anchor_a=anchor_a,
            anchor_b=anchor_b,
            started_at=now,
            duration_s=duration_s or self.settings.pk_duration_s,
        )
        await self.broadcast({"type": "pk", **self.pk.snapshot(now)})
        a, b = self.anchors[anchor_a], self.anchors[anchor_b]
        await self.speak(a, LineRequest(anchor=a, kind=LineKind.PK_START, opponent=b))
        await self.speak(b, LineRequest(anchor=b, kind=LineKind.PK_START, opponent=a))
        return self.pk

    async def _finish_pk(self) -> None:
        pk = self.pk
        assert pk is not None
        now = self.clock()
        pk.finished = True
        winner_id = pk.winner()
        await self.broadcast(
            {
                "type": "pk_end",
                **pk.snapshot(now),
                "winner": winner_id,
                "mvp": pk.mvp(winner_id) if winner_id else None,
            }
        )
        a, b = self.anchors[pk.anchor_a], self.anchors[pk.anchor_b]
        if winner_id is None:
            await self.speak(a, LineRequest(anchor=a, kind=LineKind.PK_TIE, opponent=b))
        else:
            winner = self.anchors[winner_id]
            loser = b if winner is a else a
            await self.speak(winner, LineRequest(anchor=winner, kind=LineKind.PK_WIN, opponent=loser))
            await self.speak(loser, LineRequest(anchor=loser, kind=LineKind.PK_LOSE, opponent=winner))
        self.pk = None
        self.last_pk_end = self.clock()

    # ---------------------------------------------------------------- loop
    async def tick(self) -> None:
        """Advance timers once. Called every second by ``run``."""
        now = self.clock()
        if self.pk and not self.pk.finished:
            if self.pk.is_over(now):
                await self._finish_pk()
            else:
                await self.broadcast({"type": "pk", **self.pk.snapshot(now)})
            return

        if not self.viewers:
            return

        auto = self.settings.auto_pk_every_s
        if auto and now - self.last_pk_end >= auto:
            a, b = self.rng.sample(sorted(self.anchors), 2)
            await self.start_pk(a, b)
            return

        if now - self.last_activity >= self.settings.idle_after_s:
            anchor = self.pick_anchor()
            kind = LineKind.PERFORM if self.rng.random() < 0.3 else LineKind.IDLE
            await self.speak(anchor, LineRequest(anchor=anchor, kind=kind))

    async def run(self) -> None:
        while True:
            try:
                await self.tick()
            except Exception:  # keep the room alive no matter what
                log.exception("room %s tick failed", self.room_id)
            await asyncio.sleep(1)


def _fan_public(fan: Fan) -> dict[str, Any]:
    return {
        "name": fan.name,
        "coins": fan.coins,
        "totalSpent": fan.total_spent,
        "visits": fan.visits,
    }
