import asyncio
import logging
import sys
from datetime import datetime, timedelta
from enum import Enum as PyEnum
from typing import Any, Callable, Dict, Awaitable

from aiogram import Bot, Dispatcher, Router, F, BaseMiddleware
from aiogram.client.default import DefaultBotProperties
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from aiogram.filters import BaseFilter, Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import (
    CallbackQuery, InlineKeyboardMarkup, KeyboardButton, Message,
    ReplyKeyboardMarkup, TelegramObject, Update, ErrorEvent
)
from aiogram.utils.keyboard import InlineKeyboardBuilder
from loguru import logger
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import (
    BigInteger, Boolean, DateTime, Enum, ForeignKey, Integer, 
    String, Text, select, func, or_
)
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship, selectinload

# =========================================================================================
# 1. KONFIGURATSIYA VA SOZLAMALAR (CONFIGURATION & SETTINGS)
# =========================================================================================
class Settings(BaseSettings):
    """
    Botning asosiy sozlamalari. .env faylidan yoki Render'dagi Environment'dan o'qiladi.
    """
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")
    
    BOT_TOKEN: str
    OWNER_ID: int
    DB_URL: str = "sqlite+aiosqlite:///./anime_bot.db"
    LOG_LEVEL: str = "INFO"

# Sozlamalarni yuklash
settings = Settings()

# =========================================================================================
# 2. LOGGER SOZLAMALARI (LOGGING SETUP)
# =========================================================================================
logger.remove()
# Konsolga chiqarish
logger.add(
    sys.stdout,
    level=settings.LOG_LEVEL,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan> - <level>{message}</level>"
)
# Faylga yozish (xatoliklarni saqlash uchun)
logger.add("logs/bot_errors.log", level="ERROR", rotation="10 MB", retention="10 days")

# =========================================================================================
# 3. MA'LUMOTLAR BAZASI MODELLARI (DATABASE MODELS)
# =========================================================================================
class Base(DeclarativeBase):
    """Barcha modellar uchun asosiy klass"""
    pass

# Ma'lumotlar bazasiga ulanish
engine = create_async_engine(settings.DB_URL, echo=False, pool_pre_ping=True)
AsyncSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

class UserRole(PyEnum):
    """Foydalanuvchi rollari"""
    OWNER = "owner"
    ADMIN = "admin"
    USER = "user"

class User(Base):
    """Foydalanuvchilar jadvali"""
    __tablename__ = "users"
    
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True)
    full_name: Mapped[str] = mapped_column(String(255))
    username: Mapped[str | None] = mapped_column(String(64), nullable=True)
    role: Mapped[UserRole] = mapped_column(Enum(UserRole), default=UserRole.USER)
    is_banned: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    # Aloqalar
    subscriptions = relationship("VipSubscription", back_populates="user", cascade="all, delete-orphan")

class Genre(Base):
    """Anime janrlari jadvali"""
    __tablename__ = "genres"
    
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), unique=True)

class Anime(Base):
    """Animelar jadvali"""
    __tablename__ = "anime"
    
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(255), index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    genre_id: Mapped[int | None] = mapped_column(ForeignKey("genres.id"), nullable=True)
    year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    is_vip_only: Mapped[bool] = mapped_column(Boolean, default=False)
    views: Mapped[int] = mapped_column(Integer, default=0)
    created_by: Mapped[int] = mapped_column(BigInteger)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    # Aloqalar
    episodes = relationship("Episode", back_populates="anime", cascade="all, delete-orphan")
    genre = relationship("Genre")

class Episode(Base):
    """Anime qismlari jadvali"""
    __tablename__ = "episodes"
    
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    anime_id: Mapped[int] = mapped_column(ForeignKey("anime.id", ondelete="CASCADE"))
    number: Mapped[int] = mapped_column(Integer)
    title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    file_id: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    # Aloqalar
    anime = relationship("Anime", back_populates="episodes")

