# utils/db.py
import sqlite3

def init_db(db_path):
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS phrases
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, ru_text TEXT, en_text TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS media
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, phrase_id INTEGER, media_type TEXT, path TEXT,
                  FOREIGN KEY(phrase_id) REFERENCES phrases(id))''')
    conn.commit()
    conn.close()

def add_phrase(ru_text, en_text, db_path):
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute("INSERT INTO phrases (ru_text, en_text) VALUES (?, ?)", (ru_text, en_text))
    phrase_id = c.lastrowid
    conn.commit()
    conn.close()
    return phrase_id

def get_all_phrases(db_path):
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute("SELECT id, ru_text, en_text FROM phrases")
    phrases = c.fetchall()
    conn.close()
    return phrases

def add_media(phrase_id, media_type, media_path, db_path):
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute("INSERT INTO media (phrase_id, media_type, path) VALUES (?, ?, ?)",
              (phrase_id, media_type, media_path))
    conn.commit()
    conn.close()

def clear_database(db_path):
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute("DELETE FROM phrases")
    c.execute("DELETE FROM media")
    conn.commit()
    conn.close()

def get_media(phrase_id, media_type, db_path):
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute("SELECT path FROM media WHERE phrase_id = ? AND media_type = ?", (phrase_id, media_type))
    result = c.fetchone()
    conn.close()
    return result[0] if result else None

def clear_videos(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM media WHERE media_type = 'video'")
    conn.commit()
    conn.close()