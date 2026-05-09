"""
Help Handler - /help, /rules, /faq commands
"""

import logging

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ParseMode

from config import Config
from database.db import Database
from utils.decorators import admin_only

logger = logging.getLogger(__name__)

HELP_MAIN = """
🤖 *Group Help Bot - Main Menu*

Apni category choose karo:
"""

HELP_CATEGORIES = {
    "admin": {
        "emoji": "👑",
        "title": "Admin Commands",
        "text": """
👑 *Admin Commands*

`/ban [reply/mention] [reason]` — User ko ban karo
`/unban [reply/mention]` — User ka ban hatao
`/kick [reply/mention]` — User ko kick karo
`/mute [reply/mention] [10m/2h/1d]` — User ko mute karo
`/unmute [reply/mention]` — Mute hatao
`/warn [reply/mention] [reason]` — Warning do
`/unwarn [reply/mention]` — Last warning hatao
`/warnings [reply/mention]` — Warnings dekho
`/setlimit [number]` — Warning limit set karo
`/promote [reply]` — Admin banao
`/demote [reply]` — Admin hatao
`/pin` — Message pin karo (reply mein)
`/unpin` — Pinned message hatao
`/broadcast [msg]` — Sabko message bhejo
`/groupstats` — Group ki stats dekho
""",
    },
    "moderation": {
        "emoji": "🛡️",
        "title": "Moderation",
        "text": """
🛡️ *Moderation Commands*

`/antilink on/off` — Links block karo
`/antispam on/off` — Spam block karo
`/addfilter [word]` — Word filter add karo
`/delfilter [word]` — Filter hatao
`/filters` — Saare filters dekho
""",
    },
    "general": {
        "emoji": "🔧",
        "title": "General Commands",
        "text": """
🔧 *General Commands*

`/id` — Apna ya kisi ka ID dekho
`/info [reply]` — User info
`/ping` — Bot alive hai?
`/time` — Current time
`/calc [expression]` — Calculator
`/poll Sawaal | Option1 | Option2` — Poll banao
`/weather [shehar]` — Mausam dekho
""",
    },
    "notes": {
        "emoji": "📝",
        "title": "Notes & Custom Commands",
        "text": """
📝 *Notes & Custom Commands*

`/note [naam] [content]` — Note save karo
`/getnote [naam]` — Note dekho
`/notes` — Saare notes
`/delnote [naam]` — Note hatao

`/addcmd [!cmd] [response]` — Custom command banao
`/delcmd [!cmd]` — Custom command hatao
`/cmds` — Saare custom commands
""",
    },
    "ai": {
        "emoji": "🧠",
        "title": "AI Assistant",
        "text": """
🧠 *AI Assistant (Claude Powered)*

`/ai [sawaal]` — AI se poochho
`/ask [sawaal]` — AI se poochho (same command)
`/aion` — AI auto-reply on karo (admin)
`/aioff` — AI auto-reply off karo (admin)

💡 Jab AI on ho, bot ka mention karo toh auto reply milega!
""",
    },
    "faq": {
        "emoji": "❓",
        "title": "FAQ",
        "text": """
❓ *FAQ Commands*

`/faq` — Saare FAQs dekho
`/addfaq [sawaal] | [jawab]` — FAQ add karo (Admin)
`/delfaq [ID]` — FAQ hatao (Admin)
`/rules` — Group rules dekho
`/setrules [rules]` — Rules set karo (Admin)
""",
    },
}


