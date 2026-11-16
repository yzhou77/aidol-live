"""Line generators for AI anchors.

* MockProvider    - offline, template-based; used in tests and when no API key.
* OpenAIProvider  - any OpenAI-compatible /chat/completions endpoint
                    (OpenAI, DeepSeek, Qwen/DashScope compatible mode, local
                    vLLM/Ollama ...). Falls back to the mock on any error so the
                    live room never goes silent.
"""

from __future__ import annotations

import asyncio
import json
import logging
import random
import urllib.error
import urllib.request
from typing import Protocol

from .config import Settings
from .models import LineKind, LineRequest

log = logging.getLogger(__name__)

MAX_LINE_CHARS = 240


class LineProvider(Protocol):
    async def generate(self, req: LineRequest) -> str: ...


def _clean(text: str) -> str:
    text = " ".join(text.strip().strip('"“”').split())
    return text[:MAX_LINE_CHARS]


# ---------------------------------------------------------------------------
# Mock provider
# ---------------------------------------------------------------------------

_TEMPLATES: dict[LineKind, list[str]] = {
    LineKind.GREET: [
        "Welcome to the stream, {fan}! {catch}",
        "{fan} is here! Grab a seat, today's show is a good one!",
    ],
    LineKind.REPLY: [
        "{fan} says \"{msg}\" - great question, let me think about that!",
        "Haha {fan}, \"{msg}\" - I'm going to remember that one.",
        "Got your message, {fan}! \"{msg}\" - what does everyone else think?",
    ],
    LineKind.THANKS: [
        "Thank you {fan} for the {count}x {gift}! {catch}",
        "Wow, {fan} sent a {gift}! Thank you, that means a lot!",
    ],
    LineKind.PERFORM: [
        "To thank {fan}, I'm going to {talent} - here we go!",
        "{fan} is being so awesome, so let me {talent}!",
    ],
    LineKind.IDLE: [
        "How is everyone's day going? Tell me in the chat!",
        "{catch} Anyone want me to {talent}?",
        "New here? Mention my name in the chat and I'll answer you.",
    ],
    LineKind.PK_START: [
        "PK time! {opponent}, I'm not going easy on you this round!",
        "The PK with {opponent} is on - is everyone ready? {catch}",
    ],
    LineKind.PK_WIN: [
        "We won! Thanks to everyone who supported me. {opponent}, rematch soon!",
        "That round is ours! {catch}",
    ],
    LineKind.PK_LOSE: [
        "A deal is a deal - I lost, so here's my penalty: I'll {talent}.",
        "{opponent} got me this time, but I'll be back! Penalty first - I'll {talent}.",
    ],
    LineKind.PK_TIE: [
        "It's a tie! {opponent} and I are evenly matched. Great job, everyone!",
    ],
}

_RETURNING_GREETS = [
    "{fan}, my old friend is back! Last time you said \"{last}\" - I remember!",
    "Welcome back, {fan}! Long time no see, how have you been?",
]


# Short original "shows" so offline mode still feels like a performance.
_SHOWS: dict[str, list[str]] = {
    "lulu": [
        "~ Chat lights up like stars on my screen, with you here I'm never alone ~",
        "~ The air tastes a little sweeter today, because you clicked on my stream ~",
    ],
    "jay": [
        "I dieted for three days and lost three pounds - of photos from my phone.",
        "My boss says I work like a snail. At least I bring my own house to the office.",
    ],
    "luna": [
        "The night is long, the lamp is warm, and I keep your words in the moonlight.",
        "Clouds never rush and the wind is never late; slow travelers still arrive.",
    ],
    "max": [
        "Rough early game, stable mid game, huge late-game comeback - MVP goes to chat!",
        "Ping 999, single-digit FPS, but my hype meter is maxed out!",
    ],
}


class MockProvider:
    def __init__(self, seed: int | None = None) -> None:
        self._rng = random.Random(seed)

    async def generate(self, req: LineRequest) -> str:
        line = self._template_line(req)
        if req.kind in (LineKind.PERFORM, LineKind.PK_LOSE) and req.anchor.id in _SHOWS:
            line = f"{line} {self._rng.choice(_SHOWS[req.anchor.id])}"
        return _clean(line)

    def _template_line(self, req: LineRequest) -> str:
        templates = _TEMPLATES[req.kind]
        if req.kind is LineKind.GREET and req.fan and req.fan.is_returning:
            templates = _RETURNING_GREETS if req.fan.last_message else _RETURNING_GREETS[1:]
        tpl = self._rng.choice(templates)
        return tpl.format(
            fan=req.fan.name if req.fan else "friend",
            msg=(req.message or "")[:40],
            last=(req.fan.last_message or "")[:30] if req.fan else "",
            gift=req.gift.name if req.gift else "gift",
            count=req.gift_count,
            catch=req.anchor.catchphrase,
            talent=req.anchor.talent,
            opponent=req.opponent.name if req.opponent else "my opponent",
        )


