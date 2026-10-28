import asyncio
from datetime import datetime, timedelta
from enum import Enum as PyEnum

from aiogram import Bot, Dispatcher, Router, F, BaseMiddleware
from aiogram.client.default import DefaultBotProperties
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import BaseFilter, Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import (
    CallbackQuery, InlineKeyboardMarkup, KeyboardButton, Message,
    ReplyKeyboardMarkup, TelegramObject, Update
)
from aiogram.utils.keyboard import InlineKeyboardBuilder
from loguru import logger
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import BigInteger, Boolean, DateTime, Enum, ForeignKey, Integer, String, Text, select, func
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship, selectinload

# ═══════════════════════════════════════════════════════════════
# 1. CONFIG & LOGGER
# ═══════════════════════════════════════════════════════════════
class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")
    BOT_TOKEN: str
    OWNER_ID: int
    DB_URL: str = "sqlite+aiosqlite:///./anime.db"
    LOG_LEVEL: str = "INFO"

settings = Settings()
logger.remove()
logger.add(lambda msg: print(msg, end=""), level=settings.LOG_LEVEL)

# ═══════════════════════════════════════════════════════════════
# 2. DATABASE & MODELS
# ═══════════════════════════════════════════════════════════════
class Base(DeclarativeBase): pass
engine = create_async_engine(settings.DB_URL, echo=False, pool_pre_ping=True)
AsyncSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

class UserRole(PyEnum):
    OWNER = "owner"
    ADMIN = "admin"
    USER = "user"

class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True)
    full_name: Mapped[str] = mapped_column(String(255))
    username: Mapped[str | None] = mapped_column(String(64), nullable=True)
    role: Mapped[UserRole] = mapped_column(Enum(UserRole), default=UserRole.USER)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    subscriptions = relationship("VipSubscription", back_populates="user", cascade="all, delete-orphan")

class Anime(Base):
    __tablename__ = "anime"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(255), index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_vip_only: Mapped[bool] = mapped_column(Boolean, default=False)
    views: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    episodes = relationship("Episode", back_populates="anime", cascade="all, delete-orphan")

class Episode(Base):
    __tablename__ = "episodes"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    anime_id: Mapped[int] = mapped_column(ForeignKey("anime.id", ondelete="CASCADE"))
    number: Mapped[int] = mapped_column(Integer)
    file_id: Mapped[str] = mapped_column(String(255))
    anime = relationship("Anime", back_populates="episodes")

class VipTariff(Base):
    __tablename__ = "vip_tariffs"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100))
    price: Mapped[int] = mapped_column(Integer)
    duration_days: Mapped[int] = mapped_column(Integer)

class VipSubscription(Base):
    __tablename__ = "vip_subscriptions"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    tariff_id: Mapped[int] = mapped_column(ForeignKey("vip_tariffs.id"))
    end_date: Mapped[datetime] = mapped_column(DateTime)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    user = relationship("User", back_populates="subscriptions")

class MandatoryChannel(Base):
    __tablename__ = "mandatory_channels"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    channel_id: Mapped[int] = mapped_column(BigInteger, unique=True)
    channel_username: Mapped[str] = mapped_column(String(100))

# ═══════════════════════════════════════════════════════════════
# 3. FSM STATES
# ═══════════════════════════════════════════════════════════════
class AnimeStates(StatesGroup):
    title, description, is_vip, ep_num, ep_file = State(), State(), State(), State(), State()

class ChannelStates(StatesGroup):
    waiting_channel = State()

class BroadcastStates(StatesGroup):
    waiting_message = State()

class TariffStates(StatesGroup):
    name, price, duration = State(), State(), State()

class SearchStates(StatesGroup):
    waiting_name = State()
    waiting_code = State()

class PostStates(StatesGroup):
    waiting_anime_id = State()
    waiting_text = State()

# ═══════════════════════════════════════════════════════════════
# 4. FILTERS & MIDDLEWARES
# ═══════════════════════════════════════════════════════════════
class IsOwner(BaseFilter):
    async def __call__(self, event, **kwargs) -> bool:
        user = kwargs.get("db_user")
        return user is not None and user.role == UserRole.OWNER

