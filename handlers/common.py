# handlers/common.py

from aiogram import Router, Bot, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, BotCommand, CallbackQuery, WebAppInfo, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.fsm.context import FSMContext
import aiosqlite

from handlers.profile_form import ProfileForm
from keyboards.inline import get_edit_profile_keyboard

common_router = Router()

async def set_bot_commands(bot: Bot):
    commands = [
        BotCommand(command="start", description="🏁 Перезапустити бота"),
        BotCommand(command="profile_card", description="🪪 Моя веб-анкета (створити/подивитись)"),
        BotCommand(command="check_profile", description="👀 Перевірити анкету (в чаті)"),
        BotCommand(command="all_profiles", description="📋 Показати список всіх анкет"),
        BotCommand(command="edit_profile", description="✏️ Редагувати анкету (в чаті)"),
        BotCommand(command="my_profile", description="👤 Подивитись анкету (в чаті)"),
        BotCommand(command="delete_profile", description="🗑️ Видалити свою анкету")
    ]
    await bot.set_my_commands(commands)

@common_router.message(CommandStart())
async def cmd_start(message: Message):
    await message.reply("Привіт! Щоб подивитись або створити свою анкету, використовуй команду /profile_card")

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
        await message.reply("У тебе ще немає анкети. Створи її командою /profile_card.")

@common_router.message(Command("all_profiles"))
async def show_all_profiles(message: Message, db: aiosqlite.Connection):
    if message.chat.type not in ('group', 'supergroup'):
        await message.reply("Цю команду можна використовувати тільки в групі.")
        return
    async with db.execute("SELECT username, name FROM profiles ORDER BY name") as cursor:
        all_profiles = await cursor.fetchall()
    if not all_profiles:
        await message.reply("На жаль, ще ніхто не створив анкету.")
        return
    response_text = "📋 <b>Список усіх анкет:</b>\n\n"
    for i, (username, name) in enumerate(all_profiles, 1):
        user_handle = f"@{username}" if username else name
        response_text += f"{i}. {user_handle}\n"
    await message.reply(response_text, parse_mode="HTML")

@common_router.message(Command("edit_profile"))
async def edit_profile(message: Message, db: aiosqlite.Connection, bot: Bot):
    user_id = message.from_user.id
    async with db.execute("SELECT name, age, bio, photo_id FROM profiles WHERE user_id = ?", (user_id,)) as cursor:
        profile_data = await cursor.fetchone()
    if profile_data:
        name, age, bio, photo_id = profile_data
        caption = f"Ось твоя поточна анкета. Що хочеш змінити?"
        await bot.send_photo(chat_id=message.chat.id, photo=photo_id, caption=caption, reply_markup=get_edit_profile_keyboard())
    else:
        await message.reply("У тебе ще немає анкети. Спочатку створи її командою /profile_card.")

@common_router.callback_query(F.data.startswith("edit_"))
async def handle_edit_callback(callback: CallbackQuery, state: FSMContext, bot: Bot):
    action = callback.data.split("_")[1]
    actions = { "name": (ProfileForm.editing_name, "Введи нове ім'я:"), "age": (ProfileForm.editing_age, "Введи новий вік:"), "bio": (ProfileForm.editing_bio, "Напиши нову біографію:"), "photo": (ProfileForm.editing_photo, "Надішли нове фото:") }
    if action in actions:
        state_to_set, text = actions[action]
        await state.set_state(state_to_set)
        try:
            await bot.send_message(chat_id=callback.from_user.id, text=text)
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
    profile_data = None
    username_to_check = ""
    if message.reply_to_message:
        user_id = message.reply_to_message.from_user.id
        username_to_check = message.reply_to_message.from_user.username or message.reply_to_message.from_user.first_name
        async with db.execute("SELECT name, age, bio, photo_id FROM profiles WHERE user_id = ?", (user_id,)) as cursor:
            profile_data = await cursor.fetchone()
    else:
        parts = message.text.split()
        if len(parts) < 2:
            await message.reply("<b>Неправильне використання!</b>\n"
                                "1. У відповідь (reply) на повідомлення.\n"
                                "2. Написавши: `/check_profile @username`",
                                parse_mode="HTML")
            return
        username_to_check = parts[1].lstrip('@')
        async with db.execute("SELECT name, age, bio, photo_id FROM profiles WHERE username = ?", (username_to_check,)) as cursor:
            profile_data = await cursor.fetchone()
    if profile_data:
        name, age, bio, photo_id = profile_data
        caption = f"Анкета <b>{username_to_check}</b>:\n<b>Ім'я:</b> {name}\n<b>Вік:</b> {age}\n<b>Про себе:</b> {bio}"
        await bot.send_photo(chat_id=message.chat.id, photo=photo_id, caption=caption, parse_mode="HTML")
    else:
        await message.reply(f"У користувача <b>{username_to_check}</b> поки немає анкети.", parse_mode="HTML")

@common_router.message(Command("profile_card"))
async def show_profile_card(message: Message, bot: Bot):
    webapp_url = "https://whyourevenge.github.io/whyourevenge_bot/webapp/"
    button = InlineKeyboardButton(text="Відкрити мою анкету", web_app=WebAppInfo(url=webapp_url))
    keyboard = InlineKeyboardMarkup(inline_keyboard=[[button]])
    await bot.send_message(
        chat_id=message.chat.id,
        text="Натисни кнопку, щоб відкрити, створити або відредагувати свою анкету:",
        reply_markup=keyboard
    )

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