class VipTariff(Base):
    """VIP Tariflar jadvali"""
    __tablename__ = "vip_tariffs"
    
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100))
    price: Mapped[int] = mapped_column(Integer)
    duration_days: Mapped[int] = mapped_column(Integer)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

class VipSubscription(Base):
    """Foydalanuvchilarning VIP obunalari jadvali"""
    __tablename__ = "vip_subscriptions"
    
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    tariff_id: Mapped[int] = mapped_column(ForeignKey("vip_tariffs.id"))
    start_date: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    end_date: Mapped[datetime] = mapped_column(DateTime)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    
    # Aloqalar
    user = relationship("User", back_populates="subscriptions")
    tariff = relationship("VipTariff")

class MandatoryChannel(Base):
    """Majburiy obuna kanallari jadvali"""
    __tablename__ = "mandatory_channels"
    
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    channel_id: Mapped[int] = mapped_column(BigInteger, unique=True)
    channel_username: Mapped[str] = mapped_column(String(100))

# =========================================================================================
# 4. FSM HOLATLARI (STATES)
# =========================================================================================
class AnimeStates(StatesGroup):
    """Anime yuklash jarayoni holatlari"""
    title = State()
    description = State()
    year = State()
    is_vip = State()
    ep_num = State()
    ep_file = State()

class ChannelStates(StatesGroup):
    """Kanal qo'shish jarayoni holatlari"""
    waiting_channel = State()

class BroadcastStates(StatesGroup):
    """Xabar tarqatish jarayoni holatlari"""
    waiting_message = State()

class TariffStates(StatesGroup):
    """VIP Tarif qo'shish jarayoni holatlari"""
    name = State()
    price = State()
    duration = State()

class SearchStates(StatesGroup):
    """Qidiruv jarayoni holatlari"""
    waiting_name = State()
    waiting_code = State()

class PostStates(StatesGroup):
    """Post tayyorlash jarayoni holatlari"""
    waiting_anime_id = State()
    waiting_text = State()

# =========================================================================================
# 5. FILTERLAR VA MIDDLEWARELAR (RBAC & PROTECTION)
# =========================================================================================
class IsOwner(BaseFilter):
    """Faqat Bot Egasi uchun filtr"""
    async def __call__(self, event, **kwargs) -> bool:
        user = kwargs.get("db_user")
        return user is not None and user.role == UserRole.OWNER

class IsAdmin(BaseFilter):
    """Admin va Owner uchun filtr"""
    async def __call__(self, event, **kwargs) -> bool:
        user = kwargs.get("db_user")
        return user is not None and user.role in (UserRole.OWNER, UserRole.ADMIN)

class DBSessionMiddleware(BaseMiddleware):
    """Har bir so'rov uchun DB sessiyasini ochish va yopish"""
    async def __call__(
        self, 
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]], 
        event: TelegramObject, 
        data: Dict[str, Any]
    ) -> Any:
        async with AsyncSessionLocal() as session:
            data["session"] = session
            try:
                result = await handler(event, data)
                await session.commit()
                return result
            except Exception as e:
                await session.rollback()
                logger.error(f"DB Error: {e}")
                raise e

class UserMiddleware(BaseMiddleware):
    """Foydalanuvchini DB dan topish yoki ro'yxatdan o'tkazish"""
    async def __call__(self, handler, event: TelegramObject, data: Dict[str, Any]):
        session: AsyncSession = data["session"]
        tg_user = None
        
        # Xabar yoki Callback ekanligini aniqlash
        if isinstance(event, Update):
            if event.message: 
                tg_user = event.message.from_user
            elif event.callback_query: 
                tg_user = event.callback_query.from_user

        if tg_user:
            result = await session.execute(select(User).where(User.telegram_id == tg_user.id))
            user = result.scalar_one_or_none()
            
            if user is None:
                # Yangi foydalanuvchi
                role = UserRole.OWNER if tg_user.id == settings.OWNER_ID else UserRole.USER
                user = User(
                    telegram_id=tg_user.id, 
                    full_name=tg_user.full_name, 
                    username=tg_user.username, 
                    role=role
                )
                session.add(user)
                await session.flush()
                
            data["db_user"] = user
        return await handler(event, data)

