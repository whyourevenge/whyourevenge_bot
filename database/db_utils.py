# database/db_utils.py

import aiosqlite

DB_NAME = 'profiles.db'

async def init_db():
    db = await aiosqlite.connect(DB_NAME)
    # Создаём таблицу анкет (если её нет)
    await db.execute('''
        CREATE TABLE IF NOT EXISTS profiles (
            user_id INTEGER PRIMARY KEY, username TEXT, name TEXT,
            age INTEGER, bio TEXT, photo_id TEXT
        )
    ''')
    # 👈 НОВОЕ: Создаём таблицу лайков
    await db.execute('''
        CREATE TABLE IF NOT EXISTS likes (
            like_id INTEGER PRIMARY KEY AUTOINCREMENT,
            giver_id INTEGER NOT NULL,    -- Кто поставил лайк
            receiver_id INTEGER NOT NULL, -- Кому поставили лайк
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (giver_id) REFERENCES profiles(user_id),
            FOREIGN KEY (receiver_id) REFERENCES profiles(user_id),
            UNIQUE(giver_id, receiver_id) -- Гарантирует, что один человек может лайкнуть другого только один раз
        )
    ''')
    await db.commit()
    return db