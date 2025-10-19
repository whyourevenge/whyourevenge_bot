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
from aiogram.exceptions import TelegramForbiddenError
from aiohttp import web

from database.db_utils import init_db
from handlers.common import common_router, set_bot_commands
from handlers.profile_form import form_router


# ... (функция is_valid_init_data и options_handler без изменений) ...
def is_valid_init_data(init_data: str, token: str) -> bool:
    try:
        parsed_data = dict(parse_qsl(init_data))
        tg_hash = parsed_data.pop('hash')
        data_check_string = "\n".join(sorted([f"{k}={v}" for k, v in parsed_data.items()]))
        secret_key = hmac.new("WebAppData".encode(), token.encode(), hashlib.sha256).digest()
        h = hmac.new(secret_key, data_check_string.encode(), hashlib.sha2sha256)
        return h.hexdigest() == tg_hash
    except Exception:
        return False


async def options_handler(request):
    headers = {'Access-Control-Allow-Origin': '*', 'Access-Control-Allow-Methods': 'POST, OPTIONS',
               'Access-Control-Allow-Headers': 'Content-Type', }
    return web.Response(status=200, headers=headers)


# 👈 ОБНОВЛЕНО: get_profile_handler теперь отдаёт и лайки
async def get_profile_handler(request):
    headers = {"Access-Control-Allow-Origin": "*"}
    init_data = await request.text()
    bot = request.app['bot']
    db = request.app['db']

    if not is_valid_init_data(init_data, bot.token):
        return web.json_response({"error": True, "message": "Invalid data"}, status=403, headers=headers)

    user_data_string = dict(parse_qsl(init_data))['user']
    viewer_user_id = json.loads(user_data_string)['id']  # ID того, кто смотрит
    profile_user_id = viewer_user_id  # По умолчанию, смотрим свой профиль

    # --- Получаем данные о профиле ---
    async with db.execute("SELECT name, age, bio, photo_id FROM profiles WHERE user_id = ?",
                          (profile_user_id,)) as cursor:
        profile = await cursor.fetchone()

    if not profile:
        return web.json_response({"error": True, "message": "Profile not found"}, status=404, headers=headers)

    name, age, bio, photo_id = profile

    # --- Получаем данные о лайках ---
    # Считаем общее количество лайков
    async with db.execute("SELECT COUNT(*) FROM likes WHERE receiver_id = ?", (profile_user_id,)) as cursor:
        likes_count = (await cursor.fetchone())[0]

    # Проверяем, лайкал ли текущий пользователь этот профиль
    async with db.execute("SELECT 1 FROM likes WHERE giver_id = ? AND receiver_id = ?",
                          (viewer_user_id, profile_user_id)) as cursor:
        has_liked = await cursor.fetchone() is not None

    # --- Получаем URL фото ---
    try:
        file = await bot.get_file(photo_id)
        photo_url = f"https://api.telegram.org/file/bot{bot.token}/{file.file_path}"
    except Exception:
        photo_url = "https://via.placeholder.com/120"

    return web.json_response({
        "user_id": profile_user_id,
        "name": name,
        "age": age,
        "bio": bio,
        "photo_url": photo_url,
        "likes_count": likes_count,
        "has_liked": has_liked,
        "is_own_profile": viewer_user_id == profile_user_id
    }, headers=headers)


