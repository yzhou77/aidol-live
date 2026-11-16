"""Fan memory backed by SQLite (stdlib only).

Stores each viewer's virtual-coin wallet, visit count, last message and how
much they have supported each anchor, so anchors can recognise returning fans.
"""

from __future__ import annotations

import sqlite3
import threading
import time
from pathlib import Path

from .models import Fan

_SCHEMA = """
CREATE TABLE IF NOT EXISTS fans (
    name          TEXT PRIMARY KEY,
    coins         INTEGER NOT NULL,
    total_spent   INTEGER NOT NULL DEFAULT 0,
    visits        INTEGER NOT NULL DEFAULT 0,
    last_message  TEXT,
    first_seen    REAL NOT NULL,
    last_seen     REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS support (
    fan        TEXT NOT NULL,
    anchor_id  TEXT NOT NULL,
    amount     INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (fan, anchor_id)
);
"""


class InsufficientCoins(Exception):
    pass


class FanStore:
    def __init__(self, db_path: str = ":memory:", starting_coins: int = 2000) -> None:
        if db_path != ":memory:":
            Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._lock = threading.Lock()
        self.starting_coins = starting_coins
        with self._lock, self._conn:
            self._conn.executescript(_SCHEMA)

    # -- helpers -------------------------------------------------------------
    @staticmethod
    def _row_to_fan(row: sqlite3.Row) -> Fan:
        return Fan(
            name=row["name"],
            coins=row["coins"],
            total_spent=row["total_spent"],
            visits=row["visits"],
            last_message=row["last_message"],
        )

    def get(self, name: str) -> Fan | None:
        with self._lock:
            row = self._conn.execute("SELECT * FROM fans WHERE name = ?", (name,)).fetchone()
        return self._row_to_fan(row) if row else None

    # -- writes --------------------------------------------------------------
    def record_visit(self, name: str) -> Fan:
        """Create the fan on first visit, otherwise bump the visit counter."""
        now = time.time()
        with self._lock, self._conn:
            self._conn.execute(
                """
                INSERT INTO fans (name, coins, visits, first_seen, last_seen)
                VALUES (?, ?, 1, ?, ?)
                ON CONFLICT(name) DO UPDATE SET visits = visits + 1, last_seen = excluded.last_seen
                """,
                (name, self.starting_coins, now, now),
            )
        fan = self.get(name)
        assert fan is not None
        return fan

    def record_message(self, name: str, text: str) -> None:
        with self._lock, self._conn:
            self._conn.execute(
                "UPDATE fans SET last_message = ?, last_seen = ? WHERE name = ?",
                (text[:200], time.time(), name),
            )

    def spend(self, name: str, anchor_id: str, amount: int) -> Fan:
        """Atomically deduct coins and credit support to an anchor."""
        if amount <= 0:
            raise ValueError("amount must be positive")
        with self._lock, self._conn:
            cur = self._conn.execute(
                """
                UPDATE fans SET coins = coins - ?, total_spent = total_spent + ?
                WHERE name = ? AND coins >= ?
                """,
                (amount, amount, name, amount),
            )
            if cur.rowcount == 0:
                raise InsufficientCoins(name)
            self._conn.execute(
                """
                INSERT INTO support (fan, anchor_id, amount) VALUES (?, ?, ?)
                ON CONFLICT(fan, anchor_id) DO UPDATE SET amount = amount + excluded.amount
                """,
                (name, anchor_id, amount),
            )
        fan = self.get(name)
        assert fan is not None
        return fan

    # -- reads ---------------------------------------------------------------
    def favorite_anchor(self, name: str) -> str | None:
        with self._lock:
            row = self._conn.execute(
                "SELECT anchor_id FROM support WHERE fan = ? ORDER BY amount DESC LIMIT 1",
                (name,),
            ).fetchone()
        return row["anchor_id"] if row else None

    def leaderboard(self, limit: int = 10) -> list[dict]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT name, total_spent FROM fans WHERE total_spent > 0 "
                "ORDER BY total_spent DESC, name LIMIT ?",
                (limit,),
            ).fetchall()
        return [{"name": r["name"], "total": r["total_spent"]} for r in rows]

    def close(self) -> None:
        self._conn.close()
