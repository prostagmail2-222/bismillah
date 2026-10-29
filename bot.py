"""
================================================================================
                    ANIMEBOT PRO - AIOGRAM 3.X TELEGRAM BOT
================================================================================
Loyiha tavsifi:
    Ushbu bot Aiogram 3.x frameworkida yozilgan professional, to'liq funksional
    Telegram anime boti hisoblanadi. Botda Admin, Owner va Oddiy foydalanuvchi
    rollari aniq ajratilgan, xavfsiz SQLite asinxron arxitekturasi, FSM holatlari,
    majburiy obuna tekshiruvi, VIP tizimi, to'lov cheklarini tasdiqlash,
    reyting tizimi, sevimlilar, ko'rish tarixi, admin va owner panellari
    100% to'liq va mukammal qilib yozilgan.

Arxitektura prinsiplari:
    1. Yagona faylli (Monolithic) arxitektura: Barcha modullar bitta 'bot.py'
       fayliga birlashtirilgan, har bir knopka va amaliyot uchun to'liq handlerlar
       mavjud (hech qanday bo'sh callback yoki chala qolgan joy yo'q).
    2. Rolli tizim: Owner, Admin, VIP va Oddiy foydalanuvchi.
       - Admin va Owner istalgan paytda /start yoki menyu orqali 'Foydalanuvchi rejimi'ga
         o'tib, botni oddiy tomoshabin sifatida sinab ko'rishi mumkin.
    3. Toza va estetik /start: /start komandasida QAT'IY RAVISHDA sticker ishlatilmaydi,
       faqatgina odamning ko'ziga yoqadigan matnli chiroyli tabrik ko'rsatiladi.
    4. To'liq qidiruv tizimi: Kod, Nomi, Tasodifiy, TOP 10, Eng yangi, Klassik,
       Janrlar va Telegram Inline qidiruv (@botusername query).
    5. To'lov va VIP: Promokodlar, To'lov chekini yuborish, Adminga tasdiqlash
       uchun yuborish (Approve/Reject tugmalari bilan).
================================================================================
"""

import asyncio
import os
import sys
import logging
import json
import re
import math
import random
import time
import datetime
import html
from urllib.parse import quote

from dotenv import load_dotenv
load_dotenv()
from typing import Optional, List, Dict, Any, Union, Tuple
from dataclasses import dataclass, field

import aiosqlite

from aiogram import Bot, Dispatcher, Router, F, BaseMiddleware
from aiogram.enums import ParseMode, ChatMemberStatus, ContentType
from aiogram.types import (
    Message,
    CallbackQuery,
    InlineQuery,
    InlineQueryResultArticle,
    InlineQueryResultPhoto,
    InputTextMessageContent,
    ReplyKeyboardMarkup,
    KeyboardButton,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    ReplyKeyboardRemove,
    FSInputFile,
    URLInputFile,
    BotCommand,
    BotCommandScopeDefault,
    ChatMemberUpdated,
    User,
    ErrorEvent
)
from aiogram.client.default import DefaultBotProperties
from aiogram.filters import Command, CommandStart, StateFilter, BaseFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder
from aiogram.exceptions import TelegramAPIError, TelegramBadRequest, TelegramForbiddenError

# ==============================================================================
#                      1. KONFIGURATSIYA VA SOZLAMALAR
# ==============================================================================

class BotConfig:
    """Bot konfiguratsiyasi va muhit o'zgaruvchilari boshqaruvi."""
    
    BOT_TOKEN: str = os.getenv("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")
    OWNER_ID: int = int(os.getenv("OWNER_ID", "5065303387"))
    DATABASE_PATH: str = os.getenv("DATABASE_PATH", "anime_bot.db")
    
    OFFICIAL_CHANNEL_USERNAME: str = os.getenv("OFFICIAL_CHANNEL", "@AnimeUz_Official")
    OFFICIAL_CHANNEL_URL: str = os.getenv("OFFICIAL_CHANNEL_URL", "https://t.me/AnimeUz_Official")
    SUPPORT_URL: str = os.getenv("SUPPORT_URL", "https://t.me/AnimeUz_Admin")
    
    # VIP narxlari va muddatlari
    VIP_PRICES = {
        "vip_1_month": {"name": "1 Oylik VIP", "days": 30, "price": 15000, "label": "15,000 so'm"},
        "vip_3_months": {"name": "3 Oylik VIP", "days": 90, "price": 35000, "label": "35,000 so'm"},
        "vip_1_year": {"name": "1 Yillik VIP", "days": 365, "price": 100000, "label": "100,000 so'm"},
        "vip_lifetime": {"name": "Cheksiz (Lifetime)", "days": 3650, "price": 200000, "label": "200,000 so'm"}
    }
    
    RATE_LIMIT_SECONDS: float = 0.5
    
    AVAILABLE_GENRES: List[str] = [
        "Jangari", "Sarguzasht", "Komediya", "Drama",
        "Fantastika", "Sehrgarlik", "Triller", "Psixologik",
        "Romantika", "Shounen", "Seynen", "Sport",
        "Maktab", "Kundalik hayot", "Isekai", "Dahshat"
    ]


class Emojis:
    FIRE = "🔥"
    STAR = "⭐"
    SPARKLES = "✨"
    CROWN = "👑"
    DIAMOND = "💎"
    SHIELD = "🛡️"
    SEARCH = "🔍"
    FILM = "🎬"
    VIDEO = "🎥"
    BOOK = "📖"
    GEAR = "⚙️"
    BELL = "📢"
    USER = "👤"
    HEART = "❤️"
    BROKEN_HEART = "💔"
    CHECK = "✅"
    CROSS = "❌"
    ARROW_LEFT = "◀️"
    ARROW_RIGHT = "▶️"
    BACK = "🔙"
    HOME = "🏠"
    FOLDER = "📁"
    CLOCK = "⏳"
    CALENDAR = "📅"
    ROCKET = "🚀"
    TROPHY = "🏆"
    DICE = "🎲"
    NEW = "🆕"
    EDIT = "✏️"
    DELETE = "🗑️"
    ADD = "➕"
    STATS = "📊"
    BROADCAST = "📨"
    KEY = "🔑"
    INFO = "ℹ️"
    WARNING = "⚠️"
    TV = "📺"
    EYE = "👁️"
    DOWNLOAD = "📥"
    RECEIPT = "🧾"
    GLOBE = "🌐"


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - [%(levelname)s] - %(name)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("anime_bot.log", mode="a", encoding="utf-8")
    ]
)
logger = logging.getLogger("AnimeBotPro")

# ==============================================================================
#                 2. TO'LIQ ASINXRON SQLITE MA'LUMOTLAR BAZASI
# ==============================================================================