class IsAdmin(BaseFilter):
    async def __call__(self, event, **kwargs) -> bool:
        user = kwargs.get("db_user")
        return user is not None and user.role in (UserRole.OWNER, UserRole.ADMIN)

class DBSessionMiddleware(BaseMiddleware):
    async def __call__(self, handler, event: TelegramObject, data: dict):
        async with AsyncSessionLocal() as session:
            data["session"] = session
            try:
                result = await handler(event, data)
                await session.commit()
                return result
            except Exception:
                await session.rollback()
                raise

class UserMiddleware(BaseMiddleware):
    async def __call__(self, handler, event: TelegramObject, data: dict):
        session: AsyncSession = data["session"]
        tg_user = None
        if isinstance(event, Update):
            if event.message: tg_user = event.message.from_user
            elif event.callback_query: tg_user = event.callback_query.from_user

        if tg_user:
            result = await session.execute(select(User).where(User.telegram_id == tg_user.id))
            user = result.scalar_one_or_none()
            if user is None:
                role = UserRole.OWNER if tg_user.id == settings.OWNER_ID else UserRole.USER
                user = User(telegram_id=tg_user.id, full_name=tg_user.full_name, username=tg_user.username, role=role)
                session.add(user)
                await session.flush()
            data["db_user"] = user
        return await handler(event, data)

class SubscriptionMiddleware(BaseMiddleware):
    async def __call__(self, handler, event: TelegramObject, data: dict):
        session: AsyncSession = data["session"]
        db_user: User = data.get("db_user")

        if db_user is None or db_user.role in (UserRole.OWNER, UserRole.ADMIN):
            return await handler(event, data)
        
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

# ═══════════════════════════════════════════════════════════════
# 5. KEYBOARDS
# ═══════════════════════════════════════════════════════════════
def main_reply_menu(role: UserRole) -> ReplyKeyboardMarkup:
    kb = [
        [KeyboardButton(text="🎬 Anime Izlash")],
        [KeyboardButton(text="❓ Qo'llanma"), KeyboardButton(text="💎 VIP"), KeyboardButton(text="🤖 AI")],
        [KeyboardButton(text="⚙️ Sozlamalar"), KeyboardButton(text="ℹ️ Bot haqida")],
        [KeyboardButton(text="📢 Kanallarimiz")],
    ]
    if role in (UserRole.ADMIN, UserRole.OWNER):
        kb.append([KeyboardButton(text="⚙️ Admin Panel")])
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

def admin_inline_menu() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="🎬 Anime", callback_data="a_anime")
    kb.button(text="📢 Kanallarni Sozlash", callback_data="a_channels")
    kb.button(text="📣 Xabar Yuborish", callback_data="a_broadcast")
    kb.button(text="💎 VIP Tarif Qo'shish", callback_data="a_add_tariff")
    kb.button(text="📊 Statistika", callback_data="a_stats")
    kb.adjust(1, 1, 1, 1, 1)
    return kb.as_markup()

def admin_anime_menu() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="🎬 Anime Yuklash", callback_data="a_add_anime")
    kb.button(text="💠 Qism Qo'shish", callback_data="a_add_episode")
    kb.button(text="🖇 Post Tayyorlash", callback_data="a_post")
    kb.button(text="❌ Admin Panel", callback_data="a_back")
    kb.adjust(2, 1, 1)
    return kb.as_markup()

def search_menu() -> InlineKeyboardMarkup:
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

def cancel_kb():
    return ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="❌ Bekor qilish")]], resize_keyboard=True)

# ═══════════════════════════════════════════════════════════════
# 6. HANDLERS
# ═══════════════════════════════════════════════════════════════
router = Router()

