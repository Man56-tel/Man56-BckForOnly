import sqlite3
import os
import config

DB_NAME = 'bookings.db'

# Инициализация базы данных
def init_db():
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()

    # Мастера
    cur.execute('''
        CREATE TABLE IF NOT EXISTS masters (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            login TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            calendar_id TEXT NOT NULL
        )
    ''')

    # Услуги
    cur.execute('''
        CREATE TABLE IF NOT EXISTS services (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            master_id INTEGER,
            name TEXT NOT NULL,
            duration INTEGER NOT NULL,
            FOREIGN KEY (master_id) REFERENCES masters (id)
        )
    ''')

    # Рабочее время
    cur.execute('''
        CREATE TABLE IF NOT EXISTS working_hours (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            master_id INTEGER,
            day_of_week INTEGER,  -- 0=пн, 6=вс
            start_time TEXT,
            end_time TEXT,
            break_start TEXT,
            break_end TEXT,
            FOREIGN KEY (master_id) REFERENCES masters (id)
        )
    ''')

    # Записи
    cur.execute('''
        CREATE TABLE IF NOT EXISTS bookings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            master_id INTEGER,
            service_id INTEGER,
            client_name TEXT NOT NULL,
            phone TEXT NOT NULL,
            date TEXT NOT NULL,
            time TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            event_id_google TEXT,
            telegram_notify BOOLEAN DEFAULT 0,
            chat_id TEXT,
            FOREIGN KEY (master_id) REFERENCES masters (id),
            FOREIGN KEY (service_id) REFERENCES services (id)
        )
    ''')

    # Проверим, есть ли мастера
    cur.execute("SELECT COUNT(*) FROM masters")
    if cur.fetchone()[0] == 0:
        # Добавляем тестовых мастеров
        cur.execute("INSERT INTO masters (name, login, password_hash, calendar_id) VALUES (?, ?, ?, ?)",
                    ("Мастер 1", "master1", "pass1", config.GOOGLE_CALENDAR_ID))
        cur.execute("INSERT INTO masters (name, login, password_hash, calendar_id) VALUES (?, ?, ?, ?)",
                    ("Мастер 2", "master2", "pass2", config.GOOGLE_CALENDAR_ID))

        # Услуги
        services = [
            ("Услуга 1", 30), ("Услуга 2", 60), ("Услуга 3", 90),
            ("Услуга 4", 45), ("Услуга 5", 75), ("Услуга 6", 120)
        ]
        for name, dur in services:
            cur.execute("INSERT INTO services (master_id, name, duration) VALUES (?, ?, ?)", (1, name, dur))
            cur.execute("INSERT INTO services (master_id, name, duration) VALUES (?, ?, ?)", (2, name, dur))

    conn.commit()
    conn.close()

def get_all_masters():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("SELECT id, name FROM masters")
    result = [dict(row) for row in cur.fetchall()]
    conn.close()
    return result

def get_master(master_id):
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("SELECT * FROM masters WHERE id = ?", (master_id,))
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else None

def authenticate_master(login, password):
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("SELECT * FROM masters WHERE login = ? AND password_hash = ?", (login, password))
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else None

def get_services_by_master(master_id):
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("SELECT id, name, duration FROM services WHERE master_id = ?", (master_id,))
    result = [dict(row) for row in cur.fetchall()]
    conn.close()
    return result

def get_service(service_id):
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("SELECT * FROM services WHERE id = ?", (service_id,))
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else None

def get_working_hours(master_id):
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("SELECT * FROM working_hours WHERE master_id = ?", (master_id,))
    result = [dict(row) for row in cur.fetchall()]
    conn.close()
    return result

def get_bookings_by_master(master_id):
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("SELECT * FROM bookings WHERE master_id = ? ORDER BY date, time", (master_id,))
    result = [dict(row) for row in cur.fetchall()]
    conn.close()
    return result

def add_booking(data):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute('''
        INSERT INTO bookings (master_id, service_id, client_name, phone, date, time, event_id_google, telegram_notify)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (data['master_id'], data['service_id'], data['client_name'], data['phone'],
          data['date'], data['time'], data['event_id_google'], data['telegram_notify']))
    booking_id = cur.lastrowid
    conn.commit()
    conn.close()
    return booking_id
