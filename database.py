# database.py

import sqlite3
from models import create_tables, drop_tables
from datetime import datetime
import threading

class Database:
    def __init__(self, db_name='subtitles.db'):
        """Инициализация базы данных."""
        self.conn = sqlite3.connect(db_name, check_same_thread=False)  # Отключаем проверку потока
        self.lock = threading.Lock()  # Добавляем блокировку
        create_tables(self.conn)
        print("Таблицы успешно созданы")

    def close(self):
        """Закрытие соединения с базой данных."""
        self.conn.close()

    def save_paths(self, subtitles, phrases_en, phrases_ru, output, filename):
        """Сохранение путей в базу данных."""
        with self.lock:  # Используем блокировку
            cursor = self.conn.cursor()
            # Проверка входных данных
            paths = [subtitles, phrases_en, phrases_ru, output, filename]
            if not all(isinstance(p, str) and p.strip() for p in paths):
                print("Ошибка: один или несколько путей пусты или не являются строками")
                return
            try:
                # Проверяем, есть ли запись
                cursor.execute('SELECT id FROM paths')
                existing_id = cursor.fetchone()
                if existing_id:
                    cursor.execute('''
                        UPDATE paths SET subtitles = ?, phrases_en = ?, phrases_ru = ?, output = ?, filename = ?, last_updated = CURRENT_TIMESTAMP
                        WHERE id = ?
                    ''', (subtitles, phrases_en, phrases_ru, output, filename, existing_id[0]))
                else:
                    cursor.execute('''
                        INSERT INTO paths (subtitles, phrases_en, phrases_ru, output, filename)
                        VALUES (?, ?, ?, ?, ?)
                    ''', (subtitles, phrases_en, phrases_ru, output, filename))
                self.conn.commit()
                # Проверка сохранённых данных
                cursor.execute('SELECT subtitles, phrases_en, phrases_ru, output, filename FROM paths WHERE id = ?',
                               (existing_id[0] if existing_id else 1,))
                saved_data = cursor.fetchone()
                print(f"Пути сохранены в базе данных: {saved_data}")
            except sqlite3.Error as e:
                print(f"Ошибка при сохранении путей в базу данных: {e}")

    def load_paths(self):
        """Загрузка путей из базы данных."""
        with self.lock:  # Используем блокировку
            cursor = self.conn.cursor()
            try:
                cursor.execute(
                    'SELECT subtitles, phrases_en, phrases_ru, output, filename FROM paths ORDER BY last_updated DESC LIMIT 1')
                result = cursor.fetchone()
                if result:
                    print(f"Пути загружены из базы данных: {result}")
                    return result
                default_paths = ['', '', '', '', 'episodes']
                print(f"Путей в базе данных нет, возвращены значения по умолчанию: {default_paths}")
                return default_paths
            except sqlite3.Error as e:
                print(f"Ошибка при загрузке путей из базы данных: {e}")
                default_paths = ['', '', '', '', 'episodes']
                return default_paths

    def save_table_data(self, data):
        """Сохранение данных таблицы в базу данных."""
        with self.lock:  # Используем блокировку
            cursor = self.conn.cursor()
            try:
                cursor.execute('DELETE FROM table_data')  # Очистка перед сохранением
                for row in data:
                    if len(row) != 4 or not all(isinstance(x, str) for x in row):
                        print(f"Пропущена некорректная строка: {row}")
                        continue
                    phrase, subtitle_text, selected, rus_phrase = row
                    sort_key = 0  # Значение по умолчанию
                    is_manual = False
                    cursor.execute('''
                        INSERT INTO table_data (phrase, subtitle_text, selected, rus_phrase, sort_key, is_manual)
                        VALUES (?, ?, ?, ?, ?, ?)
                    ''', (phrase, subtitle_text, selected == "Да", rus_phrase, sort_key, is_manual))
                self.conn.commit()
                cursor.execute('SELECT COUNT(*) FROM table_data')
                count = cursor.fetchone()[0]
                print(f"Сохранено {count} строк в таблице table_data")
            except sqlite3.Error as e:
                print(f"Ошибка при сохранении данных таблицы: {e}")

    def load_table_data(self):
        """Загрузка данных таблицы из базы данных."""
        with self.lock:  # Используем блокировку
            cursor = self.conn.cursor()
            try:
                cursor.execute(
                    'SELECT phrase, subtitle_text, selected, rus_phrase, sort_key, is_manual FROM table_data')
                rows = cursor.fetchall()
                data = []
                for row in rows:
                    phrase, subtitle_text, selected, rus_phrase, sort_key, is_manual = row
                    selected_str = "Да" if selected else "Нет"
                    data.append([phrase, subtitle_text, selected_str, rus_phrase])
                print(f"Загружено {len(data)} строк из таблицы table_data")
                return data
            except sqlite3.Error as e:
                print(f"Ошибка при загрузке данных таблицы: {e}")
                return []