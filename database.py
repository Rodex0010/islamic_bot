# database.py
import sqlite3
import json
import os
from datetime import datetime, timedelta
from typing import List, Dict, Optional

DB_PATH = "islamic_bot.db"

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def update_ruqyah_table():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("PRAGMA table_info(ruqyah_reciters)")
    columns = [col[1] for col in cursor.fetchall()]
    
    if 'file' not in columns:
        print("➕ Adding 'file' column to ruqyah_reciters table...")
        cursor.execute('ALTER TABLE ruqyah_reciters ADD COLUMN file TEXT')
        conn.commit()
        print("✅ Column 'file' added successfully")
    
    conn.close()

def init_database():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_tasbeeh (
            user_id INTEGER PRIMARY KEY,
            current_count INTEGER DEFAULT 0,
            current_word_index INTEGER DEFAULT 0,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS active_chats (
            chat_id INTEGER PRIMARY KEY,
            activated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_athkar_sent_at TIMESTAMP,
            last_dua_sent_at TIMESTAMP,
            last_quran_sent_at TIMESTAMP
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS athkar (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            type TEXT NOT NULL,
            content TEXT NOT NULL
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS duas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            content TEXT NOT NULL
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS reciters (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            style TEXT,
            api_url TEXT
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS ruqyah_reciters (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            style TEXT,
            file_path TEXT,
            file TEXT,
            title TEXT
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS reminders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            content TEXT NOT NULL
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            first_name TEXT,
            username TEXT,
            joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_athkar_sent_at TIMESTAMP
        )
    ''')
    
    conn.commit()
    conn.close()
    print("✅ Database tables created")
    
    update_ruqyah_table()

def load_all_data_from_json():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    athkar_files = {
        "morning": "data/morning_athkar.json",
        "evening": "data/evening_athkar.json",
        "other": "data/other_athkar.json"
    }
    
    for athkar_type, file_path in athkar_files.items():
        if os.path.exists(file_path):
            with open(file_path, "r", encoding="utf-8") as f:
                athkar_list = json.load(f)
            for content in athkar_list:
                cursor.execute('INSERT OR IGNORE INTO athkar (type, content) VALUES (?, ?)', 
                             (athkar_type, content))
    
    if os.path.exists("data/duas.json"):
        with open("data/duas.json", "r", encoding="utf-8") as f:
            duas_list = json.load(f)
        for content in duas_list:
            cursor.execute('INSERT OR IGNORE INTO duas (content) VALUES (?)', (content,))
    
    if os.path.exists("data/reciters.json"):
        with open("data/reciters.json", "r", encoding="utf-8") as f:
            reciters_list = json.load(f)
        for reciter in reciters_list:
            cursor.execute('INSERT OR IGNORE INTO reciters (id, name, style, api_url) VALUES (?, ?, ?, ?)',
                         (reciter.get('id'), reciter.get('name'), reciter.get('style'), reciter.get('api_url')))
    
    if os.path.exists("data/ruqyah.json"):
        with open("data/ruqyah.json", "r", encoding="utf-8") as f:
            ruqyah_data = json.load(f)
            reciters_list = ruqyah_data.get("reciters", [])
            for reciter in reciters_list:
                cursor.execute('INSERT OR IGNORE INTO ruqyah_reciters (id, name, style, file_path, file, title) VALUES (?, ?, ?, ?, ?, ?)',
                             (reciter.get('id'), reciter.get('name'), reciter.get('style'), reciter.get('file_path'), reciter.get('file'), reciter.get('title')))
    
    if os.path.exists("data/reminders.json"):
        with open("data/reminders.json", "r", encoding="utf-8") as f:
            reminders_list = json.load(f)
        for content in reminders_list:
            cursor.execute('INSERT OR IGNORE INTO reminders (content) VALUES (?)', (content,))
    
    conn.commit()
    conn.close()
    print("✅ Data loaded from JSON files")

def get_tasbeeh(user_id: int) -> Dict:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT current_count, current_word_index FROM user_tasbeeh WHERE user_id = ?', (user_id,))
    result = cursor.fetchone()
    conn.close()
    if result:
        return {"count": result["current_count"], "word_index": result["current_word_index"]}
    return {"count": 0, "word_index": 0}

def update_tasbeeh(user_id: int, count: int, word_index: int):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT OR REPLACE INTO user_tasbeeh (user_id, current_count, current_word_index, updated_at)
        VALUES (?, ?, ?, ?)
    ''', (user_id, count, word_index, datetime.now()))
    conn.commit()
    conn.close()

def reset_tasbeeh_count(user_id: int):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('UPDATE user_tasbeeh SET current_count = 0, updated_at = ? WHERE user_id = ?', 
                   (datetime.now(), user_id))
    conn.commit()
    conn.close()

def get_athkar_by_type(athkar_type: str):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT content FROM athkar WHERE type = ? ORDER BY id', (athkar_type,))
    results = cursor.fetchall()
    conn.close()
    return [r["content"] for r in results]

def get_all_duas():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT content FROM duas ORDER BY id')
    results = cursor.fetchall()
    conn.close()
    return [r["content"] for r in results]

def get_random_dua():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT content FROM duas ORDER BY RANDOM() LIMIT 1')
    result = cursor.fetchone()
    conn.close()
    return result["content"] if result else "ربنا آتنا في الدنيا حسنة"

def get_duas_paginated(page: int, per_page: int = 10):
    conn = get_db_connection()
    cursor = conn.cursor()
    offset = page * per_page
    cursor.execute('SELECT id, content FROM duas ORDER BY id LIMIT ? OFFSET ?', (per_page, offset))
    results = cursor.fetchall()
    cursor.execute('SELECT COUNT(*) FROM duas')
    total = cursor.fetchone()[0]
    conn.close()
    return [{"id": r["id"], "content": r["content"]} for r in results], total

def get_ruqyah_reciters():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute('SELECT id, name, style, file_path, file, title FROM ruqyah_reciters')
    except sqlite3.OperationalError:
        cursor.execute('SELECT id, name, style, file_path, title FROM ruqyah_reciters')
    
    results = cursor.fetchall()
    conn.close()
    
    reciters = []
    for r in results:
        reciter = dict(r)
        if 'file' in reciter and reciter.get('file'):
            reciter['file_path'] = reciter['file']
        reciters.append(reciter)
    
    return reciters

def add_active_chat(chat_id: int):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('INSERT OR IGNORE INTO active_chats (chat_id, activated_at) VALUES (?, ?)', 
                   (chat_id, datetime.now()))
    conn.commit()
    conn.close()

def remove_active_chat(chat_id: int):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM active_chats WHERE chat_id = ?', (chat_id,))
    conn.commit()
    conn.close()

def get_all_active_chats():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT chat_id FROM active_chats')
    results = cursor.fetchall()
    conn.close()
    return [r["chat_id"] for r in results]

def is_chat_active(chat_id: int) -> bool:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT 1 FROM active_chats WHERE chat_id = ?', (chat_id,))
    result = cursor.fetchone()
    conn.close()
    return result is not None

def get_random_reminder():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT content FROM reminders ORDER BY RANDOM() LIMIT 1')
    result = cursor.fetchone()
    conn.close()
    return result["content"] if result else "سبحان الله"

def get_athkar_count(athkar_type: str) -> int:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*) FROM athkar WHERE type = ?', (athkar_type,))
    count = cursor.fetchone()[0]
    conn.close()
    return count

def add_user(user_id: int, first_name: str = None, username: str = None):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT OR IGNORE INTO users (user_id, first_name, username, joined_at)
        VALUES (?, ?, ?, ?)
    ''', (user_id, first_name, username, datetime.now()))
    conn.commit()
    conn.close()

def get_all_users():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT user_id FROM users')
    results = cursor.fetchall()
    conn.close()
    return [r["user_id"] for r in results]

def user_exists(user_id: int) -> bool:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT 1 FROM users WHERE user_id = ?', (user_id,))
    result = cursor.fetchone()
    conn.close()
    return result is not None

def remove_user(user_id: int):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM users WHERE user_id = ?', (user_id,))
    conn.commit()
    conn.close()

def get_users_count() -> int:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*) FROM users')
    count = cursor.fetchone()[0]
    conn.close()
    return count

def force_add_channel(chat_id: int):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('INSERT OR IGNORE INTO active_chats (chat_id, activated_at) VALUES (?, ?)', 
                   (chat_id, datetime.now()))
    conn.commit()
    conn.close()
    print(f"✅ Force added channel {chat_id}")

def get_user_last_athkar_time(user_id: int):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT last_athkar_sent_at FROM users WHERE user_id = ?', (user_id,))
    result = cursor.fetchone()
    conn.close()
    if result and result['last_athkar_sent_at']:
        try:
            return datetime.fromisoformat(result['last_athkar_sent_at'])
        except:
            return None
    return None

def update_user_last_athkar_time(user_id: int, force_now: bool = False, force_time=None):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    if force_time is not None:
        current_time = force_time.isoformat()
    elif force_now:
        current_time = datetime.now().isoformat()
    else:
        current_time = datetime.now().isoformat()
    
    cursor.execute('''
        UPDATE users 
        SET last_athkar_sent_at = ? 
        WHERE user_id = ?
    ''', (current_time, user_id))
    conn.commit()
    conn.close()

def get_chat_last_sent_time(chat_id: int, msg_type: str = 'athkar'):
    conn = get_db_connection()
    cursor = conn.cursor()
    column_map = {
        'athkar': 'last_athkar_sent_at',
        'dua': 'last_dua_sent_at',
        'quran': 'last_quran_sent_at'
    }
    column = column_map.get(msg_type, 'last_athkar_sent_at')
    cursor.execute(f'SELECT {column} FROM active_chats WHERE chat_id = ?', (chat_id,))
    result = cursor.fetchone()
    conn.close()
    if result and result[column]:
        try:
            return datetime.fromisoformat(result[column])
        except:
            return None
    return None

def update_chat_last_sent_time(chat_id: int, msg_type: str = 'athkar'):
    conn = get_db_connection()
    cursor = conn.cursor()
    column_map = {
        'athkar': 'last_athkar_sent_at',
        'dua': 'last_dua_sent_at',
        'quran': 'last_quran_sent_at'
    }
    column = column_map.get(msg_type, 'last_athkar_sent_at')
    cursor.execute(f'''
        UPDATE active_chats 
        SET {column} = ? 
        WHERE chat_id = ?
    ''', (datetime.now().isoformat(), chat_id))
    conn.commit()
    conn.close()

def get_chat_activation_time(chat_id: int):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT activated_at FROM active_chats WHERE chat_id = ?', (chat_id,))
    result = cursor.fetchone()
    conn.close()
    if result and result['activated_at']:
        try:
            return datetime.fromisoformat(result['activated_at'])
        except:
            return None
    return None

def fix_missing_last_sent_for_users():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    old_time = (datetime.now() - timedelta(minutes=60)).isoformat()
    
    cursor.execute('''
        UPDATE users 
        SET last_athkar_sent_at = ? 
        WHERE last_athkar_sent_at IS NULL
    ''', (old_time,))
    
    conn.commit()
    conn.close()
    print("✅ Fixed missing last_athkar_sent_at for users")

def fix_missing_last_sent_for_chats():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    old_time = (datetime.now() - timedelta(minutes=60)).isoformat()
    
    for col in ['last_athkar_sent_at', 'last_dua_sent_at', 'last_quran_sent_at']:
        cursor.execute(f'''
            UPDATE active_chats 
            SET {col} = ? 
            WHERE {col} IS NULL
        ''', (old_time,))
    
    conn.commit()
    conn.close()
    print("✅ Fixed missing last_sent for chats")