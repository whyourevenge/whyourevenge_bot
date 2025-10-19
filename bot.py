# bot.py

import asyncio
import logging
import os
from dotenv import load_dotenv
import hmac
import hashlib
from urllib.parse import parse_qsl
import json

from aiogram import Bot, Dispatcher
from aiogram.fsm.strategy import FSMStrategy
from aiogram.types import BufferedInputFile
from aiohttp import web

from database.db_utils import init_db
from handlers.common import common_router, set_bot_commands
from handlers.profile_form import form_router


# --- Функція для перевірки даних від Telegram ---
def is_valid_init_data(init_data: str, token: str) -> bool:
    try:
        parsed_data = dict(parse_qsl(init_data))
        tg_hash = parsed_data.pop('hash')

        data_check_string = "\n".join(sorted([f"{k}={v}" for k, v in parsed_data.items()]))

        secret_key = hmac.new("WebAppData".encode(), token.encode(), hashlib.sha256).digest()
        h = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256)

        return h.hexdigest() == tg_hash
    except Exception:
        return False


# --- Веб-обробники ---

async def options_handler(request):
    """Обробник для OPTIONS-запитів (CORS)."""
    headers = {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'POST, OPTIONS',
        'Access-Control-Allow-Headers': 'Content-Type',
    }
    return web.Response(status=200, headers=headers)


async def get_profile_handler(request):
    """Обробник для отримання анкети."""
    headers = {"Access-Control-Allow-Origin": "*"}

    # 👈 ОСЬ ВИПРАВЛЕННЯ: Читаємо тіло запиту як чистий текст
    init_data = await request.text()

    bot = request.app['bot']
    db = request.app['db']

    if not is_valid_init_data(init_data, bot.token):
        return web.json_response({"error": True, "message": "Invalid data"}, status=403, headers=headers)

    user_data_string = dict(parse_qsl(init_data))['user']
    user_id = json.loads(user_data_string)['id']

    async with db.execute("SELECT name, age, bio, photo_id FROM profiles WHERE user_id = ?", (user_id,)) as cursor:
        profile = await cursor.fetchone()

    if not profile:
        return web.json_response({"error": True, "message": "Profile not found"}, status=404, headers=headers)

    name, age, bio, photo_id = profile

    try:
        file = await bot.get_file(photo_id)
        photo_url = f"https://api.telegram.org/file/bot{bot.token}/{file.file_path}"
    except Exception:
        photo_url = "https://via.placeholder.com/120"

    return web.json_response({
        "name": name,
        "age": age,
        "bio": bio,
        "photo_url": photo_url
    }, headers=headers)


async def create_profile_handler(request):
    """Обробник для створення анкети."""
    headers = {"Access-Control-Allow-Origin": "*"}
    bot = request.app['bot']
    db = request.app['db']

    try:
        post_data = await request.post()
        init_data = post_data.get('initData')

        if not init_data or not is_valid_init_data(init_data, bot.token):
            return web.json_response({"success": False, "message": "Invalid data"}, status=403, headers=headers)

        user_data_string = dict(parse_qsl(init_data))['user']
        user_info = json.loads(user_data_string)
        user_id = user_info['id']
        username = user_info.get('username', user_info['first_name'])

        name = post_data.get('name')
        age = int(post_data.get('age'))
        bio = post_data.get('bio')
        photo_file = post_data.get('photo')

        if not all([name, age, bio, photo_file]):
            return web.json_response({"success": False, "message": "All fields are required"}, status=400,
                                     headers=headers)

        photo_content = photo_file.file.read()
        sent_photo_message = await bot.send_photo(
            chat_id=user_id,
            photo=BufferedInputFile(photo_content, filename=photo_file.filename)
        )
        photo_file_id = sent_photo_message.photo[-1].file_id

        await db.execute(
            "INSERT INTO profiles (user_id, username, name, age, bio, photo_id) VALUES (?, ?, ?, ?, ?, ?)",
            (user_id, username, name, age, bio, photo_file_id)
        )
        await db.commit()

        return web.json_response({"success": True}, headers=headers)
    except Exception as e:
        logging.error(f"Error creating profile: {e}", exc_info=True)
        return web.json_response({"success": False, "message": "Internal server error"}, status=500, headers=headers)


# --- Головна функція запуску ---
async def main():
    load_dotenv()
    logging.basicConfig(level=logging.INFO)

    BOT_TOKEN = os.getenv('BOT_TOKEN')
    WEB_SERVER_HOST = os.getenv('WEB_SERVER_HOST', '127.0.0.1')
    WEB_SERVER_PORT = int(os.getenv('WEB_SERVER_PORT', 8080))

    if not BOT_TOKEN:
        print("Помилка: Не знайдено токен бота.")
        return

    bot = Bot(token=BOT_TOKEN)
    db = await init_db()
    dp = Dispatcher(fsm_strategy=FSMStrategy.GLOBAL_USER)

    app = web.Application()
    app['bot'] = bot
    app['db'] = db

    app.router.add_route('POST', '/get_profile', get_profile_handler)
    app.router.add_route('OPTIONS', '/get_profile', options_handler)
    app.router.add_route('POST', '/create_profile', create_profile_handler)
    app.router.add_route('OPTIONS', '/create_profile', options_handler)

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, WEB_SERVER_HOST, WEB_SERVER_PORT)

    dp.include_routers(common_router, form_router)

    try:
        await set_bot_commands(bot)
        logging.info("Бот і веб-сервер запускаються...")
        await bot.delete_webhook(drop_pending_updates=True)
        await asyncio.gather(
            dp.start_polling(bot, db=db, app=app),
            site.start()
        )
    finally:
        await runner.cleanup()
        await db.close()
        logging.info("Бот і веб-сервер зупинено.")


if __name__ == '__main__':
    asyncio.run(main())