import sqlite3


def init_db():
    conn = sqlite3.connect('reservations.db')
    cursor = conn.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS available_times (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            time TEXT NOT NULL,
            UNIQUE(date, time)
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS reserved_times (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            username TEXT,
            first_name TEXT,
            date TEXT NOT NULL,
            time TEXT NOT NULL
        )
    ''')

    conn.commit()
    conn.close()


init_db()
print("Database initialized successfully!")
