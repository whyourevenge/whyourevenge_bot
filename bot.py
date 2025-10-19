# bot.py

import asyncio
import logging
import os
from dotenv import load_dotenv

from aiogram import Bot, Dispatcher
from aiogram.fsm.strategy import FSMStrategy

# Імпортуємо наші "шухляди"
from database.db_utils import init_db
from handlers.common import common_router, set_bot_commands
from handlers.profile_form import form_router

async def main():
    # --- Завантаження конфігурації ---
    load_dotenv()
    logging.basicConfig(level=logging.INFO)

    BOT_TOKEN = os.getenv('BOT_TOKEN')
    if not BOT_TOKEN:
        print("Помилка: Не знайдено токен бота. Перевірте ваш .env файл.")
        return

    # --- Ініціалізація ---
    bot = Bot(token=BOT_TOKEN)
    db = await init_db()
    dp = Dispatcher(fsm_strategy=FSMStrategy.GLOBAL_USER)

    # --- Підключення роутерів ---
    dp.include_routers(common_router, form_router)

    # --- Запуск ---
    try:
        await set_bot_commands(bot)
        logging.info("Бот запускається...")
        await bot.delete_webhook(drop_pending_updates=True)
        await dp.start_polling(bot, db=db)
    finally:
        logging.info("Бот зупиняється...")
        await db.close()
        logging.info("З'єднання з БД закрито.")

if __name__ == '__main__':
    asyncio.run(main())