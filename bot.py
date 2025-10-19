# bot.py

import asyncio
import logging
import os
from dotenv import load_dotenv
import hmac
import hashlib
from urllib.parse import parse_qsl

from aiogram import Bot, Dispatcher
from aiogram.fsm.strategy import FSMStrategy
from aiohttp import web  # 👈 НОВЕ

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


# --- Наш веб-обробник, який віддає анкету ---
async def get_profile_handler(request):
    # Дозволяємо запити з будь-яких джерел (важливо для веб)
    headers = {"Access-Control-Allow-Origin": "*"}

    data = await request.json()
    init_data = data.get('initData')

    bot = request.app['bot']
    db = request.app['db']

    if not init_data or not is_valid_init_data(init_data, bot.token):
        return web.json_response({"error": True, "message": "Invalid data"}, status=403, headers=headers)

    user_data = dict(parse_qsl(init_data))['user']
    user_id = eval(user_data)['id']

    # Дістаємо фото і перетворюємо file_id на URL
    async with db.execute("SELECT name, age, bio, photo_id FROM profiles WHERE user_id = ?", (user_id,)) as cursor:
        profile = await cursor.fetchone()

    if not profile:
        return web.json_response({"error": True, "message": "Profile not found"}, status=404, headers=headers)

    name, age, bio, photo_id = profile

    try:
        # Отримуємо об'єкт файлу, щоб дістати його URL
        file = await bot.get_file(photo_id)
        photo_url = f"https://api.telegram.org/file/bot{bot.token}/{file.file_path}"
    except Exception:
        photo_url = "https://via.placeholder.com/120"  # Заглушка, якщо фото не знайдено

    return web.json_response({
        "name": name,
        "age": age,
        "bio": bio,
        "photo_url": photo_url
    }, headers=headers)


# --- Головна функція запуску ---
async def main():
    load_dotenv()
    logging.basicConfig(level=logging.INFO)

    BOT_TOKEN = os.getenv('BOT_TOKEN')
    # ВАЖЛИВО: адреса, на якій буде працювати наш сервер
    WEB_SERVER_HOST = os.getenv('WEB_SERVER_HOST', '127.0.0.1')
    WEB_SERVER_PORT = int(os.getenv('WEB_SERVER_PORT', 8080))

    if not BOT_TOKEN:
        print("Помилка: Не знайдено токен бота.")
        return

    # --- Ініціалізація ---
    bot = Bot(token=BOT_TOKEN)
    db = await init_db()
    dp = Dispatcher(fsm_strategy=FSMStrategy.GLOBAL_USER)

    # --- Веб-сервер ---
    app = web.Application()
    app['bot'] = bot
    app['db'] = db
    app.router.add_post('/get_profile', get_profile_handler)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, WEB_SERVER_HOST, WEB_SERVER_PORT)

    # --- Підключення роутерів ---
    dp.include_routers(common_router, form_router)

    # --- Запуск ---
    try:
        await set_bot_commands(bot)
        logging.info("Бот і веб-сервер запускаються...")
        await bot.delete_webhook(drop_pending_updates=True)

        # Запускаємо ОБИДВА: і бота, і сервер
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