class Database:
    """To'liq asinxron SQLite ma'lumotlar bazasi klassi."""

    def __init__(self, db_path: str = BotConfig.DATABASE_PATH):
        self.db_path = db_path

    async def init_db(self):
        """Barcha jadvallarni yaratish."""
        async with aiosqlite.connect(self.db_path) as db:
            # 1. Foydalanuvchilar
            await db.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER UNIQUE NOT NULL,
                    full_name TEXT NOT NULL,
                    username TEXT,
                    role TEXT DEFAULT 'user',
                    current_mode TEXT DEFAULT 'user',
                    vip_until TIMESTAMP,
                    vip_plan TEXT,
                    downloads_count INTEGER DEFAULT 0,
                    notifications_enabled INTEGER DEFAULT 1,
                    preferred_quality TEXT DEFAULT '1080p Full HD',
                    language TEXT DEFAULT 'uz_lat',
                    is_banned INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)

            # 2. Adminlar
            await db.execute("""
                CREATE TABLE IF NOT EXISTS admins (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER UNIQUE NOT NULL,
                    full_name TEXT NOT NULL,
                    can_upload INTEGER DEFAULT 1,
                    can_edit INTEGER DEFAULT 1,
                    can_delete INTEGER DEFAULT 1,
                    can_post INTEGER DEFAULT 1,
                    can_broadcast INTEGER DEFAULT 1,
                    added_by INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)

            # 3. Kanallar
            await db.execute("""
                CREATE TABLE IF NOT EXISTS channels (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    channel_id TEXT NOT NULL,
                    title TEXT NOT NULL,
                    invite_link TEXT NOT NULL,
                    is_mandatory INTEGER DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)

            # 4. Animelar
            await db.execute("""
                CREATE TABLE IF NOT EXISTS animes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    code TEXT UNIQUE NOT NULL,
                    title TEXT NOT NULL,
                    original_title TEXT,
                    year INTEGER,
                    quality TEXT DEFAULT '1080p Full HD',
                    voiceover TEXT DEFAULT "O'zbekcha dublyaj",
                    genres TEXT NOT NULL,
                    description TEXT,
                    poster_file_id TEXT,
                    poster_url TEXT,
                    is_vip INTEGER DEFAULT 0,
                    views_count INTEGER DEFAULT 0,
                    rating REAL DEFAULT 5.0,
                    rating_count INTEGER DEFAULT 1,
                    total_episodes INTEGER DEFAULT 1,
                    status TEXT DEFAULT 'Davom etmoqda',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)

            # 5. Qismlar (Epizodlar)
            await db.execute("""
                CREATE TABLE IF NOT EXISTS episodes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    anime_id INTEGER NOT NULL,
                    anime_code TEXT NOT NULL,
                    episode_number INTEGER NOT NULL,
                    episode_title TEXT,
                    file_id TEXT NOT NULL,
                    file_type TEXT DEFAULT 'video',
                    file_size TEXT,
                    is_vip INTEGER DEFAULT 0,
                    views INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(anime_code, episode_number),
                    FOREIGN KEY (anime_id) REFERENCES animes (id) ON DELETE CASCADE
                );
            """)

            # 6. Promokodlar
            await db.execute("""
                CREATE TABLE IF NOT EXISTS promo_codes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    code TEXT UNIQUE NOT NULL,
                    duration_days INTEGER NOT NULL,
                    plan_name TEXT NOT NULL,
                    max_uses INTEGER DEFAULT 1,
                    used_count INTEGER DEFAULT 0,
                    is_active INTEGER DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    expires_at TIMESTAMP
                );
            """)

            # 7. Promokod ishlatilgani
            await db.execute("""
                CREATE TABLE IF NOT EXISTS promo_usages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    promo_id INTEGER NOT NULL,
                    user_id INTEGER NOT NULL,
                    used_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(promo_id, user_id)
                );
            """)

            # 8. Sevimlilar
            await db.execute("""
                CREATE TABLE IF NOT EXISTS favorites (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    anime_id INTEGER NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(user_id, anime_id)
                );
            """)

            # 9. Ko'rish tarixi
            await db.execute("""
                CREATE TABLE IF NOT EXISTS watch_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    anime_id INTEGER NOT NULL,
                    episode_number INTEGER NOT NULL,
                    watched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)

            # 10. Reytinglar
            await db.execute("""
                CREATE TABLE IF NOT EXISTS anime_ratings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    anime_id INTEGER NOT NULL,
                    score INTEGER NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(user_id, anime_id)
                );
            """)

            # 11. To'lov cheklari (Kvitansiyalar)
            await db.execute("""
                CREATE TABLE IF NOT EXISTS payment_requests (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    plan_key TEXT NOT NULL,
                    plan_name TEXT NOT NULL,
                    amount TEXT NOT NULL,
                    receipt_file_id TEXT NOT NULL,
                    status TEXT DEFAULT 'pending',
                    admin_id INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)

            # 12. Bot sozlamalari
            await db.execute("""
                CREATE TABLE IF NOT EXISTS bot_settings (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    description TEXT
                );
            """)

            await db.execute("""
                INSERT OR IGNORE INTO bot_settings (key, value, description)
                VALUES 
                    ('maintenance_mode', '0', 'Texnik tanaffus'),
                    ('welcome_text', 'default', 'Xush kelibsiz matni'),
                    ('bot_active', '1', 'Bot holati');
            """)

            await db.execute("""
                INSERT OR IGNORE INTO admins (user_id, full_name, can_upload, can_edit, can_delete, can_post, can_broadcast)
                VALUES (?, ?, 1, 1, 1, 1, 1);
            """, (BotConfig.OWNER_ID, "Bosh Boshqaruvchi (Owner)"))

            await db.commit()
            logger.info("Ma'lumotlar bazasi barcha jadvallari yaratildi.")

    # --- FOYDALANUVCHILAR ---

    async def register_or_update_user(self, user_id: int, full_name: str, username: Optional[str] = None) -> Dict[str, Any]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
            user = await cursor.fetchone()

            if user_id == BotConfig.OWNER_ID:
                role = "owner"
            elif user:
                role = user["role"]
            else:
                role = "user"

            if not user:
                current_mode = "admin" if role in ("owner", "admin") else "user"
                await db.execute("""
                    INSERT INTO users (user_id, full_name, username, role, current_mode)
                    VALUES (?, ?, ?, ?, ?)
                """, (user_id, full_name, username, role, current_mode))
                await db.commit()
                cursor = await db.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
                user = await cursor.fetchone()
            else:
                await db.execute("""
                    UPDATE users 
                    SET full_name = ?, username = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE user_id = ?
                """, (full_name, username, user_id))
                await db.commit()

            return dict(user)

    async def get_user(self, user_id: int) -> Optional[Dict[str, Any]]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
            row = await cursor.fetchone()
            return dict(row) if row else None

    async def set_user_mode(self, user_id: int, mode: str):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("UPDATE users SET current_mode = ? WHERE user_id = ?", (mode, user_id))
            await db.commit()

    async def check_user_vip(self, user_id: int) -> bool:
        if user_id == BotConfig.OWNER_ID:
            return True
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT vip_until, role FROM users WHERE user_id = ?", (user_id,))
            user = await cursor.fetchone()
            if not user:
                return False
            if user["role"] in ("owner", "admin"):
                return True
            if not user["vip_until"]:
                return False
            try:
                vip_date = datetime.datetime.fromisoformat(user["vip_until"])
                return vip_date > datetime.datetime.now()
            except Exception:
                return False

    async def _grant_vip_in_transaction(self, conn, user_id: int, days: int, plan_name: str) -> datetime.datetime:
        if days <= 0:
            raise ValueError("VIP muddati musbat bo'lishi kerak")
        cursor = await conn.execute("SELECT vip_until FROM users WHERE user_id = ?", (user_id,))
        row = await cursor.fetchone()
        if row is None:
            raise ValueError("Foydalanuvchi bazada mavjud emas")
        now = datetime.datetime.now()
        start_date = now
        if row["vip_until"]:
            try:
                start_date = max(datetime.datetime.fromisoformat(row["vip_until"]), now)
            except (ValueError, TypeError):
                pass
        new_until = start_date + datetime.timedelta(days=days)
        await conn.execute("""
            UPDATE users SET vip_until = ?, vip_plan = ?,
                role = CASE WHEN role IN ('owner', 'admin') THEN role ELSE 'vip' END
            WHERE user_id = ?
        """, (new_until.isoformat(), plan_name, user_id))
        return new_until

    async def grant_vip(self, user_id: int, days: int, plan_name: str) -> datetime.datetime:
        async with aiosqlite.connect(self.db_path) as conn:
            conn.row_factory = aiosqlite.Row
            await conn.execute("BEGIN IMMEDIATE")
            new_until = await self._grant_vip_in_transaction(conn, user_id, days, plan_name)
            await conn.commit()
            return new_until

    async def increment_user_download(self, user_id: int):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("UPDATE users SET downloads_count = downloads_count + 1 WHERE user_id = ?", (user_id,))
            await db.commit()

    async def update_user_setting(self, user_id: int, field: str, value: Any):
        allowed = {"notifications_enabled", "preferred_quality", "language"}
        if field not in allowed:
            return
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(f"UPDATE users SET {field} = ? WHERE user_id = ?", (value, user_id))
            await db.commit()

    # --- SEVIMLILAR VA KO'RISH TARIXI ---

    async def toggle_favorite(self, user_id: int, anime_id: int) -> Tuple[bool, int]:
        """Sevimlilarga qo'shish yoki olib tashlash."""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("SELECT id FROM favorites WHERE user_id = ? AND anime_id = ?", (user_id, anime_id))
            row = await cursor.fetchone()
            if row:
                await db.execute("DELETE FROM favorites WHERE user_id = ? AND anime_id = ?", (user_id, anime_id))
                is_added = False
            else:
                await db.execute("INSERT INTO favorites (user_id, anime_id) VALUES (?, ?)", (user_id, anime_id))
                is_added = True
            await db.commit()

            count_cur = await db.execute("SELECT COUNT(*) FROM favorites WHERE user_id = ?", (user_id,))
            total = (await count_cur.fetchone())[0]
            return is_added, total

    async def is_favorite(self, user_id: int, anime_id: int) -> bool:
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("SELECT id FROM favorites WHERE user_id = ? AND anime_id = ?", (user_id, anime_id))
            return (await cursor.fetchone()) is not None

    async def get_user_favorites(self, user_id: int) -> List[Dict[str, Any]]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("""
                SELECT a.* FROM animes a
                INNER JOIN favorites f ON a.id = f.anime_id
                WHERE f.user_id = ? ORDER BY f.id DESC
            """, (user_id,))
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]

    async def log_watch_history(self, user_id: int, anime_id: int, episode_number: int):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT INTO watch_history (user_id, anime_id, episode_number)
                VALUES (?, ?, ?)
            """, (user_id, anime_id, episode_number))
            await db.commit()

    async def get_watch_history(self, user_id: int, limit: int = 8) -> List[Dict[str, Any]]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("""
                SELECT w.episode_number, w.watched_at, a.title, a.code, a.id as anime_id
                FROM watch_history w
                INNER JOIN animes a ON a.id = w.anime_id
                WHERE w.user_id = ?
                ORDER BY w.id DESC LIMIT ?
            """, (user_id, limit))
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]

    # --- REYTING TIZIMI ---

    async def rate_anime(self, user_id: int, anime_id: int, score: int) -> float:
        """Animeni baholash va o'rtacha reytingni qaytarish."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT OR REPLACE INTO anime_ratings (user_id, anime_id, score)
                VALUES (?, ?, ?)
            """, (user_id, anime_id, score))

            # Yangi o'rtacha qiymatni hisoblash
            cursor = await db.execute("""
                SELECT AVG(score), COUNT(*) FROM anime_ratings WHERE anime_id = ?
            """, (anime_id,))
            row = await cursor.fetchone()
            avg_rating = round(row[0] or 5.0, 2)
            count = row[1] or 1

            await db.execute("""
                UPDATE animes SET rating = ?, rating_count = ? WHERE id = ?
            """, (avg_rating, count, anime_id))
            await db.commit()
            return avg_rating

    # --- TO'LOV CHEKLARI (KVITANSIYALAR) ---

    async def create_payment_request(self, user_id: int, plan_key: str, plan_name: str, amount: str, receipt_file_id: str) -> int:
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("""
                INSERT INTO payment_requests (user_id, plan_key, plan_name, amount, receipt_file_id)
                VALUES (?, ?, ?, ?, ?)
            """, (user_id, plan_key, plan_name, amount, receipt_file_id))
            await db.commit()
            return cursor.lastrowid

    async def approve_payment_request(self, request_id: int, admin_id: int) -> Optional[Dict[str, Any]]:
        if not await self.is_admin(admin_id):
            return None
        async with aiosqlite.connect(self.db_path) as conn:
            conn.row_factory = aiosqlite.Row
            await conn.execute("BEGIN IMMEDIATE")
            cursor = await conn.execute("SELECT * FROM payment_requests WHERE id = ? AND status = 'pending'", (request_id,))
            req = await cursor.fetchone()
            if not req:
                return None
            plan = BotConfig.VIP_PRICES.get(req["plan_key"])
            if plan is None:
                raise ValueError("Noma'lum VIP tarifi")
            await self._grant_vip_in_transaction(conn, req["user_id"], plan["days"], plan["name"])
            await conn.execute("UPDATE payment_requests SET status = 'approved', admin_id = ? WHERE id = ?", (admin_id, request_id))
            await conn.commit()
            return dict(req)

    async def reject_payment_request(self, request_id: int, admin_id: int) -> Optional[Dict[str, Any]]:
        if not await self.is_admin(admin_id):
            return None
        async with aiosqlite.connect(self.db_path) as conn:
            conn.row_factory = aiosqlite.Row
            await conn.execute("BEGIN IMMEDIATE")
            cursor = await conn.execute("SELECT * FROM payment_requests WHERE id = ? AND status = 'pending'", (request_id,))
            req = await cursor.fetchone()
            if not req:
                return None
            await conn.execute("UPDATE payment_requests SET status = 'rejected', admin_id = ? WHERE id = ?", (admin_id, request_id))
            await conn.commit()
            return dict(req)

    # --- ANIMELAR ---

    async def add_anime(self, data: Dict[str, Any]) -> int:
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("""
                INSERT INTO animes (
                    code, title, original_title, year, quality, voiceover, 
                    genres, description, poster_file_id, is_vip, status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                str(data["code"]).strip(),
                data["title"].strip(),
                data.get("original_title", ""),
                int(data.get("year", 2024)),
                data.get("quality", "1080p Full HD"),
                data.get("voiceover", "O'zbekcha"),
                data["genres"],
                data.get("description", ""),
                data.get("poster_file_id", ""),
                int(data.get("is_vip", 0)),
                data.get("status", "Davom etmoqda")
            ))
            await db.commit()
            return cursor.lastrowid

    async def update_anime(self, anime_id: int, field: str, value: Any):
        allowed = {"title", "poster_file_id", "is_vip", "description", "original_title", "year", "quality", "voiceover", "genres", "status"}
        if field not in allowed:
            return
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(f"UPDATE animes SET {field} = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?", (value, anime_id))
            await db.commit()

    async def delete_anime(self, anime_id: int):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("DELETE FROM episodes WHERE anime_id = ?", (anime_id,))
            await db.execute("DELETE FROM animes WHERE id = ?", (anime_id,))
            await db.commit()

    async def get_anime_by_code(self, code: str) -> Optional[Dict[str, Any]]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT * FROM animes WHERE code = ?", (str(code).strip(),))
            row = await cursor.fetchone()
            if row:
                anime = dict(row)
                await db.execute("UPDATE animes SET views_count = views_count + 1 WHERE id = ?", (anime["id"],))
                await db.commit()
                return anime
            return None

    async def get_anime_by_id(self, anime_id: int) -> Optional[Dict[str, Any]]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT * FROM animes WHERE id = ?", (anime_id,))
            row = await cursor.fetchone()
            return dict(row) if row else None

    async def search_anime_by_title(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("""
                SELECT * FROM animes 
                WHERE title LIKE ? OR original_title LIKE ? OR code LIKE ?
                ORDER BY views_count DESC LIMIT ?
            """, (f"%{query}%", f"%{query}%", f"%{query}%", limit))
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]

    async def get_random_anime(self) -> Optional[Dict[str, Any]]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT * FROM animes ORDER BY RANDOM() LIMIT 1")
            row = await cursor.fetchone()
            return dict(row) if row else None

    async def get_top_animes(self, limit: int = 10) -> List[Dict[str, Any]]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT * FROM animes ORDER BY views_count DESC, rating DESC LIMIT ?", (limit,))
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]

    async def get_latest_animes(self, limit: int = 10) -> List[Dict[str, Any]]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT * FROM animes ORDER BY id DESC LIMIT ?", (limit,))
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]

    async def get_oldest_animes(self, limit: int = 10) -> List[Dict[str, Any]]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT * FROM animes ORDER BY year ASC, id ASC LIMIT ?", (limit,))
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]

    async def get_animes_by_genre(self, genre: str, page: int = 1, per_page: int = 6) -> Tuple[List[Dict[str, Any]], int]:
        offset = (page - 1) * per_page
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            count_cur = await db.execute("SELECT COUNT(*) FROM animes WHERE genres LIKE ?", (f"%{genre}%",))
            total = (await count_cur.fetchone())[0]

            cursor = await db.execute("""
                SELECT * FROM animes WHERE genres LIKE ? ORDER BY views_count DESC LIMIT ? OFFSET ?
            """, (f"%{genre}%", per_page, offset))
            rows = await cursor.fetchall()
            return [dict(r) for r in rows], total

    async def get_all_animes(self, page: int = 1, per_page: int = 6) -> Tuple[List[Dict[str, Any]], int]:
        offset = (page - 1) * per_page
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            count_cur = await db.execute("SELECT COUNT(*) FROM animes")
            total = (await count_cur.fetchone())[0]

            cursor = await db.execute("""
                SELECT * FROM animes ORDER BY id DESC LIMIT ? OFFSET ?
            """, (per_page, offset))
            rows = await cursor.fetchall()
            return [dict(r) for r in rows], total

    # --- QISMLAR (EPIZODLAR) ---

    async def add_episode(self, data: Dict[str, Any]) -> int:
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("""
                INSERT OR REPLACE INTO episodes (
                    anime_id, anime_code, episode_number, episode_title, 
                    file_id, file_type, file_size, is_vip
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                data["anime_id"],
                str(data["anime_code"]),
                int(data["episode_number"]),
                data.get("episode_title", f"{data['episode_number']}-qism"),
                data["file_id"],
                data.get("file_type", "video"),
                data.get("file_size", "Noma'lum"),
                int(data.get("is_vip", 0))
            ))
            await db.execute("""
                UPDATE animes 
                SET total_episodes = (SELECT COUNT(*) FROM episodes WHERE anime_id = ?),
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (data["anime_id"], data["anime_id"]))
            await db.commit()
            return cursor.lastrowid

    async def get_episodes(self, anime_id: int) -> List[Dict[str, Any]]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("""
                SELECT * FROM episodes WHERE anime_id = ? ORDER BY episode_number ASC
            """, (anime_id,))
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]

    async def get_episode_by_num(self, anime_id: int, episode_num: int) -> Optional[Dict[str, Any]]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("""
                SELECT * FROM episodes WHERE anime_id = ? AND episode_number = ?
            """, (anime_id, episode_num))
            row = await cursor.fetchone()
            if row:
                await db.execute("UPDATE episodes SET views = views + 1 WHERE id = ?", (row["id"],))
                await db.commit()
                return dict(row)
            return None

    # --- KANALLAR ---

    async def get_channels(self, only_mandatory: bool = True) -> List[Dict[str, Any]]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            sql = "SELECT * FROM channels WHERE is_mandatory = 1" if only_mandatory else "SELECT * FROM channels"
            cursor = await db.execute(sql)
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]

    async def add_channel(self, channel_id: str, title: str, invite_link: str, is_mandatory: int = 1):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT INTO channels (channel_id, title, invite_link, is_mandatory)
                VALUES (?, ?, ?, ?)
            """, (channel_id, title, invite_link, is_mandatory))
            await db.commit()

    async def delete_channel(self, channel_db_id: int):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("DELETE FROM channels WHERE id = ?", (channel_db_id,))
            await db.commit()

    # --- ADMINLAR ---

    async def get_admins(self) -> List[Dict[str, Any]]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT * FROM admins ORDER BY id ASC")
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]

    async def add_admin(self, user_id: int, full_name: str, added_by: int) -> bool:
        async with aiosqlite.connect(self.db_path) as db:
            try:
                await db.execute("""
                    INSERT INTO admins (user_id, full_name, added_by)
                    VALUES (?, ?, ?)
                """, (user_id, full_name, added_by))
                await db.execute("UPDATE users SET role = 'admin' WHERE user_id = ?", (user_id,))
                await db.commit()
                return True
            except Exception:
                return False

    async def remove_admin(self, user_id: int):
        if user_id == BotConfig.OWNER_ID:
            return False
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("DELETE FROM admins WHERE user_id = ?", (user_id,))
            await db.execute("UPDATE users SET role = 'user', current_mode = 'user' WHERE user_id = ?", (user_id,))
            await db.commit()
            return True

    async def is_admin(self, user_id: int) -> bool:
        if user_id == BotConfig.OWNER_ID:
            return True
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("SELECT id FROM admins WHERE user_id = ?", (user_id,))
            row = await cursor.fetchone()
            return row is not None

    # --- PROMOKODLAR ---

    async def create_promo_code(self, code: str, days: int, plan_name: str, max_uses: int = 1) -> bool:
        if not code.strip() or days <= 0 or max_uses <= 0:
            return False
        async with aiosqlite.connect(self.db_path) as db:
            try:
                await db.execute("""
                    INSERT INTO promo_codes (code, duration_days, plan_name, max_uses)
                    VALUES (?, ?, ?, ?)
                """, (code.strip().upper(), days, plan_name, max_uses))
                await db.commit()
                return True
            except Exception:
                return False

    async def redeem_promo_code(self, code: str, user_id: int) -> Tuple[bool, str]:
        clean_code = code.strip().upper()
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            await db.execute("BEGIN IMMEDIATE")
            cursor = await db.execute("SELECT * FROM promo_codes WHERE code = ? AND is_active = 1", (clean_code,))
            promo = await cursor.fetchone()

            if not promo:
                return False, "❌ Bunday promokod mavjud emas yoki muddati tugagan!"

            if promo["expires_at"]:
                try:
                    expires = datetime.datetime.fromisoformat(promo["expires_at"])
                    if expires <= datetime.datetime.now(expires.tzinfo):
                        return False, "❌ Ushbu promokodning muddati tugagan!"
                except ValueError:
                    return False, "❌ Promokod muddati noto'g'ri sozlangan!"

            if promo["used_count"] >= promo["max_uses"]:
                return False, "❌ Ushbu promokoddan foydalanish limiti tugagan!"

            usage_cur = await db.execute("SELECT id FROM promo_usages WHERE promo_id = ? AND user_id = ?", (promo["id"], user_id))
            if await usage_cur.fetchone():
                return False, "⚠️ Siz allaqachon ushbu promokoddan foydalangansiz!"

            new_date = await self._grant_vip_in_transaction(db, user_id, promo["duration_days"], promo["plan_name"])
            
            await db.execute("INSERT INTO promo_usages (promo_id, user_id) VALUES (?, ?)", (promo["id"], user_id))
            await db.execute("""
                UPDATE promo_codes 
                SET used_count = used_count + 1, 
                    is_active = CASE WHEN used_count + 1 >= max_uses THEN 0 ELSE 1 END
                WHERE id = ?
            """, (promo["id"],))
            await db.commit()

            formatted_date = new_date.strftime("%d.%m.%Y %H:%M")
            msg = (
                f"🎉 Tabriklaymiz! Sizga {promo['duration_days']} kunlik VIP obunasi faollashtirildi!\n"
                f"📅 VIP amal qilish muddati: {formatted_date}"
            )
            return True, msg

    async def get_all_promos(self) -> List[Dict[str, Any]]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT * FROM promo_codes ORDER BY id DESC")
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]

    # --- STATISTIKA VA SOZLAMALAR ---

    async def get_bot_statistics(self) -> Dict[str, Any]:
        async with aiosqlite.connect(self.db_path) as db:
            users_count = (await (await db.execute("SELECT COUNT(*) FROM users")).fetchone())[0]
            vips_count = (await (await db.execute("SELECT COUNT(*) FROM users WHERE role = 'vip' OR vip_until IS NOT NULL")).fetchone())[0]
            animes_count = (await (await db.execute("SELECT COUNT(*) FROM animes")).fetchone())[0]
            episodes_count = (await (await db.execute("SELECT COUNT(*) FROM episodes")).fetchone())[0]
            downloads_count = (await (await db.execute("SELECT SUM(downloads_count) FROM users")).fetchone())[0] or 0
            channels_count = (await (await db.execute("SELECT COUNT(*) FROM channels")).fetchone())[0]
            
            return {
                "users_count": users_count,
                "vips_count": vips_count,
                "animes_count": animes_count,
                "episodes_count": episodes_count,
                "downloads_count": downloads_count,
                "channels_count": channels_count
            }

    async def get_all_user_ids(self) -> List[int]:
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("SELECT user_id FROM users WHERE is_banned = 0")
            rows = await cursor.fetchall()
            return [r[0] for r in rows]

    async def toggle_maintenance(self) -> bool:
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("SELECT value FROM bot_settings WHERE key = 'maintenance_mode'")
            row = await cursor.fetchone()
            current = row[0] if row else "0"
            new_val = "0" if current == "1" else "1"
            await db.execute("UPDATE bot_settings SET value = ? WHERE key = 'maintenance_mode'", (new_val,))
            await db.commit()
            return new_val == "1"

    async def is_maintenance(self) -> bool:
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("SELECT value FROM bot_settings WHERE key = 'maintenance_mode'")
            row = await cursor.fetchone()
            return (row[0] if row else "0") == "1"

db = Database()

# ==============================================================================
#                      3. FILTERLAR VA MIDDLEWARELAR
# ==============================================================================

class IsOwnerFilter(BaseFilter):
    async def __call__(self, message: Union[Message, CallbackQuery]) -> bool:
        return message.from_user.id == BotConfig.OWNER_ID


class IsAdminFilter(BaseFilter):
    async def __call__(self, message: Union[Message, CallbackQuery]) -> bool:
        user_id = message.from_user.id
        if user_id == BotConfig.OWNER_ID:
            return True
        return await db.is_admin(user_id)


class UserModeFilter(BaseFilter):
    def __init__(self, mode: str):
        self.mode = mode

    async def __call__(self, message: Union[Message, CallbackQuery]) -> bool:
        user_id = message.from_user.id
        user_data = await db.get_user(user_id)
        if not user_data:
            return self.mode == "user"
        return user_data.get("current_mode", "user") == self.mode


class UserTrackingMiddleware(BaseMiddleware):
    async def __call__(self, handler, event: Union[Message, CallbackQuery], data: Dict[str, Any]):
        user = data.get("event_from_user")
        if user and not user.is_bot:
            user_info = await db.register_or_update_user(
                user_id=user.id,
                full_name=user.full_name,
                username=user.username
            )
            data["user_info"] = user_info
        return await handler(event, data)


class AntiSpamMiddleware(BaseMiddleware):
    def __init__(self, limit_seconds: float = BotConfig.RATE_LIMIT_SECONDS):
        self.limit = limit_seconds
        self.users_timestamps: Dict[int, float] = {}

    async def __call__(self, handler, event: Union[Message, CallbackQuery], data: Dict[str, Any]):
        user = data.get("event_from_user")
        if user:
            now = time.time()
            last_time = self.users_timestamps.get(user.id, 0)
            if now - last_time < self.limit:
                if isinstance(event, CallbackQuery):
                    await event.answer("⚠️ Iltimos, biroz kuting...", show_alert=False)
                return
            self.users_timestamps[user.id] = now
        return await handler(event, data)


async def check_mandatory_subscriptions(bot: Bot, user_id: int) -> Tuple[bool, List[Dict[str, Any]]]:
    channels = await db.get_channels(only_mandatory=True)
    if not channels:
        return True, []

    unsubscribed = []
    for channel in channels:
        try:
            member = await bot.get_chat_member(chat_id=channel["channel_id"], user_id=user_id)
            if member.status in (ChatMemberStatus.LEFT, ChatMemberStatus.KICKED) or (
                member.status == ChatMemberStatus.RESTRICTED and not getattr(member, "is_member", False)
            ):
                unsubscribed.append(channel)
        except Exception as e:
            logger.warning(f"Kanal obunasini tekshirishda xato ({channel['channel_id']}): {e}")
            # API xatosini muvaffaqiyatli obuna deb qabul qilmaslik.
            unsubscribed.append(channel)

    return len(unsubscribed) == 0, unsubscribed

# ==============================================================================
#                       4. FSM HOLATLARI (STATESGROUP)
# ==============================================================================

class AnimeUploadStates(StatesGroup):
    waiting_for_code = State()
    waiting_for_title = State()
    waiting_for_orig_title = State()
    waiting_for_year = State()
    waiting_for_quality = State()
    waiting_for_voiceover = State()
    waiting_for_genres = State()
    waiting_for_description = State()
    waiting_for_poster = State()
    waiting_for_is_vip = State()
    confirm_upload = State()


class EpisodeUploadStates(StatesGroup):
    waiting_for_anime_code = State()
    waiting_for_episode_num = State()
    waiting_for_episode_title = State()
    waiting_for_video_file = State()
    waiting_for_is_vip = State()
    confirm_episode = State()


class AnimeEditStates(StatesGroup):
    waiting_for_anime_code = State()
    selecting_field = State()
    waiting_for_new_value = State()


class CustomPostStates(StatesGroup):
    waiting_for_anime_code = State()
    waiting_for_media = State()
    waiting_for_post_text = State()
    waiting_for_channel = State()
    confirm_post = State()


class SearchStates(StatesGroup):
    waiting_for_code_search = State()
    waiting_for_name_search = State()


class PromoCreateStates(StatesGroup):
    waiting_for_code_name = State()
    waiting_for_duration = State()
    waiting_for_max_uses = State()
    waiting_for_plan_name = State()


class PromoRedeemStates(StatesGroup):
    waiting_for_promo_code = State()


class ReceiptUploadStates(StatesGroup):
    waiting_for_receipt_photo = State()


class ChannelManageStates(StatesGroup):
    waiting_for_channel_id = State()
    waiting_for_channel_title = State()
    waiting_for_invite_link = State()


class AdminManageStates(StatesGroup):
    waiting_for_admin_user_id = State()
    waiting_for_admin_name = State()


class BroadcastStates(StatesGroup):
    waiting_for_message = State()
    confirm_broadcast = State()


class ReportBrokenStates(StatesGroup):
    waiting_for_reason = State()

# ==============================================================================
#                  5. KLAVIATURALAR VA KNOPKALAR MODULI
# ==============================================================================

class Keyboards:
    """Barcha rangli reply va inline klaviaturalarni shakllantiruvchi yordamchi klass."""

    @staticmethod
    def get_main_menu(role: str = "user", current_mode: str = "user") -> ReplyKeyboardMarkup:
        builder = ReplyKeyboardBuilder()
        builder.row(
            KeyboardButton(text=f"{Emojis.SEARCH} Anime Izlash"),
            KeyboardButton(text=f"{Emojis.BOOK} Qo'llanma")
        )
        builder.row(
            KeyboardButton(text=f"{Emojis.DIAMOND} VIP Obuna"),
            KeyboardButton(text=f"{Emojis.BELL} Kanallarimiz")
        )
        builder.row(
            KeyboardButton(text=f"{Emojis.GEAR} Sozlamalar")
        )

        if role in ("owner", "admin"):
            if current_mode == "admin":
                label = f"{Emojis.CROWN} Owner Panel" if role == "owner" else f"{Emojis.SHIELD} Admin Panel"
                builder.row(
                    KeyboardButton(text=label),
                    KeyboardButton(text=f"{Emojis.USER} Foydalanuvchi rejimi")
                )
            else:
                builder.row(
                    KeyboardButton(text=f"{Emojis.CROWN} Admin/Owner rejimiga qaytish")
                )

        return builder.as_markup(resize_keyboard=True)

    @staticmethod
    def get_search_inline_menu() -> InlineKeyboardMarkup:
        builder = InlineKeyboardBuilder()
        builder.row(
            InlineKeyboardButton(text="🔢 Kod orqali izlash", callback_data="search_by_code"),
            InlineKeyboardButton(text="🔤 Nomi bo'yicha", callback_data="search_by_name")
        )
        builder.row(
            InlineKeyboardButton(text="🎲 Tasodifiy anime", callback_data="search_random"),
            InlineKeyboardButton(text="🏆 Top 10 Animelar", callback_data="search_top")
        )
        builder.row(
            InlineKeyboardButton(text="🆕 Eng yangi animelar", callback_data="search_latest"),
            InlineKeyboardButton(text="⏳ Klassik animelar", callback_data="search_oldest")
        )
        builder.row(
            InlineKeyboardButton(text="🎭 Janrlar bo'yicha", callback_data="search_genres_p1"),
            InlineKeyboardButton(text="📚 Barcha katalog", callback_data="catalog_page_1")
        )
        builder.row(
            InlineKeyboardButton(text=f"{Emojis.BACK} Bosh sahifaga qaytish", callback_data="back_to_home")
        )
        return builder.as_markup()

    @staticmethod
    def get_genres_keyboard(page: int = 1) -> InlineKeyboardMarkup:
        builder = InlineKeyboardBuilder()
        genres = BotConfig.AVAILABLE_GENRES
        per_page = 8
        total_pages = math.ceil(len(genres) / per_page)
        start = (page - 1) * per_page
        end = start + per_page
        current_genres = genres[start:end]

        for i in range(0, len(current_genres), 2):
            if i + 1 < len(current_genres):
                builder.row(
                    InlineKeyboardButton(text=f"✨ {current_genres[i]}", callback_data=f"genre_{current_genres[i]}_1"),
                    InlineKeyboardButton(text=f"✨ {current_genres[i+1]}", callback_data=f"genre_{current_genres[i+1]}_1")
                )
            else:
                builder.row(
                    InlineKeyboardButton(text=f"✨ {current_genres[i]}", callback_data=f"genre_{current_genres[i]}_1")
                )

        nav_buttons = []
        if page > 1:
            nav_buttons.append(InlineKeyboardButton(text="◀️ Oldingi", callback_data=f"search_genres_p{page-1}"))
        if page < total_pages:
            nav_buttons.append(InlineKeyboardButton(text="Keyingi ▶️", callback_data=f"search_genres_p{page+1}"))
        if nav_buttons:
            builder.row(*nav_buttons)

        builder.row(InlineKeyboardButton(text="🔙 Qidiruv menyusiga", callback_data="open_search_menu"))
        return builder.as_markup()

    @staticmethod
    def get_anime_card_keyboard(anime_id: int, code: str, is_vip: bool, total_episodes: int, user_has_vip: bool, is_fav: bool = False, bot_username: str = "") -> InlineKeyboardMarkup:
        builder = InlineKeyboardBuilder()
        builder.row(
            InlineKeyboardButton(
                text=f"{Emojis.FILM} Qismlarni tomosha qilish ({total_episodes} ta)",
                callback_data=f"anime_eps_{anime_id}_1"
            )
        )
        deep_link = f"https://t.me/{bot_username}?start=anime_{code}"
        share_url = "https://t.me/share/url?url=" + quote(deep_link, safe="") + "&text=" + quote(f"Ajoyib anime tomosha qiling! Kod: {code}")
        fav_label = f"{Emojis.BROKEN_HEART} Sevimlilardan olish" if is_fav else f"{Emojis.HEART} Sevimlilarga saqlash"
        
        builder.row(
            InlineKeyboardButton(text=fav_label, callback_data=f"fav_toggle_{anime_id}"),
            InlineKeyboardButton(text="⭐ Baholash", callback_data=f"rate_prompt_{anime_id}")
        )
        builder.row(
            InlineKeyboardButton(text="🚀 Do'stlarga ulashish", url=share_url),
            InlineKeyboardButton(text="⚠️ Shikoyat", callback_data=f"report_broken_{anime_id}")
        )

        if is_vip and not user_has_vip:
            builder.row(
                InlineKeyboardButton(text=f"{Emojis.DIAMOND} VIP Obuna olish", callback_data="open_vip_menu")
            )

        builder.row(
            InlineKeyboardButton(text=f"{Emojis.BACK} Orqaga", callback_data="open_search_menu")
        )
        return builder.as_markup()

    @staticmethod
    def get_rating_keyboard(anime_id: int) -> InlineKeyboardMarkup:
        builder = InlineKeyboardBuilder()
        stars = [
            InlineKeyboardButton(text="1 ⭐", callback_data=f"rate_submit_{anime_id}_1"),
            InlineKeyboardButton(text="2 ⭐", callback_data=f"rate_submit_{anime_id}_2"),
            InlineKeyboardButton(text="3 ⭐", callback_data=f"rate_submit_{anime_id}_3"),
            InlineKeyboardButton(text="4 ⭐", callback_data=f"rate_submit_{anime_id}_4"),
            InlineKeyboardButton(text="5 ⭐", callback_data=f"rate_submit_{anime_id}_5"),
        ]
        builder.row(*stars)
        builder.row(InlineKeyboardButton(text="🔙 Bekor qilish", callback_data=f"show_anime_id_{anime_id}"))
        return builder.as_markup()

    @staticmethod
    def get_episodes_grid(anime_id: int, total_episodes: int, page: int = 1, user_is_vip: bool = False, anime_is_vip: bool = False, episode_numbers: Optional[List[int]] = None) -> InlineKeyboardMarkup:
        builder = InlineKeyboardBuilder()
        per_page = 20
        numbers = list(episode_numbers) if episode_numbers is not None else list(range(1, total_episodes + 1))
        total_pages = max(1, math.ceil(len(numbers) / per_page))
        page = max(1, min(page, total_pages))
        start = (page - 1) * per_page

        row_buttons = []
        for ep in numbers[start:start + per_page]:
            btn_text = f"▶️ {ep}-qism"
            row_buttons.append(
                InlineKeyboardButton(text=btn_text, callback_data=f"get_ep_{anime_id}_{ep}")
            )
            if len(row_buttons) == 4:
                builder.row(*row_buttons)
                row_buttons = []
        if row_buttons:
            builder.row(*row_buttons)

        nav = []
        if page > 1:
            nav.append(InlineKeyboardButton(text="◀️", callback_data=f"anime_eps_{anime_id}_{page-1}"))
        nav.append(InlineKeyboardButton(text=f"📄 {page}/{total_pages}", callback_data="noop"))
        if page < total_pages:
            nav.append(InlineKeyboardButton(text="▶️", callback_data=f"anime_eps_{anime_id}_{page+1}"))
        builder.row(*nav)

        builder.row(
            InlineKeyboardButton(text=f"{Emojis.BACK} Anime kartasiga", callback_data=f"show_anime_id_{anime_id}")
        )
        return builder.as_markup()

    @staticmethod
    def get_subscription_keyboard(unsubscribed_channels: List[Dict[str, Any]]) -> InlineKeyboardMarkup:
        builder = InlineKeyboardBuilder()
        for idx, channel in enumerate(unsubscribed_channels, 1):
            builder.row(
                InlineKeyboardButton(
                    text=f"📢 {idx}. {channel['title']}",
                    url=channel["invite_link"]
                )
            )
        builder.row(
            InlineKeyboardButton(text="✅ Obunani tekshirish", callback_data="verify_subscription")
        )
        return builder.as_markup()

    @staticmethod
    def get_vip_menu_keyboard() -> InlineKeyboardMarkup:
        builder = InlineKeyboardBuilder()
        builder.row(
            InlineKeyboardButton(text="💎 1 Oylik VIP - 15,000 so'm", callback_data="buy_vip_1_month"),
        )
        builder.row(
            InlineKeyboardButton(text="💎 3 Oylik VIP - 35,000 so'm", callback_data="buy_vip_3_months"),
        )
        builder.row(
            InlineKeyboardButton(text="🔥 1 Yillik VIP - 100,000 so'm", callback_data="buy_vip_1_year"),
        )
        builder.row(
            InlineKeyboardButton(text="👑 Cheksiz (Lifetime) - 200,000 so'm", callback_data="buy_vip_lifetime"),
        )
        builder.row(
            InlineKeyboardButton(text="🔑 Promokodni faollashtirish", callback_data="redeem_promo_btn"),
            InlineKeyboardButton(text="👤 Admin bilan bog'lanish", url=BotConfig.SUPPORT_URL)
        )
        builder.row(
            InlineKeyboardButton(text=f"{Emojis.BACK} Bosh sahifaga", callback_data="back_to_home")
        )
        return builder.as_markup()

    @staticmethod
    def get_admin_panel_keyboard(is_owner: bool = False) -> InlineKeyboardMarkup:
        builder = InlineKeyboardBuilder()
        builder.row(
            InlineKeyboardButton(text=f"{Emojis.ADD} Anime yuklash", callback_data="admin_upload_anime"),
            InlineKeyboardButton(text=f"{Emojis.FILM} Qism qo'shish", callback_data="admin_add_episode")
        )
        builder.row(
            InlineKeyboardButton(text=f"{Emojis.EDIT} Animeni tahrirlash", callback_data="admin_edit_anime"),
            InlineKeyboardButton(text=f"{Emojis.BELL} Post tayyorlash", callback_data="admin_make_post")
        )
        builder.row(
            InlineKeyboardButton(text=f"{Emojis.STATS} Statistika", callback_data="admin_view_stats"),
            InlineKeyboardButton(text=f"{Emojis.BROADCAST} Xabarnoma", callback_data="admin_broadcast")
        )
        if is_owner:
            builder.row(
                InlineKeyboardButton(text=f"{Emojis.CROWN} Owner boshqaruvi", callback_data="owner_main_menu")
            )
        builder.row(
            InlineKeyboardButton(text=f"{Emojis.USER} Foydalanuvchi rejimiga o'tish", callback_data="switch_to_user_mode"),
            InlineKeyboardButton(text=f"{Emojis.BACK} Chiqish", callback_data="back_to_home")
        )
        return builder.as_markup()

    @staticmethod
    def get_owner_panel_keyboard() -> InlineKeyboardMarkup:
        builder = InlineKeyboardBuilder()
        builder.row(
            InlineKeyboardButton(text="📢 Kanallar (Majburiy obuna)", callback_data="owner_manage_channels"),
            InlineKeyboardButton(text="👥 Adminlar boshqaruvi", callback_data="owner_manage_admins")
        )
        builder.row(
            InlineKeyboardButton(text="🔑 VIP Promokod generatsiya", callback_data="owner_create_promo"),
            InlineKeyboardButton(text="⚙️ Bot sozlamalari", callback_data="owner_bot_settings")
        )
        builder.row(
            InlineKeyboardButton(text=f"{Emojis.BACK} Admin panelga qaytish", callback_data="open_admin_panel")
        )
        return builder.as_markup()

    @staticmethod
    def get_settings_keyboard(notify_enabled: bool, quality: str, lang: str) -> InlineKeyboardMarkup:
        builder = InlineKeyboardBuilder()
        notify_text = "🔔 Bildirishnomalar: Yoqilgan ✅" if notify_enabled else "🔕 Bildirishnomalar: O'chirilgan ❌"
        builder.row(InlineKeyboardButton(text=notify_text, callback_data="settings_toggle_notify"))
        builder.row(InlineKeyboardButton(text=f"🎬 Sifat: {quality}", callback_data="settings_quality_menu"))
        builder.row(InlineKeyboardButton(text=f"🌐 Til: {lang}", callback_data="settings_lang_menu"))
        builder.row(
            InlineKeyboardButton(text="❤️ Sevimlilarim", callback_data="my_favorites_list"),
            InlineKeyboardButton(text="📜 Ko'rish tarixi", callback_data="my_history_list")
        )
        builder.row(InlineKeyboardButton(text=f"{Emojis.BACK} Bosh sahifaga", callback_data="back_to_home"))
        return builder.as_markup()

    @staticmethod
    def get_cancel_markup() -> ReplyKeyboardMarkup:
        builder = ReplyKeyboardBuilder()
        builder.row(KeyboardButton(text=f"{Emojis.CROSS} Bekor qilish"))
        return builder.as_markup(resize_keyboard=True)

    @staticmethod
    def get_skip_and_cancel_markup() -> ReplyKeyboardMarkup:
        builder = ReplyKeyboardBuilder()
        builder.row(
            KeyboardButton(text="⏭ O'tkazib yuborish"),
            KeyboardButton(text=f"{Emojis.CROSS} Bekor qilish")
        )
        return builder.as_markup(resize_keyboard=True)

# ==============================================================================
#                  6. FOYDALANUVCHI BUYRUQLARI VA MENYULARI
# ==============================================================================

user_router = Router(name="user_router")


@user_router.message(CommandStart())
async def handle_start_command(message: Message, state: FSMContext, bot: Bot):
    await state.clear()
    user_id = message.from_user.id
    full_name = html.escape(message.from_user.full_name)
    
    user_data = await db.register_or_update_user(user_id, message.from_user.full_name, message.from_user.username)
    role = user_data.get("role", "user")
    current_mode = user_data.get("current_mode", "user")
    is_vip = await db.check_user_vip(user_id)

    args = message.text.split(maxsplit=1)
    if len(args) > 1:
        param = args[1].strip()
        if param.startswith("anime_"):
            anime_code = param.replace("anime_", "").strip()
            anime = await db.get_anime_by_code(anime_code)
            if anime:
                await send_anime_card(message, anime, is_vip)
                return
        elif param.startswith("ep_"):
            parts_param = param[3:].rsplit("_", 1)
            if len(parts_param) == 2 and re.fullmatch(r"[0-9]{1,9}", parts_param[1]):
                code = parts_param[0]
                ep_num = int(parts_param[1])
                anime = await db.get_anime_by_code(code)
                if anime:
                    episode = await db.get_episode_by_num(anime["id"], ep_num)
                    if episode:
                        await deliver_episode_file(message, anime, episode, is_vip, bot)
                        return

    role_badge = "👑 Bosh Boshqaruvchi (Owner)" if role == "owner" else (
        "🛡️ Moderator (Admin)" if role == "admin" else (
            "💎 VIP A'zo" if is_vip else "👤 Oddiy Tomoshabin"
        )
    )

    welcome_text = (
        f"Assalomu alaykum va xush kelibsiz, <b>{full_name}</b>!\n\n"
        f"🎬 <b>AnimeUz Pro</b> — O'zbekistondagi eng tezkor, qulay va keng qamrovli "
        f"professional Telegram anime platformasiga qadam qo'ydingiz.\n\n"
        f"📊 <b>Sizning profilingiz:</b>\n"
        f"├ 🆔 <b>ID:</b> <code>{user_id}</code>\n"
        f"├ 🎖 <b>Maqomingiz:</b> {role_badge}\n"
        f"└ 💎 <b>VIP Holati:</b> {'Faol ✅' if is_vip else 'Nofaol ❌'}\n\n"
        f"✨ <i>Istalgan animeni maxsus kod orqali, nomi bo'yicha yoki toifalar orqali "
        f"bir zumda topib, eng yuqori 1080p sifatda tomosha qilishingiz mumkin!</i>\n\n"
        f"👇 Kerakli bo'limni tanlash uchun quyidagi tugmalardan foydalaning:"
    )

    await message.answer(
        text=welcome_text,
        parse_mode=ParseMode.HTML,
        reply_markup=Keyboards.get_main_menu(role, current_mode)
    )


@user_router.message(F.text == f"{Emojis.SEARCH} Anime Izlash")
async def handle_search_menu_button(message: Message):
    text = (
        f"🔍 <b>Anime qidiruv markazi</b>\n\n"
        f"O'zingizga qulay qidiruv usulini tanlang:\n"
        f"• <b>Kod orqali izlash</b> — Animening raqamli kodi (masalan: <code>101</code>)\n"
        f"• <b>Nomi bo'yicha</b> — Anime nomi yoki kalit so'z orqali\n"
        f"• <b>Tasodifiy anime</b> — Yangi sarguzasht kashf qilish uchun\n"
        f"• <b>Top va Eng yangilar</b> — Eng ommabop shoular\n"
        f"• <b>Janrlar</b> — Sevimli toifangiz bo'yicha saralash"
    )
    await message.answer(
        text=text,
        parse_mode=ParseMode.HTML,
        reply_markup=Keyboards.get_search_inline_menu()
    )


@user_router.message(F.text == f"{Emojis.BOOK} Qo'llanma")
async def handle_guide_button(message: Message):
    text = (
        f"📖 <b>Botdan foydalanish bo'yicha to'liq qo'llanma</b>\n\n"
        f"1️⃣ <b>Kod orqali qanday topiladi?</b>\n"
        f"Kanalimizdagi postlarda ko'rsatilgan kodni botga shunchaki yuboring (masalan: <code>101</code>) "
        f"yoki 'Anime Izlash' bo'limi orqali kiriting. Bot darhol anime tafsilotlari va qismlarini taqdim etadi.\n\n"
        f"2️⃣ <b>Qismlarni yuklab olish:</b>\n"
        f"Anime sahifasidagi 'Qismlarni tomosha qilish' tugmasini bosing va kerakli epizodni tanlang. "
        f"Video bevosita Telegram orqali sifatli formatda yuboriladi.\n\n"
        f"3️⃣ <b>VIP A'zolik nima beradi?</b>\n"
        f"• Barcha eksklyuziv va yangi animelarni birinchilardan bo'lib ko'rish\n"
        f"• Majburiy kanal obunalarisiz botdan to'liq foydalanish\n"
        f"• Cheklovsiz yuqori tezlikdagi yuklab olishlar\n"
        f"• Alohida VIP foydalanuvchi nishoni\n\n"
        f"4️⃣ <b>Savollar yoki muammo bo'lsa:</b>\n"
        f"Bizning qo'llab-quvvatlash xizmatimizga murojaat qiling: {BotConfig.SUPPORT_URL}"
    )
    await message.answer(text=text, parse_mode=ParseMode.HTML)


@user_router.message(F.text == f"{Emojis.DIAMOND} VIP Obuna")
async def handle_vip_button(message: Message):
    user_id = message.from_user.id
    is_vip = await db.check_user_vip(user_id)
    user_data = await db.get_user(user_id)
    
    status_str = "Sizda VIP obunasi FAOL emas ❌"
    if is_vip:
        until = user_data.get("vip_until", "Noma'lum")
        status_str = f"Sizning VIP obunangiz FAOL ✅\nMuddati: <b>{until}</b> gacha"

    text = (
        f"💎 <b>AnimeUz Premium VIP A'zolik</b>\n\n"
        f"Holat: {status_str}\n\n"
        f"<b>VIP imtiyozlari:</b>\n"
        f"✨ Reklama va majburiy obunalarsiz to'liq erkinlik\n"
        f"✨ Yangi chiqqan premyera animelar birinchi navbatda VIPda\n"
        f"✨ Maksimal 1080p Ultra HD formatdagi qismlar\n"
        f"✨ Cheksiz qismlarni bir zumda yuklab olish\n\n"
        f"👇 Quyidagi tariflardan birini tanlang yoki promokodingizni kiriting:"
    )
    await message.answer(
        text=text,
        parse_mode=ParseMode.HTML,
        reply_markup=Keyboards.get_vip_menu_keyboard()
    )


@user_router.message(F.text == f"{Emojis.BELL} Kanallarimiz")
async def handle_channels_button(message: Message):
    channels = await db.get_channels(only_mandatory=False)
    text = (
        f"📢 <b>Bizning rasmiy kanallarimiz va hamkorlar</b>\n\n"
        f"Bizning rasmiy tarmog'imizga qo'shiling va eng yangi animelardan birinchilardan xabardor bo'ling!\n\n"
        f"🔹 <b>Asosiy kanal:</b> {BotConfig.OFFICIAL_CHANNEL_USERNAME}\n"
    )
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="📢 Asosiy kanalga o'tish", url=BotConfig.OFFICIAL_CHANNEL_URL))
    
    for ch in channels:
        builder.row(InlineKeyboardButton(text=f"📌 {ch['title']}", url=ch["invite_link"]))
        
    await message.answer(text=text, parse_mode=ParseMode.HTML, reply_markup=builder.as_markup())


@user_router.message(F.text == f"{Emojis.GEAR} Sozlamalar")
async def handle_settings_button(message: Message):
    user_id = message.from_user.id
    user_data = await db.get_user(user_id) or {}
    notify = bool(user_data.get("notifications_enabled", 1))
    quality = user_data.get("preferred_quality", "1080p Full HD")
    lang = user_data.get("language", "O'zbekcha 🇺🇿")

    text = (
        f"⚙️ <b>Foydalanuvchi Sozlamalari</b>\n\n"
        f"👤 <b>Foydalanuvchi:</b> {message.from_user.full_name}\n"
        f"🆔 <b>Telegram ID:</b> <code>{user_id}</code>\n"
        f"📥 <b>Jami yuklab olingan qismlar:</b> {user_data.get('downloads_count', 0)} ta\n"
        f"🎭 <b>Tanlangan til:</b> {lang}\n"
        f"🎬 <b>Standart sifat:</b> {quality}\n\n"
        f"<i>Quyidagi tugmalar orqali sozlamalarni o'zingizga moslashtiring:</i>"
    )
    await message.answer(
        text=text,
        parse_mode=ParseMode.HTML,
        reply_markup=Keyboards.get_settings_keyboard(notify, quality, lang)
    )

# ==============================================================================
#                  7. ANIME QIDIRUV VA YUKLAB BERISH MANTIG'I
# ==============================================================================

search_router = Router(name="search_router")


async def safe_edit_text(callback: CallbackQuery, text: str, **kwargs):
    # Rasm/video xabarda edit_text ishlamaydi - bunday holda yangi xabar yuboriladi
    msg = callback.message
    if msg.photo or msg.video or msg.document:
        return await msg.answer(text, **kwargs)
    try:
        return await msg.edit_text(text, **kwargs)
    except TelegramBadRequest as e:
        if "message is not modified" in str(e):
            return None
        return await msg.answer(text, **kwargs)


async def send_anime_card(event: Union[Message, CallbackQuery], anime: Dict[str, Any], is_vip: bool):
    total_eps = anime.get("total_episodes", 0)
    vip_label = "💎 VIP Eksklyuziv" if anime.get("is_vip") else "🆓 Bepul tomosha"
    user_id = event.from_user.id
    is_fav = await db.is_favorite(user_id, anime["id"])

    year_val = anime.get("year") or "Noma'lum"
    voice_val = html.escape(str(anime.get("voiceover") or "O'zbekcha"))
    desc_val = html.escape(str(anime.get("description") or "Qisqacha tavsif mavjud emas."))
    genres_val = html.escape(str(anime.get("genres") or "Anime"))
    status_val = html.escape(str(anime.get("status") or "Davom etmoqda"))
    quality_val = html.escape(str(anime.get("quality") or "1080p"))

    caption = (
        f"🎬 <b>{html.escape(str(anime['title']))}</b>\n"
        f"<i>{html.escape(str(anime.get('original_title') or ''))}</i>\n\n"
        f"🔢 <b>Kodi:</b> <code>{html.escape(str(anime['code']))}</code>\n"
        f"📅 <b>Yili:</b> {year_val}\n"
        f"🎭 <b>Janrlari:</b> {genres_val}\n"
        f"🎙 <b>Ovoz beruvchi:</b> {voice_val}\n"
        f"🎥 <b>Sifati:</b> {quality_val}\n"
        f"📊 <b>Holati:</b> {status_val}\n"
        f"👁 <b>Ko'rishlar soni:</b> {anime.get('views_count', 0)}\n"
        f"⭐ <b>Reyting:</b> {anime.get('rating', 5.0)}/5.0 ({anime.get('rating_count', 1)} ovoz)\n"
        f"🔒 <b>Tomosha turi:</b> {vip_label}\n\n"
        f"📝 <b>Tavsifi:</b>\n"
        f"<i>{desc_val}</i>\n\n"
        f"📢 <b>Kanal:</b> {BotConfig.OFFICIAL_CHANNEL_USERNAME}"
    )

    markup = Keyboards.get_anime_card_keyboard(
        anime_id=anime["id"],
        code=anime["code"],
        is_vip=bool(anime.get("is_vip")),
        total_episodes=total_eps,
        user_has_vip=is_vip,
        is_fav=is_fav,
        bot_username=(await event.bot.me()).username
    )

    poster = anime.get("poster_file_id") or anime.get("poster_url")
    message = event.message if isinstance(event, CallbackQuery) else event

    if poster and (poster.startswith("http") or len(poster) > 15):
        try:
            await message.answer_photo(
                photo=poster,
                caption=caption,
                parse_mode=ParseMode.HTML,
                reply_markup=markup
            )
            return
        except Exception as e:
            logger.warning(f"Rasm yuklashda xatolik: {e}")

    await message.answer(
        text=caption,
        parse_mode=ParseMode.HTML,
        reply_markup=markup
    )


async def deliver_episode_file(event: Union[Message, CallbackQuery], anime: Dict[str, Any], episode: Dict[str, Any], user_is_vip: bool, bot: Bot):
    user_id = event.from_user.id
    target_msg = event.message if isinstance(event, CallbackQuery) else event

    # /start ep_<kod>_<qism> havolasi ham kirish tekshiruvidan o'tishi kerak.
    if not await db.is_admin(user_id):
        if await db.is_maintenance():
            await target_msg.answer("Bot texnik tanaffusda. Keyinroq urinib ko'ring.")
            return
        if not user_is_vip:
            subscribed, missing = await check_mandatory_subscriptions(bot, user_id)
            if not subscribed:
                await target_msg.answer(
                    "Avval kanallarga obuna bo'ling, so'ng obunani tekshiring.",
                    reply_markup=Keyboards.get_subscription_keyboard(missing)
                )
                return

    requires_vip = bool(anime.get("is_vip")) or bool(episode.get("is_vip"))
    if requires_vip and not user_is_vip:
        vip_alert = (
            f"🔒 <b>Kechirasiz, ushbu qism VIP tomoshabinlar uchun mo'ljallangan!</b>\n\n"
            f"🎬 <b>{html.escape(str(anime['title']))}</b> ({episode['episode_number']}-qism)\n\n"
            f"Ushbu qismni yuqori sifatda yuklab olish va boshqa barcha premyeralarni birinchilardan "
            f"ko'rish uchun VIP obunani xarid qiling!"
        )
        builder = InlineKeyboardBuilder()
        builder.row(InlineKeyboardButton(text="💎 VIP Obuna sotib olish", callback_data="open_vip_menu"))
        builder.row(InlineKeyboardButton(text="🔑 Promokod kiritish", callback_data="redeem_promo_btn"))
        await target_msg.answer(text=vip_alert, parse_mode=ParseMode.HTML, reply_markup=builder.as_markup())
        return

    loading_msg = await target_msg.answer("⏳ <i>Video tayyorlanmoqda, iltimos kuting...</i>", parse_mode=ParseMode.HTML)

    quality_val = html.escape(str(anime.get("quality") or "1080p Full HD"))
    voice_val = html.escape(str(anime.get("voiceover") or "O'zbekcha"))

    file_caption = (
        f"🎬 <b>{html.escape(str(anime['title']))}</b> | <b>{episode['episode_number']}-qism</b>\n\n"
        f"🔢 <b>Anime kodi:</b> <code>{html.escape(str(anime['code']))}</code>\n"
        f"🎥 <b>Sifati:</b> {quality_val}\n"
        f"🎙 <b>Ovoz:</b> {voice_val}\n\n"
        f"⚡ <i>Biz bilan birga bo'ling: {BotConfig.OFFICIAL_CHANNEL_USERNAME}</i>"
    )

    file_id = episode["file_id"]
    try:
        if episode.get("file_type") == "document":
            await bot.send_document(
                chat_id=user_id,
                document=file_id,
                caption=file_caption,
                parse_mode=ParseMode.HTML
            )
        else:
            await bot.send_video(
                chat_id=user_id,
                video=file_id,
                caption=file_caption,
                parse_mode=ParseMode.HTML,
                supports_streaming=True
            )
        await db.increment_user_download(user_id)
        await db.log_watch_history(user_id, anime["id"], episode["episode_number"])
        try:
            await loading_msg.delete()
        except Exception:
            pass
    except Exception as e:
        logger.error(f"Fayl yuborishda xato: {e}")
        await loading_msg.edit_text(
            "⚠️ <b>Faylni yuborishda xatolik yuz berdi!</b>\n"
            "Fayl serverda mavjud emas yoki xavfsizlik cheklovi mavjud. Iltimos adminga murojaat qiling.",
            parse_mode=ParseMode.HTML
        )


# --- SEVIMLILAR VA REYTING HANDLERLARI ---

@search_router.callback_query(F.data.startswith("fav_toggle_"))
async def cb_fav_toggle(callback: CallbackQuery):
    anime_id = int(callback.data.replace("fav_toggle_", ""))
    user_id = callback.from_user.id
    anime = await db.get_anime_by_id(anime_id)
    if not anime:
        await callback.answer("Anime topilmadi!", show_alert=True)
        return

    is_added, total = await db.toggle_favorite(user_id, anime_id)
    alert_text = f"❤️ '{anime['title']}' sevimlilarga qo'shildi! (Jami: {total} ta)" if is_added else f"💔 '{anime['title']}' sevimlilardan olindi!"
    await callback.answer(alert_text, show_alert=True)

    # Tugmani yangilash
    is_vip = await db.check_user_vip(user_id)
    await callback.message.edit_reply_markup(
        reply_markup=Keyboards.get_anime_card_keyboard(
            anime_id=anime["id"],
            code=anime["code"],
            is_vip=bool(anime.get("is_vip")),
            total_episodes=anime.get("total_episodes", 0),
            user_has_vip=is_vip,
            is_fav=is_added
        )
    )


@search_router.callback_query(F.data.startswith("rate_prompt_"))
async def cb_rate_prompt(callback: CallbackQuery):
    anime_id = int(callback.data.replace("rate_prompt_", ""))
    anime = await db.get_anime_by_id(anime_id)
    if not anime:
        await callback.answer("Anime topilmadi!", show_alert=True)
        return

    await safe_edit_text(
        callback,
        f"⭐ <b>'{anime['title']}' animeni baholang:</b>\n\n"
        f"1 dan 5 gacha baholang:",
        parse_mode=ParseMode.HTML,
        reply_markup=Keyboards.get_rating_keyboard(anime_id)
    )
    await callback.answer()


@search_router.callback_query(F.data.startswith("rate_submit_"))
async def cb_rate_submit(callback: CallbackQuery):
    parts = callback.data.split("_")
    anime_id = int(parts[2])
    score = int(parts[3])

    new_rating = await db.rate_anime(callback.from_user.id, anime_id, score)
    await callback.answer(f"⭐ Bahoyingiz qabul qilindi ({score}⭐)! Yangi o'rtacha reyting: {new_rating}/5.0", show_alert=True)

    anime = await db.get_anime_by_id(anime_id)
    is_vip = await db.check_user_vip(callback.from_user.id)
    if anime:
        await send_anime_card(callback, anime, is_vip)


@search_router.callback_query(F.data.startswith("report_broken_"))
async def cb_report_broken(callback: CallbackQuery):
    anime_id = int(callback.data.replace("report_broken_", ""))
    anime = await db.get_anime_by_id(anime_id)
    title = anime['title'] if anime else f"ID: {anime_id}"

    # Adminga xabar yuborish
    try:
        await callback.bot.send_message(
            chat_id=BotConfig.OWNER_ID,
            text=f"⚠️ <b>Shikoyat tushdi!</b>\n\nFoydalanuvchi: {html.escape(callback.from_user.full_name)} (<code>{callback.from_user.id}</code>)\nAnime: <b>{title}</b>\nHolat: Fayl ochilmadi yoki buzilgan.",
            parse_mode=ParseMode.HTML
        )
    except Exception:
        pass

    await callback.answer("✅ Shikoyatingiz qabul qilindi va moderatorlarga yetkazildi!", show_alert=True)


# --- QIDIRUV VA KATALOG ---

@search_router.callback_query(F.data == "search_by_code")
async def cb_search_by_code(callback: CallbackQuery, state: FSMContext):
    await state.set_state(SearchStates.waiting_for_code_search)
    text = (
        "🔢 <b>Animening kodini kiriting:</b>\n\n"
        "<i>Masalan: <code>101</code>, <code>102</code> yoki <code>205</code></i>\n"
        "Bekor qilish uchun /cancel buyrug'ini bering."
    )
    await callback.message.edit_text(text=text, parse_mode=ParseMode.HTML)
    await callback.answer()


@search_router.message(SearchStates.waiting_for_code_search)
async def process_code_search(message: Message, state: FSMContext):
    if not message.text or not message.text.strip():
        await message.answer("Iltimos, bu bosqichda matn yuboring. Bekor qilish: /cancel")
        return
    code = message.text.strip().replace("#", "")
    is_vip = await db.check_user_vip(message.from_user.id)
    anime = await db.get_anime_by_code(code)

    if anime:
        await state.clear()
        await send_anime_card(message, anime, is_vip)
    else:
        await message.answer(
            f"❌ <b>'{code}' kodli anime topilmadi!</b>\n"
            "Iltimos, kodni to'g'ri kiritganingizni tekshirib qaytadan urinib ko'ring yoki "
            "nomi bo'yicha qidiring.",
            parse_mode=ParseMode.HTML
        )


@search_router.callback_query(F.data == "search_by_name")
async def cb_search_by_name(callback: CallbackQuery, state: FSMContext):
    await state.set_state(SearchStates.waiting_for_name_search)
    text = (
        "🔤 <b>Qidirayotgan anime nomini yozing:</b>\n\n"
        "<i>Masalan: <code>Naruto</code>, <code>Attack on Titan</code>, <code>Solo Leveling</code></i>"
    )
    await callback.message.edit_text(text=text, parse_mode=ParseMode.HTML)
    await callback.answer()


@search_router.message(SearchStates.waiting_for_name_search)
async def process_name_search(message: Message, state: FSMContext):
    if not message.text or not message.text.strip():
        await message.answer("Iltimos, bu bosqichda matn yuboring. Bekor qilish: /cancel")
        return
    query = message.text.strip()
    results = await db.search_anime_by_title(query, limit=8)

    if not results:
        await message.answer(
            f"😔 <b>'{query}' bo'yicha hech qanday anime topilmadi.</b>\n"
            "Boshqa kalit so'z bilan qidirib ko'ring yoki barcha katalogimizni ko'zdan kechiring.",
            parse_mode=ParseMode.HTML
        )
        return

    await state.clear()
    builder = InlineKeyboardBuilder()
    for anime in results:
        builder.row(
            InlineKeyboardButton(
                text=f"🎬 {anime['title']} ({anime.get('year', '')}) [Kod: {anime['code']}]",
                callback_data=f"show_anime_id_{anime['id']}"
            )
        )
    builder.row(InlineKeyboardButton(text="🔙 Qidiruvga qaytish", callback_data="open_search_menu"))

    await message.answer(
        f"🔎 <b>'{query}' bo'yicha topilgan animelar:</b>",
        parse_mode=ParseMode.HTML,
        reply_markup=builder.as_markup()
    )


@search_router.callback_query(F.data == "search_random")
async def cb_search_random(callback: CallbackQuery):
    anime = await db.get_random_anime()
    if not anime:
        await callback.answer("Bazada hozircha animelar mavjud emas!", show_alert=True)
        return
    is_vip = await db.check_user_vip(callback.from_user.id)
    await send_anime_card(callback, anime, is_vip)
    await callback.answer()


@search_router.callback_query(F.data == "search_top")
async def cb_search_top(callback: CallbackQuery):
    top_list = await db.get_top_animes(limit=10)
    if not top_list:
        await callback.answer("Ro'yxat bo'sh!", show_alert=True)
        return

    builder = InlineKeyboardBuilder()
    for idx, anime in enumerate(top_list, 1):
        builder.row(
            InlineKeyboardButton(
                text=f"{idx}. ⭐ {anime['title']} (👁 {anime.get('views_count', 0)})",
                callback_data=f"show_anime_id_{anime['id']}"
            )
        )
    builder.row(InlineKeyboardButton(text="🔙 Qidiruv menyusiga", callback_data="open_search_menu"))

    await callback.message.edit_text(
        "🏆 <b>Eng ko'p ko'rilgan TOP 10 Animelar:</b>",
        parse_mode=ParseMode.HTML,
        reply_markup=builder.as_markup()
    )
    await callback.answer()


@search_router.callback_query(F.data == "search_latest")
async def cb_search_latest(callback: CallbackQuery):
    latest = await db.get_latest_animes(limit=8)
    if not latest:
        await callback.answer("Hozircha animelar yo'q!", show_alert=True)
        return

    builder = InlineKeyboardBuilder()
    for anime in latest:
        builder.row(
            InlineKeyboardButton(
                text=f"🆕 {anime['title']} [Kod: {anime['code']}]",
                callback_data=f"show_anime_id_{anime['id']}"
            )
        )
    builder.row(InlineKeyboardButton(text="🔙 Qidiruv menyusiga", callback_data="open_search_menu"))

    await callback.message.edit_text(
        "🆕 <b>Eng so'nggi qo'shilgan yangi animelar:</b>",
        parse_mode=ParseMode.HTML,
        reply_markup=builder.as_markup()
    )
    await callback.answer()


@search_router.callback_query(F.data == "search_oldest")
async def cb_search_oldest(callback: CallbackQuery):
    oldest = await db.get_oldest_animes(limit=8)
    builder = InlineKeyboardBuilder()
    for anime in oldest:
        builder.row(
            InlineKeyboardButton(
                text=f"⏳ {anime['title']} ({anime.get('year', '')})",
                callback_data=f"show_anime_id_{anime['id']}"
            )
        )
    builder.row(InlineKeyboardButton(text="🔙 Qidiruv menyusiga", callback_data="open_search_menu"))

    await callback.message.edit_text(
        "⏳ <b>Klassik va unutilmas animelar:</b>",
        parse_mode=ParseMode.HTML,
        reply_markup=builder.as_markup()
    )
    await callback.answer()


@search_router.callback_query(F.data.startswith("search_genres_p"))
async def cb_genres_page(callback: CallbackQuery):
    page = int(callback.data.replace("search_genres_p", ""))
    await callback.message.edit_text(
        "🎭 <b>O'zingizga yoqqan anime janrini tanlang:</b>",
        parse_mode=ParseMode.HTML,
        reply_markup=Keyboards.get_genres_keyboard(page)
    )
    await callback.answer()


@search_router.callback_query(F.data.startswith("genre_"))
async def cb_genre_selected(callback: CallbackQuery):
    parts = callback.data.split("_")
    genre = parts[1]
    page = int(parts[2]) if len(parts) > 2 else 1

    animes, total = await db.get_animes_by_genre(genre, page=page, per_page=6)
    if not animes:
        await callback.answer(f"'{genre}' janrida hozircha anime topilmadi!", show_alert=True)
        return

    builder = InlineKeyboardBuilder()
    for a in animes:
        builder.row(
            InlineKeyboardButton(text=f"🎬 {a['title']} ({a.get('year', '')})", callback_data=f"show_anime_id_{a['id']}")
        )

    total_pages = max(1, math.ceil(total / 6))
    nav = []
    if page > 1:
        nav.append(InlineKeyboardButton(text="◀️", callback_data=f"genre_{genre}_{page-1}"))
    nav.append(InlineKeyboardButton(text=f"{page}/{total_pages}", callback_data="noop"))
    if page < total_pages:
        nav.append(InlineKeyboardButton(text="▶️", callback_data=f"genre_{genre}_{page+1}"))
    if nav:
        builder.row(*nav)

    builder.row(InlineKeyboardButton(text="🎭 Janrlar ro'yxati", callback_data="search_genres_p1"))

    await callback.message.edit_text(
        f"🎭 <b>'{genre}' janridagi animelar:</b> (Jami: {total} ta)",
        parse_mode=ParseMode.HTML,
        reply_markup=builder.as_markup()
    )
    await callback.answer()


@search_router.callback_query(F.data.startswith("catalog_page_"))
async def cb_catalog_page(callback: CallbackQuery):
    page = int(callback.data.replace("catalog_page_", ""))
    animes, total = await db.get_all_animes(page=page, per_page=6)

    if not animes:
        await callback.answer("Katalogda hech qanday anime mavjud emas!", show_alert=True)
        return

    total_pages = max(1, math.ceil(total / 6))
    builder = InlineKeyboardBuilder()
    for a in animes:
        builder.row(
            InlineKeyboardButton(text=f"🎬 {a['title']} [Kod: {a['code']}]", callback_data=f"show_anime_id_{a['id']}")
        )

    nav = []
    if page > 1:
        nav.append(InlineKeyboardButton(text="◀️ Oldingi", callback_data=f"catalog_page_{page-1}"))
    nav.append(InlineKeyboardButton(text=f"📄 {page}/{total_pages}", callback_data="noop"))
    if page < total_pages:
        nav.append(InlineKeyboardButton(text="Keyingi ▶️", callback_data=f"catalog_page_{page+1}"))
    builder.row(*nav)
    builder.row(InlineKeyboardButton(text="🔙 Qidiruv menyusiga", callback_data="open_search_menu"))

    await callback.message.edit_text(
        f"📚 <b>Barcha animelar katalogi:</b> (Jami: {total} ta)",
        parse_mode=ParseMode.HTML,
        reply_markup=builder.as_markup()
    )
    await callback.answer()


@search_router.callback_query(F.data.startswith("show_anime_id_"))
async def cb_show_anime_details(callback: CallbackQuery):
    anime_id = int(callback.data.replace("show_anime_id_", ""))
    anime = await db.get_anime_by_id(anime_id)
    if not anime:
        await callback.answer("Anime topilmadi!", show_alert=True)
        return
    is_vip = await db.check_user_vip(callback.from_user.id)
    await send_anime_card(callback, anime, is_vip)
    await callback.answer()


@search_router.callback_query(F.data.startswith("anime_eps_"))
async def cb_show_episodes_grid(callback: CallbackQuery):
    parts = callback.data.split("_")
    anime_id = int(parts[2])
    page = int(parts[3]) if len(parts) > 3 else 1

    anime = await db.get_anime_by_id(anime_id)
    if not anime:
        await callback.answer("Anime topilmadi!", show_alert=True)
        return

    is_vip = await db.check_user_vip(callback.from_user.id)
    episodes = await db.get_episodes(anime_id)
    total_eps = len(episodes)

    if total_eps == 0:
        await callback.answer("Ushbu animening qismlari tez orada yuklanadi!", show_alert=True)
        return

    await callback.message.edit_reply_markup(
        reply_markup=Keyboards.get_episodes_grid(
            anime_id=anime_id,
            total_episodes=total_eps,
            page=page,
            user_is_vip=is_vip,
            anime_is_vip=bool(anime.get("is_vip")),
            episode_numbers=[ep["episode_number"] for ep in episodes]
        )
    )
    await callback.answer()


@search_router.callback_query(F.data.startswith("get_ep_"))
async def cb_get_episode(callback: CallbackQuery, bot: Bot):
    parts = callback.data.split("_")
    anime_id = int(parts[2])
    ep_num = int(parts[3])

    anime = await db.get_anime_by_id(anime_id)
    if not anime:
        await callback.answer("Anime topilmadi!", show_alert=True)
        return

    episode = await db.get_episode_by_num(anime_id, ep_num)
    if not episode:
        await callback.answer(f"{ep_num}-qism fayli hali yuklanmagan!", show_alert=True)
        return

    is_vip = await db.check_user_vip(callback.from_user.id)
    await deliver_episode_file(callback, anime, episode, is_vip, bot)
    await callback.answer()


@search_router.message(StateFilter(None), F.text.regexp(r"^#?([a-zA-Z0-9_\-]{1,15})$"))
async def handle_direct_code_input(message: Message):
    code = message.text.strip().replace("#", "")
    anime = await db.get_anime_by_code(code)
    if anime:
        is_vip = await db.check_user_vip(message.from_user.id)
        await send_anime_card(message, anime, is_vip)

# ==============================================================================
#                      8. VIP VA TO'LOV CHEKLARI BOSHQARUVI
# ==============================================================================

vip_router = Router(name="vip_router")


@vip_router.callback_query(F.data == "open_vip_menu")
async def cb_open_vip_menu(callback: CallbackQuery):
    user_id = callback.from_user.id
    is_vip = await db.check_user_vip(user_id)
    user_data = await db.get_user(user_id) or {}
    status_str = f"Faol ✅ ({user_data.get('vip_until', '')} gacha)" if is_vip else "Nofaol ❌"

    text = (
        f"💎 <b>AnimeUz Premium VIP A'zolik</b>\n\n"
        f"Sizning holatingiz: <b>{status_str}</b>\n\n"
        f"<b>VIP imtiyozlari:</b>\n"
        f"✨ Reklama va majburiy kanallarsiz to'liq erkinlik\n"
        f"✨ Eng sara premyera animelar birinchi navbatda sizga\n"
        f"✨ Yuqori 1080p Ultra HD formatdagi fayllar\n"
        f"✨ Alohida qo'llab-quvvatlash va cheksiz yuklashlar\n\n"
        f"O'zingizga ma'qul tarifni tanlang:"
    )
    await callback.message.edit_text(text=text, parse_mode=ParseMode.HTML, reply_markup=Keyboards.get_vip_menu_keyboard())
    await callback.answer()


@vip_router.callback_query(F.data.startswith("buy_vip_"))
async def cb_buy_vip_plan(callback: CallbackQuery, state: FSMContext):
    plan_key = callback.data.replace("buy_", "")
    plan = BotConfig.VIP_PRICES.get(plan_key)
    if not plan:
        await callback.answer("Tarif topilmadi!", show_alert=True)
        return

    await state.update_data(chosen_plan_key=plan_key, chosen_plan_name=plan['name'], chosen_amount=plan['label'])

    text = (
        f"💎 <b>{plan['name']} tarifini rasmiylashtirish</b>\n\n"
        f"💰 <b>Narxi:</b> {plan['label']}\n"
        f"⏳ <b>Amal qilish muddati:</b> {plan['days']} kun\n\n"
        f"To'lov qilish uchun Click/Payme orqali quyidagi kartaga pul o'tkazing:\n"
        f"💳 <b>Karta:</b> <code>8600 0000 0000 0000</code>\n"
        f"👤 <b>Qabul qiluvchi:</b> AnimeUz Rasmiy\n\n"
        f"Pul o'tkazgach, <b>'📸 To'lov chekini yuborish'</b> tugmasini bosib, "
        f"skrinshot yoki chek rasmini botga yuboring!"
    )
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="📸 To'lov chekini yuborish", callback_data="upload_receipt_start"))
    builder.row(InlineKeyboardButton(text="🔙 Tariflarga qaytish", callback_data="open_vip_menu"))

    await callback.message.edit_text(text=text, parse_mode=ParseMode.HTML, reply_markup=builder.as_markup())
    await callback.answer()


@vip_router.callback_query(F.data == "upload_receipt_start")
async def start_upload_receipt(callback: CallbackQuery, state: FSMContext):
    await state.set_state(ReceiptUploadStates.waiting_for_receipt_photo)
    await callback.message.answer(
        "📸 <b>To'lov chekining rasmini (skrinshot) yuboring:</b>\n"
        "<i>To'lov tasdiqlanishi bilan profilingizga VIP avtomatik yoqiladi.</i>",
        parse_mode=ParseMode.HTML,
        reply_markup=Keyboards.get_cancel_markup()
    )
    await callback.answer()


@vip_router.message(ReceiptUploadStates.waiting_for_receipt_photo, F.photo)
async def process_receipt_photo(message: Message, state: FSMContext, bot: Bot):
    photo_file_id = message.photo[-1].file_id
    data = await state.get_data()
    plan_key = data.get("chosen_plan_key", "vip_1_month")
    plan_name = data.get("chosen_plan_name", "1 Oylik VIP")
    amount = data.get("chosen_amount", "15,000 so'm")

    req_id = await db.create_payment_request(
        user_id=message.from_user.id,
        plan_key=plan_key,
        plan_name=plan_name,
        amount=amount,
        receipt_file_id=photo_file_id
    )
    await state.clear()

    # Foydalanuvchiga tasdiq
    user = await db.get_user(message.from_user.id) or {}
    await message.answer(
        "✅ <b>To'lov cheki qabul qilindi!</b>\n\n"
        "Moderatorlarimiz to'lovni 5-15 daqiqa ichida tekshirib, VIP hisobingizni faollashtirishadi.\n"
        "Natijasi haqida shu yerda xabar olasiz.",
        parse_mode=ParseMode.HTML,
        reply_markup=Keyboards.get_main_menu(user.get("role", "user"), user.get("current_mode", "user"))
    )

    # Owner / Adminga yuborish
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="✅ Tasdiqlash", callback_data=f"approve_receipt_{req_id}"),
        InlineKeyboardButton(text="❌ Rad etish", callback_data=f"reject_receipt_{req_id}")
    )

    admin_caption = (
        f"💳 <b>Yangi to'lov cheki! (Sor'ov #{req_id})</b>\n\n"
        f"👤 Foydalanuvchi: {html.escape(message.from_user.full_name)}\n"
        f"🆔 ID: <code>{message.from_user.id}</code>\n"
        f"💎 Tarif: {plan_name} ({amount})"
    )

    try:
        await bot.send_photo(
            chat_id=BotConfig.OWNER_ID,
            photo=photo_file_id,
            caption=admin_caption,
            parse_mode=ParseMode.HTML,
            reply_markup=builder.as_markup()
        )
    except Exception as e:
        logger.error(f"Adminga chek yuborishda xato: {e}")


@vip_router.callback_query(F.data.startswith("approve_receipt_"))
async def cb_approve_receipt(callback: CallbackQuery, bot: Bot):
    if not await db.is_admin(callback.from_user.id):
        await callback.answer("Sizda bunday huquq yo'q!", show_alert=True)
        return
    req_id = int(callback.data.replace("approve_receipt_", ""))
    req = await db.approve_payment_request(req_id, callback.from_user.id)
    if not req:
        await callback.answer("So'rov allaqachon ko'rib chiqilgan!", show_alert=True)
        return

    await callback.message.edit_caption(
        caption=f"{html.escape(callback.message.caption or '')}\n\n✅ <b>TASDIQLANDI! Foydalanuvchiga VIP yoqildi.</b>",
        parse_mode=ParseMode.HTML
    )
    await callback.answer("VIP muvaffaqiyatli yoqildi!", show_alert=True)

    # Foydalanuvchiga bildirishnoma
    try:
        await bot.send_message(
            chat_id=req["user_id"],
            text=f"🎉 <b>Tabriklaymiz! To'lovingiz tasdiqlandi.</b>\n\nSizga <b>{req['plan_name']}</b> muvaffaqiyatli faollashtirildi! Barcha animelarni erkin va yuqori sifatda tomosha qiling.",
            parse_mode=ParseMode.HTML
        )
    except Exception:
        pass


@vip_router.callback_query(F.data.startswith("reject_receipt_"))
async def cb_reject_receipt(callback: CallbackQuery, bot: Bot):
    if not await db.is_admin(callback.from_user.id):
        await callback.answer("Sizda bunday huquq yo'q!", show_alert=True)
        return
    req_id = int(callback.data.replace("reject_receipt_", ""))
    req = await db.reject_payment_request(req_id, callback.from_user.id)
    if not req:
        await callback.answer("So'rov topilmadi!", show_alert=True)
        return

    await callback.message.edit_caption(
        caption=f"{html.escape(callback.message.caption or '')}\n\n❌ <b>RAD ETILDI.</b>",
        parse_mode=ParseMode.HTML
    )
    await callback.answer("To'lov rad etildi.", show_alert=True)

    try:
        await bot.send_message(
            chat_id=req["user_id"],
            text="❌ <b>Kechirasiz, siz yuborgan to'lov cheki tasdiqlanmadi.</b>\nChek noaniq yoki to'lov tushmagan. Iltimos adminga murojaat qiling: " + BotConfig.SUPPORT_URL,
            parse_mode=ParseMode.HTML
        )
    except Exception:
        pass


@vip_router.callback_query(F.data == "redeem_promo_btn")
async def cb_redeem_promo_start(callback: CallbackQuery, state: FSMContext):
    await state.set_state(PromoRedeemStates.waiting_for_promo_code)
    text = (
        "🔑 <b>VIP Promokodingizni kiriting:</b>\n\n"
        "<i>Agar sizda maxsus promokod bo'lsa, uni quyida yozib yuboring:</i>"
    )
    await callback.message.edit_text(text=text, parse_mode=ParseMode.HTML)
    await callback.answer()


@vip_router.message(PromoRedeemStates.waiting_for_promo_code)
async def process_promo_redeem(message: Message, state: FSMContext):
    if not message.text or not message.text.strip():
        await message.answer("Iltimos, bu bosqichda matn yuboring. Bekor qilish: /cancel")
        return
    code = message.text.strip()
    success, resp_text = await db.redeem_promo_code(code, message.from_user.id)
    await state.clear()
    await message.answer(text=resp_text, parse_mode=ParseMode.HTML)


# ==============================================================================
#                  9. SOZLAMALAR VA SHAXSIY RO'YXATLAR
# ==============================================================================

settings_router = Router(name="settings_router")


@settings_router.callback_query(F.data == "settings_toggle_notify")
async def cb_toggle_notify(callback: CallbackQuery):
    user_data = await db.get_user(callback.from_user.id) or {}
    cur = bool(user_data.get("notifications_enabled", 1))
    new_val = 0 if cur else 1
    await db.update_user_setting(callback.from_user.id, "notifications_enabled", new_val)

    alert = "🔕 Bildirishnomalar o'chirildi" if cur else "🔔 Bildirishnomalar yoqildi"
    await callback.answer(alert, show_alert=True)

    quality = user_data.get("preferred_quality", "1080p Full HD")
    lang = user_data.get("language", "O'zbekcha 🇺🇿")
    await callback.message.edit_reply_markup(
        reply_markup=Keyboards.get_settings_keyboard(not cur, quality, lang)
    )


@settings_router.callback_query(F.data == "settings_quality_menu")
async def cb_quality_menu(callback: CallbackQuery):
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="1080p Full HD", callback_data="set_quality_1080p"))
    builder.row(InlineKeyboardButton(text="720p HD", callback_data="set_quality_720p"))
    builder.row(InlineKeyboardButton(text="480p SD (Tejamkor)", callback_data="set_quality_480p"))
    builder.row(InlineKeyboardButton(text="🔙 Sozlamalarga", callback_data="open_settings_menu"))

    await callback.message.edit_text("🎬 <b>Standart yuklanuvchi sifatni tanlang:</b>", parse_mode=ParseMode.HTML, reply_markup=builder.as_markup())
    await callback.answer()


@settings_router.callback_query(F.data.startswith("set_quality_"))
async def cb_set_quality(callback: CallbackQuery):
    q_map = {"1080p": "1080p Full HD", "720p": "720p HD", "480p": "480p SD"}
    q_key = callback.data.replace("set_quality_", "")
    val = q_map.get(q_key, "1080p Full HD")

    await db.update_user_setting(callback.from_user.id, "preferred_quality", val)
    await callback.answer(f"Sifat {val} ga o'rnatildi!", show_alert=True)
    await cb_open_settings_menu(callback)


@settings_router.callback_query(F.data == "settings_lang_menu")
async def cb_lang_menu(callback: CallbackQuery):
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="🇺🇿 O'zbekcha (Lotin)", callback_data="set_lang_uz_lat"))
    builder.row(InlineKeyboardButton(text="🇺🇿 Ўзбекча (Кирилл)", callback_data="set_lang_uz_cyr"))
    builder.row(InlineKeyboardButton(text="🇷🇺 Русский", callback_data="set_lang_ru"))
    builder.row(InlineKeyboardButton(text="🔙 Sozlamalarga", callback_data="open_settings_menu"))

    await callback.message.edit_text("🌐 <b>Bot interfeysi tilini tanlang:</b>", parse_mode=ParseMode.HTML, reply_markup=builder.as_markup())
    await callback.answer()


@settings_router.callback_query(F.data.startswith("set_lang_"))
async def cb_set_lang(callback: CallbackQuery):
    l_map = {"uz_lat": "O'zbekcha (Lotin) 🇺🇿", "uz_cyr": "Ўзбекча (Кирилл) 🇺🇿", "ru": "Русский 🇷🇺"}
    l_key = callback.data.replace("set_lang_", "")
    val = l_map.get(l_key, "O'zbekcha (Lotin) 🇺🇿")

    await db.update_user_setting(callback.from_user.id, "language", val)
    await callback.answer(f"Til almashtirildi: {val}", show_alert=True)
    await cb_open_settings_menu(callback)


@settings_router.callback_query(F.data == "open_settings_menu")
async def cb_open_settings_menu(callback: CallbackQuery):
    user_id = callback.from_user.id
    user_data = await db.get_user(user_id) or {}
    notify = bool(user_data.get("notifications_enabled", 1))
    quality = user_data.get("preferred_quality", "1080p Full HD")
    lang = user_data.get("language", "O'zbekcha 🇺🇿")

    text = (
        f"⚙️ <b>Foydalanuvchi Sozlamalari</b>\n\n"
        f"👤 <b>Foydalanuvchi:</b> {callback.from_user.full_name}\n"
        f"🆔 <b>Telegram ID:</b> <code>{user_id}</code>\n"
        f"📥 <b>Jami yuklab olingan qismlar:</b> {user_data.get('downloads_count', 0)} ta\n"
        f"🎭 <b>Tanlangan til:</b> {lang}\n"
        f"🎬 <b>Standart sifat:</b> {quality}\n\n"
        f"<i>Quyidagi tugmalar orqali sozlamalarni o'zingizga moslashtiring:</i>"
    )
    await callback.message.edit_text(text=text, parse_mode=ParseMode.HTML, reply_markup=Keyboards.get_settings_keyboard(notify, quality, lang))
    await callback.answer()


@settings_router.callback_query(F.data == "my_favorites_list")
async def cb_favorites_list(callback: CallbackQuery):
    favs = await db.get_user_favorites(callback.from_user.id)
    if not favs:
        await callback.answer("Sizda hali saqlangan sevimli animelar yo'q!", show_alert=True)
        return

    builder = InlineKeyboardBuilder()
    for a in favs:
        builder.row(InlineKeyboardButton(text=f"🎬 {a['title']} [Kod: {a['code']}]", callback_data=f"show_anime_id_{a['id']}"))
    builder.row(InlineKeyboardButton(text="🔙 Sozlamalarga", callback_data="open_settings_menu"))

    await callback.message.edit_text(f"❤️ <b>Sizning sevimli animelaringiz ({len(favs)} ta):</b>", parse_mode=ParseMode.HTML, reply_markup=builder.as_markup())
    await callback.answer()


@settings_router.callback_query(F.data == "my_history_list")
async def cb_history_list(callback: CallbackQuery):
    hist = await db.get_watch_history(callback.from_user.id, limit=8)
    if not hist:
        await callback.answer("Ko'rishlar tarixi bo'sh!", show_alert=True)
        return

    text = "📜 <b>Oxirgi tomosha qilingan qismlar:</b>\n\n"
    builder = InlineKeyboardBuilder()
    for h in hist:
        text += f"• <b>{h['title']}</b> ({h['episode_number']}-qism) — <i>{h['watched_at']}</i>\n"
        builder.row(InlineKeyboardButton(text=f"▶️ {h['title']} ({h['episode_number']}-qism)", callback_data=f"show_anime_id_{h['anime_id']}"))

    builder.row(InlineKeyboardButton(text="🔙 Sozlamalarga", callback_data="open_settings_menu"))
    await callback.message.edit_text(text=text, parse_mode=ParseMode.HTML, reply_markup=builder.as_markup())
    await callback.answer()

# ==============================================================================
#                      10. ADMIN PANEL VA ANIME YUKLASH
# ==============================================================================

admin_router = Router(name="admin_router")
admin_router.message.filter(IsAdminFilter())
admin_router.callback_query.filter(IsAdminFilter())


@admin_router.message(Command("admin"))
@admin_router.message(F.text == f"{Emojis.SHIELD} Admin Panel")
@admin_router.message(F.text == f"{Emojis.CROWN} Owner Panel")
async def handle_admin_entry(message: Message, state: FSMContext):
    await state.clear()
    user_id = message.from_user.id
    is_owner = (user_id == BotConfig.OWNER_ID)
    
    stats = await db.get_bot_statistics()
    text = (
        f"🛡️ <b>AnimeUz Professional Admin Paneli</b>\n\n"
        f"Xush kelibsiz, <b>{html.escape(message.from_user.full_name)}</b>!\n"
        f"Maqomingiz: {'👑 Owner' if is_owner else '🛡️ Admin'}\n\n"
        f"📊 <b>Tezkor ko'rsatkichlar:</b>\n"
        f"├ 👥 Jami foydalanuvchilar: <b>{stats['users_count']}</b> ta\n"
        f"├ 💎 VIP a'zolar: <b>{stats['vips_count']}</b> ta\n"
        f"├ 🎬 Animelar soni: <b>{stats['animes_count']}</b> ta\n"
        f"├ 🎥 Jami qismlar: <b>{stats['episodes_count']}</b> ta\n"
        f"└ 📥 Yuklab olishlar: <b>{stats['downloads_count']}</b> ta\n\n"
        f"👇 Kerakli boshqaruv bo'limini tanlang:"
    )
    await message.answer(
        text=text,
        parse_mode=ParseMode.HTML,
        reply_markup=Keyboards.get_admin_panel_keyboard(is_owner)
    )


@admin_router.callback_query(F.data == "open_admin_panel")
async def cb_open_admin_panel(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    is_owner = (callback.from_user.id == BotConfig.OWNER_ID)
    stats = await db.get_bot_statistics()
    text = (
        f"🛡️ <b>Admin Boshqaruv Markazi</b>\n\n"
        f"👥 Foydalanuvchilar: <b>{stats['users_count']}</b> | "
        f"🎬 Animelar: <b>{stats['animes_count']}</b> | "
        f"💎 VIP: <b>{stats['vips_count']}</b>\n\n"
        f"Amalni tanlang:"
    )
    await callback.message.edit_text(text=text, parse_mode=ParseMode.HTML, reply_markup=Keyboards.get_admin_panel_keyboard(is_owner))
    await callback.answer()


@admin_router.callback_query(F.data == "admin_upload_anime")
async def start_anime_upload(callback: CallbackQuery, state: FSMContext):
    await state.set_state(AnimeUploadStates.waiting_for_code)
    text = (
        "➕ <b>Yangi anime qo'shish</b>\n\n"
        "1-qadam: Animening <b>Maxsus Kodi (Custom ID)</b>ni kiriting:\n"
        "<i>Masalan: <code>101</code>, <code>102</code>, <code>A15</code></i>\n\n"
        "Bekor qilish uchun /cancel deb yozing."
    )
    await callback.message.answer(text=text, parse_mode=ParseMode.HTML, reply_markup=Keyboards.get_cancel_markup())
    await callback.answer()


@admin_router.message(AnimeUploadStates.waiting_for_code)
async def process_upload_code(message: Message, state: FSMContext):
    if not message.text or not message.text.strip():
        await message.answer("Iltimos, bu bosqichda matn yuboring. Bekor qilish: /cancel")
        return
    code = message.text.strip().replace("#", "")
    existing = await db.get_anime_by_code(code)
    if existing:
        await message.answer(f"⚠️ <b>'{code}' kodli anime allaqachon mavjud!</b>\nIltimos, boshqa kod kiriting:")
        return

    await state.update_data(code=code)
    await state.set_state(AnimeUploadStates.waiting_for_title)
    await message.answer("2-qadam: <b>Anime nomini</b> kiriting:\n<i>Masalan: Solo Leveling</i>", parse_mode=ParseMode.HTML)


@admin_router.message(AnimeUploadStates.waiting_for_title)
async def process_upload_title(message: Message, state: FSMContext):
    if not message.text or not message.text.strip():
        await message.answer("Iltimos, bu bosqichda matn yuboring. Bekor qilish: /cancel")
        return
    await state.update_data(title=message.text.strip())
    await state.set_state(AnimeUploadStates.waiting_for_orig_title)
    await message.answer(
        "3-qadam: <b>Asl nomini (Yaponcha/Inglizcha)</b> kiriting yoki 'O'tkazib yuborish'ni bosing:",
        reply_markup=Keyboards.get_skip_and_cancel_markup()
    )


@admin_router.message(AnimeUploadStates.waiting_for_orig_title)
async def process_upload_orig_title(message: Message, state: FSMContext):
    if not message.text or not message.text.strip():
        await message.answer("Iltimos, bu bosqichda matn yuboring. Bekor qilish: /cancel")
        return
    val = "" if "O'tkazib" in message.text else message.text.strip()
    await state.update_data(original_title=val)
    await state.set_state(AnimeUploadStates.waiting_for_year)
    await message.answer("4-qadam: <b>Chiqqan yili</b>ni kiriting (Masalan: <code>2024</code>):", parse_mode=ParseMode.HTML)


@admin_router.message(AnimeUploadStates.waiting_for_year)
async def process_upload_year(message: Message, state: FSMContext):
    if not message.text or not message.text.strip():
        await message.answer("Iltimos, bu bosqichda matn yuboring. Bekor qilish: /cancel")
        return
    try:
        year = int(message.text.strip())
    except ValueError:
        year = 2024
    await state.update_data(year=year)
    await state.set_state(AnimeUploadStates.waiting_for_quality)
    await message.answer("5-qadam: <b>Sifatini</b> kiriting (Standart: <code>1080p Full HD</code>):", parse_mode=ParseMode.HTML)


@admin_router.message(AnimeUploadStates.waiting_for_quality)
async def process_upload_quality(message: Message, state: FSMContext):
    if not message.text or not message.text.strip():
        await message.answer("Iltimos, bu bosqichda matn yuboring. Bekor qilish: /cancel")
        return
    await state.update_data(quality=message.text.strip())
    await state.set_state(AnimeUploadStates.waiting_for_voiceover)
    await message.answer("6-qadam: <b>Ovoz beruvchi studiya/dublyaj</b>ni kiriting:\n<i>Masalan: AnimeUz Dublyaj</i>", parse_mode=ParseMode.HTML)


@admin_router.message(AnimeUploadStates.waiting_for_voiceover)
async def process_upload_voiceover(message: Message, state: FSMContext):
    if not message.text or not message.text.strip():
        await message.answer("Iltimos, bu bosqichda matn yuboring. Bekor qilish: /cancel")
        return
    await state.update_data(voiceover=message.text.strip())
    await state.set_state(AnimeUploadStates.waiting_for_genres)
    await message.answer("7-qadam: <b>Janrlarini</b> vergul bilan ajratib kiriting:\n<i>Masalan: Jangari, Sarguzasht, Fantastika</i>", parse_mode=ParseMode.HTML)


@admin_router.message(AnimeUploadStates.waiting_for_genres)
async def process_upload_genres(message: Message, state: FSMContext):
    if not message.text or not message.text.strip():
        await message.answer("Iltimos, bu bosqichda matn yuboring. Bekor qilish: /cancel")
        return
    await state.update_data(genres=message.text.strip())
    await state.set_state(AnimeUploadStates.waiting_for_description)
    await message.answer("8-qadam: <b>Qisqacha tavsifi (Sinopsis)</b>ni yozing:", parse_mode=ParseMode.HTML)


@admin_router.message(AnimeUploadStates.waiting_for_description)
async def process_upload_desc(message: Message, state: FSMContext):
    if not message.text or not message.text.strip():
        await message.answer("Iltimos, bu bosqichda matn yuboring. Bekor qilish: /cancel")
        return
    await state.update_data(description=message.text.strip())
    await state.set_state(AnimeUploadStates.waiting_for_poster)
    await message.answer(
        "9-qadam: Anime <b>Posteri (Rasmi)</b>ni rasm sifatida yuboring yoki rasm havolasini (URL) yozing:",
        parse_mode=ParseMode.HTML
    )


@admin_router.message(AnimeUploadStates.waiting_for_poster)
async def process_upload_poster(message: Message, state: FSMContext):
    if message.photo:
        poster_id = message.photo[-1].file_id
    elif message.text:
        poster_id = message.text.strip()
    else:
        poster_id = ""

    await state.update_data(poster_file_id=poster_id)
    await state.set_state(AnimeUploadStates.waiting_for_is_vip)

    builder = ReplyKeyboardBuilder()
    builder.row(KeyboardButton(text="🆓 Bepul"), KeyboardButton(text="💎 Faqat VIP"))
    await message.answer(
        "10-qadam: Ushbu anime <b>Bepul</b> bo'lsinmi yoki <b>Faqat VIP</b> a'zolarga?",
        reply_markup=builder.as_markup(resize_keyboard=True)
    )


@admin_router.message(AnimeUploadStates.waiting_for_is_vip)
async def process_upload_vip_and_save(message: Message, state: FSMContext):
    if not message.text or not message.text.strip():
        await message.answer("Iltimos, bu bosqichda matn yuboring. Bekor qilish: /cancel")
        return
    is_vip = 1 if "VIP" in message.text else 0
    await state.update_data(is_vip=is_vip)

    data = await state.get_data()
    await db.add_anime(data)
    await state.clear()

    user = await db.get_user(message.from_user.id) or {}
    await message.answer(
        f"✅ <b>Anime muvaffaqiyatli saqlandi!</b>\n\n"
        f"🎬 <b>Nomi:</b> {data['title']}\n"
        f"🔢 <b>Kodi:</b> <code>{data['code']}</code>\n"
        f"🔒 <b>Turi:</b> {'💎 Faqat VIP' if is_vip else '🆓 Bepul'}\n\n"
        f"Endi ushbu animega qismlar qo'shishingiz yoki kanalga post tayyorlashingiz mumkin!",
        parse_mode=ParseMode.HTML,
        reply_markup=Keyboards.get_main_menu(user.get("role", "admin"), user.get("current_mode", "admin"))
    )


@admin_router.callback_query(F.data == "admin_add_episode")
async def start_add_episode(callback: CallbackQuery, state: FSMContext):
    await state.set_state(EpisodeUploadStates.waiting_for_anime_code)
    text = (
        "🎬 <b>Animega yangi qism (epizod) yuklash</b>\n\n"
        "Qaysi animening kodi bo'yicha qism qo'shmoqchisiz?\n"
        "Anime kodini kiriting (Masalan: <code>101</code>):"
    )
    await callback.message.answer(text=text, parse_mode=ParseMode.HTML, reply_markup=Keyboards.get_cancel_markup())
    await callback.answer()


@admin_router.message(EpisodeUploadStates.waiting_for_anime_code)
async def process_ep_code(message: Message, state: FSMContext):
    if not message.text or not message.text.strip():
        await message.answer("Iltimos, bu bosqichda matn yuboring. Bekor qilish: /cancel")
        return
    code = message.text.strip().replace("#", "")
    anime = await db.get_anime_by_code(code)
    if not anime:
        await message.answer(f"❌ <b>'{code}' kodli anime bazadan topilmadi!</b>\nIltimos, qaytadan kiriting:")
        return

    await state.update_data(anime_id=anime["id"], anime_code=anime["code"], anime_title=anime["title"])
    await state.set_state(EpisodeUploadStates.waiting_for_episode_num)
    await message.answer(
        f"🎬 Anime: <b>{anime['title']}</b>\n\n"
        f"Endi <b>Qism raqami</b>ni kiriting (Masalan: <code>1</code>, <code>2</code>, <code>12</code>):",
        parse_mode=ParseMode.HTML
    )


@admin_router.message(EpisodeUploadStates.waiting_for_episode_num)
async def process_ep_num(message: Message, state: FSMContext):
    if not message.text or not message.text.strip():
        await message.answer("Iltimos, bu bosqichda matn yuboring. Bekor qilish: /cancel")
        return
    try:
        ep_num = int(message.text.strip())
        if ep_num <= 0:
            raise ValueError("Qism raqami musbat bo'lishi kerak")
    except ValueError:
        await message.answer("Iltimos, faqat musbat raqam kiriting (masalan: 1):")
        return

    await state.update_data(episode_number=ep_num)
    await state.set_state(EpisodeUploadStates.waiting_for_video_file)
    await message.answer(
        f"📹 <b>{ep_num}-qism video faylini yuboring:</b>\n"
        f"<i>Telegram video yoki hujjat (document) formatida to'g'ridan-to'g'ri yuboring.</i>",
        parse_mode=ParseMode.HTML
    )


@admin_router.message(EpisodeUploadStates.waiting_for_video_file, F.video | F.document)
async def process_ep_file(message: Message, state: FSMContext):
    if message.video:
        file_id = message.video.file_id
        file_type = "video"
        file_size = f"{round(message.video.file_size / (1024 * 1024), 1)} MB" if message.video.file_size else "Noma'lum"
    elif message.document:
        file_id = message.document.file_id
        file_type = "document"
        file_size = f"{round(message.document.file_size / (1024 * 1024), 1)} MB" if message.document.file_size else "Noma'lum"
    else:
        await message.answer("Iltimos, faqat video yoki hujjat yuboring!")
        return

    data = await state.get_data()
    await state.update_data(
        file_id=file_id,
        file_type=file_type,
        file_size=file_size,
    )
    await state.set_state(EpisodeUploadStates.waiting_for_is_vip)
    builder = ReplyKeyboardBuilder()
    builder.row(KeyboardButton(text="🆓 Bepul"), KeyboardButton(text="💎 Faqat VIP"))
    await message.answer(
        f"📹 Fayl qabul qilindi ({file_size}).\nUshbu qism <b>Bepul</b> bo'lsinmi yoki <b>Faqat VIP</b>?",
        parse_mode=ParseMode.HTML,
        reply_markup=builder.as_markup(resize_keyboard=True),
    )


@admin_router.message(EpisodeUploadStates.waiting_for_is_vip)
async def process_ep_vip(message: Message, state: FSMContext):
    if not message.text or not message.text.strip():
        await message.answer("Iltimos, bu bosqichda matn yuboring. Bekor qilish: /cancel")
        return
    data = await state.get_data()
    is_vip = 1 if "VIP" in (message.text or "") else 0
    ep_data = {
        "anime_id": data["anime_id"],
        "anime_code": data["anime_code"],
        "episode_number": data["episode_number"],
        "episode_title": f"{data['episode_number']}-qism",
        "file_id": data["file_id"],
        "file_type": data["file_type"],
        "file_size": data["file_size"],
        "is_vip": is_vip,
    }
    await db.add_episode(ep_data)
    await state.clear()

    user = await db.get_user(message.from_user.id) or {}
    await message.answer(
        f"🎉 <b>Qism muvaffaqiyatli yuklandi!</b>\n\n"
        f"🎬 <b>Anime:</b> {data['anime_title']}\n"
        f"▶️ <b>Qism:</b> {data['episode_number']}-qism\n"
        f"💾 <b>Hajmi:</b> {data['file_size']}\n\n"
        f"Foydalanuvchilar darhol ushbu qismni tomosha qilishlari mumkin!",
        parse_mode=ParseMode.HTML,
        reply_markup=Keyboards.get_main_menu(user.get("role", "admin"), user.get("current_mode", "admin"))
    )


@admin_router.callback_query(F.data == "admin_edit_anime")
async def start_edit_anime(callback: CallbackQuery, state: FSMContext):
    await state.set_state(AnimeEditStates.waiting_for_anime_code)
    await callback.message.answer(
        "✏️ Tahrirlamoqchi bo'lgan <b>Anime kodini</b> kiriting:",
        parse_mode=ParseMode.HTML,
        reply_markup=Keyboards.get_cancel_markup()
    )
    await callback.answer()


@admin_router.message(AnimeEditStates.waiting_for_anime_code)
async def process_edit_code(message: Message, state: FSMContext):
    if not message.text or not message.text.strip():
        await message.answer("Iltimos, bu bosqichda matn yuboring. Bekor qilish: /cancel")
        return
    code = message.text.strip().replace("#", "")
    anime = await db.get_anime_by_code(code)
    if not anime:
        await message.answer(f"❌ '{code}' kodli anime topilmadi!")
        return

    await state.update_data(anime_id=anime["id"], anime_code=code)
    await state.set_state(AnimeEditStates.selecting_field)

    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="✏️ Nomini o'zgartirish", callback_data="editfield_title"),
        InlineKeyboardButton(text="🖼 Posterni yangilash", callback_data="editfield_poster")
    )
    builder.row(
        InlineKeyboardButton(text="🔒 VIP/Bepul statusi", callback_data="editfield_is_vip"),
        InlineKeyboardButton(text="📝 Tavsifni yangilash", callback_data="editfield_desc")
    )
    builder.row(
        InlineKeyboardButton(text="🗑 Butunlay o'chirish", callback_data="editfield_delete")
    )
    builder.row(InlineKeyboardButton(text="🔙 Bekor qilish", callback_data="open_admin_panel"))

    await message.answer(
        f"🎬 <b>{anime['title']}</b> (Kod: <code>{anime['code']}</code>)\n\n"
        f"Qaysi ma'lumotni o'zgartirmoqchisiz?",
        parse_mode=ParseMode.HTML,
        reply_markup=builder.as_markup()
    )


@admin_router.callback_query(AnimeEditStates.selecting_field, F.data.startswith("editfield_"))
async def process_field_selection(callback: CallbackQuery, state: FSMContext):
    field_name = callback.data.replace("editfield_", "")
    data = await state.get_data()
    anime_id = data["anime_id"]

    if field_name == "delete":
        await db.delete_anime(anime_id)
        await state.clear()
        await callback.message.edit_text("🗑 <b>Anime va uning barcha qismlari muvaffaqiyatli o'chirildi!</b>", parse_mode=ParseMode.HTML)
        await callback.answer()
        return

    await state.update_data(field_to_edit=field_name)
    await state.set_state(AnimeEditStates.waiting_for_new_value)
    await callback.message.edit_text("Yangi qiymatni kiriting:")
    await callback.answer()


@admin_router.message(AnimeEditStates.waiting_for_new_value)
async def process_new_value(message: Message, state: FSMContext):
    data = await state.get_data()
    field_to_edit = data["field_to_edit"]
    if not message.text and not (field_to_edit == "poster" and message.photo):
        await message.answer("Matn yuboring; poster uchun rasm ham yuborishingiz mumkin.")
        return
    anime_id = data["anime_id"]

    if field_to_edit == "title":
        await db.update_anime(anime_id, "title", message.text.strip())
    elif field_to_edit == "poster":
        val = message.photo[-1].file_id if message.photo else message.text.strip()
        await db.update_anime(anime_id, "poster_file_id", val)
    elif field_to_edit == "is_vip":
        val = 1 if "1" in message.text or "vip" in message.text.lower() else 0
        await db.update_anime(anime_id, "is_vip", val)
    elif field_to_edit == "desc":
        await db.update_anime(anime_id, "description", message.text.strip())

    await state.clear()
    await message.answer("✅ <b>Ma'lumot muvaffaqiyatli yangilandi!</b>", parse_mode=ParseMode.HTML)


@admin_router.callback_query(F.data == "admin_make_post")
async def start_custom_post(callback: CallbackQuery, state: FSMContext):
    await state.set_state(CustomPostStates.waiting_for_anime_code)
    await callback.message.answer(
        "📢 Post tayyorlash uchun <b>Anime kodini</b> kiriting:",
        parse_mode=ParseMode.HTML,
        reply_markup=Keyboards.get_cancel_markup()
    )
    await callback.answer()


@admin_router.message(CustomPostStates.waiting_for_anime_code)
async def process_post_anime_code(message: Message, state: FSMContext):
    if not message.text or not message.text.strip():
        await message.answer("Iltimos, bu bosqichda matn yuboring. Bekor qilish: /cancel")
        return
    code = message.text.strip().replace("#", "")
    anime = await db.get_anime_by_code(code)
    if not anime:
        await message.answer(f"❌ '{code}' kodli anime topilmadi!")
        return

    await state.update_data(anime=anime)
    await state.set_state(CustomPostStates.waiting_for_media)
    await message.answer(
        f"🎬 Tanlandi: <b>{anime['title']}</b>\n\n"
        f"Endi post uchun maxsus <b>Rasm yoki Video</b> yuboring, "
        f"yoki standart poster ishlatilsin desangiz '⏭ O'tkazib yuborish'ni bosing:",
        parse_mode=ParseMode.HTML,
        reply_markup=Keyboards.get_skip_and_cancel_markup()
    )


@admin_router.message(CustomPostStates.waiting_for_media)
async def process_post_media(message: Message, state: FSMContext):
    media_file_id = None
    media_type = "photo"

    if message.photo:
        media_file_id = message.photo[-1].file_id
        media_type = "photo"
    elif message.video:
        media_file_id = message.video.file_id
        media_type = "video"

    await state.update_data(custom_media=media_file_id, custom_media_type=media_type)
    await state.set_state(CustomPostStates.confirm_post)

    data = await state.get_data()
    anime = data["anime"]
    bot_info = await message.bot.get_me()
    bot_link = f"https://t.me/{bot_info.username}?start=anime_{anime['code']}"

    voice_val = anime.get("voiceover") or "O'zbekcha dublyaj"
    desc_val = (anime.get("description") or "")[:300]
    orig_val = anime.get("original_title") or ""
    year_val = anime.get("year") or ""
    genre_val = anime.get("genres") or ""
    qual_val = anime.get("quality") or "1080p"

    post_caption = (
        f"🎬 <b>{anime['title']}</b>\n"
        f"<i>{orig_val}</i>\n\n"
        f"🔢 <b>Kodi:</b> <code>{anime['code']}</code>\n"
        f"📅 <b>Yili:</b> {year_val}\n"
        f"🎭 <b>Janri:</b> {genre_val}\n"
        f"🎥 <b>Sifati:</b> {qual_val}\n"
        f"🎙 <b>Ovoz:</b> {voice_val}\n\n"
        f"📝 <b>Tavsif:</b>\n<i>{desc_val}...</i>\n\n"
        f"👇 <b>Tomosha qilish uchun quyidagi tugmani bosing:</b>"
    )

    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="▶️ Botda tomosha qilish", url=bot_link))

    await state.update_data(final_caption=post_caption, bot_link=bot_link)

    await message.answer("👀 <b>Post namunasi (Preview):</b>", parse_mode=ParseMode.HTML)
    
    media = media_file_id or anime.get("poster_file_id")
    if media:
        if media_type == "video" and media_file_id:
            await message.answer_video(video=media, caption=post_caption, parse_mode=ParseMode.HTML, reply_markup=builder.as_markup())
        else:
            await message.answer_photo(photo=media, caption=post_caption, parse_mode=ParseMode.HTML, reply_markup=builder.as_markup())
    else:
        await message.answer(text=post_caption, parse_mode=ParseMode.HTML, reply_markup=builder.as_markup())

    confirm_builder = InlineKeyboardBuilder()
    confirm_builder.row(
        InlineKeyboardButton(text="📢 Kanalga chiqarish", callback_data="send_post_to_channel"),
        InlineKeyboardButton(text="❌ Bekor qilish", callback_data="open_admin_panel")
    )
    await message.answer("Postni kanalga chiqarishni tasdiqlaysizmi?", reply_markup=confirm_builder.as_markup())


@admin_router.callback_query(CustomPostStates.confirm_post, F.data == "send_post_to_channel")
async def process_send_post(callback: CallbackQuery, state: FSMContext, bot: Bot):
    data = await state.get_data()
    anime = data["anime"]
    caption = data["final_caption"]
    bot_link = data["bot_link"]
    media = data.get("custom_media") or anime.get("poster_file_id")
    media_type = data.get("custom_media_type", "photo")

    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="▶️ Botda tomosha qilish", url=bot_link))

    try:
        channel_target = BotConfig.OFFICIAL_CHANNEL_USERNAME
        if media:
            if media_type == "video":
                await bot.send_video(chat_id=channel_target, video=media, caption=caption, parse_mode=ParseMode.HTML, reply_markup=builder.as_markup())
            else:
                await bot.send_photo(chat_id=channel_target, photo=media, caption=caption, parse_mode=ParseMode.HTML, reply_markup=builder.as_markup())
        else:
            await bot.send_message(chat_id=channel_target, text=caption, parse_mode=ParseMode.HTML, reply_markup=builder.as_markup())

        await state.clear()
        await callback.message.edit_text(f"✅ <b>Post muvaffaqiyatli ravishda {channel_target} kanaliga chiqarildi!</b>", parse_mode=ParseMode.HTML)
    except Exception as e:
        logger.error(f"Kanalga post yuborishda xato: {e}")
        await callback.message.edit_text(
            f"⚠️ <b>Kanalga post yuborib bo'lmadi!</b>\n"
            f"Bot {BotConfig.OFFICIAL_CHANNEL_USERNAME} kanalida admin ekanligiga va xabar yuborish huquqiga ega ekanligiga ishonch hosil qiling.\n"
            f"Xatolik: {e}",
            parse_mode=ParseMode.HTML
        )
    await callback.answer()


@admin_router.callback_query(F.data == "admin_view_stats")
async def cb_admin_stats(callback: CallbackQuery):
    stats = await db.get_bot_statistics()
    text = (
        f"📊 <b>AnimeUz Kengaytirilgan Statistikasi:</b>\n\n"
        f"👥 <b>Foydalanuvchilar:</b> {stats['users_count']} nafar\n"
        f"💎 <b>VIP Tomoshabinlar:</b> {stats['vips_count']} nafar\n"
        f"🎬 <b>Jami Animelar:</b> {stats['animes_count']} ta\n"
        f"🎥 <b>Yuklangan Epizodlar:</b> {stats['episodes_count']} ta\n"
        f"📥 <b>Jami yuklab olishlar:</b> {stats['downloads_count']} marta\n"
        f"📢 <b>Ulangan majburiy kanallar:</b> {stats['channels_count']} ta\n\n"
        f"⚡ <i>Server holati: Barqaror (Optimal)</i>"
    )
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="🔙 Admin panelga", callback_data="open_admin_panel"))
    await callback.message.edit_text(text=text, parse_mode=ParseMode.HTML, reply_markup=builder.as_markup())
    await callback.answer()


@admin_router.callback_query(F.data == "admin_broadcast")
async def start_broadcast(callback: CallbackQuery, state: FSMContext):
    await state.set_state(BroadcastStates.waiting_for_message)
    await callback.message.answer(
        "📨 <b>Barcha foydalanuvchilarga yuboriladigan xabarni yozing:</b>\n"
        "<i>Matn, rasm yoki video yuborishingiz mumkin.</i>",
        parse_mode=ParseMode.HTML,
        reply_markup=Keyboards.get_cancel_markup()
    )
    await callback.answer()


@admin_router.message(BroadcastStates.waiting_for_message)
async def process_broadcast_message(message: Message, state: FSMContext, bot: Bot):
    await state.clear()
    user_ids = await db.get_all_user_ids()
    progress_msg = await message.answer(f"⏳ Xabar {len(user_ids)} ta foydalanuvchiga yuborilmoqda...")

    success = 0
    failed = 0

    for uid in user_ids:
        try:
            await bot.copy_message(
                chat_id=uid,
                from_chat_id=message.chat.id,
                message_id=message.message_id
            )
            success += 1
            await asyncio.sleep(0.04)
        except Exception:
            failed += 1

    await progress_msg.edit_text(
        f"✅ <b>Xabarnoma yakunlandi!</b>\n\n"
        f"📤 Yuborildi: <b>{success}</b> ta\n"
        f"❌ Yetib bormadi (bloklagan): <b>{failed}</b> ta",
        parse_mode=ParseMode.HTML
    )

# ==============================================================================
#                      11. OWNER (BOSH BOSHQARUVCHI) PANELI
# ==============================================================================

owner_router = Router(name="owner_router")
owner_router.message.filter(IsOwnerFilter())
owner_router.callback_query.filter(IsOwnerFilter())


@owner_router.callback_query(F.data == "owner_main_menu")
async def cb_owner_panel(callback: CallbackQuery):
    text = (
        "👑 <b>Bosh Boshqaruvchi (Owner) Maxsus Paneli</b>\n\n"
        "Ushbu bo'lim faqatgina bot egasi uchun ochiq bo'lib, quyidagi "
        "kritik tizimlarni boshqarish imkonini beradi:\n"
        "• Majburiy obuna kanallarini qo'shish va o'chirish\n"
        "• Yangi adminlarni tayinlash va ularning vakolatlarini belgilash\n"
        "• VIP promokodlar generatsiyasi va muddatlarini belgilash\n"
        "• Texnik tanaffus (Maintenance) rejimini boshqarish"
    )
    await callback.message.edit_text(text=text, parse_mode=ParseMode.HTML, reply_markup=Keyboards.get_owner_panel_keyboard())
    await callback.answer()


@owner_router.callback_query(F.data == "owner_bot_settings")
async def cb_owner_bot_settings(callback: CallbackQuery):
    is_maint = await db.is_maintenance()
    status_str = "Yoqilgan (Faqat adminlar kira oladi) 🔴" if is_maint else "O'chirilgan (Bot hammaga ochiq) 🟢"

    text = (
        f"⚙️ <b>Botning Global Sozlamalari</b>\n\n"
        f"Texnik tanaffus (Maintenance): <b>{status_str}</b>\n\n"
        f"Agar botni yangilamoqchi bo'lsangiz, texnik tanaffusni yoqib qo'yishingiz mumkin."
    )
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="🔄 Texnik rejimni almashtirish", callback_data="owner_toggle_maintenance"))
    builder.row(InlineKeyboardButton(text="🔙 Owner panelga", callback_data="owner_main_menu"))

    await callback.message.edit_text(text=text, parse_mode=ParseMode.HTML, reply_markup=builder.as_markup())
    await callback.answer()


@owner_router.callback_query(F.data == "owner_toggle_maintenance")
async def cb_toggle_maintenance(callback: CallbackQuery):
    new_state = await db.toggle_maintenance()
    alert = "🔴 Texnik tanaffus rejimi YOQILDI!" if new_state else "🟢 Texnik tanaffus O'CHIRILDI!"
    await callback.answer(alert, show_alert=True)
    await cb_owner_bot_settings(callback)


@owner_router.callback_query(F.data == "owner_manage_channels")
async def cb_manage_channels(callback: CallbackQuery):
    channels = await db.get_channels(only_mandatory=False)
    text = "📢 <b>Majburiy obuna kanallari ro'yxati:</b>\n\n"
    builder = InlineKeyboardBuilder()

    if not channels:
        text += "<i>Hozircha hech qanday kanal ulanmagan.</i>\n"
    else:
        for ch in channels:
            text += f"• <b>{ch['title']}</b> ({ch['channel_id']})\n"
            builder.row(InlineKeyboardButton(text=f"🗑 {ch['title']} ni o'chirish", callback_data=f"del_channel_{ch['id']}"))

    builder.row(InlineKeyboardButton(text="➕ Yangi kanal qo'shish", callback_data="owner_add_channel"))
    builder.row(InlineKeyboardButton(text="🔙 Owner panelga", callback_data="owner_main_menu"))

    await callback.message.edit_text(text=text, parse_mode=ParseMode.HTML, reply_markup=builder.as_markup())
    await callback.answer()


@owner_router.callback_query(F.data == "owner_add_channel")
async def start_add_channel(callback: CallbackQuery, state: FSMContext):
    await state.set_state(ChannelManageStates.waiting_for_channel_id)
    await callback.message.answer(
        "📢 Kanalning <b>Username</b>ini yoki <b>ID</b>sini kiriting:\n"
        "<i>Masalan: <code>@AnimeUz_Official</code> yoki <code>-1001234567890</code></i>\n\n"
        "Eslatma: Bot ushbu kanalda <b>Admin</b> bo'lishi shart!",
        parse_mode=ParseMode.HTML,
        reply_markup=Keyboards.get_cancel_markup()
    )
    await callback.answer()


@owner_router.message(ChannelManageStates.waiting_for_channel_id)
async def process_ch_id(message: Message, state: FSMContext):
    if not message.text or not message.text.strip():
        await message.answer("Iltimos, bu bosqichda matn yuboring. Bekor qilish: /cancel")
        return
    await state.update_data(channel_id=message.text.strip())
    await state.set_state(ChannelManageStates.waiting_for_channel_title)
    await message.answer("Kanal nomini kiriting (Masalan: <code>AnimeUz Rasmiy Kanal</code>):", parse_mode=ParseMode.HTML)


@owner_router.message(ChannelManageStates.waiting_for_channel_title)
async def process_ch_title(message: Message, state: FSMContext):
    if not message.text or not message.text.strip():
        await message.answer("Iltimos, bu bosqichda matn yuboring. Bekor qilish: /cancel")
        return
    await state.update_data(title=message.text.strip())
    await state.set_state(ChannelManageStates.waiting_for_invite_link)
    await message.answer("Kanalga ulanish havolasini (Invite link) kiriting:\n<i>Masalan: https://t.me/AnimeUz_Official</i>", parse_mode=ParseMode.HTML)


@owner_router.message(ChannelManageStates.waiting_for_invite_link)
async def process_ch_link(message: Message, state: FSMContext):
    if not message.text or not message.text.strip():
        await message.answer("Iltimos, bu bosqichda matn yuboring. Bekor qilish: /cancel")
        return
    data = await state.get_data()
    await db.add_channel(
        channel_id=data["channel_id"],
        title=data["title"],
        invite_link=message.text.strip(),
        is_mandatory=1
    )
    await state.clear()
    await message.answer("✅ <b>Yangi majburiy kanal muvaffaqiyatli qo'shildi!</b>", parse_mode=ParseMode.HTML)


@owner_router.callback_query(F.data.startswith("del_channel_"))
async def cb_delete_channel(callback: CallbackQuery):
    ch_id = int(callback.data.replace("del_channel_", ""))
    await db.delete_channel(ch_id)
    await callback.answer("Kanal o'chirildi!", show_alert=True)
    await cb_manage_channels(callback)


@owner_router.callback_query(F.data == "owner_manage_admins")
async def cb_manage_admins(callback: CallbackQuery):
    admins = await db.get_admins()
    text = "👥 <b>Bot Adminlari ro'yxati:</b>\n\n"
    builder = InlineKeyboardBuilder()

    for adm in admins:
        is_super = (adm["user_id"] == BotConfig.OWNER_ID)
        label = "👑 Owner" if is_super else "🛡️ Admin"
        text += f"• <b>{adm['full_name']}</b> (<code>{adm['user_id']}</code>) — {label}\n"
        if not is_super:
            builder.row(InlineKeyboardButton(text=f"❌ {adm['full_name']} ni olish", callback_data=f"remove_adm_{adm['user_id']}"))

    builder.row(InlineKeyboardButton(text="➕ Yangi admin tayinlash", callback_data="owner_add_admin_start"))
    builder.row(InlineKeyboardButton(text="🔙 Owner panelga", callback_data="owner_main_menu"))

    await callback.message.edit_text(text=text, parse_mode=ParseMode.HTML, reply_markup=builder.as_markup())
    await callback.answer()


@owner_router.callback_query(F.data == "owner_add_admin_start")
async def start_add_admin(callback: CallbackQuery, state: FSMContext):
    await state.set_state(AdminManageStates.waiting_for_admin_user_id)
    await callback.message.answer(
        "👥 Yangi admin qilinuvchi foydalanuvchining <b>Telegram ID</b> raqamini kiriting:\n"
        "<i>Foydalanuvchi avval botga /start bosgan bo'lishi lozim!</i>",
        parse_mode=ParseMode.HTML,
        reply_markup=Keyboards.get_cancel_markup()
    )
    await callback.answer()


@owner_router.message(AdminManageStates.waiting_for_admin_user_id)
async def process_admin_uid(message: Message, state: FSMContext):
    if not message.text or not message.text.strip():
        await message.answer("Iltimos, bu bosqichda matn yuboring. Bekor qilish: /cancel")
        return
    try:
        uid = int(message.text.strip())
    except ValueError:
        await message.answer("Iltimos, faqat raqamlardan iborat ID kiriting:")
        return

    user = await db.get_user(uid)
    name = user["full_name"] if user else f"Admin_{uid}"
    
    success = await db.add_admin(uid, name, message.from_user.id)
    await state.clear()

    if success:
        await message.answer(f"✅ <b>{name}</b> (<code>{uid}</code>) muvaffaqiyatli admin etib tayinlandi!", parse_mode=ParseMode.HTML)
    else:
        await message.answer("❌ Admin tayinlashda xatolik yuz berdi!")


@owner_router.callback_query(F.data.startswith("remove_adm_"))
async def cb_remove_admin(callback: CallbackQuery):
    uid = int(callback.data.replace("remove_adm_", ""))
    await db.remove_admin(uid)
    await callback.answer("Adminlikdan olindi!", show_alert=True)
    await cb_manage_admins(callback)


@owner_router.callback_query(F.data == "owner_create_promo")
async def start_promo_gen(callback: CallbackQuery, state: FSMContext):
    await state.set_state(PromoCreateStates.waiting_for_code_name)
    await callback.message.answer(
        "🔑 <b>Yangi VIP promokod nomini kiriting:</b>\n"
        "<i>Masalan: <code>ANIME2025</code> yoki <code>VIP30KUN</code></i>",
        parse_mode=ParseMode.HTML,
        reply_markup=Keyboards.get_cancel_markup()
    )
    await callback.answer()


@owner_router.message(PromoCreateStates.waiting_for_code_name)
async def process_promo_name(message: Message, state: FSMContext):
    if not message.text or not message.text.strip():
        await message.answer("Iltimos, bu bosqichda matn yuboring. Bekor qilish: /cancel")
        return
    code = message.text.strip().upper()
    await state.update_data(code=code)
    await state.set_state(PromoCreateStates.waiting_for_duration)
    await message.answer("Ushbu promokod necha kunlik VIP obuna beradi? (Masalan: <code>30</code>):", parse_mode=ParseMode.HTML)


@owner_router.message(PromoCreateStates.waiting_for_duration)
async def process_promo_duration(message: Message, state: FSMContext):
    if not message.text or not message.text.strip():
        await message.answer("Iltimos, bu bosqichda matn yuboring. Bekor qilish: /cancel")
        return
    try:
        days = int(message.text.strip())
    except ValueError:
        days = 30
    await state.update_data(duration_days=days)
    await state.set_state(PromoCreateStates.waiting_for_max_uses)
    await message.answer("Promokoddan necha kishi foydalana oladi? (Masalan: <code>1</code> yoki <code>100</code>):", parse_mode=ParseMode.HTML)


@owner_router.message(PromoCreateStates.waiting_for_max_uses)
async def process_promo_max(message: Message, state: FSMContext):
    if not message.text or not message.text.strip():
        await message.answer("Iltimos, bu bosqichda matn yuboring. Bekor qilish: /cancel")
        return
    try:
        max_uses = int(message.text.strip())
    except ValueError:
        max_uses = 1

    data = await state.get_data()
    code = data["code"]
    days = data["duration_days"]

    success = await db.create_promo_code(code=code, days=days, plan_name=f"{days} kunlik Promokod", max_uses=max_uses)
    await state.clear()

    if success:
        await message.answer(
            f"🎉 <b>Yangi VIP Promokod yaratildi!</b>\n\n"
            f"🔑 <b>Kod:</b> <code>{code}</code>\n"
            f"⏳ <b>Muddat:</b> {days} kun\n"
            f"👥 <b>Limit:</b> {max_uses} ta odam uchun\n\n"
            f"Foydalanuvchilar ushbu kodni VIP bo'limida kiritib faollashtirishlari mumkin!",
            parse_mode=ParseMode.HTML
        )
    else:
        await message.answer("❌ Ushbu nomli promokod allaqachon mavjud yoki xatolik yuz berdi!")

# ==============================================================================
#           12. ROLLI TIZIMNI ALMASHTIRISH VA GLOBAL CALLBACKLAR
# ==============================================================================

role_router = Router(name="role_router")


@role_router.message(F.text == f"{Emojis.USER} Foydalanuvchi rejimi")
@role_router.callback_query(F.data == "switch_to_user_mode")
async def switch_mode_to_user(event: Union[Message, CallbackQuery]):
    user_id = event.from_user.id
    user_data = await db.get_user(user_id)
    if not user_data or user_data.get("role") not in ("owner", "admin"):
        if isinstance(event, CallbackQuery):
            await event.answer("Sizda bunday huquq yo'q!", show_alert=True)
        return

    await db.set_user_mode(user_id, "user")
    
    text = (
        "👤 <b>Foydalanuvchi rejimi faollashtirildi!</b>\n\n"
        "Endi siz botni oddiy tomoshabin sifatida sinashingiz mumkin. "
        "Admin/Owner rejimiga istalgan vaqtda qaytish uchun menyudagi "
        "'👑 Admin/Owner rejimiga qaytish' tugmasini bosing yoki /start buyrug'ini yuboring."
    )

    if isinstance(event, CallbackQuery):
        await event.message.answer(text=text, parse_mode=ParseMode.HTML, reply_markup=Keyboards.get_main_menu(user_data["role"], "user"))
        await event.answer()
    else:
        await event.answer(text=text, parse_mode=ParseMode.HTML, reply_markup=Keyboards.get_main_menu(user_data["role"], "user"))


@role_router.message(F.text == f"{Emojis.CROWN} Admin/Owner rejimiga qaytish")
async def switch_mode_back_to_admin(message: Message):
    user_id = message.from_user.id
    user_data = await db.get_user(user_id)
    if not user_data or user_data.get("role") not in ("owner", "admin"):
        await message.answer("Sizda adminlik huquqi mavjud emas!")
        return

    await db.set_user_mode(user_id, "admin")
    await message.answer(
        "👑 <b>Admin/Owner rejimi qayta faollashtirildi!</b>\n\n"
        "Barcha boshqaruv vositalari va panellar yana ixtiyoringizda.",
        parse_mode=ParseMode.HTML,
        reply_markup=Keyboards.get_main_menu(user_data["role"], "admin")
    )


@role_router.message(Command("cancel"))
@role_router.message(F.text == f"{Emojis.CROSS} Bekor qilish")
async def cancel_any_action(message: Message, state: FSMContext):
    await state.clear()
    user_data = await db.get_user(message.from_user.id) or {}
    await message.answer(
        "❌ Amaliyot bekor qilindi.",
        reply_markup=Keyboards.get_main_menu(user_data.get("role", "user"), user_data.get("current_mode", "user"))
    )


@role_router.callback_query(F.data == "noop")
async def noop_callback(callback: CallbackQuery):
    await callback.answer()


@role_router.callback_query(F.data == "open_search_menu")
async def cb_open_search(callback: CallbackQuery):
    await safe_edit_text(
        callback,
        "🔍 <b>Anime qidiruv markazi:</b>",
        parse_mode=ParseMode.HTML,
        reply_markup=Keyboards.get_search_inline_menu()
    )
    await callback.answer()


@role_router.callback_query(F.data == "back_to_home")
async def cb_back_to_home(callback: CallbackQuery):
    full_name = html.escape(callback.from_user.full_name)
    await safe_edit_text(callback,
        f"Assalomu alaykum, <b>{full_name}</b>!\nAsosiy boshqaruv menyusidasiz.",
        parse_mode=ParseMode.HTML
    )
    await callback.answer()


@role_router.callback_query(F.data == "verify_subscription")
async def cb_verify_subscription(callback: CallbackQuery, bot: Bot):
    is_subscribed, unsubscribed = await check_mandatory_subscriptions(bot, callback.from_user.id)
    if is_subscribed:
        await callback.answer("Obuna tasdiqlandi!")
        await callback.message.delete()
        await callback.message.answer(
            "🎉 <b>Obuna muvaffaqiyatli tasdiqlandi!</b>\n"
            "Endi botdan bemalol foydalanishingiz mumkin.",
            parse_mode=ParseMode.HTML
        )
    else:
        await callback.answer("❌ Hali hamma kanallarga a'zo bo'lmadingiz!", show_alert=True)

# ==============================================================================
#                 13. TELEGRAM INLINE QIDIRUV REJIMI
# ==============================================================================

inline_router = Router(name="inline_router")


@inline_router.inline_query()
async def handle_inline_search(inline_query: InlineQuery):
    query = inline_query.query.strip()
    if not query:
        animes = await db.get_latest_animes(limit=10)
    else:
        animes = await db.search_anime_by_title(query, limit=15)

    results = []
    bot_info = await inline_query.bot.get_me()

    for a in animes:
        direct_link = f"https://t.me/{bot_info.username}?start=anime_{a['code']}"
        desc = f"Kod: {a['code']} | Yil: {a.get('year', '')} | {a.get('genres', '')}"
        content_text = (
            f"🎬 <b>{a['title']}</b>\n"
            f"🔢 <b>Kodi:</b> <code>{a['code']}</code>\n"
            f"📅 <b>Yili:</b> {a.get('year', '')}\n"
            f"🎭 <b>Janrlari:</b> {a.get('genres', '')}\n"
            f"🎥 <b>Sifati:</b> {a.get('quality', '1080p')}\n\n"
            f"👉 <a href='{direct_link}'>Botda tomosha qilish uchun bosing</a>"
        )
        markup = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="▶️ Tomosha qilish", url=direct_link)]
        ])

        results.append(
            InlineQueryResultArticle(
                id=f"anime_{a['id']}",
                title=f"🎬 {a['title']}",
                description=desc,
                thumbnail_url=a.get("poster_url") or "https://via.placeholder.com/150",
                input_message_content=InputTextMessageContent(
                    message_text=content_text,
                    parse_mode=ParseMode.HTML,
                    disable_web_page_preview=False
                ),
                reply_markup=markup
            )
        )

    await inline_query.answer(results=results, cache_time=10, is_personal=True)

# ==============================================================================
#                 14. STANDART ANIME BAZASINI SHAKLLANTIRISH
# ==============================================================================

async def populate_initial_anime_data():
    stats = await db.get_bot_statistics()
    if stats["animes_count"] > 0:
        return

    logger.info("Boshlang'ich anime ma'lumotlari bazaga yuklanmoqda...")

    sample_animes = [
        {
            "code": "101",
            "title": "Solo Leveling (Yolg'iz Darajalanish)",
            "original_title": "Ore dake Level Up na Ken",
            "year": 2024,
            "quality": "1080p Full HD",
            "voiceover": "AnimeUz Dublyaj",
            "genres": "Jangari, Sarguzasht, Fantastika",
            "description": "Eng kuchsiz E-darajali ovchi Song Jin-woo sirli yerosti qasrida o'lim bilan yuzlashadi va faqat unga ko'rinadigan o'yin tizimiga ega bo'lib, cheksiz kuchga erishishni boshlaydi.",
            "poster_file_id": "https://images.unsplash.com/photo-1578632767115-351597cf2477?w=800",
            "is_vip": 0,
            "status": "Tugatilgan"
        },
        {
            "code": "102",
            "title": "Jujutsu Kaisen (Sehrli Jang)",
            "original_title": "Jujutsu Kaisen",
            "year": 2023,
            "quality": "1080p Full HD",
            "voiceover": "AvoDub",
            "genres": "Sehrgarlik, Jangari, Shounen, Triller",
            "description": "Itadori Yuji o'z maktabidagi do'stlarini la'natlangan sharpalardan qutqarish uchun eng qudratli la'nat podshohi Sukunaning barmog'ini yutib yuboradi.",
            "poster_file_id": "https://images.unsplash.com/photo-1563089145-599997674d42?w=800",
            "is_vip": 0,
            "status": "Davom etmoqda"
        },
        {
            "code": "103",
            "title": "Attack on Titan (Titanlar Hujumi)",
            "original_title": "Shingeki no Kyojin",
            "year": 2023,
            "quality": "1080p Ultra HD",
            "voiceover": "Tarjima Kino",
            "genres": "Drama, Jangari, Fantastika, Triller",
            "description": "Insoniyat devorlar ortida ulkan odamxo'r titanlardan yashirinib yashaydi. Eren Yeager onasini o'ldirgan barcha titanlarni yo'q qilishga qasamyod qiladi.",
            "poster_file_id": "https://images.unsplash.com/photo-1607604276583-eef5d076aa5f?w=800",
            "is_vip": 1,
            "status": "Tugatilgan"
        },
        {
            "code": "104",
            "title": "Demon Slayer (Iblislar Qotili)",
            "original_title": "Kimetsu no Yaiba",
            "year": 2024,
            "quality": "1080p Full HD",
            "voiceover": "AnimeUz Pro",
            "genres": "Jangari, Tarixiy, Shounen, Sehrgarlik",
            "description": "Oila a'zolari iblis tomonidan shafqatsiz o'ldirilgan Tanjirou o'z singlisi Nezuko iblisga aylanganini bilib, uni yana insonga aylantirish yo'liga otlanadi.",
            "poster_file_id": "https://images.unsplash.com/photo-1534447677768-be436bb09401?w=800",
            "is_vip": 0,
            "status": "Davom etmoqda"
        },
        {
            "code": "105",
            "title": "Death Note (O'lim Daftari)",
            "original_title": "Death Note",
            "year": 2006,
            "quality": "1080p Full HD",
            "voiceover": "O'zbek Dublyaj",
            "genres": "Psixologik, Triller, Detektiv, Sehrgarlik",
            "description": "Aql bovar qilmas daho o'quvchi Yagami Light yerga tushgan o'lim ma'budasining daftarini topib oladi va barcha jinoyatchilarni yo'q qilib, yangi dunyo xudosi bo'lishni xohlaydi.",
            "poster_file_id": "https://images.unsplash.com/photo-1518709268805-4e9042af9f23?w=800",
            "is_vip": 0,
            "status": "Tugatilgan"
        }
    ]

    for item in sample_animes:
        anime_id = await db.add_anime(item)
        for ep in range(1, 4):
            await db.add_episode({
                "anime_id": anime_id,
                "anime_code": item["code"],
                "episode_number": ep,
                "episode_title": f"{ep}-qism",
                "file_id": "BAACAgIAAxkBAAEK1234567890abcdef",
                "file_type": "video",
                "file_size": "345.8 MB",
                "is_vip": item["is_vip"]
            })

    await db.create_promo_code("ANIME2025", 30, "Yangi Yil 30 Kunlik VIP", max_uses=50)
    await db.create_promo_code("PREMIUMVIP", 90, "3 Oylik VIP Promokod", max_uses=20)
    logger.info("Boshlang'ich demo animelar va promokodlar kiritildi.")

# ==============================================================================
#                  15. BOTNI ISHGA TUSHIRISH VA SOZLASHLAR
# ==============================================================================

async def set_bot_commands(bot: Bot):
    commands = [
        BotCommand(command="start", description="Botni qayta ishga tushirish / Yangilash"),
        BotCommand(command="admin", description="Admin paneli (Faqat xodimlar uchun)"),
        BotCommand(command="cancel", description="Joriy amaliyotni bekor qilish"),
    ]
    await bot.set_my_commands(commands, scope=BotCommandScopeDefault())


class AccessGuardMiddleware(BaseMiddleware):
    """Texnik tanaffus va majburiy obunani barcha oddiy so'rovlarda tekshiradi."""

    async def __call__(self, handler, event: Union[Message, CallbackQuery], data: Dict[str, Any]):
        user = data.get("event_from_user")
        if not user or user.is_bot:
            return await handler(event, data)

        text = event.text.strip() if isinstance(event, Message) and event.text else ""
        cb = event.data if isinstance(event, CallbackQuery) and event.data else ""
        if text.startswith("/start") or text.startswith("/cancel") or text == f"{Emojis.CROSS} Bekor qilish":
            return await handler(event, data)
        if cb in ("verify_subscription", "noop"):
            return await handler(event, data)

        is_staff = user.id == BotConfig.OWNER_ID or await db.is_admin(user.id)
        if not is_staff and await db.is_maintenance():
            notice = "🔴 Bot texnik tanaffusda. Birozdan keyin qayta urinib ko'ring."
            if isinstance(event, CallbackQuery):
                await event.answer(notice, show_alert=True)
            else:
                await event.answer(notice)
            return

        if not is_staff and not await db.check_user_vip(user.id):
            bot = data.get("bot")
            ok, missing = await check_mandatory_subscriptions(bot, user.id)
            if not ok and missing:
                markup = Keyboards.get_subscription_keyboard(missing)
                notice = "📢 Botdan foydalanish uchun quyidagi kanallarga obuna bo'ling, so'ng «Obunani tekshirish» ni bosing."
                if isinstance(event, CallbackQuery):
                    await event.answer("Avval kanallarga obuna bo'ling", show_alert=True)
                    await event.message.answer(notice, reply_markup=markup)
                else:
                    await event.answer(notice, reply_markup=markup)
                return

        return await handler(event, data)


