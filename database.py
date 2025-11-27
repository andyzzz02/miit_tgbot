import sqlite3
import os

def init_database():
    os.makedirs("data", exist_ok=True)
    conn = sqlite3.connect("data/database.db")
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_id INTEGER UNIQUE NOT NULL,
            full_name TEXT NOT NULL,
            username TEXT,
            role TEXT DEFAULT 'user',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            type TEXT NOT NULL,
            room TEXT NOT NULL,
            description TEXT NOT NULL,
            photo_id TEXT,
            status TEXT DEFAULT 'new',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            assigned_to INTEGER,
            completed_at DATETIME,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    
    conn.commit()
    conn.close()

def add_user(telegram_id, full_name, username=None, role='user'):
    conn = sqlite3.connect("data/database.db")
    cursor = conn.cursor()
    cursor.execute('INSERT OR IGNORE INTO users (telegram_id, full_name, username, role) VALUES (?, ?, ?, ?)', 
                   (telegram_id, full_name, username, role))
    conn.commit()
    conn.close()

def create_request(user_id, request_type, room, description, photo_id=None):
    conn = sqlite3.connect("data/database.db")
    cursor = conn.cursor()
    cursor.execute('INSERT INTO requests (user_id, type, room, description, photo_id) VALUES (?, ?, ?, ?, ?)', 
                   (user_id, request_type, room, description, photo_id))
    request_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return request_id

def get_user_by_telegram_id(telegram_id):
    conn = sqlite3.connect("data/database.db")
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users WHERE telegram_id = ?', (telegram_id,))
    user = cursor.fetchone()
    conn.close()
    return user

def get_user_requests(telegram_id):
    conn = sqlite3.connect("data/database.db")
    cursor = conn.cursor()
    cursor.execute('SELECT r.* FROM requests r JOIN users u ON r.user_id = u.id WHERE u.telegram_id = ? ORDER BY r.created_at DESC', (telegram_id,))
    requests = cursor.fetchall()
    conn.close()
    return requests

def get_request_by_id(request_id):
    conn = sqlite3.connect("data/database.db")
    cursor = conn.cursor()
    cursor.execute('''
        SELECT 
            r.id, r.user_id, r.type, r.room, r.description, 
            r.photo_id, r.status, r.created_at, r.assigned_to, r.completed_at,
            u.telegram_id, u.full_name  -- ИЗМЕНИЛ ПОРЯДОК: сначала telegram_id, потом full_name
        FROM requests r 
        JOIN users u ON r.user_id = u.id 
        WHERE r.id = ?
    ''', (request_id,))
    request = cursor.fetchone()
    conn.close()
    
    # ДЛЯ ОТЛАДКИ
    if request:
        print(f"🔍 СТРУКТУРА ЗАЯВКИ #{request_id}:")
        columns = [
            "r.id", "r.user_id", "r.type", "r.room", "r.description", 
            "r.photo_id", "r.status", "r.created_at", "r.assigned_to", "r.completed_at",
            "u.telegram_id", "u.full_name"  # ТЕПЕРЬ telegram_id на [10], full_name на [11]
        ]
        for i, (col, value) in enumerate(zip(columns, request)):
            print(f"  [{i}] {col}: {value}")
    
    return request
# === ДОБАВЛЕННЫЕ ФУНКЦИИ ДЛЯ РАБОТЫ СО СТАТУСАМИ ===

def update_request_status(request_id, status):
    """Обновляет статус заявки"""
    conn = sqlite3.connect("data/database.db")
    cursor = conn.cursor()
    
    if status == 'completed':
        cursor.execute('UPDATE requests SET status = ?, completed_at = CURRENT_TIMESTAMP WHERE id = ?', (status, request_id))
    else:
        cursor.execute('UPDATE requests SET status = ? WHERE id = ?', (status, request_id))
    
    conn.commit()
    conn.close()
    print(f"✅ Статус заявки #{request_id} изменен на: {status}")

def get_all_requests(limit=50):
    """Получает все заявки"""
    conn = sqlite3.connect("data/database.db")
    cursor = conn.cursor()
    cursor.execute('''
        SELECT 
            r.id, r.user_id, r.type, r.room, r.description, 
            r.photo_id, r.status, r.created_at, r.assigned_to, r.completed_at,
            u.telegram_id, u.full_name  -- ТАКОЙ ЖЕ ПОРЯДОК КАК В get_request_by_id
        FROM requests r 
        JOIN users u ON r.user_id = u.id 
        ORDER BY r.created_at DESC 
        LIMIT ?
    ''', (limit,))
    requests = cursor.fetchall()
    conn.close()
    return requests

def get_requests_by_status(status):
    """Получает заявки по статусу"""
    conn = sqlite3.connect("data/database.db")
    cursor = conn.cursor()
    cursor.execute('''
        SELECT r.*, u.full_name, u.telegram_id 
        FROM requests r 
        JOIN users u ON r.user_id = u.id 
        WHERE r.status = ?
        ORDER BY r.created_at DESC
    ''', (status,))
    requests = cursor.fetchall()
    conn.close()
    return requests



