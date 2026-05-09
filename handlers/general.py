"""
General Handler - id, info, ping, notes, custom commands, polls, etc.
"""

import logging
import math
import re
from datetime import datetime, timezone

from telegram import Update
from telegram.constants import ParseMode

from config import Config
from database.db import Database
from utils.decorators import admin_only, group_only
from utils.helpers import format_user_info, mention_user

logger = logging.getLogger(__name__)

# Safe eval ke liye allowed operators
SAFE_CHARS = re.compile(r"^[\d\s\+\-\*\/\(\)\.\%\^]+$")


class GeneralHandlers:
    def __init__(self, db: Database, config: Config):
        self.db = db
        self.config = config

    async def id_command(self, update: Update, context):
        """User ya chat ID dikhao"""
        chat = update.effective_chat
        user = update.effective_user

        if update.message.reply_to_message:
            target = update.message.reply_to_message.from_user
            text = (
                f"👤 **{target.full_name}**\n"
                f"├ User ID: `{target.id}`\n"
                f"└ Chat ID: `{chat.id}`"
            )
        elif chat.type == "private":
            text = f"👤 **Aapka ID:** `{user.id}`"
        else:
            text = (
                f"📋 **IDs:**\n"
                f"├ Aapka ID: `{user.id}`\n"
                f"└ Group ID: `{chat.id}`"
            )

        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)

    async def info_command(self, update: Update, context):
        """User info dikhao"""
        target = (
            update.message.reply_to_message.from_user
            if update.message.reply_to_message
            else update.effective_user
        )

        stats = await self.db.get_user_stats(update.effective_chat.id, target.id)
        warns = await self.db.get_warn_count(update.effective_chat.id, target.id)

        text = format_user_info(target)
        text += f"\n├ Messages: `{stats.get('messages', 0)}`"
        text += f"\n└ Warnings: `{warns}`"

        if update.effective_chat.type != "private":
            try:
                member = await update.effective_chat.get_member(target.id)
                text += f"\n\n**Status:** {member.status}"
            except Exception:
                pass

        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)

    async def ping_command(self, update: Update, context):
        """Ping-pong — bot alive check"""
        start = datetime.now()
        msg = await update.message.reply_text("🏓 Pinging...")
        latency = (datetime.now() - start).total_seconds() * 1000
        await msg.edit_text(f"🏓 **Pong!** `{latency:.0f}ms`", parse_mode=ParseMode.MARKDOWN)

    async def time_command(self, update: Update, context):
        """Current time dikhao"""
        now = datetime.now(timezone.utc)
        ist = now.replace(tzinfo=None)  # IST = UTC + 5:30
        from datetime import timedelta
        ist = now + timedelta(hours=5, minutes=30)

        text = (
            f"🕐 **Current Time**\n\n"
            f"🌍 UTC: `{now.strftime('%Y-%m-%d %H:%M:%S')}`\n"
            f"🇮🇳 IST: `{ist.strftime('%Y-%m-%d %H:%M:%S')}`"
        )
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)

    async def calc_command(self, update: Update, context):
        """Simple calculator"""
        if not context.args:
            await update.message.reply_text("❓ Usage: `/calc [expression]`\nExample: `/calc 15 * 7 + 3`", parse_mode=ParseMode.MARKDOWN)
            return

        expr = " ".join(context.args).replace("^", "**")

        if not SAFE_CHARS.match(expr.replace("**", "")):
            await update.message.reply_text("❌ Sirf numbers aur basic operators (+, -, *, /, %) allowed hain!")
            return

        try:
            result = eval(expr, {"__builtins__": {}}, {"math": math})
            await update.message.reply_text(
                f"🧮 `{expr}` = **{result}**",
                parse_mode=ParseMode.MARKDOWN,
            )
        except ZeroDivisionError:
            await update.message.reply_text("❌ Zero se divide nahi kar sakte!")
        except Exception:
            await update.message.reply_text("❌ Invalid expression!")

    async def weather_command(self, update: Update, context):
        """Weather info (simple - without external API)"""
        if not context.args:
            await update.message.reply_text(
                "❓ Usage: `/weather [shehar]`\nExample: `/weather Mumbai`",
                parse_mode=ParseMode.MARKDOWN,
            )
            return

        city = " ".join(context.args)
        await update.message.reply_text(
            f"🌤️ **{city}** ka mausam:\n\n"
            f"_Weather API key nahi hai. OpenWeatherMap ka free API add kar sakte ho._\n\n"
            f"💡 `WEATHER_API_KEY` environment variable mein OpenWeatherMap key daalo.",
            parse_mode=ParseMode.MARKDOWN,
        )

    async def create_poll_command(self, update: Update, context):
        """Poll banao"""
        text = update.message.text.split(None, 1)
        if len(text) < 2:
            await update.message.reply_text(
                "❓ Usage: `/poll Sawaal | Option1 | Option2 | Option3`",
                parse_mode=ParseMode.MARKDOWN,
            )
            return

        parts = [p.strip() for p in text[1].split("|")]
        if len(parts) < 3:
            await update.message.reply_text("❌ Kam se kam 1 sawaal aur 2 options chahiye!")
            return

        question = parts[0]
        options = parts[1:]

        if len(options) > 10:
            await update.message.reply_text("❌ Maximum 10 options allowed hain!")
            return

        try:
            await context.bot.send_poll(
                chat_id=update.effective_chat.id,
                question=question,
                options=options,
                is_anonymous=False,
            )
            await update.message.delete()
        except Exception as e:
            await update.message.reply_text(f"❌ Poll nahi bana: {e}")

    # ─── Custom Commands ────────────────────────────────────────────────────

    @admin_only
    @group_only
    async def add_custom_command(self, update: Update, context):
        """Custom command add karo"""
        text = update.message.text.split(None, 2)
        if len(text) < 3:
            await update.message.reply_text(
                "❓ Usage: `/addcmd !commandname response text`\n"
                "Example: `/addcmd !website Visit us at example.com`",
                parse_mode=ParseMode.MARKDOWN,
            )
            return

        cmd = text[1].lower().lstrip("!/")
        response = text[2]

        if await self.db.add_custom_command(
            update.effective_chat.id, cmd, response, update.effective_user.id
        ):
            await update.message.reply_text(
                f"✅ Custom command `!{cmd}` add ho gaya!",
                parse_mode=ParseMode.MARKDOWN,
            )
        else:
            await update.message.reply_text("❌ Command add nahi ho saka!")

    @admin_only
    @group_only
    async def del_custom_command(self, update: Update, context):
        """Custom command hatao"""
        if not context.args:
            await update.message.reply_text("❓ Usage: `/delcmd !commandname`", parse_mode=ParseMode.MARKDOWN)
            return

        cmd = context.args[0].lower().lstrip("!/")
        if await self.db.del_custom_command(update.effective_chat.id, cmd):
            await update.message.reply_text(f"✅ Command `!{cmd}` hata diya!", parse_mode=ParseMode.MARKDOWN)
        else:
            await update.message.reply_text(f"❌ Command `!{cmd}` nahi mila!", parse_mode=ParseMode.MARKDOWN)

    async def list_custom_commands(self, update: Update, context):
        """Saare custom commands list karo"""
        cmds = await self.db.list_custom_commands(update.effective_chat.id)

        if not cmds:
            await update.message.reply_text(
                "ℹ️ Koi custom commands nahi hain.\n"
                "Admin `/addcmd !cmd response` se add kar sakta hai.",
                parse_mode=ParseMode.MARKDOWN,
            )
            return

        text = "⚡ **Custom Commands:**\n\n"
        for cmd in cmds:
            text += f"• `!{cmd}`\n"

        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)

    async def custom_command_handler(self, update: Update, context):
        """Custom commands ! se start hone waale handle karo"""
        if not update.effective_message or not update.effective_message.text:
            return

        text = update.effective_message.text
        if not text.startswith("!"):
            return

        cmd = text.split()[0][1:].lower()
        response = await self.db.get_custom_command(update.effective_chat.id, cmd)

        if response:
            await update.message.reply_text(response)

    # ─── Notes ──────────────────────────────────────────────────────────────

    @admin_only
    @group_only
    async def add_note_command(self, update: Update, context):
        """Note save karo"""
        text = update.message.text.split(None, 2)
        if len(text) < 3:
            await update.message.reply_text(
                "❓ Usage: `/note [naam] [content]`",
                parse_mode=ParseMode.MARKDOWN,
            )
            return

        name = text[1].lower()
        content = text[2]

        if await self.db.add_note(update.effective_chat.id, name, content, update.effective_user.id):
            await update.message.reply_text(f"📝 Note `{name}` save ho gaya!", parse_mode=ParseMode.MARKDOWN)
        else:
            await update.message.reply_text("❌ Note save nahi ho saka!")

    async def get_note_command(self, update: Update, context):
        """Note get karo"""
        if not context.args:
            await update.message.reply_text("❓ Usage: `/getnote [naam]`", parse_mode=ParseMode.MARKDOWN)
            return

        name = context.args[0].lower()
        content = await self.db.get_note(update.effective_chat.id, name)

        if content:
            await update.message.reply_text(f"📝 **{name}**\n\n{content}", parse_mode=ParseMode.MARKDOWN)
        else:
            await update.message.reply_text(f"❌ Note `{name}` nahi mila!", parse_mode=ParseMode.MARKDOWN)

    async def list_notes_command(self, update: Update, context):
        """Saare notes list karo"""
        notes = await self.db.list_notes(update.effective_chat.id)

        if not notes:
            await update.message.reply_text("ℹ️ Koi notes nahi hain.", parse_mode=ParseMode.MARKDOWN)
            return

        text = "📝 **Notes:**\n\n"
        for note in notes:
            text += f"• `{note}` — `/getnote {note}`\n"

        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)

    @admin_only
    @group_only
    async def del_note_command(self, update: Update, context):
        """Note hatao"""
        if not context.args:
            await update.message.reply_text("❓ Usage: `/delnote [naam]`", parse_mode=ParseMode.MARKDOWN)
            return

        name = context.args[0].lower()
        if await self.db.del_note(update.effective_chat.id, name):
            await update.message.reply_text(f"✅ Note `{name}` hata diya!", parse_mode=ParseMode.MARKDOWN)
        else:
            await update.message.reply_text(f"❌ Note `{name}` nahi mila!", parse_mode=ParseMode.MARKDOWN)
