"""
Обработчики команд бота.
"""
import logging
import re
from datetime import date, datetime, timedelta
import zoneinfo

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from app.config import Config
from app.services.authedu_client import AutheduClient, AutheduAPIError
from app.services.storage import Storage
from app.keyboards.inline import get_main_keyboard, get_back_keyboard, get_faq_keyboard
from app.utils.formatting import format_homework_list

logger = logging.getLogger(__name__)

router = Router()


class DateInputState(StatesGroup):
    """Состояния для ввода даты."""
    waiting_for_date = State()


class KeyInputState(StatesGroup):
    """Состояния для ввода ключа."""
    waiting_for_key = State()


_config: Config | None = None
_client: AutheduClient | None = None
_storage: Storage | None = None


def setup_handlers(config: Config, client: AutheduClient, storage: Storage):
    """Инициализировать обработчики с конфигурацией."""
    global _config, _client, _storage
    _config = config
    _client = client
    _storage = storage


def get_today() -> date:
    """Получить сегодняшнюю дату по Москве."""
    tz = zoneinfo.ZoneInfo(_config.timezone if _config else "Europe/Moscow")
    return datetime.now(tz).date()


# ============= /start и авторизация =============

@router.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext):
    """Обработчик команды /start."""
    await state.clear()
    user_id = message.from_user.id

    # Проверяем авторизацию
    if _storage.is_authorized(user_id):
        if _storage.is_admin(user_id):
            await message.answer(
                "👋 <b>Привет, создатель!</b>\n\n"
                "Я покажу домашние задания из дневника.\n\n"
                "💡 <i>Подсказка: /admin — управление ключами</i>",
                reply_markup=get_main_keyboard(),
                parse_mode="HTML",
            )
        else:
            await message.answer(
                "👋 <b>Добро пожаловать в бета-тест!</b>\n\n"
                "Вы были приглашены для тестирования бота.\n\n"
                "Выберите нужный период:",
                reply_markup=get_main_keyboard(),
                parse_mode="HTML",
            )
    else:
        await state.set_state(KeyInputState.waiting_for_key)
        await message.answer(
            "🔐 <b>Доступ ограничен</b>\n\n"
            "Этот бот работает по приглашениям.\n\n"
            "Если у тебя есть ключ доступа — отправь его сейчас.\n"
            "Формат: <code>XXXX-XXXX-XXXX</code>",
            parse_mode="HTML",
        )


@router.message(KeyInputState.waiting_for_key)
async def process_key_input(message: Message, state: FSMContext):
    """Обработка введённого ключа."""
    key = message.text.strip().upper()
    user_id = message.from_user.id
    username = message.from_user.username
    if username:
        username = f"@{username}"
    else:
        username = message.from_user.full_name

    if _storage.activate_key(key, user_id, username):
        await state.clear()
        await message.answer(
            "✅ <b>Ключ активирован!</b>\n\n"
            "Добро пожаловать в бета-тест! 🎉\n"
            "Теперь тебе доступны все функции бота.\n\n"
            "Выбери период для просмотра ДЗ:",
            reply_markup=get_main_keyboard(),
            parse_mode="HTML",
        )
        logger.info(f"Пользователь {user_id} ({username}) активировал ключ {key}")
    else:
        await message.answer(
            "❌ <b>Неверный или уже использованный ключ</b>\n\n"
            "Проверь правильность ключа и попробуй ещё раз.\n"
            "Формат: <code>XXXX-XXXX-XXXX</code>",
            parse_mode="HTML",
        )


# ============= Проверка доступа =============

async def check_access(event: Message | CallbackQuery, state: FSMContext = None) -> bool:
    """Проверить доступ пользователя."""
    user_id = event.from_user.id if event.from_user else 0

    if not _storage.is_authorized(user_id):
        text = (
            "🔐 <b>Доступ ограничен</b>\n\n"
            "Отправь ключ доступа чтобы активировать бота."
        )
        if isinstance(event, Message):
            if state:
                await state.set_state(KeyInputState.waiting_for_key)
            await event.answer(text, parse_mode="HTML")
        else:
            await event.answer("⛔ Нет доступа. Введи /start", show_alert=True)
        return False
    return True


