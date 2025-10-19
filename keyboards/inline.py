# keyboards/inline.py

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

def get_edit_profile_keyboard():
    """Генерує інлайн-клавіатуру для редагування профілю."""
    buttons = [
        [InlineKeyboardButton(text="✏️ Змінити ім'я", callback_data="edit_name")],
        [InlineKeyboardButton(text="✏️ Змінити вік", callback_data="edit_age")],
        [InlineKeyboardButton(text="✏️ Змінити біо", callback_data="edit_bio")],
        [InlineKeyboardButton(text="🖼️ Змінити фото", callback_data="edit_photo")],
    ]
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    return keyboard