# ---------------------------------------------------------------------------
# OpenAI-compatible provider
# ---------------------------------------------------------------------------

_GUARDRAILS = (
    "Rules: 1) You are an AI streamer; if asked, say honestly that you are an AI. "
    "2) Never pressure or hint that viewers should spend money, and never treat viewers "
    "differently based on how much they give. "
    "3) If a viewer seems down, respond kindly and, if needed, suggest reaching out to "
    "people they trust or a professional. "
    "4) No politics, sexual content or violence. "
    "5) Output only what you say out loud, casual spoken English, at most 40 words."
)

_TASKS: dict[LineKind, str] = {
    LineKind.GREET: "Viewer {fan} just joined the stream. {memory}Greet them warmly.",
    LineKind.REPLY: "Viewer {fan} wrote in chat: \"{msg}\". {memory}Respond to them.",
    LineKind.THANKS: "Viewer {fan} sent {count}x {gift}. Thank them sincerely and briefly.",
    LineKind.PERFORM: "To thank {fan}, {talent} right now (original and short).",
    LineKind.IDLE: "The chat has been quiet for a while. Bring up a topic naturally.",
    LineKind.PK_START: "Your gift PK battle against {opponent} just started. Say a fun opening line.",
    LineKind.PK_WIN: "You won the PK against {opponent}. Thank everyone and show respect to your opponent.",
    LineKind.PK_LOSE: "You lost the PK against {opponent}. Accept the penalty lightheartedly: {talent}.",
    LineKind.PK_TIE: "Your PK against {opponent} ended in a tie. Say a closing line.",
}


def build_messages(req: LineRequest) -> list[dict[str, str]]:
    a = req.anchor
    system = (
        f"You are \"{a.name}\", an AI host in a group live stream. Persona: {a.persona} "
        f"Catchphrase: \"{a.catchphrase}\". Talent: {a.talent}. {_GUARDRAILS}"
    )
    memory = ""
    if req.fan and req.fan.is_returning:
        memory = f"(Returning viewer, visit #{req.fan.visits}"
        if req.fan.last_message:
            memory += f"; last time they said \"{req.fan.last_message[:40]}\""
        memory += ".) "
    task = _TASKS[req.kind].format(
        fan=req.fan.name if req.fan else "a viewer",
        msg=req.message or "",
        memory=memory,
        gift=req.gift.name if req.gift else "gift",
        count=req.gift_count,
        talent=a.talent,
        opponent=req.opponent.name if req.opponent else "your opponent",
    )
    context = ""
    if req.recent_chat:
        context = "Recent chat:\n" + "\n".join(req.recent_chat[-8:]) + "\n\n"
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": context + task},
    ]


class OpenAIProvider:
    def __init__(self, settings: Settings, fallback: LineProvider | None = None) -> None:
        self.base_url = settings.llm_base_url
        self.api_key = settings.llm_api_key
        self.model = settings.llm_model
        self.timeout = settings.llm_timeout_s
        self.fallback = fallback or MockProvider()

    def _post(self, messages: list[dict[str, str]]) -> str:
        body = json.dumps(
            {"model": self.model, "messages": messages, "temperature": 0.9, "max_tokens": 150}
        ).encode()
        req = urllib.request.Request(
            f"{self.base_url}/chat/completions",
            data=body,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=self.timeout) as resp:
            data = json.loads(resp.read())
        return data["choices"][0]["message"]["content"]

    async def generate(self, req: LineRequest) -> str:
        try:
            text = await asyncio.to_thread(self._post, build_messages(req))
            text = _clean(text)
            if text:
                return text
        except (urllib.error.URLError, TimeoutError, KeyError, IndexError, ValueError) as exc:
            log.warning("LLM call failed, using fallback: %s", exc)
        return await self.fallback.generate(req)


def make_provider(settings: Settings) -> LineProvider:
    if settings.llm_provider == "openai" and settings.llm_api_key:
        return OpenAIProvider(settings)
    if settings.llm_provider == "openai":
        log.warning("LLM_PROVIDER=openai but LLM_API_KEY is empty; using mock provider")
    return MockProvider()