# ============= Главное меню =============

@router.callback_query(F.data == "back_to_menu")
async def back_to_menu(callback: CallbackQuery, state: FSMContext):
    """Вернуться в главное меню."""
    if not await check_access(callback):
        return

    await state.clear()

    await callback.message.edit_text(
        "📚 <b>Главное меню</b>\n\n"
        "Выбери период:",
        reply_markup=get_main_keyboard(),
        parse_mode="HTML",
    )
    await callback.answer()


# ============= FAQ =============

@router.callback_query(F.data == "faq")
async def show_faq(callback: CallbackQuery):
    """Показать FAQ."""
    if not await check_access(callback):
        return

    faq_text = """❓ <b>Часто задаваемые вопросы</b>

<b>Что это за бот?</b>
Бот показывает домашние задания из электронного дневника (authedu.mosreg.ru).

<b>Как пользоваться?</b>
• Нажми кнопку с нужным периодом (сегодня, завтра, неделя)
• Или напиши дату/период в чат:
  - <code>25.12.2025</code> — ДЗ на конкретную дату
  - <code>25.02-28.02</code> — ДЗ с 25 по 28 февраля
  - <code>25-28</code> — ДЗ с 25 по 28 число текущего месяца
  - <code>25,26,27,28</code> — ДЗ за перечисленные дни

<b>Почему бот закрытый?</b>
Бот находится в стадии бета-теста. Доступ выдаётся по приглашениям.

<b>Нашёл баг / есть идея?</b>
Напиши создателю бота."""

    await callback.message.edit_text(
        faq_text,
        reply_markup=get_faq_keyboard(),
        parse_mode="HTML",
    )
    await callback.answer()


# ============= Обработчики ДЗ =============

@router.callback_query(F.data == "hw_today")
async def hw_today(callback: CallbackQuery):
    """ДЗ на сегодня."""
    if not await check_access(callback):
        return

    await callback.answer("Загружаю...")
    today = get_today()
    await send_homework(callback.message, today, today)


@router.callback_query(F.data == "hw_tomorrow")
async def hw_tomorrow(callback: CallbackQuery):
    """ДЗ на завтра."""
    if not await check_access(callback):
        return

    await callback.answer("Загружаю...")
    tomorrow = get_today() + timedelta(days=1)
    await send_homework(callback.message, tomorrow, tomorrow)


@router.callback_query(F.data == "hw_week")
async def hw_week(callback: CallbackQuery):
    """ДЗ на неделю."""
    if not await check_access(callback):
        return

    await callback.answer("Загружаю...")
    today = get_today()
    week_later = today + timedelta(days=7)
    await send_homework(callback.message, today, week_later, is_range=True)


@router.callback_query(F.data == "hw_custom_date")
async def hw_custom_date(callback: CallbackQuery, state: FSMContext):
    """Запросить ввод даты."""
    if not await check_access(callback):
        return

    await state.set_state(DateInputState.waiting_for_date)

    await callback.message.edit_text(
        "📅 <b>Введи дату</b>\n\n"
        "Формат: <code>ДД.ММ.ГГГГ</code> или <code>ГГГГ-ММ-ДД</code>\n\n"
        "Примеры:\n"
        "• <code>25.12.2025</code>\n"
        "• <code>2025-12-25</code>",
        reply_markup=get_back_keyboard(),
        parse_mode="HTML",
    )
    await callback.answer()


@router.message(DateInputState.waiting_for_date)
async def process_custom_date(message: Message, state: FSMContext):
    """Обработать введённую дату."""
    if not await check_access(message, state):
        return

    text = message.text.strip()
    target_date = parse_date(text)

    if target_date is None:
        await message.answer(
            "❌ Не удалось распознать дату.\n"
            "Введи в формате <code>ДД.ММ.ГГГГ</code>",
            parse_mode="HTML",
            reply_markup=get_back_keyboard(),
        )
        return

    await state.clear()
    await send_homework(message, target_date, target_date)


# ============= Универсальный обработчик даты =============

