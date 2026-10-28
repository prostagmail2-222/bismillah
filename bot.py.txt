"""
Anime Telegram Bot — To'liq bitta faylli versiya.
Ishga tushirish: python bot.py
"""

import asyncio
from datetime import datetime, timedelta
from enum import Enum as PyEnum
from functools import wraps

from aiogram import Bot, Dispatcher, Router, F, BaseMiddleware
from aiogram.client.default import DefaultBotProperties
from aiogram.exceptions import (
    TelegramBadRequest,
    TelegramForbiddenError,
    TelegramRetryAfter,
)
from aiogram.filters import BaseFilter, Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardMarkup,
    KeyboardButton,
    Message,
    ReplyKeyboardMarkup,
    TelegramObject,
    Update,
)
from aiogram.utils.keyboard import InlineKeyboardBuilder
from loguru import logger
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
    select,
)
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    mapped_column,
    relationship,
    selectinload,
)


# ═══════════════════════════════════════════════════════════════
# 1. CONFIG
# ═══════════════════════════════════════════════════════════════
class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    BOT_TOKEN: str
    OWNER_ID: int
    DB_URL: str = "sqlite+aiosqlite:///./anime.db"
    LOG_LEVEL: str = "INFO"


settings = Settings()

logger.remove()
logger.add(
    lambda msg: print(msg, end=""),
    level=settings.LOG_LEVEL,
    format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>",
)


# ═══════════════════════════════════════════════════════════════
# 2. DATABASE
# ═══════════════════════════════════════════════════════════════
class Base(DeclarativeBase):
    pass


engine = create_async_engine(settings.DB_URL, echo=False, pool_pre_ping=True)
AsyncSessionLocal = async_sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)


# ═══════════════════════════════════════════════════════════════
# 3. MODELS
# ═══════════════════════════════════════════════════════════════
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
    is_banned: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    subscriptions = relationship(
        "VipSubscription", back_populates="user", cascade="all, delete-orphan"
    )


class Anime(Base):
    __tablename__ = "anime"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(255), index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    genre: Mapped[str | None] = mapped_column(String(255), nullable=True)
    year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    is_vip_only: Mapped[bool] = mapped_column(Boolean, default=False)
    created_by: Mapped[int] = mapped_column(BigInteger)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    episodes = relationship(
        "Episode", back_populates="anime", cascade="all, delete-orphan"
    )


class Episode(Base):
    __tablename__ = "episodes"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    anime_id: Mapped[int] = mapped_column(ForeignKey("anime.id", ondelete="CASCADE"))
    number: Mapped[int] = mapped_column(Integer)
    file_id: Mapped[str] = mapped_column(String(255))
    added_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    anime = relationship("Anime", back_populates="episodes")


class VipTariff(Base):
    __tablename__ = "vip_tariffs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100))
    price: Mapped[int] = mapped_column(Integer)
    duration_days: Mapped[int] = mapped_column(Integer)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class VipSubscription(Base):
    __tablename__ = "vip_subscriptions"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    tariff_id: Mapped[int] = mapped_column(ForeignKey("vip_tariffs.id"))
    start_date: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    end_date: Mapped[datetime] = mapped_column(DateTime)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    user = relationship("User", back_populates="subscriptions")


class MandatoryChannel(Base):
    __tablename__ = "mandatory_channels"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    channel_id: Mapped[int] = mapped_column(BigInteger, unique=True)
    channel_username: Mapped[str] = mapped_column(String(100))
    invite_link: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


# ═══════════════════════════════════════════════════════════════
# 4. FSM STATES
# ═══════════════════════════════════════════════════════════════
class AnimeStates(StatesGroup):
    title = State()
    description = State()
    genre = State()
    year = State()
    is_vip = State()
    episode_number = State()
    episode_file = State()


class AdminStates(StatesGroup):
    waiting_admin_id = State()


class ChannelStates(StatesGroup):
    waiting_channel = State()


class BroadcastStates(StatesGroup):
    waiting_message = State()


class TariffStates(StatesGroup):
    name = State()
    price = State()
    duration = State()