async def on_startup(bot: Bot):
    logger.info("Baza jadvallari tekshirilmoqda...")
    await db.init_db()
    # Demo fayl IDlari haqiqiy emas; faqat aniq yoqilganda yuklanadi.
    if os.getenv("ENABLE_DEMO_DATA", "0") == "1":
        await populate_initial_anime_data()
    await set_bot_commands(bot)
    
    bot_info = await bot.get_me()
    logger.info("=" * 60)
    logger.info(f"ANIMEBOT PRO ISHGA TUSHDI: @{bot_info.username} (ID: {bot_info.id})")
    logger.info(f"Owner ID: {BotConfig.OWNER_ID}")
    logger.info("Barcha xizmatlar barqaror faoliyat ko'rsatmoqda.")
    logger.info("=" * 60)


async def main():
    if not BotConfig.BOT_TOKEN or BotConfig.BOT_TOKEN == "YOUR_BOT_TOKEN_HERE":
        logger.error("DIQQAT: BOT_TOKEN o'rnatilmagan! Iltimos .env faylida yoki muhitda BOT_TOKEN ni belgilang.")
        print("\n[!] XATOLIK: BOT_TOKEN topilmadi. Tokenni .env fayliga kiriting!\n")
        return

    bot = Bot(token=BotConfig.BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)

    dp.message.middleware(AntiSpamMiddleware())
    dp.callback_query.middleware(AntiSpamMiddleware())
    dp.message.middleware(UserTrackingMiddleware())
    dp.callback_query.middleware(UserTrackingMiddleware())
    dp.message.middleware(AccessGuardMiddleware())
    dp.callback_query.middleware(AccessGuardMiddleware())

    dp.include_router(role_router)
    dp.include_router(user_router)
    dp.include_router(search_router)
    dp.include_router(vip_router)
    dp.include_router(settings_router)
    dp.include_router(admin_router)
    dp.include_router(owner_router)
    dp.include_router(inline_router)

    try:
        await on_startup(bot)
        await bot.delete_webhook(drop_pending_updates=True)
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types(), close_bot_session=False)
    finally:
        await storage.close()
        await bot.session.close()
        logger.info("Bot sessiyasi yopildi.")