class SubscriptionMiddleware(BaseMiddleware):
    """Majburiy obunani tekshirish"""
    async def __call__(self, handler, event: TelegramObject, data: Dict[str, Any]):
        session: AsyncSession = data["session"]
        db_user: User = data.get("db_user")

        # Admin va Ownerlar tekshirilmaydi
        if db_user is None or db_user.role in (UserRole.OWNER, UserRole.ADMIN):
            return await handler(event, data)
        
        # /start bosganda o'tkazib yuborish
        if isinstance(event, Update) and event.message and event.message.text == "/start":
            return await handler(event, data)

        result = await session.execute(select(MandatoryChannel))
        channels = result.scalars().all()
        
        if not channels:
            return await handler(event, data)

        missing = []
        for ch in channels:
            try:
                member = await event.bot.get_chat_member(ch.channel_id, db_user.telegram_id)
                if member.status in ("left", "kicked"):
                    missing.append(ch)
            except:
                missing.append(ch)

        if missing:
            kb = InlineKeyboardBuilder()
            for ch in missing:
                kb.button(text=f"📢 {ch.channel_username}", url=f"https://t.me/{ch.channel_username.lstrip('@')}")
            kb.button(text="✅ Tekshirish", callback_data="check_sub")
            kb.adjust(1)
            
            if isinstance(event, Update) and event.message:
                await event.message.answer("⚠️ <b>Botdan foydalanish uchun quyidagi kanallarga obuna bo'ling:</b>", reply_markup=kb.as_markup())
            elif isinstance(event, Update) and event.callback_query:
                await event.callback_query.answer("Avval kanallarga obuna bo'ling!", show_alert=True)
            return
            
        return await handler(event, data)

# =========================================================================================
# 6. KLAVIATURALAR (KEYBOARDS)
# =========================================================================================
def main_reply_menu(role: UserRole) -> ReplyKeyboardMarkup:
    """Asosiy menyu"""
    kb = [
        [KeyboardButton(text="🎬 Anime Izlash"), KeyboardButton(text="🔥 Top Animelar")],
        [KeyboardButton(text="❓ Qo'llanma"), KeyboardButton(text="💎 VIP"), KeyboardButton(text="🤖 AI")],
        [KeyboardButton(text="⚙️ Sozlamalar"), KeyboardButton(text="ℹ️ Bot haqida")],
        [KeyboardButton(text="📢 Kanallarimiz")],
    ]
    if role in (UserRole.ADMIN, UserRole.OWNER):
        kb.append([KeyboardButton(text="⚙️ Admin Panel")])
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

def admin_inline_menu() -> InlineKeyboardMarkup:
    """Admin panel menyusi"""
    kb = InlineKeyboardBuilder()
    kb.button(text="🎬 Anime Boshqaruvi", callback_data="a_anime")
    kb.button(text="📢 Kanallarni Sozlash", callback_data="a_channels")
    kb.button(text="📣 Xabar Yuborish", callback_data="a_broadcast")
    kb.button(text="💎 VIP Tarif Qo'shish", callback_data="a_add_tariff")
    kb.button(text="📊 Statistika", callback_data="a_stats")
    kb.adjust(1, 1, 1, 1, 1)
    return kb.as_markup()

def admin_anime_menu() -> InlineKeyboardMarkup:
    """Anime boshqaruvi menyusi"""
    kb = InlineKeyboardBuilder()
    kb.button(text="🎬 Anime Yuklash", callback_data="a_add_anime")
    kb.button(text="💠 Qism Qo'shish", callback_data="a_add_episode")
    kb.button(text="🖇 Post Tayyorlash", callback_data="a_post")
    kb.button(text="❌ Admin Panel", callback_data="a_back")
    kb.adjust(2, 1, 1)
    return kb.as_markup()