# ═══════════════════════════════════════════════════════════════
# 5. FILTERS
# ═══════════════════════════════════════════════════════════════
class IsOwner(BaseFilter):
    async def __call__(self, event, **kwargs) -> bool:
        user = kwargs.get("db_user")
        return user is not None and user.role == UserRole.OWNER


class IsAdmin(BaseFilter):
    async def __call__(self, event, **kwargs) -> bool:
        user = kwargs.get("db_user")
        return user is not None and user.role in (UserRole.OWNER, UserRole.ADMIN)


# ═══════════════════════════════════════════════════════════════
# 6. MIDDLEWARES
# ═══════════════════════════════════════════════════════════════
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
            if event.message:
                tg_user = event.message.from_user
            elif event.callback_query:
                tg_user = event.callback_query.from_user

        if tg_user:
            result = await session.execute(
                select(User).where(User.telegram_id == tg_user.id)
            )
            user = result.scalar_one_or_none()
            if user is None:
                role = (
                    UserRole.OWNER
                    if tg_user.id == settings.OWNER_ID
                    else UserRole.USER
                )
                user = User(
                    telegram_id=tg_user.id,
                    full_name=tg_user.full_name,
                    username=tg_user.username,
                    role=role,
                )
                session.add(user)
                await session.flush()
            data["db_user"] = user
        return await handler(event, data)


class ThrottlingMiddleware(BaseMiddleware):
    def __init__(self, rate_limit: float = 0.5):
        self.rate_limit = rate_limit
        self.users: dict[int, float] = {}

    async def __call__(self, handler, event: TelegramObject, data: dict):
        user = getattr(event, "from_user", None)
        if user:
            import time

            now = time.monotonic()
            last = self.users.get(user.id, 0)
            if now - last < self.rate_limit:
                return
            self.users[user.id] = now
        return await handler(event, data)


class SubscriptionMiddleware(BaseMiddleware):
    SKIP_COMMANDS = {"start", "help"}

    async def __call__(self, handler, event: TelegramObject, data: dict):
        session: AsyncSession = data["session"]
        db_user: User | None = data.get("db_user")

        if db_user is None or db_user.role.value in ("owner", "admin"):
            return await handler(event, data)

        text = None
        if isinstance(event, Update) and event.message:
            text = event.message.text
        if text and text.startswith("/") and text.split()[0][1:] in self.SKIP_COMMANDS:
            return await handler(event, data)

        result = await session.execute(
            select(MandatoryChannel).where(MandatoryChannel.is_active == True)
        )
        channels = list(result.scalars().all())

        missing = []
        for ch in channels:
            try:
                member = await bot.get_chat_member(ch.channel_id, db_user.telegram_id)
                if member.status in ("left", "kicked"):
                    missing.append(ch)
            except TelegramBadRequest:
                missing.append(ch)

        if missing:
            kb = InlineKeyboardBuilder()
            for ch in missing:
                kb.button(
                    text=f"📢 {ch.channel_username}",
                    url=ch.invite_link
                    or f"https://t.me/{ch.channel_username.lstrip('@')}",
                )
            kb.button(text="✅ Tekshirish", callback_data="check_subscription")
            kb.adjust(1)

            if isinstance(event, Update) and event.message:
                await event.message.answer(
                    "📢 Botdan foydalanish uchun quyidagi kanallarga obuna bo'ling:",
                    reply_markup=kb.as_markup(),
                )
            elif isinstance(event, Update) and event.callback_query:
                await event.callback_query.answer(
                    "Avval kanallarga obuna bo'ling!", show_alert=True
                )
            return

        return await handler(event, data)


# ═══════════════════════════════════════════════════════════════
# 7. KEYBOARDS
# ═══════════════════════════════════════════════════════════════
def user_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🎬 Anime"), KeyboardButton(text="💎 VIP")],
            [KeyboardButton(text="👤 Profil")],
        ],
        resize_keyboard=True,
    )


def admin_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="⚙️ Admin panel")],
            [KeyboardButton(text="🏠 Asosiy menyu")],
        ],
        resize_keyboard=True,
    )


def cancel_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="❌ Bekor qilish")]], resize_keyboard=True
    )


