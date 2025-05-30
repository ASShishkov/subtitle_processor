# database.py

import sqlite3
from models import create_tables, drop_tables
from datetime import datetime

class Database:
    def __init__(self, db_name='subtitles.db'):
        """Инициализация базы данных."""
        self.conn = sqlite3.connect(db_name)
        create_tables(self.conn)

    def close(self):
        """Закрытие соединения с базой данных."""
        self.conn.close()

    def save_paths(self, subtitles, phrases_en, phrases_ru, output, filename):
        """Сохранение путей в базу данных."""
        cursor = self.conn.cursor()
        # Проверяем, есть ли запись, и обновляем её
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
        print(f"Пути сохранены: {subtitles}, {phrases_en}, {phrases_ru}, {output}, {filename}")

    def load_paths(self):
        """Загрузка путей из базы данных."""
        cursor = self.conn.cursor()
        cursor.execute('SELECT subtitles, phrases_en, phrases_ru, output, filename FROM paths')
        result = cursor.fetchone()
        if result:
            print(f"Пути загружены из базы данных (последняя запись): {result}")
            return result
        default_paths = ['', '', '', '', 'episodes']
        print(f"Путей в базе данных нет, возвращаем значения по умолчанию: {default_paths}")
        return default_paths

    def save_table_data(self, data):
        """Сохранение данных таблицы в базу данных."""
        cursor = self.conn.cursor()
        cursor.execute('DELETE FROM table_data')  # Очистка перед сохранением
        for row in data:
            if len(row) == 4:  # Проверяем, что строка содержит все необходимые поля
                phrase, subtitle_text, selected, rus_phrase = row
                sort_key = 0  # Значение по умолчанию
                is_manual = False
                cursor.execute('''
                    INSERT INTO table_data (phrase, subtitle_text, selected, rus_phrase, sort_key, is_manual)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (phrase, subtitle_text, selected == "Да", rus_phrase, sort_key, is_manual))
        self.conn.commit()

    def load_table_data(self):
        """Загрузка данных таблицы из базы данных."""
        cursor = self.conn.cursor()
        cursor.execute('SELECT phrase, subtitle_text, selected, rus_phrase, sort_key, is_manual FROM table_data')
        rows = cursor.fetchall()
        data = []
        for row in rows:
            phrase, subtitle_text, selected, rus_phrase, sort_key, is_manual = row
            selected_str = "Да" if selected else "Нет"
            data.append([phrase, subtitle_text, selected_str, rus_phrase])
        return data