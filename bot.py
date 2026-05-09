"""
Telegram Group Help Bot - Main Entry Point
Render pe deploy hoga, polling mode mein chalega
"""

import asyncio
import logging
import os
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

from telegram import Update
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    ChatMemberHandler,
    CommandHandler,
    MessageHandler,
    filters,
)

from config import Config
from database.db import Database
from handlers.admin import AdminHandlers
from handlers.ai_chat import AIChatHandlers
from handlers.general import GeneralHandlers
from handlers.help import HelpHandlers
from handlers.moderation import ModerationHandlers
from handlers.welcome import WelcomeHandlers

# ─── Logging Setup ──────────────────────────────────────────────────────────
logging.basicConfig(
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    level=logging.INFO,
    datefmt="%Y-%m-%d %H:%M:%S",
)
logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)


# ─── Health Check Server (Render ke liye zaroori) ───────────────────────────
class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/plain")
        self.end_headers()
        self.wfile.write(b"Bot is alive!")

    def log_message(self, format, *args):
        pass  # Server logs suppress karo


def run_health_server():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(("0.0.0.0", port), HealthHandler)
    logger.info(f"Health check server running on port {port}")
    server.serve_forever()


# ─── Main Function ──────────────────────────────────────────────────────────
async def main():
    # Config validate karo
    config = Config()
    config.validate()

    # Database initialize karo
    db = Database(config.DATABASE_PATH)
    await db.initialize()
    logger.info("✅ Database initialized")

    # Bot application build karo
    app = (
        Application.builder()
        .token(config.BOT_TOKEN)
        .build()
    )

    # Handlers initialize karo
    welcome_h = WelcomeHandlers(db, config)
    help_h = HelpHandlers(db, config)
    admin_h = AdminHandlers(db, config)
    mod_h = ModerationHandlers(db, config)
    general_h = GeneralHandlers(db, config)
    ai_h = AIChatHandlers(db, config)

    # ── Welcome / Goodbye ──────────────────────────────────────────────────
    app.add_handler(ChatMemberHandler(welcome_h.handle_member_update, ChatMemberHandler.CHAT_MEMBER))

    # ── Help Commands ──────────────────────────────────────────────────────
    app.add_handler(CommandHandler("start", help_h.start_command))
    app.add_handler(CommandHandler("help", help_h.help_command))
    app.add_handler(CommandHandler("rules", help_h.rules_command))
    app.add_handler(CommandHandler("setrules", help_h.set_rules_command))
    app.add_handler(CommandHandler("faq", help_h.faq_command))
    app.add_handler(CommandHandler("addfaq", help_h.add_faq_command))
    app.add_handler(CommandHandler("delfaq", help_h.del_faq_command))

    # ── Admin Commands ─────────────────────────────────────────────────────
    app.add_handler(CommandHandler("ban", admin_h.ban_command))
    app.add_handler(CommandHandler("unban", admin_h.unban_command))
    app.add_handler(CommandHandler("kick", admin_h.kick_command))
    app.add_handler(CommandHandler("mute", admin_h.mute_command))
    app.add_handler(CommandHandler("unmute", admin_h.unmute_command))
    app.add_handler(CommandHandler("warn", admin_h.warn_command))
    app.add_handler(CommandHandler("unwarn", admin_h.unwarn_command))
    app.add_handler(CommandHandler("warnings", admin_h.warnings_command))
    app.add_handler(CommandHandler("promote", admin_h.promote_command))
    app.add_handler(CommandHandler("demote", admin_h.demote_command))
    app.add_handler(CommandHandler("pin", admin_h.pin_command))
    app.add_handler(CommandHandler("unpin", admin_h.unpin_command))
    app.add_handler(CommandHandler("broadcast", admin_h.broadcast_command))
    app.add_handler(CommandHandler("groupstats", admin_h.group_stats_command))
    app.add_handler(CommandHandler("setlimit", admin_h.set_warn_limit_command))

    # ── Moderation Commands ────────────────────────────────────────────────
    app.add_handler(CommandHandler("addfilter", mod_h.add_filter_command))
    app.add_handler(CommandHandler("delfilter", mod_h.del_filter_command))
    app.add_handler(CommandHandler("filters", mod_h.list_filters_command))
    app.add_handler(CommandHandler("antilink", mod_h.toggle_antilink_command))
    app.add_handler(CommandHandler("antispam", mod_h.toggle_antispam_command))

    # ── General Commands ───────────────────────────────────────────────────
    app.add_handler(CommandHandler("id", general_h.id_command))
    app.add_handler(CommandHandler("info", general_h.info_command))
    app.add_handler(CommandHandler("ping", general_h.ping_command))
    app.add_handler(CommandHandler("time", general_h.time_command))
    app.add_handler(CommandHandler("addcmd", general_h.add_custom_command))
    app.add_handler(CommandHandler("delcmd", general_h.del_custom_command))
    app.add_handler(CommandHandler("cmds", general_h.list_custom_commands))
    app.add_handler(CommandHandler("note", general_h.add_note_command))
    app.add_handler(CommandHandler("getnote", general_h.get_note_command))
    app.add_handler(CommandHandler("notes", general_h.list_notes_command))
    app.add_handler(CommandHandler("delnote", general_h.del_note_command))
    app.add_handler(CommandHandler("poll", general_h.create_poll_command))
    app.add_handler(CommandHandler("weather", general_h.weather_command))
    app.add_handler(CommandHandler("calc", general_h.calc_command))

    # ── AI Commands ────────────────────────────────────────────────────────
    app.add_handler(CommandHandler("ai", ai_h.ai_command))
    app.add_handler(CommandHandler("ask", ai_h.ai_command))
    app.add_handler(CommandHandler("aion", ai_h.toggle_ai_on))
    app.add_handler(CommandHandler("aioff", ai_h.toggle_ai_off))
    app.add_handler(CommandHandler("aistatus", ai_h.ai_status_command))
    app.add_handler(CommandHandler("aimodels", ai_h.ai_models_command))

    # ── Callback Queries (Inline Buttons) ──────────────────────────────────
    app.add_handler(CallbackQueryHandler(help_h.help_callback, pattern="^help_"))
    app.add_handler(CallbackQueryHandler(admin_h.confirm_ban_callback, pattern="^confirm_ban_"))
    app.add_handler(CallbackQueryHandler(mod_h.antilink_callback, pattern="^antilink_"))

    # ── Message Handlers ───────────────────────────────────────────────────
    # Moderation: Links, spam check karo
    app.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, mod_h.message_filter_handler),
        group=1,
    )
    # Custom commands handle karo
    app.add_handler(
        MessageHandler(filters.TEXT & filters.COMMAND, general_h.custom_command_handler),
        group=2,
    )
    # AI auto-reply (mention pe)
    app.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, ai_h.auto_reply_handler),
        group=3,
    )

    # ── Error Handler ──────────────────────────────────────────────────────
    app.add_error_handler(error_handler)

    logger.info("🤖 Bot starting in polling mode...")
    await app.run_polling(
        allowed_updates=Update.ALL_TYPES,
        drop_pending_updates=True,
    )


async def error_handler(update, context):
    logger.error(f"Error: {context.error}", exc_info=context.error)
    if update and update.effective_message:
        try:
            await update.effective_message.reply_text(
                "⚠️ Kuch error aa gaya. Admin ko batao!"
            )
        except Exception:
            pass

# bot.py की आखिरी लाइन्स (if __name__ == "__main__": वाला हिस्सा) बदलें:

if __name__ == "__main__":
    # Health server को अलग thread में शुरू करें
    health_thread = threading.Thread(target=run_health_server, daemon=True)
    health_thread.start()

    # Bot चलाने का सबसे स्टेबल तरीका (Render/Linux के लिए)
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot stopped!")
    except RuntimeError as e:
        if "Event loop is closed" in str(e) or "already running" in str(e):
            # अगर लूप पहले से चल रहा है या बंद हो गया है, तो उसे यहाँ हैंडल करें
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(main())
        else:
            raise e