def admin_panel_kb() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="🎬 Anime qo'shish", callback_data="a_add_anime")
    kb.button(text="📢 Kanallar", callback_data="a_channels")
    kb.button(text="📣 Broadcast", callback_data="a_broadcast")
    kb.button(text="📊 Statistika", callback_data="a_stats")
    kb.button(text="💎 Tarif qo'shish", callback_data="a_add_tariff")
    kb.adjust(2)
    return kb.as_markup()


def owner_panel_kb() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="👤 Admin qo'shish", callback_data="o_add_admin")
    kb.button(text="⬅️ Orqaga", callback_data="o_back")
    kb.adjust(1)
    return kb.as_markup()


# ═══════════════════════════════════════════════════════════════
# 8. ROUTER
# ═══════════════════════════════════════════════════════════════
router = Router()


# ─── USER HANDLERS ────────────────────────────────────────────
@router.message(CommandStart())
async def cmd_start(message: Message, db_user: User, state: FSMContext):
    await state.clear()
    is_admin = db_user.role in (UserRole.OWNER, UserRole.ADMIN)
    menu = admin_menu() if is_admin else user_menu()

    await message.answer(
        f"👋 Salom, <b>{message.from_user.full_name}</b>!\n\n"
        f"🎌 Anime botga xush kelibsiz!\n"
        f"Rolingiz: <b>{db_user.role.value}</b>",
        reply_markup=menu,
    )


@router.message(F.text == "🏠 Asosiy menyu")
async def back_to_main(message: Message, db_user: User):
    is_admin = db_user.role in (UserRole.OWNER, UserRole.ADMIN)
    menu = admin_menu() if is_admin else user_menu()
    await message.answer("🏠 Asosiy menyu", reply_markup=menu)


@router.message(F.text == "❌ Bekor qilish")
async def cancel(message: Message, state: FSMContext, db_user: User):
    await state.clear()
    is_admin = db_user.role in (UserRole.OWNER, UserRole.ADMIN)
    menu = admin_menu() if is_admin else user_menu()
    await message.answer("❌ Bekor qilindi", reply_markup=menu)


@router.message(F.text == "👤 Profil")
async def profile(message: Message, db_user: User, session: AsyncSession):
    result = await session.execute(
        select(VipSubscription).where(
            VipSubscription.user_id == db_user.id,
            VipSubscription.is_active == True,
            VipSubscription.end_date > datetime.utcnow(),
        )
    )
    sub = result.scalar_one_or_none()

    text = (
        f"👤 <b>Profil</b>\n\n"
        f"🆔 ID: <code>{db_user.telegram_id}</code>\n"
        f"📝 Ism: {db_user.full_name}\n"
        f"🎭 Rol: <b>{db_user.role.value}</b>\n"
    )
    if sub:
        text += f"💎 VIP: <b>{sub.end_date.strftime('%d.%m.%Y')}</b> gacha"
    else:
        text += "💎 VIP: <b>Yo'q</b>"

    await message.answer(text)


@router.message(F.text == "💎 VIP")
async def vip_shop(message: Message, session: AsyncSession):
    result = await session.execute(
        select(VipTariff).where(VipTariff.is_active == True)
    )
    tariffs = list(result.scalars().all())

    if not tariffs:
        await message.answer("💎 Hozircha tariflar mavjud emas")
        return

    kb = InlineKeyboardBuilder()
    for t in tariffs:
        kb.button(
            text=f"💎 {t.name} — {t.price:,} so'm / {t.duration_days} kun",
            callback_data=f"buy_{t.id}",
        )
    kb.adjust(1)
    await message.answer("💎 <b>VIP tariflar</b>", reply_markup=kb.as_markup())


@router.callback_query(F.data.startswith("buy_"))
async def buy_vip(
    call: CallbackQuery, session: AsyncSession, db_user: User
):
    tariff_id = int(call.data.split("_")[1])
    tariff = await session.get(VipTariff, tariff_id)
    if not tariff:
        await call.answer("Tarif topilmadi", show_alert=True)
        return

    sub = VipSubscription(
        user_id=db_user.id,
        tariff_id=tariff.id,
        end_date=datetime.utcnow() + timedelta(days=tariff.duration_days),
    )
    session.add(sub)
    await session.flush()

    await call.message.edit_text(
        f"✅ VIP faollashtirildi!\n"
        f"📅 {sub.end_date.strftime('%d.%m.%Y')} gacha"
    )
    await call.answer("✅ VIP faollashtirildi")