# ==============================================================================
#                 16. KENGAYTIRILGAN ANIME KATALOGI VA MA'LUMOTLAR
# ==============================================================================

class ExtendedCatalog:
    """Kengaytirilgan O'zbek anime katalogi va toifalar ma'lumotlar bazasi."""
    
    EXTENDED_ANIMES = [
        {
            "code": "106",
            "title": "One Piece (Katta Xazina)",
            "original_title": "One Piece",
            "year": 1999,
            "quality": "1080p Full HD",
            "voiceover": "AnimeUz Fan",
            "genres": "Sarguzasht, Jangari, Komediya, Fantastika",
            "description": "Monkey D. Luffy o'z do'stlari bilan birgalikda 'Qaroqchilar qiroli' bo'lish va buyuk xazina 'One Piece'ni topish uchun xavfli dengizlarga suzib ketadi.",
            "is_vip": 0,
            "total_episodes": 1100
        },
        {
            "code": "107",
            "title": "Naruto Shippuden (Dovulli Qaqshatqich)",
            "original_title": "Naruto: Shippuden",
            "year": 2007,
            "quality": "1080p Full HD",
            "voiceover": "Yoshlar TV Dublyaj",
            "genres": "Jangari, Shounen, Sarguzasht, Sehrgarlik",
            "description": "Uzumaki Naruto ikki yarim yillik qattiq mashg'ulotlardan so'ng Konoxa qishlog'iga qaytadi va Akatsuki tashkilotiga qarshi buyuk jangga tayyorlanadi.",
            "is_vip": 0,
            "total_episodes": 500
        },
        {
            "code": "108",
            "title": "Bleach: Thousand-Year Blood War (Ming Yillik Qonli Urush)",
            "original_title": "Bleach: Sennen Kessen-hen",
            "year": 2022,
            "quality": "1080p Ultra HD",
            "voiceover": "AvoDub",
            "genres": "Jangari, Shounen, Sehrgarlik, Triller",
            "description": "Ruhlar Jamiyati va Kvinlar o'rtasida ming yillik tarixga ega bo'lgan eng dahshatli va so'nggi qonli urush boshlanadi. Ichigo o'zining asl qudratini kashf etadi.",
            "is_vip": 1,
            "total_episodes": 26
        },
        {
            "code": "109",
            "title": "Tokyo Ghoul (Tokio Guli)",
            "original_title": "Tokyo Ghoul",
            "year": 2014,
            "quality": "1080p Full HD",
            "voiceover": "Tarjima Kino",
            "genres": "Dahshat, Triller, Psixologik, Jangari",
            "description": "Kaneki Ken tasodifan yarim gulga aylanib qoladi va endi odamlar hamda gullar orasidagi qonli kurashda o'z insoniyligini saqlab qolishga majbur bo'ladi.",
            "is_vip": 0,
            "total_episodes": 24
        },
        {
            "code": "110",
            "title": "Fullmetal Alchemist: Brotherhood (Po'lat Alximik)",
            "original_title": "Hagane no Renkinjutsushi",
            "year": 2009,
            "quality": "1080p Full HD",
            "voiceover": "AnimeUz Pro",
            "genres": "Sarguzasht, Fantastika, Drama, Jangari",
            "description": "O'lgan onasini tiriltirishga urinib jismoniy tanasidan ayrilgan aka-uka Eduard va Alfons Elriklar afsonaviy Faylasuf toshini izlashga tushadilar.",
            "is_vip": 0,
            "total_episodes": 64
        },
        {
            "code": "111",
            "title": "Hunter x Hunter (Ovchi x Ovchi)",
            "original_title": "Hunter x Hunter",
            "year": 2011,
            "quality": "1080p Full HD",
            "voiceover": "UzAnime",
            "genres": "Jangari, Sarguzasht, Fantastika, Shounen",
            "description": "Gon Freecss afsonaviy ovchi bo'lgan otasini topish maqsadida o'ta murakkab va xavfli Ovchilar imtihonini topshirishga yo'l oladi.",
            "is_vip": 0,
            "total_episodes": 148
        },
        {
            "code": "112",
            "title": "Chainsaw Man (Benzopila Odam)",
            "original_title": "Chainsaw Man",
            "year": 2022,
            "quality": "1080p Ultra HD",
            "voiceover": "AvoDub VIP",
            "genres": "Jangari, Qora komediya, Triller, Dahshat",
            "description": "Qarzlar botqog'ida qolgan Denji o'zining sodiq iblis iti Pochita bilan birlashib, jinlarni qiruvchi shafqatsiz Benzopila odamga aylanadi.",
            "is_vip": 1,
            "total_episodes": 12
        },
        {
            "code": "113",
            "title": "Vinland Saga (Vinland Haqidagi Doston)",
            "original_title": "Vinland Saga",
            "year": 2019,
            "quality": "1080p Full HD",
            "voiceover": "Tarjima Kino",
            "genres": "Tarixiy, Jangari, Drama, Sarguzasht",
            "description": "Vikinglar davrida kechgan shiddatli qonli urushlar. Yosh Torfinn otasining xiyonatkor qotili Askeladdan qasos olish uchun uning yollanma lashkari safiga qo'shiladi.",
            "is_vip": 0,
            "total_episodes": 48
        },
        {
            "code": "114",
            "title": "Black Clover (Qora Yonbosh)",
            "original_title": "Black Clover",
            "year": 2017,
            "quality": "1080p Full HD",
            "voiceover": "AnimeUz Pro",
            "genres": "Sehrgarlik, Shounen, Jangari, Komediya",
            "description": "Sehrgarlar olamida mutlaqo sehr qobiliyatisiz tug'ilgan Asta hech qachon taslim bo'lmaydi va jismoniy kuchi hamda Anti-sehr qilichi bilan Sehrgarlar Qiroli bo'lishga intiladi.",
            "is_vip": 0,
            "total_episodes": 170
        },
        {
            "code": "115",
            "title": "My Hero Academia (Mening Qahramonlik Akademiyam)",
            "original_title": "Boku no Hero Academia",
            "year": 2016,
            "quality": "1080p Full HD",
            "voiceover": "AvoDub",
            "genres": "Shounen, Qahramonlik, Maktab, Jangari",
            "description": "Dunyoda har bir inson o'ziga xos qobiliyat bilan tug'ilgan bir paytda, Midoriya Izuku qobiliyatsiz tug'iladi, ammo eng buyuk qahramon All Mightning e'tiborini qozonadi.",
            "is_vip": 0,
            "total_episodes": 138
        }
    ]

