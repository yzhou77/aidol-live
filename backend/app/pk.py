"""PK battle: two anchors compete for gift points within a fixed time window.

Pure logic with an injected clock so it can be unit-tested without sleeping.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class PKBattle:
    anchor_a: str
    anchor_b: str
    started_at: float
    duration_s: float
    scores: dict[str, int] = field(default_factory=dict)
    # per-anchor contributor totals, used to name the MVP fan
    contributors: dict[str, dict[str, int]] = field(default_factory=dict)
    finished: bool = False

    def __post_init__(self) -> None:
        if self.anchor_a == self.anchor_b:
            raise ValueError("PK needs two different anchors")
        for a in (self.anchor_a, self.anchor_b):
            self.scores.setdefault(a, 0)
            self.contributors.setdefault(a, {})

    @property
    def participants(self) -> tuple[str, str]:
        return self.anchor_a, self.anchor_b

    def remaining(self, now: float) -> int:
        return max(0, int(round(self.started_at + self.duration_s - now)))

    def is_over(self, now: float) -> bool:
        return now >= self.started_at + self.duration_s

    def add_points(self, anchor_id: str, fan: str, points: int, now: float) -> bool:
        """Credit points to an anchor. Returns False if not counted."""
        if self.finished or self.is_over(now) or anchor_id not in self.scores:
            return False
        if points <= 0:
            return False
        self.scores[anchor_id] += points
        bucket = self.contributors[anchor_id]
        bucket[fan] = bucket.get(fan, 0) + points
        return True

    def winner(self) -> str | None:
        """Winning anchor id, or None for a tie."""
        a, b = self.anchor_a, self.anchor_b
        if self.scores[a] == self.scores[b]:
            return None
        return a if self.scores[a] > self.scores[b] else b

    def loser(self) -> str | None:
        w = self.winner()
        if w is None:
            return None
        return self.anchor_b if w == self.anchor_a else self.anchor_a

    def mvp(self, anchor_id: str) -> str | None:
        bucket = self.contributors.get(anchor_id) or {}
        if not bucket:
            return None
        return max(bucket.items(), key=lambda kv: kv[1])[0]

    def snapshot(self, now: float) -> dict[str, Any]:
        return {
            "anchorA": self.anchor_a,
            "anchorB": self.anchor_b,
            "scores": dict(self.scores),
            "remaining": self.remaining(now),
            "duration": int(self.duration_s),
            "finished": self.finished,
        }