# ─── ASOSIY MENYU ─────────────────────────────────────────────
@router.message(CommandStart())
async def cmd_start(message: Message, db_user: User, state: FSMContext):
    await state.clear()
    await message.answer(f"👋 <b>Salom, {message.from_user.full_name}!</b>\n\n🎌 <i>Anime botimizga xush kelibsiz!</i>", reply_markup=main_reply_menu(db_user.role))

@router.callback_query(F.data == "check_sub")
async def check_sub(call: CallbackQuery):
    await call.answer("✅ Tekshirildi! Agar obuna bo'lgan bo'lsangiz, qayta urinib ko'ring.", show_alert=True)

@router.message(F.text == "❓ Qo'llanma")
async def guide(message: Message):
    await message.answer("📖 <b>Qo'llanma:</b>\n\n1. <b>Anime Izlash</b> orqali animelarni toping.\n2. <b>VIP</b> bo'limidan premium obuna sotib oling.")

@router.message(F.text == "🤖 AI")
async def ai_stub(message: Message):
    await message.answer("🤖 <b>AI Yordamchi:</b>\n\nHozircha texnik xizmat ko'rsatilmoqda. Tez orada ishga tushadi! ⚡️")

# BU YERDA XATOLIK TUZATILDI (settings -> user_settings)
@router.message(F.text == "⚙️ Sozlamalar")
async def user_settings(message: Message, db_user: User):
    await message.answer(f"⚙️ <b>Sozlamalar:</b>\n\n🆔 ID: <code>{db_user.telegram_id}</code>\n🎭 Rol: {db_user.role.value.upper()}\n🌐 Til: O'zbekcha 🇺🇿")

@router.message(F.text == "ℹ️ Bot haqida")
async def about_bot(message: Message):
    await message.answer("ℹ️ <b>Bot haqida:</b>\n\nEng so'nggi va sifatli animelarni tomosha qiling. Bot doimiy yangilanib turadi! 🚀")

@router.message(F.text == "📢 Kanallarimiz")
async def our_channels(message: Message):
    await message.answer("📢 <b>Rasmiy kanallarimiz:</b>\n\n👉 @kanalimiz (namuna)")

# ─── ADMIN PANEL ──────────────────────────────────────────────
@router.message(Command("admin"))
@router.message(F.text == "⚙️ Admin Panel")
async def admin_panel(message: Message, db_user: User):
    if db_user.role not in (UserRole.ADMIN, UserRole.OWNER): return
    await message.answer("🚀 <b>Admin panelga xush kelibsiz!</b>", reply_markup=admin_inline_menu())

@router.callback_query(F.data == "a_back")
async def admin_back(call: CallbackQuery):
    await call.message.edit_text("🚀 <b>Admin panelga xush kelibsiz!</b>", reply_markup=admin_inline_menu())
    await call.answer()

@router.callback_query(F.data == "a_anime")
async def admin_anime_panel(call: CallbackQuery):
    await call.message.edit_text("🎬 <b>Anime bo'limi</b>", reply_markup=admin_anime_menu())
    await call.answer()

# ─── STATISTIKA ───────────────────────────────────────────────
@router.callback_query(F.data == "a_stats")
async def stats_panel(call: CallbackQuery, session: AsyncSession):
    users_count = (await session.execute(select(func.count(User.id)))).scalar()
    animes_count = (await session.execute(select(func.count(Anime.id)))).scalar()
    text = f"📊 <b>Statistika</b>\n\n👥 Foydalanuvchilar: {users_count}\n🎬 Animelar: {animes_count}"
    kb = InlineKeyboardBuilder(); kb.button(text="⬅️ Orqaga", callback_data="a_back")
    await call.message.edit_text(text, reply_markup=kb.as_markup()); await call.answer()

# ─── QIDIRUV (USER) ───────────────────────────────────────────
@router.message(F.text == "🎬 Anime Izlash")
async def search_start(message: Message):
    await message.answer("🔍 <b>Anime Izlash</b>\n\nQidiruv turini tanlang:", reply_markup=search_menu())

