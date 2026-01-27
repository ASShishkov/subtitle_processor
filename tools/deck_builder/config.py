# config.py
import os


# Папки и файлы
RU_TEXT = "input/ru_text.txt"
EN_TEXT = "input/en_text.txt"
RU_AUDIO_DIR = "input/ru_audio"
EN_AUDIO_DIR = "input/en_audio"
IMG_DIR = "input/images"
VIDEO_DIR = "input/videos"
OUTPUT_DECK = "output/deck.apkg"
OUTPUT_DIR = "output"

# Бесплатный лимит Google Cloud TTS (WaveNet)
FREE_LIMIT = 1_000_000

# Настройки Google Cloud TTS
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
GOOGLE_CREDENTIALS = os.getenv("GOOGLE_CREDENTIALS", os.path.join(BASE_DIR, "keys/anki-tts-key_3.json"))

PROJECT_ID = "anki-tts-456709"

# Настройки голосов
RU_VOICE = {
    "language_code": "ru-RU",
    "name": "ru-RU-Wavenet-A"
}
EN_VOICE = {
    "language_code": "en-US",
    "name": "en-US-Wavenet-F"
}

# --- ИЗМЕНЕНО: Настройки по умолчанию для полей карточки ---
ELEMENT_SPACING = 10  # расстояние между элементами в пикселях
FRONT_ORDER = ["ru_text", "image", "ru_audio"]  # порядок элементов на лицевой стороне
BACK_ORDER = ["en_text", "video", "en_audio"]   # порядок элементов на оборотной стороне
MEDIA_SIZE = {"width": 300, "height": 200} # размер медиафайлов
MEDIA_PROCESSING = "resize"  # "resize" или "crop"