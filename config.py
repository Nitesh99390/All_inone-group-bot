"""
Configuration - Environment variables se settings load karta hai
"""

import os
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Config:
    # ── Required ──────────────────────────────────────────────────────────────
    BOT_TOKEN: str = field(default_factory=lambda: os.environ.get("BOT_TOKEN", ""))

    # ── Optional ──────────────────────────────────────────────────────────────
    GROQ_API_KEY: str = field(
        default_factory=lambda: os.environ.get("GROQ_API_KEY", "")
    )
    GROQ_MODEL: str = field(
        default_factory=lambda: os.environ.get("GROQ_MODEL", "llama-3.3-70b-versatile")
    )
    ANTHROPIC_API_KEY: str = field(
        default_factory=lambda: os.environ.get("ANTHROPIC_API_KEY", "")
    )
    OWNER_ID: int = field(
        default_factory=lambda: int(os.environ.get("OWNER_ID", "0"))
    )
    DATABASE_PATH: str = field(
        default_factory=lambda: os.environ.get("DATABASE_PATH", "bot_data.db")
    )
    LOG_CHANNEL_ID: Optional[int] = field(
        default_factory=lambda: (
            int(os.environ.get("LOG_CHANNEL_ID"))
            if os.environ.get("LOG_CHANNEL_ID")
            else None
        )
    )

    # ── Bot Settings ──────────────────────────────────────────────────────────
    MAX_WARNINGS: int = field(
        default_factory=lambda: int(os.environ.get("MAX_WARNINGS", "3"))
    )
    FLOOD_LIMIT: int = field(
        default_factory=lambda: int(os.environ.get("FLOOD_LIMIT", "5"))
    )
    FLOOD_WINDOW: int = field(
        default_factory=lambda: int(os.environ.get("FLOOD_WINDOW", "5"))  # seconds
    )
    AI_MODEL: str = field(
        default_factory=lambda: os.environ.get("AI_MODEL", "claude-opus-4-5")
    )

    def validate(self):
        if not self.BOT_TOKEN:
            raise ValueError(
                "❌ BOT_TOKEN environment variable set nahi hai!\n"
                "Render dashboard mein Environment Variables mein add karo."
            )

    @property
    def has_groq(self) -> bool:
        return bool(self.GROQ_API_KEY)

    @property
    def has_ai(self) -> bool:
        return bool(self.GROQ_API_KEY or self.ANTHROPIC_API_KEY)

    @property
    def active_ai_provider(self) -> str:
        """Priority: Groq > Anthropic"""
        if self.GROQ_API_KEY:
            return "groq"
        if self.ANTHROPIC_API_KEY:
            return "anthropic"
        return "none"

    @property
    def has_owner(self) -> bool:
        return self.OWNER_ID != 0
