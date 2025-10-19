# handlers/profile_form.py

from aiogram import Router, F, Bot
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, CallbackQuery  # 👈 Додали CallbackQuery
import aiosqlite
import logging

form_router = Router()


class ProfileForm(StatesGroup):
    # Стани для створення
    name = State()
    age = State()
    bio = State()
    photo = State()
    # 👈 НОВЕ: Стани для редагування
    editing_name = State()
    editing_age = State()
    editing_bio = State()
    editing_photo = State()


# --- Логіка СТВОРЕННЯ анкети (залишається без змін) ---
# ... (весь ваш код для @form_router.message(Command("create_profile")) і далі до кінця анкети) ...
@form_router.message(Command("create_profile"))
async def start_profile_creation(message: Message, state: FSMContext, db: aiosqlite.Connection, bot: Bot):
    if message.chat.type not in ('group', 'supergroup'):
        await message.reply("Цю команду потрібно використовувати у групі!")
        return
    user_id = message.from_user.id
    username = message.from_user.username or message.from_user.first_name
    async with db.execute("SELECT 1 FROM profiles WHERE user_id = ?", (user_id,)) as cursor:
        exists = await cursor.fetchone()
    if exists:
        await message.reply(
            "У тебе вже є анкета! Щоб створити нову, спочатку видали стару командою /delete_profile або відредагуй її /edit_profile")
        return
    await state.set_state(ProfileForm.name)
    try:
        await bot.send_message(chat_id=user_id, text="Починаємо створювати твою анкету. Як тебе звати?")
        await message.reply(
            f"@{username}, я написав тобі в особисті повідомлення (ОП). Будь ласка, дай відповідь мені там.")
    except Exception as e:
        await message.reply(
            f"@{username}, я не можу написати тобі в ОП. Будь ласка, почни зі мною діалог і спробуй знову.")
        logging.error(f"Не можу написати користувачу {user_id}: {e}", exc_info=True)
        await state.clear()


@form_router.message(ProfileForm.name)
async def process_name(message: Message, state: FSMContext):
    await state.update_data(name=message.text)
    await state.set_state(ProfileForm.age)
    await message.reply("Відмінно! Скільки тобі років?")


@form_router.message(ProfileForm.age)
async def process_age(message: Message, state: FSMContext):
    if not message.text.isdigit():
        await message.reply("Будь ласка, введи вік цифрами.")
        return
    await state.update_data(age=int(message.text))
    await state.set_state(ProfileForm.bio)
    await message.reply("Супер! Тепер розкажи трохи про себе.")


@form_router.message(ProfileForm.bio)
async def process_bio(message: Message, state: FSMContext):
    await state.update_data(bio=message.text)
    await state.set_state(ProfileForm.photo)
    await message.reply("Майже готово! Тепер надішли мені своє фото.")


@form_router.message(ProfileForm.photo, F.photo)
async def process_photo(message: Message, state: FSMContext, db: aiosqlite.Connection):
    photo_file_id = message.photo[-1].file_id
    await state.update_data(photo_id=photo_file_id)
    user_data = await state.get_data()
    user_id = message.from_user.id
    username = message.from_user.username or message.from_user.first_name
    await db.execute(
        "INSERT INTO profiles (user_id, username, name, age, bio, photo_id) VALUES (?, ?, ?, ?, ?, ?)",
        (user_id, username, user_data['name'], user_data['age'], user_data['bio'], user_data['photo_id'])
    )
    await db.commit()
    await state.clear()
    await message.reply("Твоя анкета готова і збережена! 🎉")


@form_router.message(ProfileForm.photo)
async def process_photo_invalid(message: Message):
    await message.reply("Будь ласка, надішли саме фотографію.")


# --- 👈 НОВЕ: Логіка РЕДАГУВАННЯ анкети ---

@form_router.message(ProfileForm.editing_name)
async def process_edit_name(message: Message, state: FSMContext, db: aiosqlite.Connection):
    await db.execute("UPDATE profiles SET name = ? WHERE user_id = ?", (message.text, message.from_user.id))
    await db.commit()
    await state.clear()
    await message.reply("Ім'я успішно оновлено!")


@form_router.message(ProfileForm.editing_age)
async def process_edit_age(message: Message, state: FSMContext, db: aiosqlite.Connection):
    if not message.text.isdigit():
        await message.reply("Будь ласка, введи вік цифрами.")
        return
    await db.execute("UPDATE profiles SET age = ? WHERE user_id = ?", (int(message.text), message.from_user.id))
    await db.commit()
    await state.clear()
    await message.reply("Вік успішно оновлено!")


@form_router.message(ProfileForm.editing_bio)
async def process_edit_bio(message: Message, state: FSMContext, db: aiosqlite.Connection):
    await db.execute("UPDATE profiles SET bio = ? WHERE user_id = ?", (message.text, message.from_user.id))
    await db.commit()
    await state.clear()
    await message.reply("Біографію успішно оновлено!")


@form_router.message(ProfileForm.editing_photo, F.photo)
async def process_edit_photo(message: Message, state: FSMContext, db: aiosqlite.Connection):
    photo_file_id = message.photo[-1].file_id
    await db.execute("UPDATE profiles SET photo_id = ? WHERE user_id = ?", (photo_file_id, message.from_user.id))
    await db.commit()
    await state.clear()
    await message.reply("Фото успішно оновлено!")


@form_router.message(ProfileForm.editing_photo)
async def process_edit_photo_invalid(message: Message):
    await message.reply("Будь ласка, надішли саме фотографію.")