"""
Обработчики админ-меню (управление ключами).
"""
import logging
from datetime import datetime

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command

from app.services.storage import Storage
from app.keyboards.inline import (
    get_admin_keyboard,
    get_keys_list_keyboard,
    get_back_to_admin_keyboard,
)

logger = logging.getLogger(__name__)

router = Router()

_storage: Storage | None = None


def setup_admin_handlers(storage: Storage):
    """Инициализировать обработчики."""
    global _storage
    _storage = storage


def is_admin(user_id: int) -> bool:
    """Проверить права админа."""
    if _storage is None:
        return False
    return _storage.is_admin(user_id)


# ============= Админ-меню =============

@router.message(Command("admin"))
async def cmd_admin(message: Message):
    """Команда /admin — открыть админ-меню."""
    if not is_admin(message.from_user.id):
        return

    unused = len(_storage.get_unused_keys())
    used = len(_storage.get_used_keys())
    users = _storage.get_user_count()

    await message.answer(
        "🔐 <b>Админ-панель</b>\n\n"
        f"📊 Статистика:\n"
        f"• Активных ключей: {unused}\n"
        f"• Использованных ключей: {used}\n"
        f"• Пользователей: {users}\n",
        reply_markup=get_admin_keyboard(),
        parse_mode="HTML",
    )


@router.callback_query(F.data == "admin_menu")
async def admin_menu(callback: CallbackQuery):
    """Вернуться в админ-меню."""
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Нет доступа", show_alert=True)
        return

    unused = len(_storage.get_unused_keys())
    used = len(_storage.get_used_keys())
    users = _storage.get_user_count()

    await callback.message.edit_text(
        "🔐 <b>Админ-панель</b>\n\n"
        f"📊 Статистика:\n"
        f"• Активных ключей: {unused}\n"
        f"• Использованных ключей: {used}\n"
        f"• Пользователей: {users}\n",
        reply_markup=get_admin_keyboard(),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data == "admin_create_key")
async def admin_create_key(callback: CallbackQuery):
    """Создать новый ключ."""
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Нет доступа", show_alert=True)
        return

    key = _storage.generate_key()

    try:
        await callback.message.edit_text(
            "✅ <b>Ключ создан!</b>\n\n"
            f"<code>{key}</code>\n\n"
            "👆 Нажми чтобы скопировать.",
            reply_markup=get_back_to_admin_keyboard(),
            parse_mode="HTML",
        )
    except Exception:
        # Игнорируем ошибку если сообщение уже отредактировано
        pass
    await callback.answer("Ключ создан!")


@router.callback_query(F.data == "admin_unused_keys")
async def admin_unused_keys(callback: CallbackQuery):
    """Показать неиспользованные ключи."""
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Нет доступа", show_alert=True)
        return

    keys = _storage.get_unused_keys()

    if not keys:
        try:
            await callback.message.edit_text(
                "📭 <b>Нет активных ключей</b>\n\n"
                "Создай новый ключ чтобы пригласить друга.",
                reply_markup=get_back_to_admin_keyboard(),
                parse_mode="HTML",
            )
        except Exception:
            pass
    else:
        text = "🔑 <b>Активные ключи:</b>\n\n"
        for k in keys[:20]:
            created = format_date(k.created_at)
            text += f"<code>{k.key}</code>\n   📅 Создан: {created}\n\n"

        try:
            await callback.message.edit_text(
                text,
                reply_markup=get_keys_list_keyboard(keys[:10], unused=True),
                parse_mode="HTML",
            )
        except Exception:
            pass
    await callback.answer()


@router.callback_query(F.data == "admin_used_keys")
async def admin_used_keys(callback: CallbackQuery):
    """Показать использованные ключи."""
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Нет доступа", show_alert=True)
        return

    keys = _storage.get_used_keys()

    if not keys:
        try:
            await callback.message.edit_text(
                "📭 <b>Нет использованных ключей</b>",
                reply_markup=get_back_to_admin_keyboard(),
                parse_mode="HTML",
            )
        except Exception:
            pass
    else:
        text = "👥 <b>Использованные ключи:</b>\n\n"
        for k in keys[:20]:
            # Берём информацию из связанного пользователя
            username = k.user.username or f"ID:{k.user.user_id}" if k.user else "—"
            activated = format_date(k.user.activated_at) if k.user else "—"
            text += f"<code>{k.key}</code>\n   👤 {username}\n   📅 Активирован: {activated}\n\n"

        try:
            await callback.message.edit_text(
                text,
                reply_markup=get_keys_list_keyboard(keys[:10], unused=False),
                parse_mode="HTML",
            )
        except Exception:
            pass
    await callback.answer()


@router.callback_query(F.data.startswith("delete_key:"))
async def admin_delete_key(callback: CallbackQuery):
    """Удалить ключ."""
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Нет доступа", show_alert=True)
        return

    key = callback.data.split(":", 1)[1]

    if _storage.delete_key(key):
        await callback.answer("🗑 Ключ удалён!", show_alert=True)
    else:
        await callback.answer("❌ Ключ не найден", show_alert=True)

    await admin_menu(callback)


def format_date(dt: datetime | None) -> str:
    """Форматировать дату."""
    if not dt:
        return "—"
    try:
        return dt.strftime("%d.%m.%Y %H:%M")
    except:
        return str(dt)[:16]
