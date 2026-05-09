"""
Helper Functions
"""

import re
from datetime import datetime
from typing import Optional, Tuple

from telegram import Message, Update, User


def mention_user(user: User) -> str:
    """User ka markdown mention banao"""
    name = user.full_name or user.username or str(user.id)
    return f"[{name}](tg://user?id={user.id})"


def extract_user_and_reason(message: Message) -> Tuple[Optional[User], str]:
    """Reply ya mention se user aur reason nikalo"""
    target_user = None
    reason = ""

    if message.reply_to_message:
        target_user = message.reply_to_message.from_user
        args = message.text.split(None, 1)
        reason = args[1] if len(args) > 1 else "No reason given"

    elif message.entities:
        for entity in message.entities:
            if entity.type == "mention":
                username = message.text[entity.offset + 1: entity.offset + entity.length]
                # Username se user dhundo - limitation hai, mostly reply use karo
                reason = message.text.split(None, 2)
                reason = reason[2] if len(reason) > 2 else "No reason given"
                break
    return target_user, reason


def parse_time(time_str: str) -> Optional[int]:
    """
    Time string parse karo seconds mein.
    Examples: '10m', '2h', '1d', '30s'
    """
    units = {"s": 1, "m": 60, "h": 3600, "d": 86400}
    match = re.match(r"^(\d+)([smhd])$", time_str.lower())
    if not match:
        return None
    value, unit = int(match.group(1)), match.group(2)
    return value * units[unit]


def format_duration(seconds: int) -> str:
    """Seconds ko human-readable format mein convert karo"""
    if seconds < 60:
        return f"{seconds} second"
    elif seconds < 3600:
        return f"{seconds // 60} minute"
    elif seconds < 86400:
        return f"{seconds // 3600} ghante"
    else:
        return f"{seconds // 86400} din"


def is_url(text: str) -> bool:
    """Check karo text mein URL hai ya nahi"""
    url_pattern = re.compile(
        r"(https?://|www\.|t\.me/|telegram\.me/|bit\.ly/|tinyurl\.com/)",
        re.IGNORECASE
    )
    return bool(url_pattern.search(text))


def chunk_text(text: str, max_len: int = 4096) -> list:
    """Lambe text ko chunks mein todna"""
    return [text[i:i+max_len] for i in range(0, len(text), max_len)]


def escape_markdown(text: str) -> str:
    """Telegram Markdown ke special chars escape karo"""
    special_chars = r"\_*[]()~`>#+-=|{}.!"
    for char in special_chars:
        text = text.replace(char, f"\\{char}")
    return text


def format_user_info(user: User) -> str:
    """User ka nicely formatted info"""
    lines = [
        f"👤 **User Info**",
        f"├ ID: `{user.id}`",
        f"├ Naam: {user.full_name}",
    ]
    if user.username:
        lines.append(f"├ Username: @{user.username}")
    if user.is_bot:
        lines.append(f"└ Type: 🤖 Bot")
    else:
        lines.append(f"└ Type: 👤 Human")
    return "\n".join(lines)