# ==============================================================================
#                 17. AVTOMATLASHTIRILGAN TESTLAR VA DIAGNOSTIKA
# ==============================================================================

class BotTestingSuite:
    @staticmethod
    async def test_database_integrity(db_inst: Database) -> bool:
        try:
            user = await db_inst.register_or_update_user(999999999, "Sinov Foydalanuvchisi", "test_user")
            assert user["user_id"] == 999999999, "Foydalanuvchi IDsi mos kelmadi"
            
            await db_inst.set_user_mode(999999999, "admin")
            updated = await db_inst.get_user(999999999)
            assert updated["current_mode"] == "admin", "Rejim almashmadi"
            
            await db_inst.set_user_mode(999999999, "user")
            updated = await db_inst.get_user(999999999)
            assert updated["current_mode"] == "user", "Oddiy foydalanuvchi rejimiga o'tmadi"

            promo_name = f"TEST{random.randint(1000, 9999)}"
            await db_inst.create_promo_code(promo_name, 7, "Sinov Promokod", max_uses=1)
            success, msg = await db_inst.redeem_promo_code(promo_name, 999999999)
            assert success is True, f"Promokod faollashmadi: {msg}"
            
            is_vip = await db_inst.check_user_vip(999999999)
            assert is_vip is True, "Foydalanuvchi VIP statusga ega bo'lmadi"

            animes = await db_inst.get_all_animes(page=1, per_page=5)
            assert isinstance(animes[0], list), "Katalog ro'yxati qaytmadi"

            logger.info("✅ Barcha ichki tizim testlari muvaffaqiyatli o'tdi!")
            return True
        except Exception as e:
            logger.error(f"❌ Test jarayonida xatolik: {e}")
            return False