@router.callback_query(F.data.startswith("s_"))
async def search_callback(call: CallbackQuery, session: AsyncSession, state: FSMContext):
    action = call.data.split("_")[1]
    if action == "back": await call.message.delete()
    elif action == "name": await state.set_state(SearchStates.waiting_name); await call.message.answer("📝 Nomini yozing:")
    elif action == "code": await state.set_state(SearchStates.waiting_code); await call.message.answer("🔢 Kodini yozing:")
    elif action == "all":
        result = await session.execute(select(Anime).order_by(Anime.id.desc()))
        animes = result.scalars().all()
        text = "🎞 <b>Barcha animelar:</b>\n\n" + "".join([f"<code>{a.id}</code> | {a.title}\n" for a in animes])
        await call.message.edit_text(text)
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
    try: code = int(message.text)
    except: return await message.answer("Faqat raqam yuboring.")
    result = await session.execute(select(Anime).where(Anime.id == code))
    anime = result.scalar_one_or_none()
    if not anime: return await message.answer("Topilmadi.")
    anime.views += 1; await session.flush()
    await message.answer(f"🎬 <b>{anime.title}</b>\n\n{anime.description or ''}\n👁 Ko'rishlar: {anime.views}")

# ─── VIP TIZIMI ───────────────────────────────────────────────
@router.message(F.text == "💎 VIP")
async def vip_shop(message: Message, session: AsyncSession):
    result = await session.execute(select(VipTariff))
    tariffs = result.scalars().all()
    if not tariffs: return await message.answer("Hozircha VIP tariflar yo'q.")
    kb = InlineKeyboardBuilder()
    for t in tariffs: kb.button(text=f"💎 {t.name} — {t.price:,} so'm", callback_data=f"buy_{t.id}")
    kb.adjust(1)
    await message.answer("💎 <b>VIP Tariflar</b>", reply_markup=kb.as_markup())

@router.callback_query(F.data.startswith("buy_"))
async def buy_vip(call: CallbackQuery, session: AsyncSession, db_user: User):
    t_id = int(call.data.split("_")[1])
    tariff = await session.get(VipTariff, t_id)
    sub = VipSubscription(user_id=db_user.id, tariff_id=tariff.id, end_date=datetime.utcnow() + timedelta(days=tariff.duration_days))
    session.add(sub); await session.flush()
    await call.message.edit_text(f"✅ VIP obuna olindi! {sub.end_date.strftime('%d.%m.%Y')} gacha."); await call.answer()

# ─── ANIME YUKLASH (ADMIN) ────────────────────────────────────
@router.callback_query(F.data == "a_add_anime")
async def anime_add_start(call: CallbackQuery, state: FSMContext):
    await state.set_state(AnimeStates.title)
    await call.message.answer("🎬 Anime nomini yuboring:", reply_markup=cancel_kb()); await call.answer()

@router.message(AnimeStates.title)
async def anime_title(message: Message, state: FSMContext):
    await state.update_data(title=message.text); await state.set_state(AnimeStates.description)
    await message.answer("📝 Tavsif yuboring (yoki /skip):")

@router.message(Command("skip"), AnimeStates.description)
async def anime_skip(message: Message, state: FSMContext):
    await state.update_data(description=None); await state.set_state(AnimeStates.is_vip)
    kb = InlineKeyboardBuilder(); kb.button(text="🎬 Oddiy", callback_data="vip_0"); kb.button(text="💎 VIP", callback_data="vip_1")
    await message.answer("💎 VIP uchunmi?", reply_markup=kb.as_markup())

@router.message(AnimeStates.description)
async def anime_desc(message: Message, state: FSMContext):
    await state.update_data(description=message.text); await state.set_state(AnimeStates.is_vip)
    kb = InlineKeyboardBuilder(); kb.button(text="🎬 Oddiy", callback_data="vip_0"); kb.button(text="💎 VIP", callback_data="vip_1")
    await message.answer("💎 VIP uchunmi?", reply_markup=kb.as_markup())