@router.message(F.text)
async def handle_any_text(message: Message, state: FSMContext):
    """Обработать любой текст — проверить, не дата или диапазон ли это."""
    current_state = await state.get_state()
    if current_state == KeyInputState.waiting_for_key:
        return

    if not _storage.is_authorized(message.from_user.id):
        return

    text = message.text.strip()
    
    date_range = parse_date_range(text)
    if date_range is not None:
        from_date, to_date = date_range
        await send_homework(message, from_date, to_date, is_range=True)
        return
    
    target_date = parse_date(text)
    if target_date is not None:
        await send_homework(message, target_date, target_date)


# ============= Отправка ДЗ =============

async def send_homework(
    message: Message,
    from_date: date,
    to_date: date,
    is_range: bool = False,
):
    """Получить и отправить домашние задания."""
    if _client is None:
        await message.answer("❌ Клиент API не инициализирован")
        return

    try:
        items = await _client.fetch_homeworks(from_date, to_date)

        if not is_range:
            items = [item for item in items if item.homework_date == from_date]

        text = format_homework_list(items, from_date, is_range=is_range)

        await message.answer(
            text,
            parse_mode="HTML",
            reply_markup=get_main_keyboard(),
            disable_web_page_preview=True,
        )

    except AutheduAPIError as e:
        logger.error(f"Ошибка API: {e}")
        await message.answer(str(e), reply_markup=get_main_keyboard())


# ============= Утилиты =============

def parse_date(text: str) -> date | None:
    """Распарсить дату из строки."""
    text = text.strip()

    for fmt in ("%d.%m.%Y", "%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue

    patterns = [
        r"(\d{1,2})\.(\d{1,2})\.(\d{4})",
        r"(\d{4})-(\d{1,2})-(\d{1,2})",
    ]

    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            groups = match.groups()
            try:
                if len(groups[0]) == 4:
                    return date(int(groups[0]), int(groups[1]), int(groups[2]))
                else:
                    return date(int(groups[2]), int(groups[1]), int(groups[0]))
            except ValueError:
                continue

    return None


def parse_date_range(text: str) -> tuple[date, date] | None:
    """Распарсить диапазон дат из строки."""
    text = text.strip()
    today = get_today()
    
    # ДД.ММ-ДД.ММ
    range_pattern = r"(\d{1,2})\.(\d{1,2})(?:\.(\d{4}))?\s*-\s*(\d{1,2})\.(\d{1,2})(?:\.(\d{4}))?"
    match = re.match(range_pattern, text)
    if match:
        try:
            d1, m1, y1, d2, m2, y2 = match.groups()
            year = int(y1) if y1 else today.year
            year2 = int(y2) if y2 else year
            from_date = date(year, int(m1), int(d1))
            to_date = date(year2, int(m2), int(d2))
            if from_date <= to_date:
                return from_date, to_date
        except ValueError:
            pass
    
    # Перечисление через запятую
    if "," in text and "-" not in text:
        parts = [p.strip() for p in text.split(",")]
        dates = []
        for part in parts:
            date_match = re.match(r"(\d{1,2})\.(\d{1,2})(?:\.(\d{4}))?", part)
            if date_match:
                d, m, y = date_match.groups()
                year = int(y) if y else today.year
                try:
                    dates.append(date(year, int(m), int(d)))
                except ValueError:
                    pass
            else:
                try:
                    day = int(part)
                    dates.append(date(today.year, today.month, day))
                except ValueError:
                    pass
        if len(dates) >= 2:
            return min(dates), max(dates)
        elif len(dates) == 1:
            return dates[0], dates[0]
    
    # ДД-ДД (текущий месяц)
    day_range_pattern = r"^(\d{1,2})\s*-\s*(\d{1,2})$"
    match = re.match(day_range_pattern, text)
    if match:
        try:
            d1, d2 = int(match.group(1)), int(match.group(2))
            from_date = date(today.year, today.month, d1)
            to_date = date(today.year, today.month, d2)
            if from_date <= to_date:
                return from_date, to_date
        except ValueError:
            pass
    
    return None