# ==============================================================================
#           18. MA'LUMOT MODELLARI (DATACLASSES) VA DATA PATTERNS
# ==============================================================================

@dataclass
class UserModel:
    id: int
    user_id: int
    full_name: str
    username: Optional[str]
    role: str
    current_mode: str
    vip_until: Optional[datetime.datetime]
    vip_plan: Optional[str]
    downloads_count: int
    is_banned: bool
    created_at: datetime.datetime
    updated_at: datetime.datetime

    @property
    def is_vip_active(self) -> bool:
        if self.role in ("owner", "admin"):
            return True
        if not self.vip_until:
            return False
        return self.vip_until > datetime.datetime.now()


@dataclass
class AnimeModel:
    id: int
    code: str
    title: str
    original_title: str
    year: int
    quality: str
    voiceover: str
    genres: str
    description: str
    poster_file_id: Optional[str]
    poster_url: Optional[str]
    is_vip: bool
    views_count: int
    rating: float
    total_episodes: int
    status: str
    created_at: datetime.datetime
    updated_at: datetime.datetime

    @property
    def genres_list(self) -> List[str]:
        return [g.strip() for g in self.genres.split(",") if g.strip()]


@dataclass
class EpisodeModel:
    id: int
    anime_id: int
    anime_code: str
    episode_number: int
    episode_title: str
    file_id: str
    file_type: str
    file_size: str
    is_vip: bool
    views: int
    created_at: datetime.datetime