def search_menu() -> InlineKeyboardMarkup:
    """Qidiruv menyusi"""
    kb = InlineKeyboardBuilder()
    kb.button(text="🎲 Tasodifiy anime", callback_data="s_random")
    kb.button(text="📝 Nom orqali", callback_data="s_name")
    kb.button(text="🔢 Kod orqali", callback_data="s_code")
    kb.button(text="👑 Top", callback_data="s_top")
    kb.button(text="📄 Eng Yangi", callback_data="s_new")
    kb.button(text="📼 Eng eski", callback_data="s_old")
    kb.button(text="🎞 Barcha animelar", callback_data="s_all")
    kb.button(text="🏠 Orqaga", callback_data="s_back")
    kb.adjust(1, 2, 3, 1, 1)
    return kb.as_markup()

def cancel_kb() -> ReplyKeyboardMarkup:
    """Bekor qilish tugmasi"""
    return ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="❌ Bekor qilish")]], resize_keyboard=True)

# =========================================================================================
# 7. HANDLERLAR (BARCHA LOGIKA)
# =========================================================================================
router = Router()

# --- ASOSIY MENYU VA START ---
@router.message(CommandStart())
async def cmd_start(message: Message, db_user: User, state: FSMContext):
    await state.clear()
    text = (
        f"👋 <b>Salom, {message.from_user.full_name}!</b>\n\n"
        f"🎌 <i>Anime botimizga xush kelibsiz!</i>\n"
        f"Bu yerda siz eng sara va sifatli animelarni topishingiz mumkin.\n\n"
        f"👇 Kerakli bo'limni tanlang:"
    )
    await message.answer(text, reply_markup=main_reply_menu(db_user.role))

@router.callback_query(F.data == "check_sub")
async def check_sub(call: CallbackQuery):
    await call.answer("✅ Tekshirildi! Agar obuna bo'lgan bo'lsangiz, qayta /start bosing.", show_alert=True)

@router.message(F.text == "❓ Qo'llanma")
async def guide(message: Message):
    await message.answer(
        "📖 <b>Botdan foydalanish qo'llanmasi:</b>\n\n"
        "1️⃣ <b>Anime Izlash</b> bo'limi orqali o'zingizga yoqqan animeni toping.\n"
        "2️⃣ <b>VIP</b> bo'limidan premium obuna sotib oling va yopiq animelarni ko'ring.\n"
        "3️⃣ Muammo yuzaga kelsa, adminga murojaat qiling."
    )

@router.message(F.text == "🤖 AI")
async def ai_stub(message: Message):
    await message.answer("🤖 <b>AI Yordamchi:</b>\n\nHozircha texnik xizmat ko'rsatilmoqda. Tez orada ishga tushadi! ⚡️")

@router.message(F.text == "⚙️ Sozlamalar")
async def user_settings(message: Message, db_user: User):
    await message.answer(
        f"⚙️ <b>Sizning sozlamalaringiz:</b>\n\n"
        f"🆔 <b>ID:</b> <code>{db_user.telegram_id}</code>\n"
        f"🎭 <b>Rol:</b> {db_user.role.value.upper()}\n"
        f"🌐 <b>Til:</b> O'zbekcha 🇺🇿"
    )

@router.message(F.text == "ℹ️ Bot haqida")
async def about_bot(message: Message):
    await message.answer("ℹ️ <b>Bot haqida:</b>\n\nUshbu bot orqali siz eng so'nggi va sifatli animelarni tomosha qilishingiz mumkin. Bot doimiy ravishda yangilanib boradi! 🚀")

@router.message(F.text == "📢 Kanallarimiz")
async def our_channels(message: Message):
    await message.answer("📢 <b>Bizning rasmiy kanallarimiz:</b>\n\n👉 @kanalimiz (namuna)")

# --- ADMIN PANEL ---
@router.message(Command("admin"))
@router.message(F.text == "⚙️ Admin Panel")
async def admin_panel(message: Message, db_user: User):
    if db_user.role not in (UserRole.ADMIN, UserRole.OWNER):
        return
    await message.answer("🚀 <b>Admin boshqaruv paneliga xush kelibsiz!</b>\nKerakli bo'limni tanlang:", reply_markup=admin_inline_menu())