@router.callback_query(F.data == "check_subscription")
async def check_sub(call: CallbackQuery):
    await call.answer("✅ Tekshirildi! Qayta yuboring", show_alert=True)


@router.message(F.text == "🎬 Anime")
async def anime_list(message: Message, session: AsyncSession):
    result = await session.execute(
        select(Anime).order_by(Anime.created_at.desc()).limit(20)
    )
    animes = list(result.scalars().all())

    if not animes:
        await message.answer("🎬 Anime ro'yxati bo'sh")
        return

    kb = InlineKeyboardBuilder()
    for a in animes:
        vip = "💎" if a.is_vip_only else "🎬"
        kb.button(text=f"{vip} {a.title}", callback_data=f"view_{a.id}")
    kb.adjust(1)
    await message.answer("🎬 <b>Anime katalogi</b>", reply_markup=kb.as_markup())


@router.callback_query(F.data.startswith("view_"))
async def view_anime(call: CallbackQuery, session: AsyncSession, db_user: User):
    anime_id = int(call.data.split("_")[1])
    result = await session.execute(
        select(Anime).options(selectinload(Anime.episodes)).where(Anime.id == anime_id)
    )
    anime = result.scalar_one_or_none()
    if not anime:
        await call.answer("Topilmadi", show_alert=True)
        return

    if anime.is_vip_only and db_user.role == UserRole.USER:
        result2 = await session.execute(
            select(VipSubscription).where(
                VipSubscription.user_id == db_user.id,
                VipSubscription.is_active == True,
                VipSubscription.end_date > datetime.utcnow(),
            )
        )
        if not result2.scalar_one_or_none():
            await call.answer(
                "💎 Bu anime faqat VIP uchun! VIP sotib oling.", show_alert=True
            )
            return

    text = f"🎬 <b>{anime.title}</b>\n"
    if anime.year:
        text += f"📅 {anime.year}\n"
    if anime.genre:
        text += f"🏷 {anime.genre}\n"
    if anime.description:
        text += f"\n{anime.description}\n"
    text += f"\n📺 Qismlar: <b>{len(anime.episodes)}</b>"

    await call.message.edit_text(text)
    await call.answer()


# ─── ADMIN PANEL ──────────────────────────────────────────────
@router.message(F.text == "⚙️ Admin panel", IsAdmin())
async def admin_panel(message: Message, db_user: User):
    kb = admin_panel_kb()
    if db_user.role == UserRole.OWNER:
        kb = InlineKeyboardBuilder.from_markup(kb)
        kb.row(
            InlineKeyboardButton(
                text="👑 Owner panel", callback_data="o_panel"
            )
        )
        kb = kb.as_markup()
    await message.answer("⚙️ <b>Admin panel</b>", reply_markup=kb)


@router.callback_query(F.data == "o_panel", IsOwner())
async def owner_panel(call: CallbackQuery):
    await call.message.edit_text(
        "👑 <b>Owner panel</b>", reply_markup=owner_panel_kb()
    )
    await call.answer()


@router.callback_query(F.data == "o_back", IsOwner())
async def owner_back(call: CallbackQuery):
    await call.message.edit_text(
        "⚙️ <b>Admin panel</b>", reply_markup=admin_panel_kb()
    )
    await call.answer()


# ─── ADMIN QO'SHISH ───────────────────────────────────────────
@router.callback_query(F.data == "o_add_admin", IsOwner())
async def add_admin_start(call: CallbackQuery, state: FSMContext):
    await state.set_state(AdminStates.waiting_admin_id)
    await call.message.answer(
        "👤 Yangi adminning Telegram ID sini yuboring:\n\n"
        "(Foydalanuvchi botga /start bosgan bo'lishi shart)",
        reply_markup=cancel_kb(),
    )
    await call.answer()


