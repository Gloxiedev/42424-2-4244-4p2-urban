import time
from collections import deque
from typing import Dict

_message_history: Dict[int, deque] = {}
_warned_users: Dict[int, float] = {}

WINDOW_SECONDS = 5
MAX_MESSAGES = 6
LINK_PATTERNS = ["http://", "https://", ".com/", ".gg/", "discord.gg/"]

PHISHING_KEYWORDS = [
    "free nitro", "steam gift", "click here", "claim your",
    "bit.ly", "tinyurl", "adf.ly", "ow.ly",
]


def is_spam(discord_id: int, content: str) -> bool:
    now = time.time()
    if discord_id not in _message_history:
        _message_history[discord_id] = deque()

    hist = _message_history[discord_id]
    hist.append(now)

    while hist and now - hist[0] > WINDOW_SECONDS:
        hist.popleft()

    return len(hist) > MAX_MESSAGES


def is_phishing(content: str) -> bool:
    lower = content.lower()
    has_link = any(p in lower for p in LINK_PATTERNS)
    has_keyword = any(k in lower for k in PHISHING_KEYWORDS)
    return has_link and has_keyword


def is_in_cooldown(discord_id: int) -> bool:
    last = _warned_users.get(discord_id, 0)
    return time.time() - last < 30


def set_cooldown(discord_id: int):
    _warned_users[discord_id] = time.time()


def clear_history(discord_id: int):
    _message_history.pop(discord_id, None)