@router.callback_query(F.data == "a_back")
async def admin_back(call: CallbackQuery):
    await call.message.edit_text("🚀 <b>Admin boshqaruv paneliga xush kelibsiz!</b>", reply_markup=admin_inline_menu())
    await call.answer()

@router.callback_query(F.data == "a_anime")
async def admin_anime_panel(call: CallbackQuery):
    await call.message.edit_text("🎬 <b>Anime Boshqaruvi</b>\nNima qilmoqchisiz?", reply_markup=admin_anime_menu())
    await call.answer()

# --- STATISTIKA ---
@router.callback_query(F.data == "a_stats")
async def stats_panel(call: CallbackQuery, session: AsyncSession):
    users_count = (await session.execute(select(func.count(User.id)))).scalar()
    animes_count = (await session.execute(select(func.count(Anime.id)))).scalar()
    ep_count = (await session.execute(select(func.count(Episode.id)))).scalar()
    
    text = (
        f"📊 <b>Bot Statistikasi</b>\n\n"
        f"👥 Foydalanuvchilar: <b>{users_count}</b>\n"
        f"🎬 Animelar: <b>{animes_count}</b>\n"
        f"📺 Qismlar: <b>{ep_count}</b>"
    )
    kb = InlineKeyboardBuilder()
    kb.button(text="⬅️ Orqaga", callback_data="a_back")
    await call.message.edit_text(text, reply_markup=kb.as_markup())
    await call.answer()

# --- QIDIRUV TIZIMI ---
@router.message(F.text == "🎬 Anime Izlash")
async def search_start(message: Message):
    await message.answer("🔍 <b>Anime Izlash</b>\n\nQidiruv turini tanlang:", reply_markup=search_menu())

@router.callback_query(F.data.startswith("s_"))
async def search_callback(call: CallbackQuery, session: AsyncSession, state: FSMContext):
    action = call.data.split("_")[1]
    
    if action == "back":
        await call.message.delete()
    elif action == "name":
        await state.set_state(SearchStates.waiting_name)
        await call.message.answer("📝 Anime nomini yozing:")
    elif action == "code":
        await state.set_state(SearchStates.waiting_code)
        await call.message.answer("🔢 Anime kodini (ID) yozing:")
    elif action == "all":
        result = await session.execute(select(Anime).order_by(Anime.id.desc()).limit(30))
        animes = result.scalars().all()
        text = "🎞 <b>Barcha animelar (oxirgi 30 ta):</b>\n\n" + "".join([f"<code>{a.id}</code> | {a.title}\n" for a in animes])
        await call.message.edit_text(text)
    elif action == "top":
        result = await session.execute(select(Anime).order_by(Anime.views.desc()).limit(10))
        animes = result.scalars().all()
        text = "👑 <b>TOP 10 Animelar:</b>\n\n" + "".join([f"<code>{a.id}</code> | {a.title} (👁 {a.views})\n" for a in animes])
        await call.message.edit_text(text)
    elif action == "random":
        result = await session.execute(select(Anime).order_by(func.random()).limit(1))
        anime = result.scalar_one_or_none()
        if anime:
            await call.message.answer(f"🎲 Tasodifiy anime:\n\n<code>{anime.id}</code> | {anime.title}")
        else:
            await call.answer("Hozircha animelar yo'q", show_alert=True)
    await call.answer()

@router.message(SearchStates.waiting_name)
async def search_by_name(message: Message, state: FSMContext, session: AsyncSession):
    await state.clear()
    result = await session.execute(select(Anime).where(Anime.title.ilike(f"%{message.text}%")))
    animes = result.scalars().all()
    text = "🔍 <b>Natijalar:</b>\n\n" + "".join([f"<code>{a.id}</code> | {a.title}\n" for a in animes]) if animes else "Hech narsa topilmadi."
    await message.answer(text)

