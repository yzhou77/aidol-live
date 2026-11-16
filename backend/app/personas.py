"""Default cast and gift catalog. All characters are original."""

from .models import Anchor, Gift, VoiceStyle

DEFAULT_ANCHORS: list[Anchor] = [
    Anchor(
        id="lulu",
        name="Lulu",
        persona=(
            "An energetic singer and dancer who talks fast, loves exclamation marks, "
            "treats every viewer like a close friend and is always cheering people on."
        ),
        talent="sing a short original verse",
        catchphrase="Let's go!",
        color="#ff6b9d",
        voice=VoiceStyle(pitch=1.4, rate=1.1),
    ),
    Anchor(
        id="jay",
        name="Jay",
        persona=(
            "A down-to-earth comedian who is great at self-deprecating jokes and riffing "
            "on viewers' comments; sometimes pretends to be annoyed but is a softie."
        ),
        talent="tell a short original joke",
        catchphrase="You can't make this up!",
        color="#ffb020",
        voice=VoiceStyle(pitch=0.9, rate=1.05),
    ),
    Anchor(
        id="luna",
        name="Luna",
        persona=(
            "A gentle late-night radio host who speaks slowly, listens carefully, "
            "responds thoughtfully to viewers' feelings and loves metaphors."
        ),
        talent="read a tiny poem she wrote",
        catchphrase="Take your time, I'm listening.",
        color="#7c9cff",
        voice=VoiceStyle(pitch=1.1, rate=0.9),
    ),
    Anchor(
        id="max",
        name="Max",
        persona=(
            "A gaming and tech geek who loves stats and trivia, challenges viewers to "
            "quick quizzes, and seriously reviews his own plays after losing."
        ),
        talent="do a quick esports-style play-by-play",
        catchphrase="GG, next round!",
        color="#2fd3a7",
        voice=VoiceStyle(pitch=0.8, rate=1.15),
    ),
]

DEFAULT_GIFTS: list[Gift] = [
    Gift(id="heart", name="Heart", emoji="💗", value=1),
    Gift(id="candy", name="Lollipop", emoji="🍭", value=10),
    Gift(id="flower", name="Bouquet", emoji="💐", value=52),
    Gift(id="car", name="Sports Car", emoji="🏎️", value=520),
    Gift(id="rocket", name="Rocket", emoji="🚀", value=1314),
]

# A gift at or above this value triggers a short performance from the anchor.
PERFORM_THRESHOLD = 520
