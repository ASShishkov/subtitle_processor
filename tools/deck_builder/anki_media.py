# anki_media.py
from PIL import Image
import os
import shutil
import config  # Импорт config для OUTPUT_DIR
from logger import get_logger
from utils.file_utils import normalize_path, sanitize_filename

def process_media(file_path, media_type, media_size, media_processing, platform):
    logger = get_logger()
    if file_path is None:
        logger.error("Попытка обработки None вместо пути к файлу")
        return None
    file_path = normalize_path(file_path)
    logger.debug(f"Обработка медиафайла: {file_path}, тип: {media_type}, размер: {media_size}, метод: {media_processing}")

    # Определяем выходную папку
    media_output_dir = normalize_path(os.path.join(config.OUTPUT_DIR, "media"))
    os.makedirs(media_output_dir, exist_ok=True)  # Создаем папку, если она не существует

    output_path = file_path
    try:
        if media_type == "image":
            with Image.open(file_path) as img:
                if media_processing == "crop":
                    img.thumbnail((media_size["width"], media_size["height"]), Image.Resampling.LANCZOS)
                else:
                    img = img.resize((media_size["width"], media_size["height"]), Image.Resampling.LANCZOS)
                temp_filename = sanitize_filename(os.path.basename(file_path))
                temp_path = os.path.join(media_output_dir, temp_filename)
                img.save(temp_path)
                output_path = temp_path
                logger.info(f"Изображение обработано: {output_path}")
        elif media_type == "video":
            if not os.path.exists(file_path):
                logger.error(f"Видеофайл не найден: {file_path}")
                return None
            temp_filename = sanitize_filename(os.path.basename(file_path))
            temp_path = os.path.join(media_output_dir, temp_filename)
            shutil.copy2(file_path, temp_path)  # Просто копируем видео
            output_path = temp_path
            logger.info(f"Видео скопировано: {output_path}")
    except Exception as e:
        logger.error(f"Ошибка при обработке медиафайла {file_path}: {str(e)}")
        return None
    return output_path