# 👈 НОВОЕ: Обработчик для лайков
async def like_profile_handler(request):
    headers = {"Access-Control-Allow-Origin": "*"}
    bot = request.app['bot']
    db = request.app['db']

    try:
        data = await request.json()
        init_data = data.get('initData')
        receiver_id = data.get('receiver_id')

        if not is_valid_init_data(init_data, bot.token):
            return web.json_response({"success": False, "message": "Invalid data"}, status=403, headers=headers)

        user_data_string = dict(parse_qsl(init_data))['user']
        giver_info = json.loads(user_data_string)
        giver_id = giver_info['id']
        giver_username = giver_info.get('username', giver_info['first_name'])

        # Запрещаем лайкать самого себя
        if giver_id == receiver_id:
            return web.json_response({"success": False, "message": "You can't like yourself"}, status=400,
                                     headers=headers)

        # INSERT OR IGNORE - если такая запись уже есть, команда просто проигнорируется
        await db.execute(
            "INSERT OR IGNORE INTO likes (giver_id, receiver_id) VALUES (?, ?)",
            (giver_id, receiver_id)
        )
        await db.commit()

        # Попытка отправить уведомление
        try:
            await bot.send_message(
                chat_id=receiver_id,
                text=f"❤️ Ваша анкета сподобалася користувачу @{giver_username}!"
            )
        except TelegramForbiddenError:
            logging.warning(f"Не вдалося надіслати повідомлення користувачу {receiver_id}, бот заблокований.")
        except Exception as e:
            logging.error(f"Помилка при відправці повідомлення про лайк: {e}")

        return web.json_response({"success": True}, headers=headers)
    except Exception as e:
        logging.error(f"Error processing like: {e}", exc_info=True)
        return web.json_response({"success": False, "message": "Internal server error"}, status=500, headers=headers)


# ... (код create_profile_handler без изменений) ...
async def create_profile_handler(request):
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
        sent_photo_message = await bot.send_photo(chat_id=user_id,
                                                  photo=BufferedInputFile(photo_content, filename=photo_file.filename))
        photo_file_id = sent_photo_message.photo[-1].file_id
        await db.execute("INSERT INTO profiles (user_id, username, name, age, bio, photo_id) VALUES (?, ?, ?, ?, ?, ?)",
                         (user_id, username, name, age, bio, photo_file_id))
        await db.commit()
        return web.json_response({"success": True}, headers=headers)
    except Exception as e:
        logging.error(f"Error creating profile: {e}", exc_info=True)
        return web.json_response({"success": False, "message": "Internal server error"}, status=500, headers=headers)


# --- Главная функция запуска ---
async def main():
    # ... (код загрузки конфига без изменений) ...
    load_dotenv()
    logging.basicConfig(level=logging.INFO)
    BOT_TOKEN = os.getenv('BOT_TOKEN')
    WEB_SERVER_HOST = os.getenv('WEB_SERVER_HOST', '127.0.0.1')
    WEB_SERVER_PORT = int(os.getenv('WEB_SERVER_PORT', 8080))
    if not BOT_TOKEN:
        print("Ошибка: Не найден токен бота.")
        return

    bot = Bot(token=BOT_TOKEN)
    db = await init_db()
    dp = Dispatcher(fsm_strategy=FSMStrategy.GLOBAL_USER)

    app = web.Application(client_max_size=1024 ** 2 * 10)
    app['bot'] = bot
    app['db'] = db

    # 👈 ОБНОВЛЕНО: Добавляем новый обработчик
    app.router.add_route('POST', '/get_profile', get_profile_handler)
    app.router.add_route('OPTIONS', '/get_profile', options_handler)
    app.router.add_route('POST', '/create_profile', create_profile_handler)
    app.router.add_route('OPTIONS', '/create_profile', options_handler)
    app.router.add_route('POST', '/like_profile', like_profile_handler)
    app.router.add_route('OPTIONS', '/like_profile', options_handler)

    # ... (остальной код запуска без изменений) ...
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, WEB_SERVER_HOST, WEB_SERVER_PORT)
    dp.include_routers(common_router, form_router)
    try:
        await set_bot_commands(bot)
        logging.info("Бот и веб-сервер запускаются...")
        await bot.delete_webhook(drop_pending_updates=True)
        await asyncio.gather(dp.start_polling(bot, db=db, app=app), site.start())
    finally:
        await runner.cleanup()
        await db.close()
        logging.info("Бот и веб-сервер остановлены.")


if __name__ == '__main__':
    asyncio.run(main())