@router.message(AdminStates.waiting_admin_id, IsOwner())
async def add_admin_save(
    message: Message, state: FSMContext, session: AsyncSession, db_user: User
):
    try:
        tg_id = int(message.text.strip())
    except ValueError:
        await message.answer("❌ Noto'g'ri ID. Qayta yuboring:")
        return

    result = await session.execute(select(User).where(User.telegram_id == tg_id))
    user = result.scalar_one_or_none()
    if not user:
        await message.answer("❌ Foydalanuvchi topilmadi. /start bosganini tekshiring.")
        return

    if user.role == UserRole.OWNER:
        await message.answer("❌ Bu owner, o'zgartirib bo'lmaydi.")
        return

    user.role = UserRole.ADMIN
    await session.flush()
    await state.clear()

    await message.answer(
        f"✅ <b>{user.full_name}</b> admin qilib tayinlandi!",
        reply_markup=admin_menu(),
    )
    try:
        await message.bot.send_message(
            tg_id, "🎉 Siz admin etib tayinlandingiz!"
        )
    except Exception:
        pass


# ─── ANIME QO'SHISH ───────────────────────────────────────────
@router.callback_query(F.data == "a_add_anime", IsAdmin())
async def anime_add_start(call: CallbackQuery, state: FSMContext):
    await state.set_state(AnimeStates.title)
    await call.message.answer(
        "🎬 Anime nomini yuboring:", reply_markup=cancel_kb()
    )
    await call.answer()


@router.message(AnimeStates.title, IsAdmin())
async def anime_title(message: Message, state: FSMContext):
    await state.update_data(title=message.text)
    await state.set_state(AnimeStates.description)
    await message.answer("📝 Tavsif yuboring (yoki /skip):")


@router.message(Command("skip"), AnimeStates.description)
async def anime_skip_desc(message: Message, state: FSMContext):
    await state.update_data(description=None)
    await state.set_state(AnimeStates.genre)
    await message.answer("🏷 Janrni yuboring (yoki /skip):")


@router.message(AnimeStates.description, IsAdmin())
async def anime_desc(message: Message, state: FSMContext):
    await state.update_data(description=message.text)
    await state.set_state(AnimeStates.genre)
    await message.answer("🏷 Janrni yuboring (yoki /skip):")


@router.message(Command("skip"), AnimeStates.genre)
async def anime_skip_genre(message: Message, state: FSMContext):
    await state.update_data(genre=None)
    await state.set_state(AnimeStates.year)
    await message.answer("📅 Yilni yuboring (yoki /skip):")


@router.message(AnimeStates.genre, IsAdmin())
async def anime_genre(message: Message, state: FSMContext):
    await state.update_data(genre=message.text)
    await state.set_state(AnimeStates.year)
    await message.answer("📅 Yilni yuboring (yoki /skip):")


@router.message(Command("skip"), AnimeStates.year)
async def anime_skip_year(message: Message, state: FSMContext):
    await state.update_data(year=None)
    await state.set_state(AnimeStates.is_vip)
    await ask_vip(message)


async def ask_vip(message: Message):
    kb = InlineKeyboardBuilder()
    kb.button(text="🎬 Oddiy", callback_data="vip_0")
    kb.button(text="💎 VIP", callback_data="vip_1")
    kb.adjust(2)
    await message.answer("💎 VIP uchunmi?", reply_markup=kb.as_markup())


@router.message(AnimeStates.year, IsAdmin())
async def anime_year(message: Message, state: FSMContext):
    try:
        year = int(message.text)
    except ValueError:
        await message.answer("❌ Yil raqam bo'lishi kerak:")
        return
    await state.update_data(year=year)
    await state.set_state(AnimeStates.is_vip)
    await ask_vip(message)


@router.callback_query(F.data.startswith("vip_"), AnimeStates.is_vip, IsAdmin())
async def anime_vip_choice(
    call: CallbackQuery, state: FSMContext, session: AsyncSession, db_user: User
):
    is_vip = call.data == "vip_1"
    data = await state.get_data()

    anime = Anime(
        title=data["title"],
        description=data.get("description"),
        genre=data.get("genre"),
        year=data.get("year"),
        is_vip_only=is_vip,
        created_by=db_user.telegram_id,
    )
    session.add(anime)
    await session.flush()

    await state.update_data(anime_id=anime.id)
    await state.set_state(AnimeStates.episode_number)

    await call.message.edit_text(
        f"✅ Anime yaratildi: <b>{anime.title}</b>\n\n"
        f"📺 Endi birinchi qism raqamini yuboring (masalan: 1):"
    )
    await call.answer()


