"""
Moderation Handler - Auto-moderation features
"""

import logging
import re

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ParseMode
from telegram.error import BadRequest

from config import Config
from database.db import Database
from utils.decorators import admin_only, group_only
from utils.helpers import is_url, mention_user

logger = logging.getLogger(__name__)

# Links ke patterns
LINK_PATTERNS = [
    r"https?://",
    r"www\.",
    r"t\.me/",
    r"telegram\.me/",
    r"bit\.ly/",
    r"tinyurl\.com/",
    r"[\w\-]+\.(?:com|net|org|io|xyz|me|link|click|info|biz|co)",
]
LINK_REGEX = re.compile("|".join(LINK_PATTERNS), re.IGNORECASE)


class ModerationHandlers:
    def __init__(self, db: Database, config: Config):
        self.db = db
        self.config = config

    async def message_filter_handler(self, update: Update, context):
        """Saare messages check karo moderation ke liye"""
        if not update.effective_message or not update.effective_user:
            return
        if update.effective_chat.type == "private":
            return

        message = update.effective_message
        user = update.effective_user
        chat = update.effective_chat

        # Bot messages skip karo
        if user.is_bot:
            return

        # Admin messages skip karo
        from utils.decorators import is_admin
        if await is_admin(update):
            # Stats update karo
            await self.db.increment_message_count(chat.id, user.id)
            return

        settings = await self.db.get_group_settings(chat.id)
        text = message.text or message.caption or ""

        # ── Flood Check ───────────────────────────────────────────────────
        if settings.get("antispam", 1):
            is_flooding = await self.db.check_flood(
                chat.id, user.id,
                self.config.FLOOD_LIMIT,
                self.config.FLOOD_WINDOW
            )
            if is_flooding:
                try:
                    await message.delete()
                    from telegram import ChatPermissions
                    from datetime import datetime, timedelta
                    await chat.restrict_member(
                        user.id,
                        permissions=ChatPermissions(can_send_messages=False),
                        until_date=datetime.now() + timedelta(minutes=5),
                    )
                    warn_msg = await chat.send_message(
                        f"🚫 {mention_user(user)} spam kar raha hai! 5 minute ke liye mute ho gaya.",
                        parse_mode=ParseMode.MARKDOWN,
                    )
                    # Warning message bhi 10 sec baad delete karo
                    context.job_queue.run_once(
                        lambda ctx: ctx.bot.delete_message(chat.id, warn_msg.message_id),
                        10
                    )
                except Exception as e:
                    logger.error(f"Flood mute error: {e}")
                return

        # ── Anti-Link Check ───────────────────────────────────────────────
        if settings.get("antilink", 0) and text:
            if LINK_REGEX.search(text):
                try:
                    await message.delete()
                    warn_msg = await chat.send_message(
                        f"🔗 {mention_user(user)}, is group mein links allowed nahi hain!",
                        parse_mode=ParseMode.MARKDOWN,
                    )
                    # 8 sec baad warning delete karo
                    if context.job_queue:
                        context.job_queue.run_once(
                            lambda ctx: ctx.bot.delete_message(chat.id, warn_msg.message_id),
                            8
                        )
                except Exception as e:
                    logger.error(f"Anti-link error: {e}")
                return

        # ── Word Filter Check ─────────────────────────────────────────────
        if text:
            filters = await self.db.get_filters(chat.id)
            text_lower = text.lower()
            for f in filters:
                if f["keyword"] in text_lower:
                    try:
                        await message.delete()
                        if f["action"] == "warn":
                            warn_count = await self.db.add_warning(
                                chat.id, user.id,
                                f"Filtered word: {f['keyword']}",
                                context.bot.id,
                            )
                            await chat.send_message(
                                f"⚠️ {mention_user(user)}: Filtered word use ki! Warning #{warn_count}",
                                parse_mode=ParseMode.MARKDOWN,
                            )
                    except Exception as e:
                        logger.error(f"Filter action error: {e}")
                    return

        # Stats update karo
        await self.db.increment_message_count(chat.id, user.id)

    @admin_only
    @group_only
    async def toggle_antilink_command(self, update: Update, context):
        """Anti-link toggle karo"""
        if not context.args or context.args[0].lower() not in ("on", "off"):
            settings = await self.db.get_group_settings(update.effective_chat.id)
            current = "on" if settings.get("antilink") else "off"
            keyboard = InlineKeyboardMarkup([[
                InlineKeyboardButton("✅ On", callback_data="antilink_on"),
                InlineKeyboardButton("❌ Off", callback_data="antilink_off"),
            ]])
            await update.message.reply_text(
                f"🔗 Anti-Link abhi: **{current.upper()}**\nChange karo:",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=keyboard,
            )
            return

        value = 1 if context.args[0].lower() == "on" else 0
        await self.db.update_group_setting(update.effective_chat.id, "antilink", value)
        status = "✅ On" if value else "❌ Off"
        await update.message.reply_text(f"🔗 Anti-Link: **{status}**", parse_mode=ParseMode.MARKDOWN)

    async def antilink_callback(self, update: Update, context):
        """Antilink inline button"""
        query = update.callback_query
        await query.answer()
        value = 1 if "on" in query.data else 0
        await self.db.update_group_setting(update.effective_chat.id, "antilink", value)
        status = "✅ On" if value else "❌ Off"
        await query.edit_message_text(f"🔗 Anti-Link: **{status}**", parse_mode=ParseMode.MARKDOWN)

    @admin_only
    @group_only
    async def toggle_antispam_command(self, update: Update, context):
        """Anti-spam toggle karo"""
        if not context.args or context.args[0].lower() not in ("on", "off"):
            settings = await self.db.get_group_settings(update.effective_chat.id)
            current = "on" if settings.get("antispam", 1) else "off"
            await update.message.reply_text(
                f"🛡️ Anti-Spam abhi: **{current.upper()}**\n"
                f"Usage: `/antispam on/off`",
                parse_mode=ParseMode.MARKDOWN,
            )
            return

        value = 1 if context.args[0].lower() == "on" else 0
        await self.db.update_group_setting(update.effective_chat.id, "antispam", value)
        status = "✅ On" if value else "❌ Off"
        await update.message.reply_text(f"🛡️ Anti-Spam: **{status}**", parse_mode=ParseMode.MARKDOWN)

    @admin_only
    @group_only
    async def add_filter_command(self, update: Update, context):
        """Word filter add karo"""
        if len(context.args) < 1:
            await update.message.reply_text(
                "❓ Usage: `/addfilter [word] [action: delete/warn]`\n"
                "Default action: delete",
                parse_mode=ParseMode.MARKDOWN,
            )
            return

        keyword = context.args[0].lower()
        action = context.args[1].lower() if len(context.args) > 1 else "delete"
        if action not in ("delete", "warn"):
            action = "delete"

        if await self.db.add_filter(update.effective_chat.id, keyword, action):
            await update.message.reply_text(
                f"✅ Filter add: `{keyword}` (Action: {action})",
                parse_mode=ParseMode.MARKDOWN,
            )
        else:
            await update.message.reply_text("❌ Filter add nahi ho saka!")

    @admin_only
    @group_only
    async def del_filter_command(self, update: Update, context):
        """Filter hatao"""
        if not context.args:
            await update.message.reply_text("❓ Usage: `/delfilter [word]`", parse_mode=ParseMode.MARKDOWN)
            return

        keyword = context.args[0].lower()
        if await self.db.del_filter(update.effective_chat.id, keyword):
            await update.message.reply_text(f"✅ Filter hata diya: `{keyword}`", parse_mode=ParseMode.MARKDOWN)
        else:
            await update.message.reply_text(f"❌ Filter `{keyword}` nahi mila!", parse_mode=ParseMode.MARKDOWN)

    @admin_only
    @group_only
    async def list_filters_command(self, update: Update, context):
        """Saare filters dikhaao"""
        filters = await self.db.get_filters(update.effective_chat.id)

        if not filters:
            await update.message.reply_text("ℹ️ Koi filters nahi hain.\n`/addfilter [word]` se add karo.", parse_mode=ParseMode.MARKDOWN)
            return

        text = "🛡️ **Active Filters:**\n\n"
        for f in filters:
            text += f"• `{f['keyword']}` — {f['action']}\n"

        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)
