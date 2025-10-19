# database/db_utils.py

import aiosqlite

DB_NAME = 'profiles.db'

async def init_db():
    db = await aiosqlite.connect(DB_NAME)
    await db.execute('''
        CREATE TABLE IF NOT EXISTS profiles (
            user_id INTEGER PRIMARY KEY, username TEXT, name TEXT,
            age INTEGER, bio TEXT, photo_id TEXT
        )
    ''')
    await db.commit()
    return db