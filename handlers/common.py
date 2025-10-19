# handlers/common.py

from aiogram import Router, Bot
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, BotCommand
import aiosqlite

common_router = Router()

async def set_bot_commands(bot: Bot):
    commands = [
        BotCommand(command="start", description="🏁 Перезапустити бота"),
        BotCommand(command="create_profile", description="📝 Створити нову анкету"),
        BotCommand(command="my_profile", description="👤 Подивитись свою анкету"),
        BotCommand(command="check_profile", description="👀 Перевірити анкету іншого (через reply)"),
        BotCommand(command="delete_profile", description="🗑️ Видалити свою анкету")
    ]
    await bot.set_my_commands(commands)

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