@router.message(SearchStates.waiting_code)
async def search_by_code(message: Message, state: FSMContext, session: AsyncSession):
    await state.clear()
    try: 
        code = int(message.text)
    except: 
        return await message.answer("Faqat raqam yuboring.")
        
    result = await session.execute(select(Anime).where(Anime.id == code))
    anime = result.scalar_one_or_none()
    
    if not anime: 
        return await message.answer("Topilmadi.")
    
    anime.views += 1
    await session.flush()
    await message.answer(f"🎬 <b>{anime.title}</b>\n\n{anime.description or 'Tavsif yo`q'}\n👁 Ko'rishlar: {anime.views}")

# --- VIP TIZIMI ---
@router.message(F.text == "💎 VIP")
async def vip_shop(message: Message, session: AsyncSession):
    result = await session.execute(select(VipTariff).where(VipTariff.is_active == True))
    tariffs = result.scalars().all()
    
    if not tariffs: 
        return await message.answer("Hozircha VIP tariflar mavjud emas.")
        
    kb = InlineKeyboardBuilder()
    for t in tariffs: 
        kb.button(text=f"💎 {t.name} — {t.price:,} so'm", callback_data=f"buy_{t.id}")
    kb.adjust(1)
    await message.answer("💎 <b>VIP Tariflar</b>\n\nO'zingizga mos tarifni tanlang:", reply_markup=kb.as_markup())

@router.callback_query(F.data.startswith("buy_"))
async def buy_vip(call: CallbackQuery, session: AsyncSession, db_user: User):
    t_id = int(call.data.split("_")[1])
    tariff = await session.get(VipTariff, t_id)
    
    if not tariff: 
        return await call.answer("Tarif topilmadi", show_alert=True)
    
    sub = VipSubscription(user_id=db_user.id, tariff_id=tariff.id, end_date=datetime.utcnow() + timedelta(days=tariff.duration_days))
    session.add(sub)
    await session.flush()
    
    await call.message.edit_text(f"✅ <b>Tabriklaymiz!</b>\nSiz VIP obuna sotib oldingiz.\n📅 Amal qilish muddati: <b>{sub.end_date.strftime('%d.%m.%Y')}</b> gacha.")
    await call.answer()

# =========================================================================================
# ANIME YUKLASH JARAYONI (TO'LIQ VA MUKAMMAL)
# =========================================================================================
@router.callback_query(F.data == "a_add_anime")
async def anime_add_start(call: CallbackQuery, state: FSMContext):
    await state.set_state(AnimeStates.title)
    await call.message.answer("🎬 <b>Yangi anime nomini</b> yuboring:", reply_markup=cancel_kb())
    await call.answer()

@router.message(AnimeStates.title)
async def anime_title(message: Message, state: FSMContext):
    await state.update_data(title=message.text)
    await state.set_state(AnimeStates.description)
    await message.answer("📝 <b>Tavsif</b> yuboring (yoki /skip):")

@router.message(Command("skip"), AnimeStates.description)
async def anime_skip_desc(message: Message, state: FSMContext):
    await state.update_data(description=None)
    await state.set_state(AnimeStates.is_vip)
    
    kb = InlineKeyboardBuilder()
    kb.button(text="🎬 Oddiy", callback_data="vip_0")
    kb.button(text="💎 VIP", callback_data="vip_1")
    await message.answer("💎 Bu anime faqat VIP foydalanuvchilar uchunmi?", reply_markup=kb.as_markup())

@router.message(AnimeStates.description)
async def anime_desc(message: Message, state: FSMContext):
    await state.update_data(description=message.text)
    await state.set_state(AnimeStates.is_vip)
    
    kb = InlineKeyboardBuilder()
    kb.button(text="🎬 Oddiy", callback_data="vip_0")
    kb.button(text="💎 VIP", callback_data="vip_1")
    await message.answer("💎 Bu anime faqat VIP foydalanuvchilar uchunmi?", reply_markup=kb.as_markup())

