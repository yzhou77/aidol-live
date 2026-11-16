# AI Group Live

A live-streaming room where **every streamer is an AI**. Several AI anchors with distinct
personas share one stage: they chat with viewers, thank gifts, put on short performances,
and battle each other in timed **PK rounds** where viewers' (virtual) gifts decide the winner.
Anchors remember returning fans and greet them by what they talked about last time.

> All gifts use virtual coins only. No real payments are involved, and every host is clearly labeled as AI.

## Features (v0.1)

| Area | What works today |
| --- | --- |
| Multi-anchor stage | 4 original personas, each with its own voice style, catchphrase and talent |
| Chat | Viewers send danmaku; the anchor named in the message (or the quietest one) replies |
| Gifts | 5 gift tiers paid with virtual coins; big gifts trigger a performance |
| PK battles | Two anchors, countdown, live score bar, winner/loser lines, MVP fan |
| Fan memory | SQLite-backed wallet, visit count, last message, favorite anchor, leaderboard |
| Idle engine | Anchors make small talk or perform when the room goes quiet; optional auto-PK |
| Voice | Browser text-to-speech (Web Speech API) with per-anchor pitch/rate |
| LLM | Pluggable: offline mock (default) or any OpenAI-compatible endpoint, with fallback |
| Safety | AI disclosure in UI and prompt; prompts forbid pressuring viewers to spend |

## Architecture

```
 Angular 19 (signals, standalone)            FastAPI (Python 3.11+)
┌──────────────────────────────┐   WS    ┌──────────────────────────────────────┐
│ LiveRoomService  ◄───────────┼────────►│ /ws/rooms/{id}  →  Room engine        │
│  - signals: anchors, pk, feed│  JSON   │   ├─ PKBattle (pure, clock-injected) │
│ SpeechService (Web Speech)   │ events  │   ├─ FanStore (SQLite)               │
│ AnchorCard / PkBar / Chat /  │         │   ├─ LineProvider (Mock | OpenAI)    │
│ GiftBar components           │         │   └─ run(): 1s tick → PK, idle talk  │
└──────────────────────────────┘         └──────────────────────────────────────┘
```

* The **Room** engine is transport-agnostic: each viewer is just an async `send(event)`
  callable, so the same code runs behind WebSockets and in unit tests.
* Time is injected (`clock`), so PK countdowns and idle timers are tested without sleeping.
* Persona prompts stay server-side; the client only receives public anchor fields.

### WebSocket protocol

Client → server: `join {fan}`, `chat {text}`, `gift {anchorId, giftId, count}`,
`start_pk {anchorA, anchorB}`

Server → client: `state`, `speech {anchorId, kind, text}`, `chat`, `gift`, `wallet`,
`leaderboard`, `pk`, `pk_end {winner, mvp}`, `viewers`, `system`, `error`

## Getting started

**Backend**

```bash
cd backend
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt
cp .env.example .env        # Windows: copy .env.example .env
pytest -q
uvicorn app.main:app --reload --port 8000
```

Without an API key the anchors use built-in offline lines, so everything runs out of the box.
To use a real model, set `LLM_PROVIDER=openai` and `LLM_API_KEY` in `backend/.env`;
any OpenAI-compatible service works by also setting `LLM_BASE_URL` and `LLM_MODEL`.

**Frontend**

```bash
cd frontend
npm install
npm start                   # http://localhost:4200, proxies /api and /ws to :8000
```

Open two browser windows with different nicknames to see multi-viewer behaviour.

## Roadmap

- [ ] Stream LLM tokens so anchors start speaking sooner
- [ ] Anchor-to-anchor banter (two AIs riffing on each other during PK)
- [ ] Server-side neural TTS with per-anchor voices; lip-sync
- [ ] Live2D / animated avatars instead of SVG faces
- [ ] Fan levels and fan clubs built on the support history
- [ ] Content moderation layer for incoming chat
- [ ] Multiple rooms, room lobby, PK history persistence
- [ ] Auth, rate limiting, Docker compose, load test for many concurrent viewers

## Project layout

```
backend/
  app/        config, models, personas, pk, fans, llm, room, main (FastAPI)
  tests/      pytest suite for PK, fan store, room engine and prompts
frontend/
  src/app/    services (WebSocket room state, speech) and UI components
```

## License

MIT