@router.message(AnimeStates.episode_number, IsAdmin())
async def episode_number(message: Message, state: FSMContext):
    try:
        num = int(message.text)
    except ValueError:
        await message.answer("❌ Raqam yuboring:")
        return
    await state.update_data(episode_number=num)
    await state.set_state(AnimeStates.episode_file)
    await message.answer("🎥 Endi video faylni yuboring:")


@router.message(AnimeStates.episode_file, F.video, IsAdmin())
async def episode_file(
    message: Message, state: FSMContext, session: AsyncSession
):
    data = await state.get_data()
    ep = Episode(
        anime_id=data["anime_id"],
        number=data["episode_number"],
        file_id=message.video.file_id,
    )
    session.add(ep)
    await session.flush()
    await state.clear()

    await message.answer(
        f"✅ <b>{data['episode_number']}-qism</b> qo'shildi!\n\n"
        f"Yana qism qo'shish uchun anime menyusidan foydalaning.",
        reply_markup=admin_menu(),
    )


# ─── KANAL QO'SHISH ───────────────────────────────────────────
@router.callback_query(F.data == "a_channels", IsAdmin())
async def channels_menu(call: CallbackQuery, session: AsyncSession):
    result = await session.execute(select(MandatoryChannel))
    channels = list(result.scalars().all())

    text = "📢 <b>Majburiy kanallar</b>\n\n"
    if channels:
        for ch in channels:
            text += f"• {ch.channel_username} ({'✅' if ch.is_active else '❌'})\n"
    else:
        text += "Hozircha yo'q"

    kb = InlineKeyboardBuilder()
    kb.button(text="➕ Kanal qo'shish", callback_data="a_add_channel")
    kb.adjust(1)
    await call.message.edit_text(text, reply_markup=kb.as_markup())
    await call.answer()


@router.callback_query(F.data == "a_add_channel", IsAdmin())
async def add_channel_start(call: CallbackQuery, state: FSMContext):
    await state.set_state(ChannelStates.waiting_channel)
    await call.message.answer(
        "📢 Kanal ma'lumotlarini yuboring:\n\n"
        "Format: <code>@username -1001234567890</code>\n"
        "yoki faqat: <code>@username</code>",
        reply_markup=cancel_kb(),
    )
    await call.answer()


@router.message(ChannelStates.waiting_channel, IsAdmin())
async def add_channel_save(message: Message, state: FSMContext, session: AsyncSession):
    parts = message.text.split()
    if len(parts) < 1:
        await message.answer("❌ Format noto'g'ri")
        return

    username = parts[0]
    try:
        chat = await message.bot.get_chat(username)
        channel_id = chat.id
    except Exception as e:
        await message.answer(f"❌ Kanalga ulanib bo'lmadi: {e}")
        return

    ch = MandatoryChannel(
        channel_id=channel_id,
        channel_username=username if username.startswith("@") else f"@{username}",
    )
    session.add(ch)
    await session.flush()
    await state.clear()

    await message.answer(
        f"✅ Kanal qo'shildi: {ch.channel_username}", reply_markup=admin_menu()
    )


# ─── BROADCAST ────────────────────────────────────────────────
@router.callback_query(F.data == "a_broadcast", IsAdmin())
async def broadcast_start(call: CallbackQuery, state: FSMContext):
    await state.set_state(BroadcastStates.waiting_message)
    await call.message.answer(
        "📣 Tarqatiladigan xabarni yuboring (matn/rasm/video):",
        reply_markup=cancel_kb(),
    )
    await call.answer()


@router.message(BroadcastStates.waiting_message, IsAdmin())
async def broadcast_send(message: Message, state: FSMContext, session: AsyncSession):
    await state.clear()
    status = await message.answer("⏳ Tarqatish boshlandi...")

    result = await session.execute(select(User).where(User.is_banned == False))
    users = list(result.scalars().all())

    sent = blocked = failed = 0
    for u in users:
        try:
            await message.copy_to(u.telegram_id)
            sent += 1
        except TelegramForbiddenError:
            blocked += 1
        except TelegramRetryAfter as e:
            await asyncio.sleep(e.retry_after)
            try:
                await message.copy_to(u.telegram_id)
                sent += 1
            except Exception:
                failed += 1
        except Exception:
            failed += 1
        await asyncio.sleep(0.05)

    await status.edit_text(
        f"✅ <b>Tarqatish tugadi</b>\n\n"
        f"📤 Yuborildi: {sent}\n"
        f"🚫 Bloklagan: {blocked}\n"
        f"❌ Xatolik: {failed}"
    )


