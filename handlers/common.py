# handlers/common.py

from aiogram import Router, Bot, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, BotCommand, CallbackQuery  # 👈 Додали CallbackQuery
from aiogram.fsm.context import FSMContext  # 👈 Додали FSMContext
import aiosqlite

from handlers.profile_form import ProfileForm  # 👈 Імпортуємо наш FSM
from keyboards.inline import get_edit_profile_keyboard  # 👈 Імпортуємо нашу клавіатуру

common_router = Router()


async def set_bot_commands(bot: Bot):
    commands = [
        BotCommand(command="start", description="🏁 Перезапустити бота"),
        BotCommand(command="create_profile", description="📝 Створити нову анкету"),
        BotCommand(command="edit_profile", description="✏️ Редагувати свою анкету"),  # 👈 НОВА КОМАНДА
        BotCommand(command="my_profile", description="👤 Подивитись свою анкету"),
        BotCommand(command="check_profile", description="👀 Перевірити анкету іншого (через reply)"),
        BotCommand(command="delete_profile", description="🗑️ Видалити свою анкету")
    ]
    await bot.set_my_commands(commands)


# ... (код для /start, /my_profile, /check_profile, /delete_profile залишається без змін) ...
@common_router.message(CommandStart())
async def cmd_start(message: Message):
    await message.reply("Привіт! Я бот для анкет. Використовуй команду /create_profile, щоб почати.")


@common_router.message(Command("my_profile"))
async def show_my_profile(message: Message, db: aiosqlite.Connection, bot: Bot):
    user_id = message.from_user.id
    async with db.execute("SELECT name, age, bio, photo_id FROM profiles WHERE user_id = ?", (user_id,)) as cursor:
        profile_data = await cursor.fetchone()
    if profile_data:
        name, age, bio, photo_id = profile_data
        caption = f"<b>Ім'я:</b> {name}\n<b>Вік:</b> {age}\n<b>Про себе:</b> {bio}"
        await bot.send_photo(chat_id=message.chat.id, photo=photo_id, caption=caption, parse_mode="HTML")
    else:
        await message.reply("У тебе ще немає анкети. Створи її командою /create_profile (у групі).")


# 👈 НОВЕ: Команда для початку редагування
@common_router.message(Command("edit_profile"))
async def edit_profile(message: Message, db: aiosqlite.Connection, bot: Bot):
    user_id = message.from_user.id
    async with db.execute("SELECT name, age, bio, photo_id FROM profiles WHERE user_id = ?", (user_id,)) as cursor:
        profile_data = await cursor.fetchone()

    if profile_data:
        name, age, bio, photo_id = profile_data
        caption = f"Ось твоя поточна анкета. Що хочеш змінити?"
        # Надсилаємо фото з клавіатурою
        await bot.send_photo(
            chat_id=message.chat.id,
            photo=photo_id,
            caption=caption,
            reply_markup=get_edit_profile_keyboard()  # 👈 Використовуємо нашу клавіатуру
        )
    else:
        await message.reply("У тебе ще немає анкети, щоб її редагувати. Спочатку створи її командою /create_profile.")


# 👈 НОВЕ: Обробники колбеків (натискань на кнопки)
@common_router.callback_query(F.data.startswith("edit_"))
async def handle_edit_callback(callback: CallbackQuery, state: FSMContext, bot: Bot):
    action = callback.data.split("_")[1]  # Отримуємо "name", "age" і т.д.

    # Словник: дія -> (стан, текст_запрошення)
    actions = {
        "name": (ProfileForm.editing_name, "Введи нове ім'я:"),
        "age": (ProfileForm.editing_age, "Введи новий вік:"),
        "bio": (ProfileForm.editing_bio, "Напиши нову біографію:"),
        "photo": (ProfileForm.editing_photo, "Надішли нове фото:")
    }

    if action in actions:
        state_to_set, text = actions[action]
        await state.set_state(state_to_set)

        # Відповідаємо в ОП, щоб не заважати в групі
        try:
            await bot.send_message(chat_id=callback.from_user.id, text=text)
            # Відповідаємо на колбек, щоб зник годинник на кнопці
            await callback.answer("Я написав тобі в особисті повідомлення.")
        except Exception:
            await callback.answer("Помилка! Спершу почни зі мною діалог в ОП.", show_alert=True)
    else:
        await callback.answer("Невідома дія.")


@common_router.message(Command("check_profile"))
async def check_profile(message: Message, db: aiosqlite.Connection, bot: Bot):
    if message.chat.type not in ('group', 'supergroup'):
        await message.reply("Цю команду потрібно використовувати у групі!")
        return
    if not message.reply_to_message:
        await message.reply("Використовуй цю команду у відповідь на повідомлення користувача.")
        return
    user_id = message.reply_to_message.from_user.id
    username = message.reply_to_message.from_user.username or message.reply_to_message.from_user.first_name
    async with db.execute("SELECT name, age, bio, photo_id FROM profiles WHERE user_id = ?", (user_id,)) as cursor:
        profile_data = await cursor.fetchone()
    if profile_data:
        name, age, bio, photo_id = profile_data
        caption = f"Анкета @{username}:\n<b>Ім'я:</b> {name}\n<b>Вік:</b> {age}\n<b>Про себе:</b> {bio}"
        await bot.send_photo(chat_id=message.chat.id, photo=photo_id, caption=caption, parse_mode="HTML")
    else:
        await message.reply(f"У користувача @{username} поки немає анкети.")


@common_router.message(Command("delete_profile"))
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