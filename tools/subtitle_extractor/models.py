# models.py

def create_tables(conn):
    """Создание таблиц в базе данных."""
    cursor = conn.cursor()

    # Таблица для хранения путей
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS paths (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            subtitles TEXT,
            phrases_en TEXT,
            phrases_ru TEXT,
            output TEXT,
            filename TEXT,
            last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Таблица для хранения данных таблицы (фразы, субтитры, выбор)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS table_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            phrase TEXT,
            subtitle_text TEXT,
            selected BOOLEAN,
            rus_phrase TEXT,
            sort_key INTEGER,
            is_manual BOOLEAN,
            last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    conn.commit()

def drop_tables(conn):
    """Удаление таблиц (для тестирования или очистки)."""
    cursor = conn.cursor()
    cursor.execute('DROP TABLE IF EXISTS paths')
    cursor.execute('DROP TABLE IF EXISTS table_data')
    conn.commit()

# Пример использования (не вызывать напрямую, будет использоваться в database.py)
if __name__ == "__main__":
    import sqlite3
    conn = sqlite3.connect('subtitles.db')
    create_tables(conn)
    conn.close()