# 🤖 Telegram Group Help Bot

> **Deep-featured Telegram group management bot** — Claude AI powered, Render pe deploy hoga

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://python.org)
[![python-telegram-bot](https://img.shields.io/badge/python--telegram--bot-21.6-green.svg)](https://python-telegram-bot.org)
[![Deploy on Render](https://img.shields.io/badge/Deploy-Render-purple.svg)](https://render.com)

---

## ✨ Features

| Feature | Description |
|---|---|
| 👑 **Admin Tools** | Ban, unban, kick, mute, unmute, warn, promote, demote |
| 🛡️ **Auto-Moderation** | Anti-link, anti-spam, flood control, word filters |
| 🧠 **AI Assistant** | Claude-powered Q&A (mention pe auto-reply) |
| 👋 **Welcome System** | Custom welcome/goodbye messages |
| 📝 **Notes** | Group-specific notes system |
| ⚡ **Custom Commands** | `!command` style custom responses |
| ❓ **FAQ System** | Admin-managed FAQ |
| 📊 **Group Stats** | Member count, message stats |
| 🗳️ **Polls** | Inline poll creation |

---

## 🚀 Deployment Guide

### Step 1: Bot Token Lao

1. Telegram pe [@BotFather](https://t.me/BotFather) pe jaao
2. `/newbot` command bhejo
3. Naam aur username do
4. **Token copy karo**

### Step 2: GitHub Pe Upload Karo

```bash
# Repository clone ya create karo
git init
git add .
git commit -m "Initial bot setup"

# GitHub pe push karo
git remote add origin https://github.com/AAPKA_USERNAME/telegram-group-bot.git
git branch -M main
git push -u origin main
```

### Step 3: Render Pe Deploy Karo

1. [render.com](https://render.com) pe account banao
2. **New → Web Service** click karo
3. GitHub repository connect karo
4. Settings:
   - **Runtime:** Python 3
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `python bot.py`

### Step 4: Environment Variables Set Karo

Render Dashboard → Aapki Service → **Environment** tab:

| Variable | Required | Description |
|---|---|---|
| `BOT_TOKEN` | ✅ Yes | BotFather se mila token |
| `ANTHROPIC_API_KEY` | ❌ Optional | AI features ke liye |
| `OWNER_ID` | ❌ Optional | Aapka Telegram User ID |
| `DATABASE_PATH` | ❌ Optional | Default: `/data/bot_data.db` |
| `MAX_WARNINGS` | ❌ Optional | Default: `3` |
| `FLOOD_LIMIT` | ❌ Optional | Default: `5` messages |

### Step 5: Bot Ko Group Mein Add Karo

1. Bot ko group mein add karo
2. Bot ko **Admin** banao (zaroor karo!)
3. `/start` ya `/help` bhejo

---

## 📋 Commands Reference

### 👥 Everyone ke liye
```
/help          — Interactive help menu
/rules         — Group rules dekho
/faq           — FAQ list
/id            — User/chat ID
/info          — User info
/ping          — Bot latency
/time          — Current time
/calc 5*3+2    — Calculator
/poll Q|Op1|Op2 — Poll banao
/getnote naam  — Note padho
/notes         — Saare notes
/cmds          — Custom commands list
/ai sawaal     — AI se poochho
```

### 👑 Admin ke liye
```
/ban           — User ban karo (reply mein)
/unban         — Ban hatao
/kick          — Kick karo
/mute 10m      — Mute karo (10m/2h/1d)
/unmute        — Unmute karo
/warn reason   — Warning do
/unwarn        — Warnings hatao
/warnings      — Warnings dekho
/setlimit 5    — Warn limit set karo
/promote       — Admin banao
/demote        — Admin hatao
/pin           — Message pin karo
/setrules text — Rules set karo
/antilink on   — Links block karo
/antispam on   — Spam control
/addfilter word — Word filter add karo
/addcmd !cmd resp — Custom command
/addfaq Q|A    — FAQ add karo
/note naam text — Note save karo
/aion          — AI auto-reply on
/aioff         — AI off
/groupstats    — Group statistics
```

---

## 🏗️ Project Structure

```
telegram-group-bot/
├── bot.py                  ← Main entry point
├── config.py               ← Environment config
├── requirements.txt        ← Dependencies
├── render.yaml             ← Render deployment
├── .env.example            ← Environment template
├── .gitignore
├── database/
│   ├── __init__.py
│   └── db.py               ← SQLite async database
├── handlers/
│   ├── __init__.py
│   ├── welcome.py          ← Join/leave messages
│   ├── help.py             ← Help, rules, FAQ
│   ├── admin.py            ← Ban, mute, warn, etc.
│   ├── moderation.py       ← Auto-mod, filters
│   ├── general.py          ← Notes, commands, polls
│   └── ai_chat.py          ← Claude AI integration
└── utils/
    ├── __init__.py
    ├── decorators.py       ← Permission checks
    └── helpers.py          ← Utility functions
```

---

## ⚙️ Local Development

```bash
# Virtual environment banao
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Dependencies install karo
pip install -r requirements.txt

# .env file banao
cp .env.example .env
# .env mein apna BOT_TOKEN daalo

# Bot chalaao
python bot.py
```

---

## 🔧 Customization

### Welcome Message Custom Karo
Database mein `welcome_msg` field update karo. Available variables:
- `{mention}` — User ka clickable mention
- `{name}` — User ka naam  
- `{username}` — @username
- `{chat_name}` — Group ka naam
- `{id}` — User ID
- `{date}` — Aaj ki date

### AI System Prompt
`handlers/ai_chat.py` mein `SYSTEM_PROMPT` edit karo.

---

## 📞 Support

Issues? GitHub Issues pe post karo ya group mein `/help` likho!

---

*Made with ❤️ using Python + python-telegram-bot + Claude AI*
