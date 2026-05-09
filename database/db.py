"""
Database - Aiosqlite ke saath async SQLite operations
"""

import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import aiosqlite

logger = logging.getLogger(__name__)


class Database:
    def __init__(self, db_path: str):
        self.db_path = db_path

    async def initialize(self):
        """Saari tables create karo agar exist nahi karti"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.executescript("""
                PRAGMA journal_mode=WAL;
                PRAGMA foreign_keys=ON;

                -- Group settings
                CREATE TABLE IF NOT EXISTS group_settings (
                    chat_id     INTEGER PRIMARY KEY,
                    rules       TEXT DEFAULT '',
                    welcome_msg TEXT DEFAULT '',
                    antilink    INTEGER DEFAULT 0,
                    antispam    INTEGER DEFAULT 1,
                    ai_enabled  INTEGER DEFAULT 0,
                    warn_limit  INTEGER DEFAULT 3,
                    created_at  TEXT DEFAULT (datetime('now'))
                );

                -- User warnings
                CREATE TABLE IF NOT EXISTS warnings (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    chat_id     INTEGER NOT NULL,
                    user_id     INTEGER NOT NULL,
                    reason      TEXT DEFAULT 'No reason given',
                    warned_by   INTEGER NOT NULL,
                    warned_at   TEXT DEFAULT (datetime('now')),
                    UNIQUE(chat_id, user_id, warned_at)
                );

                -- Word filters
                CREATE TABLE IF NOT EXISTS filters (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    chat_id     INTEGER NOT NULL,
                    keyword     TEXT NOT NULL,
                    action      TEXT DEFAULT 'delete',
                    UNIQUE(chat_id, keyword)
                );

                -- Custom commands
                CREATE TABLE IF NOT EXISTS custom_commands (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    chat_id     INTEGER NOT NULL,
                    command     TEXT NOT NULL,
                    response    TEXT NOT NULL,
                    created_by  INTEGER,
                    UNIQUE(chat_id, command)
                );

                -- FAQ
                CREATE TABLE IF NOT EXISTS faq (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    chat_id     INTEGER NOT NULL,
                    question    TEXT NOT NULL,
                    answer      TEXT NOT NULL,
                    UNIQUE(chat_id, question)
                );

                -- Notes
                CREATE TABLE IF NOT EXISTS notes (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    chat_id     INTEGER NOT NULL,
                    name        TEXT NOT NULL,
                    content     TEXT NOT NULL,
                    created_by  INTEGER,
                    UNIQUE(chat_id, name)
                );

                -- User stats
                CREATE TABLE IF NOT EXISTS user_stats (
                    chat_id     INTEGER NOT NULL,
                    user_id     INTEGER NOT NULL,
                    messages    INTEGER DEFAULT 0,
                    joined_at   TEXT DEFAULT (datetime('now')),
                    PRIMARY KEY (chat_id, user_id)
                );

                -- Flood control tracking
                CREATE TABLE IF NOT EXISTS flood_tracker (
                    chat_id     INTEGER NOT NULL,
                    user_id     INTEGER NOT NULL,
                    count       INTEGER DEFAULT 0,
                    last_msg    TEXT DEFAULT (datetime('now')),
                    PRIMARY KEY (chat_id, user_id)
                );

                -- Banned users log
                CREATE TABLE IF NOT EXISTS ban_log (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    chat_id     INTEGER NOT NULL,
                    user_id     INTEGER NOT NULL,
                    reason      TEXT DEFAULT 'No reason',
                    banned_by   INTEGER NOT NULL,
                    banned_at   TEXT DEFAULT (datetime('now'))
                );
            """)
            await db.commit()
        logger.info("Database tables ready ✅")

    # ─── Group Settings ────────────────────────────────────────────────────

    async def get_group_settings(self, chat_id: int) -> Dict[str, Any]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            # Pehle ensure karo row exist karti hai
            await db.execute(
                "INSERT OR IGNORE INTO group_settings (chat_id) VALUES (?)",
                (chat_id,)
            )
            await db.commit()
            async with db.execute(
                "SELECT * FROM group_settings WHERE chat_id = ?", (chat_id,)
            ) as cur:
                row = await cur.fetchone()
                return dict(row) if row else {}

    async def update_group_setting(self, chat_id: int, key: str, value: Any):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                f"INSERT OR IGNORE INTO group_settings (chat_id) VALUES (?)",
                (chat_id,)
            )
            await db.execute(
                f"UPDATE group_settings SET {key} = ? WHERE chat_id = ?",
                (value, chat_id)
            )
            await db.commit()

    # ─── Warnings ──────────────────────────────────────────────────────────

    async def add_warning(self, chat_id: int, user_id: int, reason: str, warned_by: int) -> int:
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "INSERT INTO warnings (chat_id, user_id, reason, warned_by) VALUES (?, ?, ?, ?)",
                (chat_id, user_id, reason, warned_by)
            )
            await db.commit()
            async with db.execute(
                "SELECT COUNT(*) FROM warnings WHERE chat_id = ? AND user_id = ?",
                (chat_id, user_id)
            ) as cur:
                row = await cur.fetchone()
                return row[0]

    async def get_warnings(self, chat_id: int, user_id: int) -> List[Dict]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM warnings WHERE chat_id = ? AND user_id = ? ORDER BY warned_at DESC",
                (chat_id, user_id)
            ) as cur:
                rows = await cur.fetchall()
                return [dict(r) for r in rows]

    async def clear_warnings(self, chat_id: int, user_id: int) -> int:
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "DELETE FROM warnings WHERE chat_id = ? AND user_id = ?",
                (chat_id, user_id)
            )
            await db.commit()
            return cursor.rowcount

    async def get_warn_count(self, chat_id: int, user_id: int) -> int:
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(
                "SELECT COUNT(*) FROM warnings WHERE chat_id = ? AND user_id = ?",
                (chat_id, user_id)
            ) as cur:
                row = await cur.fetchone()
                return row[0]

    # ─── Filters ───────────────────────────────────────────────────────────

    async def add_filter(self, chat_id: int, keyword: str, action: str = "delete") -> bool:
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute(
                    "INSERT OR REPLACE INTO filters (chat_id, keyword, action) VALUES (?, ?, ?)",
                    (chat_id, keyword.lower(), action)
                )
                await db.commit()
            return True
        except Exception:
            return False

    async def del_filter(self, chat_id: int, keyword: str) -> bool:
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "DELETE FROM filters WHERE chat_id = ? AND keyword = ?",
                (chat_id, keyword.lower())
            )
            await db.commit()
            return cursor.rowcount > 0

    async def get_filters(self, chat_id: int) -> List[Dict]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM filters WHERE chat_id = ? ORDER BY keyword",
                (chat_id,)
            ) as cur:
                return [dict(r) for r in await cur.fetchall()]

    # ─── Custom Commands ───────────────────────────────────────────────────

    async def add_custom_command(self, chat_id: int, command: str, response: str, created_by: int) -> bool:
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute(
                    "INSERT OR REPLACE INTO custom_commands (chat_id, command, response, created_by) VALUES (?, ?, ?, ?)",
                    (chat_id, command.lower().lstrip("/"), response, created_by)
                )
                await db.commit()
            return True
        except Exception:
            return False

    async def del_custom_command(self, chat_id: int, command: str) -> bool:
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "DELETE FROM custom_commands WHERE chat_id = ? AND command = ?",
                (chat_id, command.lower().lstrip("/"))
            )
            await db.commit()
            return cursor.rowcount > 0

    async def get_custom_command(self, chat_id: int, command: str) -> Optional[str]:
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(
                "SELECT response FROM custom_commands WHERE chat_id = ? AND command = ?",
                (chat_id, command.lower().lstrip("/"))
            ) as cur:
                row = await cur.fetchone()
                return row[0] if row else None

    async def list_custom_commands(self, chat_id: int) -> List[str]:
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(
                "SELECT command FROM custom_commands WHERE chat_id = ? ORDER BY command",
                (chat_id,)
            ) as cur:
                return [row[0] for row in await cur.fetchall()]

    # ─── FAQ ───────────────────────────────────────────────────────────────

    async def add_faq(self, chat_id: int, question: str, answer: str) -> bool:
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute(
                    "INSERT OR REPLACE INTO faq (chat_id, question, answer) VALUES (?, ?, ?)",
                    (chat_id, question, answer)
                )
                await db.commit()
            return True
        except Exception:
            return False

    async def del_faq(self, chat_id: int, faq_id: int) -> bool:
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "DELETE FROM faq WHERE id = ? AND chat_id = ?",
                (faq_id, chat_id)
            )
            await db.commit()
            return cursor.rowcount > 0

    async def get_faqs(self, chat_id: int) -> List[Dict]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM faq WHERE chat_id = ? ORDER BY id",
                (chat_id,)
            ) as cur:
                return [dict(r) for r in await cur.fetchall()]

    # ─── Notes ─────────────────────────────────────────────────────────────

    async def add_note(self, chat_id: int, name: str, content: str, created_by: int) -> bool:
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute(
                    "INSERT OR REPLACE INTO notes (chat_id, name, content, created_by) VALUES (?, ?, ?, ?)",
                    (chat_id, name.lower(), content, created_by)
                )
                await db.commit()
            return True
        except Exception:
            return False

    async def get_note(self, chat_id: int, name: str) -> Optional[str]:
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(
                "SELECT content FROM notes WHERE chat_id = ? AND name = ?",
                (chat_id, name.lower())
            ) as cur:
                row = await cur.fetchone()
                return row[0] if row else None

    async def list_notes(self, chat_id: int) -> List[str]:
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(
                "SELECT name FROM notes WHERE chat_id = ? ORDER BY name",
                (chat_id,)
            ) as cur:
                return [row[0] for row in await cur.fetchall()]

    async def del_note(self, chat_id: int, name: str) -> bool:
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "DELETE FROM notes WHERE chat_id = ? AND name = ?",
                (chat_id, name.lower())
            )
            await db.commit()
            return cursor.rowcount > 0

    # ─── User Stats ────────────────────────────────────────────────────────

    async def increment_message_count(self, chat_id: int, user_id: int):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT INTO user_stats (chat_id, user_id, messages)
                VALUES (?, ?, 1)
                ON CONFLICT(chat_id, user_id) DO UPDATE SET messages = messages + 1
            """, (chat_id, user_id))
            await db.commit()

    async def get_user_stats(self, chat_id: int, user_id: int) -> Dict:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM user_stats WHERE chat_id = ? AND user_id = ?",
                (chat_id, user_id)
            ) as cur:
                row = await cur.fetchone()
                return dict(row) if row else {"messages": 0}

    async def get_group_stats(self, chat_id: int) -> Dict:
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(
                "SELECT COUNT(*) as total_users, SUM(messages) as total_msgs FROM user_stats WHERE chat_id = ?",
                (chat_id,)
            ) as cur:
                row = await cur.fetchone()
                return {"total_users": row[0] or 0, "total_messages": row[1] or 0}

    # ─── Flood Control ─────────────────────────────────────────────────────

    async def check_flood(self, chat_id: int, user_id: int, limit: int, window: int) -> bool:
        """True return karo agar user flood kar raha hai"""
        import time
        now = datetime.utcnow().isoformat()

        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT count, last_msg FROM flood_tracker WHERE chat_id = ? AND user_id = ?",
                (chat_id, user_id)
            ) as cur:
                row = await cur.fetchone()

            if row:
                last_time = datetime.fromisoformat(row["last_msg"])
                diff = (datetime.utcnow() - last_time).total_seconds()
                if diff < window:
                    new_count = row["count"] + 1
                    await db.execute(
                        "UPDATE flood_tracker SET count = ?, last_msg = ? WHERE chat_id = ? AND user_id = ?",
                        (new_count, now, chat_id, user_id)
                    )
                    await db.commit()
                    return new_count >= limit
                else:
                    await db.execute(
                        "UPDATE flood_tracker SET count = 1, last_msg = ? WHERE chat_id = ? AND user_id = ?",
                        (now, chat_id, user_id)
                    )
                    await db.commit()
            else:
                await db.execute(
                    "INSERT INTO flood_tracker (chat_id, user_id, count, last_msg) VALUES (?, ?, 1, ?)",
                    (chat_id, user_id, now)
                )
                await db.commit()
            return False
