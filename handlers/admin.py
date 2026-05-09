"""
Admin Handler - Ban, kick, mute, warn, promote, etc.
"""

import logging
from datetime import datetime, timedelta

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ChatMemberStatus, ParseMode
from telegram.error import BadRequest

from config import Config
from database.db import Database
from utils.decorators import admin_only, group_only, is_bot_admin
from utils.helpers import extract_user_and_reason, format_duration, mention_user, parse_time

logger = logging.getLogger(__name__)


class AdminHandlers:
    def __init__(self, db: Database, config: Config):
        self.db = db
        self.config = config

    def _get_target_user(self, update: Update):
        """Reply se target user nikalo"""
        msg = update.effective_message
        if msg.reply_to_message and msg.reply_to_message.from_user:
            return msg.reply_to_message.from_user
        return None

    def _get_reason(self, args: list, skip: int = 0) -> str:
        args_after = args[skip:] if len(args) > skip else []
        return " ".join(args_after) if args_after else "Koi reason nahi diya"

    @admin_only
    @group_only
    async def ban_command(self, update: Update, context):
        """User ban karo"""
        user = self._get_target_user(update)
        if not user:
            await update.message.reply_text("❓ Kisi message pe reply karo jise ban karna ho.")
            return

        reason = self._get_reason(context.args)
        chat = update.effective_chat

        # Bot ko ban nahi kar sakte
        if user.is_bot:
            await update.message.reply_text("❌ Bots ko is tarah ban nahi kar sakte!")
            return

        # Confirmation button
        keyboard = InlineKeyboardMarkup([[
            InlineKeyboardButton("✅ Haan, Ban karo!", callback_data=f"confirm_ban_{user.id}_{chat.id}"),
            InlineKeyboardButton("❌ Cancel", callback_data="confirm_ban_cancel"),
        ]])

        await update.message.reply_text(
            f"⚠️ Kya aap **{user.full_name}** ko ban karna chahte ho?\n"
            f"📋 Reason: {reason}",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=keyboard,
        )

        # Context mein store karo
        context.user_data["pending_ban"] = {
            "user_id": user.id,
            "user_name": user.full_name,
            "chat_id": chat.id,
            "reason": reason,
            "by": update.effective_user.id,
        }

    async def confirm_ban_callback(self, update: Update, context):
        """Ban confirm karo ya cancel karo"""
        query = update.callback_query
        await query.answer()

        if query.data == "confirm_ban_cancel":
            await query.edit_message_text("❌ Ban cancel kar diya.")
            return

        data = context.user_data.get("pending_ban")
        if not data:
            await query.edit_message_text("❌ Ban data mila nahi. Dobara try karo.")
            return

        try:
            await context.bot.ban_chat_member(
                chat_id=data["chat_id"],
                user_id=data["user_id"],
            )
            await self.db.update_group_setting(data["chat_id"], "chat_id", data["chat_id"])

            await query.edit_message_text(
                f"🔨 **{data['user_name']}** ko ban kar diya!\n"
                f"📋 Reason: {data['reason']}",
                parse_mode=ParseMode.MARKDOWN,
            )
        except BadRequest as e:
            await query.edit_message_text(f"❌ Ban nahi ho saka: {e}")

    @admin_only
    @group_only
    async def unban_command(self, update: Update, context):
        """User unban karo"""
        user = self._get_target_user(update)
        if not user:
            await update.message.reply_text("❓ Reply karo jise unban karna ho.")
            return

        try:
            await update.effective_chat.unban_member(user.id)
            await update.message.reply_text(
                f"✅ {mention_user(user)} ka ban hata diya!",
                parse_mode=ParseMode.MARKDOWN,
            )
        except BadRequest as e:
            await update.message.reply_text(f"❌ Unban nahi ho saka: {e}")

    @admin_only
    @group_only
    async def kick_command(self, update: Update, context):
        """User ko kick karo (ban + unban)"""
        user = self._get_target_user(update)
        if not user:
            await update.message.reply_text("❓ Reply karo jise kick karna ho.")
            return

        reason = self._get_reason(context.args)
        chat = update.effective_chat

        try:
            await chat.ban_member(user.id)
            await chat.unban_member(user.id)
            await update.message.reply_text(
                f"👢 {mention_user(user)} ko kick kar diya!\n📋 Reason: {reason}",
                parse_mode=ParseMode.MARKDOWN,
            )
        except BadRequest as e:
            await update.message.reply_text(f"❌ Kick nahi ho saka: {e}")

    @admin_only
    @group_only
    async def mute_command(self, update: Update, context):
        """User ko mute karo"""
        user = self._get_target_user(update)
        if not user:
            await update.message.reply_text("❓ Reply karo jise mute karna ho.")
            return

        # Time parse karo (optional)
        until = None
        duration_text = "hamesha ke liye"

        if context.args:
            seconds = parse_time(context.args[0])
            if seconds:
                until = datetime.now() + timedelta(seconds=seconds)
                duration_text = format_duration(seconds)

        try:
            from telegram import ChatPermissions
            await update.effective_chat.restrict_member(
                user.id,
                permissions=ChatPermissions(can_send_messages=False),
                until_date=until,
            )
            await update.message.reply_text(
                f"🔇 {mention_user(user)} ko **{duration_text}** ke liye mute kar diya!",
                parse_mode=ParseMode.MARKDOWN,
            )
        except BadRequest as e:
            await update.message.reply_text(f"❌ Mute nahi ho saka: {e}")

    @admin_only
    @group_only
    async def unmute_command(self, update: Update, context):
        """User unmute karo"""
        user = self._get_target_user(update)
        if not user:
            await update.message.reply_text("❓ Reply karo jise unmute karna ho.")
            return

        try:
            from telegram import ChatPermissions
            await update.effective_chat.restrict_member(
                user.id,
                permissions=ChatPermissions(
                    can_send_messages=True,
                    can_send_media_messages=True,
                    can_send_other_messages=True,
                    can_add_web_page_previews=True,
                ),
            )
            await update.message.reply_text(
                f"🔊 {mention_user(user)} ka mute hata diya!",
                parse_mode=ParseMode.MARKDOWN,
            )
        except BadRequest as e:
            await update.message.reply_text(f"❌ Unmute nahi ho saka: {e}")

    @admin_only
    @group_only
    async def warn_command(self, update: Update, context):
        """Warning do"""
        user = self._get_target_user(update)
        if not user:
            await update.message.reply_text("❓ Reply karo jise warn karna ho.")
            return

        reason = self._get_reason(context.args)
        chat = update.effective_chat
        settings = await self.db.get_group_settings(chat.id)
        warn_limit = settings.get("warn_limit", self.config.MAX_WARNINGS)

        warn_count = await self.db.add_warning(
            chat.id, user.id, reason, update.effective_user.id
        )

        msg = (
            f"⚠️ {mention_user(user)} ko warning mili!\n"
            f"📋 Reason: {reason}\n"
            f"🔢 Warnings: {warn_count}/{warn_limit}"
        )

        if warn_count >= warn_limit:
            msg += f"\n\n🔨 **{warn_limit} warnings poori! Auto-ban ho raha hai!**"
            try:
                await chat.ban_member(user.id)
                await self.db.clear_warnings(chat.id, user.id)
            except BadRequest:
                pass

        await update.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN)

    @admin_only
    @group_only
    async def unwarn_command(self, update: Update, context):
        """Last warning hatao"""
        user = self._get_target_user(update)
        if not user:
            await update.message.reply_text("❓ Reply karo jis ka warn hatana ho.")
            return

        count = await self.db.clear_warnings(update.effective_chat.id, user.id)
        if count:
            await update.message.reply_text(
                f"✅ {mention_user(user)} ki saari {count} warnings hata di!",
                parse_mode=ParseMode.MARKDOWN,
            )
        else:
            await update.message.reply_text("ℹ️ Is user ki koi warnings nahi hain.")

    async def warnings_command(self, update: Update, context):
        """Warnings dekho"""
        user = self._get_target_user(update) or update.effective_user
        warns = await self.db.get_warnings(update.effective_chat.id, user.id)

        if not warns:
            await update.message.reply_text(
                f"✅ {mention_user(user)} ko koi warnings nahi hain!",
                parse_mode=ParseMode.MARKDOWN,
            )
            return

        text = f"⚠️ **{user.full_name} ki Warnings ({len(warns)}):**\n\n"
        for i, w in enumerate(warns, 1):
            text += f"{i}. {w['reason']} — {w['warned_at'][:10]}\n"

        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)

    @admin_only
    @group_only
    async def promote_command(self, update: Update, context):
        """User ko admin banao"""
        user = self._get_target_user(update)
        if not user:
            await update.message.reply_text("❓ Reply karo jise promote karna ho.")
            return

        try:
            await update.effective_chat.promote_member(
                user.id,
                can_delete_messages=True,
                can_restrict_members=True,
                can_pin_messages=True,
                can_invite_users=True,
            )
            await update.message.reply_text(
                f"⭐ {mention_user(user)} ab Admin ban gaya!",
                parse_mode=ParseMode.MARKDOWN,
            )
        except BadRequest as e:
            await update.message.reply_text(f"❌ Promote nahi ho saka: {e}")

    @admin_only
    @group_only
    async def demote_command(self, update: Update, context):
        """Admin se hatao"""
        user = self._get_target_user(update)
        if not user:
            await update.message.reply_text("❓ Reply karo jise demote karna ho.")
            return

        try:
            await update.effective_chat.promote_member(
                user.id,
                can_delete_messages=False,
                can_restrict_members=False,
                can_pin_messages=False,
                can_invite_users=False,
                can_manage_chat=False,
            )
            await update.message.reply_text(
                f"⬇️ {mention_user(user)} ko demote kar diya!",
                parse_mode=ParseMode.MARKDOWN,
            )
        except BadRequest as e:
            await update.message.reply_text(f"❌ Demote nahi ho saka: {e}")

    @admin_only
    @group_only
    async def pin_command(self, update: Update, context):
        """Message pin karo"""
        if not update.message.reply_to_message:
            await update.message.reply_text("❓ Kisi message pe reply karo jise pin karna ho.")
            return

        try:
            await update.message.reply_to_message.pin(disable_notification=False)
            await update.message.reply_text("📌 Message pin ho gaya!")
        except BadRequest as e:
            await update.message.reply_text(f"❌ Pin nahi ho saka: {e}")

    @admin_only
    @group_only
    async def unpin_command(self, update: Update, context):
        """Unpin karo"""
        try:
            await update.effective_chat.unpin_message()
            await update.message.reply_text("📌 Message unpin ho gaya!")
        except BadRequest as e:
            await update.message.reply_text(f"❌ Unpin nahi ho saka: {e}")

    @admin_only
    async def broadcast_command(self, update: Update, context):
        """Broadcast message — sirf owner ke liye"""
        if update.effective_user.id != self.config.OWNER_ID:
            await update.message.reply_text("❌ Sirf bot owner broadcast kar sakta hai!")
            return

        if not context.args:
            await update.message.reply_text("❓ Usage: `/broadcast [message]`", parse_mode=ParseMode.MARKDOWN)
            return

        msg = " ".join(context.args)
        await update.message.reply_text(
            f"📢 **Broadcast Message:**\n\n{msg}\n\n"
            f"_(Yeh feature group broadcast ke liye use hota hai)_",
            parse_mode=ParseMode.MARKDOWN,
        )

    @admin_only
    @group_only
    async def group_stats_command(self, update: Update, context):
        """Group stats dikhao"""
        chat = update.effective_chat
        stats = await self.db.get_group_stats(chat.id)
        settings = await self.db.get_group_settings(chat.id)

        admins = await chat.get_administrators()

        text = (
            f"📊 **Group Stats — {chat.title}**\n\n"
            f"👥 Tracked Users: `{stats['total_users']}`\n"
            f"💬 Total Messages: `{stats['total_messages']}`\n"
            f"👑 Admins: `{len(admins)}`\n"
            f"🔗 Anti-Link: {'✅ On' if settings.get('antilink') else '❌ Off'}\n"
            f"🛡️ Anti-Spam: {'✅ On' if settings.get('antispam') else '❌ Off'}\n"
            f"🧠 AI: {'✅ On' if settings.get('ai_enabled') else '❌ Off'}\n"
            f"⚠️ Warn Limit: `{settings.get('warn_limit', self.config.MAX_WARNINGS)}`\n"
        )

        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)

    @admin_only
    @group_only
    async def set_warn_limit_command(self, update: Update, context):
        """Warning limit set karo"""
        if not context.args or not context.args[0].isdigit():
            await update.message.reply_text("❓ Usage: `/setlimit [number]`", parse_mode=ParseMode.MARKDOWN)
            return

        limit = int(context.args[0])
        if limit < 1 or limit > 20:
            await update.message.reply_text("❌ Limit 1 se 20 ke beech honi chahiye!")
            return

        await self.db.update_group_setting(update.effective_chat.id, "warn_limit", limit)
        await update.message.reply_text(f"✅ Warning limit **{limit}** set kar di!", parse_mode=ParseMode.MARKDOWN)