@router.callback_query(F.data.startswith("vip_"), AnimeStates.is_vip)
async def anime_vip_choice(call: CallbackQuery, state: FSMContext, session: AsyncSession):
    is_vip = call.data == "vip_1"
    data = await state.get_data()
    
    anime = Anime(
        title=data.get("title", "Noma'lum"),
        description=data.get("description"),
        is_vip_only=is_vip,
        created_by=call.from_user.id
    )
    session.add(anime)
    await session.flush()
    
    await state.update_data(anime_id=anime.id)
    await state.set_state(AnimeStates.ep_num)
    await call.message.edit_text(f"✅ Anime yaratildi: <b>{anime.title}</b>\n\n📺 Endi 1-qism raqamini yuboring:")
    await call.answer()

@router.message(AnimeStates.ep_num)
async def ep_num(message: Message, state: FSMContext):
    try: 
        num = int(message.text)
    except: 
        return await message.answer("❌ Faqat raqam yuboring:")
        
    await state.update_data(ep_num=num)
    await state.set_state(AnimeStates.ep_file)
    await message.answer("🎥 Endi video faylni yuboring:")

@router.message(AnimeStates.ep_file, F.video)
async def ep_file(message: Message, state: FSMContext, session: AsyncSession, db_user: User):
    data = await state.get_data()
    ep = Episode(anime_id=data["anime_id"], number=data["ep_num"], file_id=message.video.file_id)
    session.add(ep)
    await session.flush()
    await state.clear()
    await message.answer("✅ <b>Qism muvaffaqiyatli qo'shildi!</b>", reply_markup=main_reply_menu(db_user.role))
# =========================================================================================

# --- POST TAYYORLASH (ADMIN) ---
@router.callback_query(F.data == "a_post")
async def post_start(call: CallbackQuery, state: FSMContext):
    await state.set_state(PostStates.waiting_anime_id)
    await call.message.answer("🖇 Qaysi anime uchun post tayyorlaymiz? Anime <b>ID</b> raqamini yuboring:", reply_markup=cancel_kb())
    await call.answer()

@router.message(PostStates.waiting_anime_id)
async def post_anime_id(message: Message, state: FSMContext, session: AsyncSession):
    try: 
        anime_id = int(message.text)
    except: 
        return await message.answer("Faqat ID raqam yuboring:")
    
    anime = await session.get(Anime, anime_id)
    if not anime: 
        return await message.answer("Bunday ID li anime topilmadi.")
    
    await state.update_data(post_anime_id=anime_id)
    await state.set_state(PostStates.waiting_text)
    await message.answer(f"🖇 <b>{anime.title}</b> uchun post matnini yuboring:")

@router.message(PostStates.waiting_text)
async def post_text(message: Message, state: FSMContext, session: AsyncSession, db_user: User):
    data = await state.get_data()
    anime_id = data["post_anime_id"]
    await state.clear()
    await message.answer(f"✅ <b>Post tayyorlandi!</b>\n\n🎬 Anime ID: {anime_id}\n📝 Matn: {message.text or message.caption}", reply_markup=main_reply_menu(db_user.role))

# --- KANALLAR (ADMIN) ---
@router.callback_query(F.data == "a_channels")
async def channels_menu(call: CallbackQuery, session: AsyncSession):
    result = await session.execute(select(MandatoryChannel))
    channels = result.scalars().all()
    text = "📢 <b>Majburiy kanallar</b>\n\n" + ("".join([f"• {ch.channel_username}\n" for ch in channels]) if channels else "Hozircha yo'q")
    
    kb = InlineKeyboardBuilder()
    kb.button(text="➕ Kanal qo'shish", callback_data="a_add_channel")
    kb.button(text="⬅️ Orqaga", callback_data="a_back")
    kb.adjust(1)
    await call.message.edit_text(text, reply_markup=kb.as_markup())
    await call.answer()

@router.callback_query(F.data == "a_add_channel")
async def add_channel_start(call: CallbackQuery, state: FSMContext):
    await state.set_state(ChannelStates.waiting_channel)
    await call.message.answer("📢 Kanal username yuboring (masalan: @kanalim):", reply_markup=cancel_kb())
    await call.answer()

