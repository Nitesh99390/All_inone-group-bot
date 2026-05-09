"""
Welcome Handler - Naye members ka swagat karo
"""

import logging
from datetime import datetime

from telegram import ChatMember, ChatMemberUpdated, Update
from telegram.constants import ParseMode

from config import Config
from database.db import Database
from utils.helpers import mention_user

logger = logging.getLogger(__name__)

DEFAULT_WELCOME = (
    "👋 Swagat hai {mention} bhai!\n\n"
    "🏠 **{chat_name}** mein aapka khoob swagat hai!\n"
    "📜 Rules padhne ke liye /rules likho.\n"
    "❓ Koi sawaal ho toh /help likho.\n\n"
    "Mazze karo! 🎉"
)

DEFAULT_GOODBYE = (
    "👋 {name} ne group chhod diya.\n"
    "Aane waale log kuch bhi nahi ruk sakte! 😔"
)


class WelcomeHandlers:
    def __init__(self, db: Database, config: Config):
        self.db = db
        self.config = config

    async def handle_member_update(self, update: Update, context):
        """Chat member status change handle karo"""
        result = self._extract_status_change(update.chat_member)
        if result is None:
            return

        was_member, is_member = result
        chat = update.effective_chat
        user = update.chat_member.new_chat_member.user

        # Naya member join hua
        if not was_member and is_member:
            await self._send_welcome(context, chat, user)
            # Stats update karo
            await self.db.update_group_setting(chat.id, "chat_id", chat.id)

        # Member ne group chhoda
        elif was_member and not is_member:
            await self._send_goodbye(context, chat, user)

    async def _send_welcome(self, context, chat, user):
        """Welcome message bhejo"""
        settings = await self.db.get_group_settings(chat.id)
        template = settings.get("welcome_msg") or DEFAULT_WELCOME

        msg = template.format(
            mention=mention_user(user),
            name=user.full_name,
            username=f"@{user.username}" if user.username else user.full_name,
            chat_name=chat.title or "Group",
            id=user.id,
            date=datetime.now().strftime("%d %b %Y"),
        )

        try:
            await context.bot.send_message(
                chat_id=chat.id,
                text=msg,
                parse_mode=ParseMode.MARKDOWN,
            )
        except Exception as e:
            logger.error(f"Welcome message send nahi hua: {e}")

    async def _send_goodbye(self, context, chat, user):
        """Goodbye message bhejo"""
        settings = await self.db.get_group_settings(chat.id)
        template = settings.get("goodbye_msg", DEFAULT_GOODBYE)

        msg = template.format(
            mention=mention_user(user),
            name=user.full_name,
            username=f"@{user.username}" if user.username else user.full_name,
        )

        try:
            await context.bot.send_message(
                chat_id=chat.id,
                text=msg,
                parse_mode=ParseMode.MARKDOWN,
            )
        except Exception as e:
            logger.error(f"Goodbye message send nahi hua: {e}")

    @staticmethod
    def _extract_status_change(chat_member_update: ChatMemberUpdated):
        """Member join hua ya gaya - decide karo"""
        status_change = chat_member_update.difference().get("status")
        if status_change is None:
            return None

        old_is_member, new_is_member = (
            status in [
                ChatMember.MEMBER,
                ChatMember.OWNER,
                ChatMember.ADMINISTRATOR,
            ]
            for status in status_change
        )
        if old_is_member == new_is_member:
            return None
        return old_is_member, new_is_member
