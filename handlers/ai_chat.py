"""
AI Chat Handler - Groq (primary) + Anthropic (fallback) support
"""

import logging

import httpx
from telegram import Update
from telegram.constants import ChatAction, ParseMode

from config import Config
from database.db import Database
from utils.decorators import admin_only, group_only

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """Tum ek helpful Telegram group assistant ho. Tumhara naam "Helper Bot" hai.
Tum Hinglish (Hindi + English mix) mein baat karte ho — friendly, concise aur helpful.
Group ke sawaalon ka jawab do. Agar koi technical sawaal ho toh clearly explain karo.
Jawab 200 words se kam rakho jab tak zaroorat na ho.
Kabhi bhi harmful, illegal ya offensive content mat generate karo."""

# Groq ke popular models
GROQ_MODELS = {
    "llama-3.3-70b-versatile": "Llama 3.3 70B (Default - Best)",
    "llama-3.1-8b-instant":    "Llama 3.1 8B (Fastest)",
    "mixtral-8x7b-32768":      "Mixtral 8x7B (Long context)",
    "gemma2-9b-it":            "Gemma2 9B (Google)",
}

GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
ANTHROPIC_API_URL = "https://api.anthropic.com/v1/messages"


class AIChatHandlers:
    def __init__(self, db: Database, config: Config):
        self.db = db
        self.config = config

    # ─── Commands ────────────────────────────────────────────────────────────

    async def ai_command(self, update: Update, context):
        """/ai ya /ask command handle karo"""
        if not self.config.has_ai:
            await update.message.reply_text(
                "❌ AI feature enable nahi hai!\n\n"
                "Render Dashboard → Environment Variables mein daalo:\n"
                "`GROQ_API_KEY` — groq.com/keys se free mein milega 🆓",
                parse_mode=ParseMode.MARKDOWN,
            )
            return

        text = update.message.text.split(None, 1)
        question = text[1].strip() if len(text) > 1 else ""

        if not question and update.message.reply_to_message:
            question = update.message.reply_to_message.text or ""

        if not question:
            await update.message.reply_text(
                "❓ Koi sawaal poochho!\nUsage: `/ai [sawaal]`",
                parse_mode=ParseMode.MARKDOWN,
            )
            return

        await update.effective_chat.send_action(ChatAction.TYPING)

        try:
            answer, provider = await self._call_ai(question)
            provider_badge = "⚡ Groq" if provider == "groq" else "🧠 Claude"
            await update.message.reply_text(
                f"{provider_badge} *AI Answer:*\n\n{answer}",
                parse_mode=ParseMode.MARKDOWN,
            )
        except Exception as e:
            logger.error(f"AI error: {e}")
            await update.message.reply_text(
                "❌ AI se jawab nahi aaya. Thodi der baad try karo."
            )

    async def ai_models_command(self, update: Update, context):
        """/aimodels — available models dikhao"""
        provider = self.config.active_ai_provider
        if provider == "groq":
            current = self.config.GROQ_MODEL
            text = f"⚡ *Groq Models* (current: `{current}`)\n\n"
            for model, desc in GROQ_MODELS.items():
                tick = "✅ " if model == current else "▸ "
                text += f"{tick}`{model}`\n  _{desc}_\n\n"
            text += "Change karne ke liye `GROQ_MODEL` env variable update karo."
        elif provider == "anthropic":
            text = f"🧠 *Anthropic Claude* active hai\nModel: `{self.config.AI_MODEL}`"
        else:
            text = "❌ Koi AI provider configured nahi hai."

        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)

    async def ai_status_command(self, update: Update, context):
        """/aistatus — AI provider info"""
        provider = self.config.active_ai_provider
        if provider == "groq":
            text = (
                f"⚡ *AI Provider: Groq*\n"
                f"Model: `{self.config.GROQ_MODEL}`\n"
                f"Speed: Ultra-fast ⚡\n"
                f"Cost: Free tier available 🆓"
            )
        elif provider == "anthropic":
            text = (
                f"🧠 *AI Provider: Anthropic Claude*\n"
                f"Model: `{self.config.AI_MODEL}`"
            )
        else:
            text = (
                "❌ *Koi AI provider set nahi hai!*\n\n"
                "Groq API key lao (free):\n"
                "👉 https://console.groq.com/keys"
            )
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)

    async def auto_reply_handler(self, update: Update, context):
        """Bot mention pe auto-reply (jab AI on ho)"""
        if not update.effective_message or not update.effective_message.text:
            return
        if update.effective_chat.type == "private":
            return

        settings = await self.db.get_group_settings(update.effective_chat.id)
        if not settings.get("ai_enabled") or not self.config.has_ai:
            return

        text = update.effective_message.text
        bot_username = context.bot.username

        is_mentioned = (
            f"@{bot_username}" in text
            or (
                update.effective_message.reply_to_message
                and update.effective_message.reply_to_message.from_user
                and update.effective_message.reply_to_message.from_user.id == context.bot.id
            )
        )

        if not is_mentioned:
            return

        question = text.replace(f"@{bot_username}", "").strip()
        if not question:
            return

        await update.effective_chat.send_action(ChatAction.TYPING)
        try:
            answer, _ = await self._call_ai(question)
            await update.message.reply_text(answer)
        except Exception as e:
            logger.error(f"AI auto-reply error: {e}")

    @admin_only
    @group_only
    async def toggle_ai_on(self, update: Update, context):
        """AI on karo"""
        if not self.config.has_ai:
            await update.message.reply_text(
                "❌ Pehle `GROQ_API_KEY` set karo!\n"
                "👉 https://console.groq.com/keys — Free hai!",
                parse_mode=ParseMode.MARKDOWN,
            )
            return

        await self.db.update_group_setting(update.effective_chat.id, "ai_enabled", 1)
        provider = "⚡ Groq" if self.config.active_ai_provider == "groq" else "🧠 Claude"
        bot = await context.bot.get_me()
        await update.message.reply_text(
            f"🧠 *AI Auto-Reply: ON* ({provider})\n\n"
            f"`@{bot.username}` mention karo ya reply karo!",
            parse_mode=ParseMode.MARKDOWN,
        )

    @admin_only
    @group_only
    async def toggle_ai_off(self, update: Update, context):
        """AI off karo"""
        await self.db.update_group_setting(update.effective_chat.id, "ai_enabled", 0)
        await update.message.reply_text("🧠 *AI Auto-Reply: OFF*", parse_mode=ParseMode.MARKDOWN)

    # ─── Core AI Caller ──────────────────────────────────────────────────────

    async def _call_ai(self, question: str) -> tuple[str, str]:
        """
        AI call karo — Groq pehle, Anthropic fallback.
        Returns: (answer_text, provider_name)
        """
        if self.config.has_groq:
            try:
                answer = await self._call_groq(question)
                return answer, "groq"
            except Exception as e:
                logger.warning(f"Groq failed, trying Anthropic fallback: {e}")
                if self.config.ANTHROPIC_API_KEY:
                    answer = await self._call_anthropic(question)
                    return answer, "anthropic"
                raise
        elif self.config.ANTHROPIC_API_KEY:
            answer = await self._call_anthropic(question)
            return answer, "anthropic"
        else:
            raise RuntimeError("Koi AI provider configured nahi hai!")

    async def _call_groq(self, question: str) -> str:
        """Groq API call — OpenAI-compatible format"""
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                GROQ_API_URL,
                headers={
                    "Authorization": f"Bearer {self.config.GROQ_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self.config.GROQ_MODEL,
                    "messages": [
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user",   "content": question},
                    ],
                    "max_tokens": 512,
                    "temperature": 0.7,
                },
            )
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"].strip()

    async def _call_anthropic(self, question: str) -> str:
        """Anthropic Claude API call (fallback)"""
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                ANTHROPIC_API_URL,
                headers={
                    "x-api-key": self.config.ANTHROPIC_API_KEY,
                    "anthropic-version": "2023-06-01",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self.config.AI_MODEL,
                    "max_tokens": 512,
                    "system": SYSTEM_PROMPT,
                    "messages": [{"role": "user", "content": question}],
                },
            )
            response.raise_for_status()
            data = response.json()
            return data["content"][0]["text"].strip()
