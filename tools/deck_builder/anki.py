# anki.py
import genanki
import os
import re
import glob
import hashlib
import time
from datetime import datetime
from logger import get_logger
from anki_model import create_model
from anki_media import process_media
from utils.db import get_all_phrases, get_media
import config
from utils.file_utils import normalize_path, sanitize_filename


def create_deck(audio_files, deck_type="mixed", answer_position="below", spacing=10,
                front_order=["title", "image", "audio"], back_order=["title", "video", "audio"],
                media_size={"width": 300, "height": 200}, media_processing="resize", deck_name="МояКолода",
                db_path="anki.db", video_format="mp4"):
    logger = get_logger()
    logger.info(f"Создание колоды Anki: {deck_name}...")

    css = """
    video { max-width: 100%; width: 100%; height: auto; display: inline-block; object-fit: contain; }
    .video-container { max-width: 100%; margin: 0 auto; }
    """
    model = create_model(deck_type, answer_position, spacing, front_order, back_order, css=css)
    deck_id = 987654321
    phrases = get_all_phrases(db_path)

    # --- НОВОЕ (п.3): Обновленная логика формирования имени ---
    PLATFORM_MAP = {"mp4": "iOS-Android", "m4v": "iOS", "webm": "PC-Android"}

    unique_phrases = len(phrases)
    card_count = unique_phrases * 2 if deck_type == "mixed" else unique_phrases

    sanitized_deck_name = sanitize_filename(deck_name)
    front_str = ",".join(front_order)
    back_str = ",".join(back_order)
    current_date = datetime.now().strftime("%Y-%m-%d")

    platform = PLATFORM_MAP.get(video_format, "N/A")

    formatted_deck_name = f"{sanitized_deck_name}_(front-{front_str}_back-{back_str})_{unique_phrases}p_{card_count}c_{platform}_{video_format}_{current_date}"

    deck = genanki.Deck(deck_id, formatted_deck_name)
    logger.debug(f"Создана колода с ID: {deck_id}")

    media_files = []
    for i, (phrase_id, ru_text, en_text) in enumerate(phrases):
        logger.debug(f"Обработка карточки {i + 1}: ru_text='{ru_text.strip()}', en_text='{en_text.strip()}'")

        def extract_number(filename):
            match = re.search(r'(\d+)\.mp3$', filename)
            return int(match.group(1)) if match else None

        ru_audio_files = glob.glob(normalize_path(os.path.join(config.RU_AUDIO_DIR, "*.mp3")))
        en_audio_files = glob.glob(normalize_path(os.path.join(config.EN_AUDIO_DIR, "*.mp3")))
        ru_audio_dict = {extract_number(os.path.basename(f)): f for f in ru_audio_files if
                         extract_number(os.path.basename(f)) is not None}
        en_audio_dict = {extract_number(os.path.basename(f)): f for f in en_audio_files if
                         extract_number(os.path.basename(f)) is not None}

        ru_audio_path = normalize_path(ru_audio_dict.get(i + 1, ""))
        en_audio_path = normalize_path(en_audio_dict.get(i + 1, ""))
        ru_audio = os.path.basename(ru_audio_path) if ru_audio_path else ""
        en_audio = os.path.basename(en_audio_path) if en_audio_path else ""
        img = f"{i + 1:03d}.jpg"
        img_path = normalize_path(os.path.join(config.IMG_DIR, img))
        video_path = get_media(phrase_id, "video", db_path)
        logger.debug(f"Получен путь к видео для phrase_id {phrase_id}: {video_path}")

        if video_path and not os.path.exists(video_path):
            logger.error(f"Видеофайл не найден: {video_path}")
            video_path = None
        elif video_path:
            selected_format = video_format
            if selected_format in ["m4v", "webm"]:
                video_path_alt = video_path.rsplit('.', 1)[0] + f'.{selected_format}'
                video_path = video_path_alt if os.path.exists(video_path_alt) else video_path
                logger.debug(f"Проверен альтернативный путь для формата .{selected_format}: {video_path}")

        processed_image = process_media(img_path, "image", media_size, media_processing,
                                        video_format) if os.path.exists(img_path) else None
        processed_video = process_media(video_path, "video", media_size, media_processing,
                                        video_format) if video_path else None
        logger.debug(f"Обработанное видео для phrase_id {phrase_id}: {processed_video}")

        image_field = f'<img src="{os.path.basename(processed_image)}">' if processed_image else ""
        video_field = f'<video width="{media_size["width"]}" height="{media_size["height"]}" controls playsinline webkit-playsinline><source src="{os.path.basename(processed_video)}" type="video/{video_format}">Your browser does not support the video tag.</video>' if processed_video else ""

        if processed_image and os.path.exists(processed_image):
            media_files.append(normalize_path(processed_image))
            logger.info(f"Добавлено изображение: {processed_image}")
        if processed_video and os.path.exists(processed_video):
            media_files.append(normalize_path(processed_video))
            logger.info(f"Добавлено видео: {processed_video}")

        fields = [
            ru_text.strip(),
            en_text.strip(),
            f"[sound:{ru_audio}]" if ru_audio and os.path.exists(ru_audio_path) else "",
            f"[sound:{en_audio}]" if en_audio and os.path.exists(en_audio_path) else "",
            image_field,
            video_field,
        ]
        logger.debug(f"Поля карточки {i + 1}: {fields}")
        if "video" in back_order and processed_video:
            video_index = back_order.index("video")
            audio_index = back_order.index("audio") if "audio" in back_order else -1
            if audio_index != -1 and video_index > audio_index:
                fields.insert(video_index + 1, video_field)

        guid = hashlib.md5(f"{ru_text}{en_text}{time.time()}".encode('utf-8')).hexdigest()
        note = genanki.Note(model=model, fields=fields, guid=guid)
        deck.add_note(note)
        logger.info(f"Карточка {i + 1} добавлена в колоду")

        if ru_audio and os.path.exists(ru_audio_path):
            media_files.append(normalize_path(ru_audio_path))
            logger.debug(f"Добавлен русский аудиофайл в медиа: {ru_audio}")
        if en_audio and os.path.exists(en_audio_path):
            media_files.append(normalize_path(en_audio_path))
            logger.debug(f"Добавлен английский аудиофайл в медиа: {en_audio}")

    package = genanki.Package(deck)
    package.media_files = media_files
    output_filename = normalize_path(f"output/{formatted_deck_name}.apkg")
    package.write_to_file(output_filename)
    logger.info(f"Колода сохранена в {output_filename}")