@router.callback_query(F.data.startswith("vip_"), AnimeStates.is_vip)
async def anime_vip_choice(call: CallbackQuery, state: FSMContext, session: AsyncSession):
    is_vip = call.data == "vip_1"
    data = await state.get_data()
    anime = Anime(title=data["title"], description=data.get("description"), is_vip_only=is_vip, created_by=call.from_user.id)
    session.add(anime); await session.flush()
    await state.update_data(anime_id=anime.id); await state.set_state(AnimeStates.ep_num)
    await call.message.edit_text(f"✅ Yaratildi: <b>{anime.title}</b>\n\n📺 1-qism raqamini yuboring:"); await call.answer()

@router.message(AnimeStates.ep_num)
async def ep_num(message: Message, state: FSMContext):
    try: num = int(message.text)
    except: return await message.answer("Faqat raqam:")
    await state.update_data(ep_num=num); await state.set_state(AnimeStates.ep_file)
    await message.answer("🎥 Video yuboring:")

@router.message(AnimeStates.ep_file, F.video)
async def ep_file(message: Message, state: FSMContext, session: AsyncSession, db_user: User):
    data = await state.get_data()
    ep = Episode(anime_id=data["anime_id"], number=data["ep_num"], file_id=message.video.file_id)
    session.add(ep); await session.flush(); await state.clear()
    await message.answer("✅ Qism qo'shildi!", reply_markup=main_reply_menu(db_user.role))

# ─── POST TAYYORLASH (ADMIN) ──────────────────────────────────
@router.callback_query(F.data == "a_post")
async def post_start(call: CallbackQuery, state: FSMContext):
    await state.set_state(PostStates.waiting_anime_id)
    await call.message.answer("🖇 Qaysi anime uchun post tayyorlaymiz? Anime <b>ID</b> raqamini yuboring:", reply_markup=cancel_kb())
    await call.answer()

@router.message(PostStates.waiting_anime_id)
async def post_anime_id(message: Message, state: FSMContext, session: AsyncSession):
    try: anime_id = int(message.text)
    except: return await message.answer("Faqat ID raqam yuboring:")
    
    anime = await session.get(Anime, anime_id)
    if not anime: return await message.answer("Bunday ID li anime topilmadi.")
    
    await state.update_data(post_anime_id=anime_id)
    await state.set_state(PostStates.waiting_text)
    await message.answer(f"🖇 <b>{anime.title}</b> uchun post matnini yuboring (yoki rasm/video bilan birga caption qilib yuboring):")

@router.message(PostStates.waiting_text)
async def post_text(message: Message, state: FSMContext, session: AsyncSession, db_user: User):
    data = await state.get_data()
    anime_id = data["post_anime_id"]
    await state.clear()

    await message.answer(
        f"✅ <b>Post muvaffaqiyatli tayyorlandi!</b>\n\n"
        f"🎬 Anime ID: {anime_id}\n"
        f"📝 Matn: {message.text or message.caption or 'Media bilan'}\n\n"
        f"<i>Postni kanalingizga joylashingiz mumkin.</i>",
        reply_markup=main_reply_menu(db_user.role)
    )

# ─── KANALLAR (ADMIN) ─────────────────────────────────────────
@router.callback_query(F.data == "a_channels")
async def channels_menu(call: CallbackQuery, session: AsyncSession):
    result = await session.execute(select(MandatoryChannel))
    channels = result.scalars().all()
    text = "📢 <b>Majburiy kanallar</b>\n\n" + ("".join([f"• {ch.channel_username}\n" for ch in channels]) if channels else "Hozircha yo'q")
    kb = InlineKeyboardBuilder(); kb.button(text="➕ Kanal qo'shish", callback_data="a_add_channel"); kb.button(text="⬅️ Orqaga", callback_data="a_back"); kb.adjust(1)
    await call.message.edit_text(text, reply_markup=kb.as_markup()); await call.answer()

@router.callback_query(F.data == "a_add_channel")
async def add_channel_start(call: CallbackQuery, state: FSMContext):
    await state.set_state(ChannelStates.waiting_channel)
    await call.message.answer("📢 Kanal username yuboring (masalan: @kanalim):", reply_markup=cancel_kb()); await call.answer()

