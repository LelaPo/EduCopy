"""
Inline-клавиатуры бота.
"""
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder


def get_main_keyboard() -> InlineKeyboardMarkup:
    """Главная клавиатура после /start."""
    builder = InlineKeyboardBuilder()
    
    builder.row(
        InlineKeyboardButton(text="📚 ДЗ на сегодня", callback_data="hw_today"),
        InlineKeyboardButton(text="📖 ДЗ на завтра", callback_data="hw_tomorrow"),
    )
    builder.row(
        InlineKeyboardButton(text="📅 ДЗ на дату...", callback_data="hw_custom_date"),
        InlineKeyboardButton(text="🗓 ДЗ на неделю", callback_data="hw_week"),
    )
    builder.row(
        InlineKeyboardButton(text="❓ FAQ", callback_data="faq"),
    )
    
    return builder.as_markup()


def get_back_keyboard() -> InlineKeyboardMarkup:
    """Кнопка возврата в меню."""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="◀️ Назад в меню", callback_data="back_to_menu"),
    )
    return builder.as_markup()


def get_faq_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура для FAQ."""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="◀️ Назад в меню", callback_data="back_to_menu"),
    )
    return builder.as_markup()


# ============= Админ-клавиатуры =============

def get_admin_keyboard() -> InlineKeyboardMarkup:
    """Админ-меню."""
    builder = InlineKeyboardBuilder()
    
    builder.row(
        InlineKeyboardButton(text="➕ Создать ключ", callback_data="admin_create_key"),
    )
    builder.row(
        InlineKeyboardButton(text="🔑 Активные ключи", callback_data="admin_unused_keys"),
        InlineKeyboardButton(text="👥 Использованные", callback_data="admin_used_keys"),
    )
    builder.row(
        InlineKeyboardButton(text="◀️ В главное меню", callback_data="back_to_menu"),
    )
    
    return builder.as_markup()


def get_back_to_admin_keyboard() -> InlineKeyboardMarkup:
    """Назад в админ-меню."""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="◀️ Назад", callback_data="admin_menu"),
    )
    return builder.as_markup()


def get_keys_list_keyboard(keys: list, unused: bool = True) -> InlineKeyboardMarkup:
    """Клавиатура со списком ключей для удаления."""
    builder = InlineKeyboardBuilder()
    
    for k in keys[:8]:  # Максимум 8 кнопок
        short_key = k.key[:8] + "..."
        builder.row(
            InlineKeyboardButton(
                text=f"🗑 {short_key}", 
                callback_data=f"delete_key:{k.key}"
            ),
        )
    
    builder.row(
        InlineKeyboardButton(text="◀️ Назад", callback_data="admin_menu"),
    )
    
    return builder.as_markup()
