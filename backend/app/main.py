"""FastAPI entry point: REST for read-only data, one WebSocket per viewer.

Run:  uvicorn app.main:app --reload --port 8000   (from the backend/ folder)
"""

from __future__ import annotations

import asyncio
import json
import logging
import uuid
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect

from .config import Settings
from .fans import FanStore
from .llm import make_provider
from .personas import DEFAULT_ANCHORS, DEFAULT_GIFTS
from .room import Room, RoomError

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("ai-group-live")

DEFAULT_ROOM = "main"
rooms: dict[str, Room] = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = Settings.from_env()
    fans = FanStore(settings.db_path, starting_coins=settings.starting_coins)
    room = Room(
        DEFAULT_ROOM,
        DEFAULT_ANCHORS,
        DEFAULT_GIFTS,
        make_provider(settings),
        fans,
        settings,
    )
    rooms[DEFAULT_ROOM] = room
    task = asyncio.create_task(room.run())
    log.info("room '%s' started with provider=%s", DEFAULT_ROOM, settings.llm_provider)
    try:
        yield
    finally:
        task.cancel()
        fans.close()
        rooms.clear()


app = FastAPI(title="AI Group Live", version="0.1.0", lifespan=lifespan)


def get_room(room_id: str) -> Room:
    room = rooms.get(room_id)
    if room is None:
        raise HTTPException(status_code=404, detail="room not found")
    return room


@app.get("/api/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/rooms/{room_id}")
async def room_state(room_id: str) -> dict[str, Any]:
    return get_room(room_id).snapshot()


async def dispatch(room: Room, conn_id: str, msg: dict[str, Any]) -> None:
    kind = msg.get("type")
    if kind == "chat":
        await room.chat(conn_id, str(msg.get("text", "")))
    elif kind == "gift":
        await room.gift(
            conn_id,
            str(msg.get("anchorId", "")),
            str(msg.get("giftId", "")),
            int(msg.get("count", 1)),
        )
    elif kind == "start_pk":
        await room.start_pk(str(msg.get("anchorA", "")), str(msg.get("anchorB", "")))
    else:
        raise RoomError(f"Unknown message type: {kind}")


@app.websocket("/ws/rooms/{room_id}")
async def room_socket(websocket: WebSocket, room_id: str) -> None:
    room = rooms.get(room_id)
    await websocket.accept()
    if room is None:
        await websocket.close(code=4404)
        return

    conn_id = uuid.uuid4().hex
    joined = False
    try:
        while True:
            raw = await websocket.receive_text()
            try:
                msg = json.loads(raw)
                if not isinstance(msg, dict):
                    raise ValueError("message must be an object")
                if not joined:
                    if msg.get("type") != "join":
                        raise RoomError("Please join the room first")
                    await room.join(conn_id, str(msg.get("fan", "")), websocket.send_json)
                    joined = True
                else:
                    await dispatch(room, conn_id, msg)
            except RoomError as err:
                await websocket.send_json({"type": "error", "message": str(err)})
            except (TypeError, ValueError):
                await websocket.send_json({"type": "error", "message": "Malformed message"})
    except WebSocketDisconnect:
        pass
    finally:
        await room.leave(conn_id)