@router.message(ChannelStates.waiting_channel)
async def add_channel_save(message: Message, state: FSMContext, session: AsyncSession, db_user: User):
    username = message.text.strip()
    try:
        chat = await message.bot.get_chat(username)
        ch = MandatoryChannel(channel_id=chat.id, channel_username=username)
        session.add(ch); await session.flush(); await state.clear()
        await message.answer(f"✅ Kanal qo'shildi: {username}", reply_markup=main_reply_menu(db_user.role))
    except Exception as e:
        await message.answer(f"❌ Xatolik: {e}")

# ─── BROADCAST (ADMIN) ────────────────────────────────────────
@router.callback_query(F.data == "a_broadcast")
async def broadcast_start(call: CallbackQuery, state: FSMContext):
    await state.set_state(BroadcastStates.waiting_message)
    await call.message.answer("📣 Tarqatiladigan xabarni yuboring:", reply_markup=cancel_kb()); await call.answer()

@router.message(BroadcastStates.waiting_message)
async def broadcast_send(message: Message, state: FSMContext, session: AsyncSession):
    await state.clear()
    status = await message.answer("⏳ Tarqatish boshlandi...")
    result = await session.execute(select(User))
    users = result.scalars().all()
    sent = 0
    for u in users:
        try: await message.copy_to(u.telegram_id); sent += 1
        except: pass
        await asyncio.sleep(0.05)
    await status.edit_text(f"✅ Tarqatish tugadi. Yuborildi: {sent}")

# ─── TARIF QO'SHISH (OWNER) ───────────────────────────────────
@router.callback_query(F.data == "a_add_tariff", IsOwner())
async def tariff_start(call: CallbackQuery, state: FSMContext):
    await state.set_state(TariffStates.name)
    await call.message.answer("💎 Tarif nomini yuboring:", reply_markup=cancel_kb()); await call.answer()

@router.message(TariffStates.name)
async def tariff_name(message: Message, state: FSMContext):
    await state.update_data(name=message.text); await state.set_state(TariffStates.price)
    await message.answer("💰 Narxini yuboring:")

@router.message(TariffStates.price)
async def tariff_price(message: Message, state: FSMContext):
    try: price = int(message.text)
    except: return await message.answer("Faqat raqam:")
    await state.update_data(price=price); await state.set_state(TariffStates.duration)
    await message.answer("📅 Necha kunlik?")

@router.message(TariffStates.duration)
async def tariff_duration(message: Message, state: FSMContext, session: AsyncSession, db_user: User):
    try: days = int(message.text)
    except: return await message.answer("Faqat raqam:")
    data = await state.get_data()
    tariff = VipTariff(name=data["name"], price=data["price"], duration_days=days)
    session.add(tariff); await session.flush(); await state.clear()
    await message.answer(f"✅ Tarif qo'shildi!", reply_markup=main_reply_menu(db_user.role))

# ─── BEKOR QILISH ─────────────────────────────────────────────
@router.message(F.text == "❌ Bekor qilish")
async def cancel(message: Message, state: FSMContext, db_user: User):
    await state.clear(); await message.answer("❌ Bekor qilindi", reply_markup=main_reply_menu(db_user.role))

# ═══════════════════════════════════════════════════════════════
# 7. BOT START
# ═══════════════════════════════════════════════════════════════
bot = Bot(token=settings.BOT_TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
dp = Dispatcher(storage=MemoryStorage())
dp.update.outer_middleware(DBSessionMiddleware())
dp.update.outer_middleware(UserMiddleware())
dp.update.outer_middleware(SubscriptionMiddleware()) # Majburiy obuna
dp.include_router(router)

async def main():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("✅ Database tayyor, bot ishga tushmoqda...")
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    try: asyncio.run(main())
    except (KeyboardInterrupt, SystemExit): logger.warning("Bot to'xtatildi")