# ─── STATISTIKA ───────────────────────────────────────────────
@router.callback_query(F.data == "a_stats", IsAdmin())
async def stats(call: CallbackQuery, session: AsyncSession):
    from sqlalchemy import func

    users_count = (
        await session.execute(select(func.count(User.id)))
    ).scalar()
    admins_count = (
        await session.execute(
            select(func.count(User.id)).where(
                User.role.in_([UserRole.ADMIN, UserRole.OWNER])
            )
        )
    ).scalar()
    animes_count = (
        await session.execute(select(func.count(Anime.id)))
    ).scalar()
    vips_count = (
        await session.execute(
            select(func.count(VipSubscription.id)).where(
                VipSubscription.is_active == True,
                VipSubscription.end_date > datetime.utcnow(),
            )
        )
    ).scalar()

    await call.message.edit_text(
        f"📊 <b>Statistika</b>\n\n"
        f"👥 Foydalanuvchilar: <b>{users_count}</b>\n"
        f"🎭 Adminlar: <b>{admins_count}</b>\n"
        f"💎 VIP: <b>{vips_count}</b>\n"
        f"🎬 Animelar: <b>{animes_count}</b>"
    )
    await call.answer()


# ─── TARIF QO'SHISH ───────────────────────────────────────────
@router.callback_query(F.data == "a_add_tariff", IsAdmin())
async def tariff_start(call: CallbackQuery, state: FSMContext):
    await state.set_state(TariffStates.name)
    await call.message.answer(
        "💎 Tarif nomini yuboring (masalan: 1 oylik):", reply_markup=cancel_kb()
    )
    await call.answer()


@router.message(TariffStates.name, IsAdmin())
async def tariff_name(message: Message, state: FSMContext):
    await state.update_data(name=message.text)
    await state.set_state(TariffStates.price)
    await message.answer("💰 Narxini so'mda yuboring:")


@router.message(TariffStates.price, IsAdmin())
async def tariff_price(message: Message, state: FSMContext):
    try:
        price = int(message.text)
    except ValueError:
        await message.answer("❌ Raqam yuboring:")
        return
    await state.update_data(price=price)
    await state.set_state(TariffStates.duration)
    await message.answer("📅 Necha kunlik? (masalan: 30)")


@router.message(TariffStates.duration, IsAdmin())
async def tariff_duration(
    message: Message, state: FSMContext, session: AsyncSession
):
    try:
        days = int(message.text)
    except ValueError:
        await message.answer("❌ Raqam yuboring:")
        return
    data = await state.get_data()
    tariff = VipTariff(name=data["name"], price=data["price"], duration_days=days)
    session.add(tariff)
    await session.flush()
    await state.clear()
    await message.answer(
        f"✅ Tarif qo'shildi: {tariff.name} — {tariff.price:,} so'm / {days} kun",
        reply_markup=admin_menu(),
    )


# ═══════════════════════════════════════════════════════════════
# 9. BOT & DISPATCHER
# ═══════════════════════════════════════════════════════════════
bot = Bot(
    token=settings.BOT_TOKEN,
    default=DefaultBotProperties(parse_mode="HTML"),
)
dp = Dispatcher(storage=MemoryStorage())

dp.update.outer_middleware(ThrottlingMiddleware(rate_limit=0.3))
dp.update.outer_middleware(DBSessionMiddleware())
dp.update.outer_middleware(UserMiddleware())
dp.update.outer_middleware(SubscriptionMiddleware())

dp.include_router(router)


# ═══════════════════════════════════════════════════════════════
# 10. MAIN
# ═══════════════════════════════════════════════════════════════
async def main():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("✅ Database tayyor")

    logger.info("🚀 Bot ishga tushmoqda...")
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.warning("Bot to'xtatildi")