class HelpHandlers:
    def __init__(self, db: Database, config: Config):
        self.db = db
        self.config = config

    async def start_command(self, update: Update, context):
        """Bot start karo"""
        user = update.effective_user
        chat = update.effective_chat

        if chat.type == "private":
            text = (
                f"👋 Salam {user.first_name}!\n\n"
                f"Main ek **Group Help Bot** hoon — powered by AI 🤖\n\n"
                f"Mujhe apne group mein add karo aur `/help` likho.\n\n"
                f"**Features:**\n"
                f"• 👑 Admin tools (ban, kick, mute, warn)\n"
                f"• 🛡️ Auto-moderation (antilink, antispam, filters)\n"
                f"• 🧠 AI Assistant (Claude powered)\n"
                f"• 📝 Notes & Custom Commands\n"
                f"• ❓ FAQ system\n"
                f"• 👋 Welcome/Goodbye messages\n"
                f"• 📊 Group statistics\n"
            )
            keyboard = InlineKeyboardMarkup([[
                InlineKeyboardButton("📖 Help Menu", callback_data="help_main"),
                InlineKeyboardButton("➕ Group mein add karo", url=f"https://t.me/{context.bot.username}?startgroup=true"),
            ]])
            await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=keyboard)
        else:
            await self.help_command(update, context)

    async def help_command(self, update: Update, context):
        """Help menu dikhao"""
        keyboard = self._build_help_keyboard()
        await update.message.reply_text(
            HELP_MAIN,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=keyboard,
        )

    async def help_callback(self, update: Update, context):
        """Inline button press handle karo"""
        query = update.callback_query
        await query.answer()

        action = query.data.replace("help_", "")

        if action == "main":
            keyboard = self._build_help_keyboard()
            await query.edit_message_text(
                HELP_MAIN,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=keyboard,
            )
        elif action in HELP_CATEGORIES:
            cat = HELP_CATEGORIES[action]
            keyboard = InlineKeyboardMarkup([[
                InlineKeyboardButton("◀️ Wapas", callback_data="help_main")
            ]])
            await query.edit_message_text(
                cat["text"],
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=keyboard,
            )

    def _build_help_keyboard(self) -> InlineKeyboardMarkup:
        buttons = []
        cats = list(HELP_CATEGORIES.items())
        for i in range(0, len(cats), 2):
            row = []
            for key, cat in cats[i:i+2]:
                row.append(InlineKeyboardButton(
                    f"{cat['emoji']} {cat['title']}",
                    callback_data=f"help_{key}"
                ))
            buttons.append(row)
        return InlineKeyboardMarkup(buttons)

    async def rules_command(self, update: Update, context):
        """Group rules dikhao"""
        settings = await self.db.get_group_settings(update.effective_chat.id)
        rules = settings.get("rules", "")

        if not rules:
            await update.message.reply_text(
                "📜 Is group ke liye abhi koi rules set nahi hue.\n"
                "Admin `/setrules [rules text]` se rules set kar sakta hai."
            )
        else:
            await update.message.reply_text(
                f"📜 **Group Rules**\n\n{rules}",
                parse_mode=ParseMode.MARKDOWN,
            )

    @admin_only
    async def set_rules_command(self, update: Update, context):
        """Rules set karo"""
        if not context.args:
            await update.message.reply_text(
                "❓ Usage: `/setrules [rules text]`\n\n"
                "Example:\n`/setrules 1. Respect karo\n2. Spam mat karo`",
                parse_mode=ParseMode.MARKDOWN,
            )
            return

        rules = " ".join(context.args)
        await self.db.update_group_setting(update.effective_chat.id, "rules", rules)
        await update.message.reply_text("✅ Rules set ho gaye!")

    async def faq_command(self, update: Update, context):
        """FAQ list dikhao"""
        faqs = await self.db.get_faqs(update.effective_chat.id)

        if not faqs:
            await update.message.reply_text(
                "❓ Abhi koi FAQ nahi hai.\n"
                "Admin `/addfaq sawaal | jawab` se add kar sakta hai."
            )
            return

        text = "❓ **Frequently Asked Questions**\n\n"
        for faq in faqs:
            text += f"**{faq['id']}.** {faq['question']}\n"
            text += f"💬 {faq['answer']}\n\n"

        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)

    @admin_only
    async def add_faq_command(self, update: Update, context):
        """FAQ add karo"""
        text = " ".join(context.args) if context.args else ""
        if "|" not in text:
            await update.message.reply_text(
                "❓ Usage: `/addfaq sawaal | jawab`",
                parse_mode=ParseMode.MARKDOWN,
            )
            return

        parts = text.split("|", 1)
        question = parts[0].strip()
        answer = parts[1].strip()

        if await self.db.add_faq(update.effective_chat.id, question, answer):
            await update.message.reply_text(f"✅ FAQ add ho gaya!\n\n**Q:** {question}\n**A:** {answer}", parse_mode=ParseMode.MARKDOWN)
        else:
            await update.message.reply_text("❌ FAQ add nahi ho saka!")

    @admin_only
    async def del_faq_command(self, update: Update, context):
        """FAQ hatao"""
        if not context.args or not context.args[0].isdigit():
            await update.message.reply_text("❓ Usage: `/delfaq [ID]`", parse_mode=ParseMode.MARKDOWN)
            return

        faq_id = int(context.args[0])
        if await self.db.del_faq(update.effective_chat.id, faq_id):
            await update.message.reply_text(f"✅ FAQ #{faq_id} hata diya!")
        else:
            await update.message.reply_text(f"❌ FAQ #{faq_id} nahi mila!")