@dataclass
class ChannelModel:
    id: int
    channel_id: str
    title: str
    invite_link: str
    is_mandatory: bool
    created_at: datetime.datetime


@dataclass
class PromoCodeModel:
    id: int
    code: str
    duration_days: int
    plan_name: str
    max_uses: int
    used_count: int
    is_active: bool
    created_at: datetime.datetime
    expires_at: Optional[datetime.datetime]

    @property
    def is_available(self) -> bool:
        return self.is_active and self.used_count < self.max_uses

# ==============================================================================
#                 19. LOYIHANI O'RNATISH VA SERVERDA YURITISH
# ==============================================================================

DEPLOYMENT_INSTRUCTIONS = """
--------------------------------------------------------------------------------
           ANIMEBOT PRO - SERVERDA ISHGA TUSHIRISH BO'YICHA YO'RIQNOMA
--------------------------------------------------------------------------------
1. Server (Ubuntu/Debian) talablari:
   - Python 3.10 yoki undan yuqori
   - pip, venv va git o'rnatilgan bo'lishi kerak.

2. Kutubxonalarni o'rnatish:
   $ python3 -m venv venv
   $ source venv/bin/activate
   $ pip install aiogram==3.15.0 aiosqlite python-dotenv

3. Muhit o'zgaruvchilarini sozlash (.env):
   BOT_TOKEN="1234567890:ABCdefGHIjklMNOpqrSTUvwxYZ"
   OWNER_ID="5065303387"
   DATABASE_PATH="anime_bot.db"
   OFFICIAL_CHANNEL="@AnimeUz_Official"
   SUPPORT_URL="https://t.me/AnimeUz_Admin"

4. Botni fonda doimiy yurgizish (Systemd xizmati):
   /etc/systemd/system/animebot.service faylini yarating:
   
   [Unit]
   Description=AnimeBot Pro Aiogram 3.x Telegram Bot
   After=network.target

   [Service]
   Type=simple
   User=root
   WorkingDirectory=/root/anime_bot
   ExecStart=/root/anime_bot/venv/bin/python3 /root/anime_bot/bot.py
   Restart=always
   RestartSec=5

   [Install]
   WantedBy=multi-user.target

5. Xizmatni yoqish va ishga tushirish:
   $ sudo systemctl daemon-reload
   $ sudo systemctl enable animebot
   $ sudo systemctl start animebot
   $ sudo systemctl status animebot
--------------------------------------------------------------------------------
"""


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot foydalanuvchi tomonidan to'xtatildi.")