@router.message(ChannelStates.waiting_channel)
async def add_channel_save(message: Message, state: FSMContext, session: AsyncSession, db_user: User):
    username = message.text.strip()
    try:
        chat = await message.bot.get_chat(username)
        ch = MandatoryChannel(channel_id=chat.id, channel_username=username)
        session.add(ch)
        await session.flush()
        await state.clear()
        await message.answer(f"✅ Kanal qo'shildi: {username}", reply_markup=main_reply_menu(db_user.role))
    except Exception as e:
        await message.answer(f"❌ Xatolik: {e}")

# --- BROADCAST (ADMIN) ---
@router.callback_query(F.data == "a_broadcast")
async def broadcast_start(call: CallbackQuery, state: FSMContext):
    await state.set_state(BroadcastStates.waiting_message)
    await call.message.answer("📣 Tarqatiladigan xabarni yuboring:", reply_markup=cancel_kb())
    await call.answer()

@router.message(BroadcastStates.waiting_message)
async def broadcast_send(message: Message, state: FSMContext, session: AsyncSession):
    await state.clear()
    status = await message.answer("⏳ Tarqatish boshlandi...")
    
    result = await session.execute(select(User))
    users = result.scalars().all()
    sent = 0
    
    for u in users:
        try: 
            await message.copy_to(u.telegram_id)
            sent += 1
        except: 
            pass
        await asyncio.sleep(0.05)
        
    await status.edit_text(f"✅ Tarqatish tugadi. Yuborildi: {sent}")

# --- TARIF QO'SHISH (OWNER) ---
@router.callback_query(F.data == "a_add_tariff", IsOwner())
async def tariff_start(call: CallbackQuery, state: FSMContext):
    await state.set_state(TariffStates.name)
    await call.message.answer("💎 Tarif nomini yuboring:", reply_markup=cancel_kb())
    await call.answer()

@router.message(TariffStates.name)
async def tariff_name(message: Message, state: FSMContext):
    await state.update_data(name=message.text)
    await state.set_state(TariffStates.price)
    await message.answer("💰 Narxini yuboring:")

@router.message(TariffStates.price)
async def tariff_price(message: Message, state: FSMContext):
    try: 
        price = int(message.text)
    except: 
        return await message.answer("Faqat raqam:")
        
    await state.update_data(price=price)
    await state.set_state(TariffStates.duration)
    await message.answer("📅 Necha kunlik?")

@router.message(TariffStates.duration)
async def tariff_duration(message: Message, state: FSMContext, session: AsyncSession, db_user: User):
    try: 
        days = int(message.text)
    except: 
        return await message.answer("Faqat raqam:")
        
    data = await state.get_data()
    tariff = VipTariff(name=data["name"], price=data["price"], duration_days=days)
    session.add(tariff)
    await session.flush()
    await state.clear()
    await message.answer(f"✅ Tarif qo'shildi!", reply_markup=main_reply_menu(db_user.role))

# --- BEKOR QILISH ---
@router.message(F.text == "❌ Bekor qilish")
async def cancel(message: Message, state: FSMContext, db_user: User):
    await state.clear()
    await message.answer("❌ Bekor qilindi", reply_markup=main_reply_menu(db_user.role))

# =========================================================================================
# 8. BOTNI ISHGA TUSHIRISH
# =========================================================================================
async def main():
    # Bot va Dispatcher yaratish
    bot = Bot(token=settings.BOT_TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
    dp = Dispatcher(storage=MemoryStorage())
    
    # Middlewarelarni ulash
    dp.update.outer_middleware(DBSessionMiddleware())
    dp.update.outer_middleware(UserMiddleware())
    dp.update.outer_middleware(SubscriptionMiddleware())
    
    # Routerni ulash
    dp.include_router(router)

    # Bazani yaratish
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    logger.info("✅ Database tayyor, bot ishga tushmoqda...")
    await bot.delete_webhook(drop_pending_updates=True)
    
    # Botni ishga tushirish
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.warning("Bot to'xtatildi")
