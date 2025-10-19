import asyncio
import logging
import aiosqlite
import os
from dotenv import load_dotenv

from aiogram import Bot, Dispatcher, Router, types
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.strategy import FSMStrategy
from aiogram.types import Message, BotCommand  # 👈 1. ІМПОРТУЄМО BotCommand

# --- Налаштування ---
load_dotenv()
logging.basicConfig(level=logging.INFO)
BOT_TOKEN = os.getenv('BOT_TOKEN')
DB_NAME = 'profiles.db'

# Перевірка, чи завантажився токен
if not BOT_TOKEN:
    print("Помилка: Не знайдено токен бота. Перевірте ваш .env файл.")
    exit()

# --- Створюємо ГОЛОВНІ об'єкти ---
dp = Dispatcher(fsm_strategy=FSMStrategy.GLOBAL_USER)
form_router = Router()


# --- FSM (Машина станів) ---
class ProfileForm(StatesGroup):
    name = State()
    age = State()
    bio = State()


# 👈 2. СТВОРЮЄМО ФУНКЦІЮ ДЛЯ ВСТАНОВЛЕННЯ КОМАНД
async def set_bot_commands(bot: Bot):
    """
    Створює меню команд у Telegram.
    """
    commands = [
        BotCommand(command="start", description="🏁 Перезапустити бота"),
        BotCommand(command="create_profile", description="📝 Створити нову анкету"),
        BotCommand(command="my_profile", description="👤 Подивитись свою анкету"),
        BotCommand(command="check_profile", description="👀 Перевірити анкету іншого (через reply)"),
        BotCommand(command="delete_profile", description="🗑️ Видалити свою анкету")
    ]
    # Встановлюємо команди для всіх користувачів у всіх чатах (за замовчуванням)
    await bot.set_my_commands(commands)


# --- Функція для ініціалізації БД ---
async def init_db():
    db = await aiosqlite.connect(DB_NAME)
    await db.execute('''
                     CREATE TABLE IF NOT EXISTS profiles
                     (
                         user_id
                         INTEGER
                         PRIMARY
                         KEY,
                         username
                         TEXT,
                         name
                         TEXT,
                         age
                         INTEGER,
                         bio
                         TEXT
                     )
                     ''')
    await db.commit()
    return db


# --- Обробники команд, що прив'язані до form_router ---
# ... (весь ваш код для обробки анкет залишається тут БЕЗ ЗМІН) ...
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
        await message.reply("У тебе вже є анкета! Щоб створити нову, спочатку видали стару командою /delete_profile")
        return
    await state.set_state(ProfileForm.name)
    try:
        await bot.send_message(chat_id=user_id, text="Починаємо створювати твою анкету. Як тебе звати?")
        await message.reply(
            f"@{username}, я написав тобі в особисті повідомлення (ОП). Будь ласка, дай відповідь мені там.")
    except Exception as e:
        await message.reply(
            f"@{username}, я не можу написати тобі в ОП. Будь ласка, почни зі мною діалог (натисни на моє ім'я та 'Start') і спробуй знову.")
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
async def process_bio(message: Message, state: FSMContext, db: aiosqlite.Connection):
    await state.update_data(bio=message.text)
    user_data = await state.get_data()
    user_id = message.from_user.id
    username = message.from_user.username or message.from_user.first_name
    await db.execute("INSERT INTO profiles (user_id, username, name, age, bio) VALUES (?, ?, ?, ?, ?)",
                     (user_id, username, user_data['name'], user_data['age'], user_data['bio']))
    await db.commit()
    await state.clear()
    await message.reply("Твоя анкета готова і збережена в базі даних! 🎉", parse_mode="HTML")


# --- Обробники команд, що прив'язані до головного диспетчера 'dp' ---
# ... (весь ваш код для інших команд залишається тут БЕЗ ЗМІН) ...
@dp.message(CommandStart())
async def cmd_start(message: Message):
    await message.reply("Привіт! Я бот для анкет. Додай мене в групу і використовуй команду /create_profile")


@dp.message(Command("my_profile"))
async def show_my_profile(message: Message, db: aiosqlite.Connection):
    user_id = message.from_user.id
    async with db.execute("SELECT name, age, bio FROM profiles WHERE user_id = ?", (user_id,)) as cursor:
        profile_data = await cursor.fetchone()
    if profile_data:
        name, age, bio = profile_data
        await message.reply(f"Твоя анкета:\n<b>Ім'я:</b> {name}\n<b>Вік:</b> {age}\n<b>Про себе:</b> {bio}",
                            parse_mode="HTML")
    else:
        await message.reply("У тебе ще немає анкети. Створи її командою /create_profile (у групі).")


@dp.message(Command("check_profile"))
async def check_profile(message: Message, db: aiosqlite.Connection):
    if message.chat.type not in ('group', 'supergroup'):
        await message.reply("Цю команду потрібно використовувати у групі!")
        return
    if not message.reply_to_message:
        await message.reply(
            "Щоб подивитися анкету, використовуй цю команду у відповідь (reply) на повідомлення користувача.")
        return
    user_id = message.reply_to_message.from_user.id
    username = message.reply_to_message.from_user.username or message.reply_to_message.from_user.first_name
    async with db.execute("SELECT name, age, bio FROM profiles WHERE user_id = ?", (user_id,)) as cursor:
        profile_data = await cursor.fetchone()
    if profile_data:
        name, age, bio = profile_data
        await message.reply(f"Анкета @{username}:\n<b>Ім'я:</b> {name}\n<b>Вік:</b> {age}\n<b>Про себе:</b> {bio}",
                            parse_mode="HTML")
    else:
        await message.reply(f"У користувача @{username} поки немає анкети.")


@dp.message(Command("delete_profile"))
async def delete_profile(message: Message, db: aiosqlite.Connection):
    user_id = message.from_user.id
    async with db.execute("SELECT 1 FROM profiles WHERE user_id = ?", (user_id,)) as cursor:
        exists = await cursor.fetchone()
    if exists:
        await db.execute("DELETE FROM profiles WHERE user_id = ?", (user_id,))
        await db.commit()
        await message.reply("Твою анкету видалено з бази даних.")
    else:
        await message.reply("У тебе і так немає анкети.")


# --- Функція запуску бота ---
async def main():
    bot = Bot(token=BOT_TOKEN)
    db = await init_db()

    dp.include_router(form_router)

    # 👈 3. ВИКЛИКАЄМО ФУНКЦІЮ ПЕРЕД ЗАПУСКОМ БОТА
    await set_bot_commands(bot)

    try:
        logging.info("Бот запускається...")
        await bot.delete_webhook(drop_pending_updates=True)
        await dp.start_polling(bot, db=db)
    finally:
        logging.info("Бот зупиняється...")
        await db.close()
        logging.info("З'єднання з БД закрито.")


if __name__ == '__main__':
    asyncio.run(main())