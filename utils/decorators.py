"""
Decorators - Permission checks ke liye
"""

import functools
import logging
from typing import Callable

from telegram import Update
from telegram.constants import ChatMemberStatus

logger = logging.getLogger(__name__)

ADMIN_STATUSES = {ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER}


def admin_only(func: Callable) -> Callable:
    """Sirf group admins ke liye"""
    @functools.wraps(func)
    async def wrapper(self, update: Update, context, *args, **kwargs):
        if not update.effective_chat or not update.effective_user:
            return
        chat = update.effective_chat
        user = update.effective_user

        # Private chat mein allow karo
        if chat.type == "private":
            return await func(self, update, context, *args, **kwargs)

        member = await chat.get_member(user.id)
        if member.status not in ADMIN_STATUSES:
            await update.message.reply_text(
                "❌ Yeh command sirf **admins** ke liye hai!",
                parse_mode="Markdown"
            )
            return
        return await func(self, update, context, *args, **kwargs)
    return wrapper


def owner_only(config):
    """Sirf bot owner ke liye"""
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(self, update: Update, context, *args, **kwargs):
            user = update.effective_user
            if not user or user.id != config.OWNER_ID:
                await update.message.reply_text("❌ Yeh command sirf bot owner ke liye hai!")
                return
            return await func(self, update, context, *args, **kwargs)
        return wrapper
    return decorator


def group_only(func: Callable) -> Callable:
    """Sirf groups mein kaam karta hai"""
    @functools.wraps(func)
    async def wrapper(self, update: Update, context, *args, **kwargs):
        if update.effective_chat.type == "private":
            await update.message.reply_text(
                "❌ Yeh command sirf groups mein use karo!"
            )
            return
        return await func(self, update, context, *args, **kwargs)
    return wrapper


async def is_admin(update: Update) -> bool:
    """Check karo user admin hai ya nahi"""
    if update.effective_chat.type == "private":
        return True
    member = await update.effective_chat.get_member(update.effective_user.id)
    return member.status in ADMIN_STATUSES


async def is_bot_admin(update: Update) -> bool:
    """Check karo bot admin hai ya nahi"""
    bot = update.get_bot()
    member = await update.effective_chat.get_member(bot.id)
    return member.status in ADMIN_STATUSES
