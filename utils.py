import pysrt
import pymorphy3
import re
import difflib

# Инициализация морфологического анализатора
morph = pymorphy3.MorphAnalyzer()


def parse_srt(file_path):
    """Парсит SRT-файл и возвращает список субтитров."""
    try:
        return pysrt.open(file_path)
    except Exception as e:
        raise ValueError(f"Ошибка при парсинге SRT-файла: {e}")


def normalize_text(text):
    """Нормализует текст, приводя слова к их базовой форме."""
    # Удаляем лишние пробелы и приводим к нижнему регистру
    text = text.strip().lower()
    # Разбиваем на слова и нормализуем каждое слово
    words = re.findall(r'\w+', text)
    normalized = [morph.parse(word)[0].normal_form for word in words]
    return ' '.join(normalized)


def find_matches(subtitle_text, phrase, threshold=0.8):
    """Ищет совпадения между текстом субтитра и фразой с учетом порога."""
    # Нормализуем текст субтитра и фразу
    norm_subtitle = normalize_text(subtitle_text)
    norm_phrase = normalize_text(phrase)

    # Проверяем точное совпадение с помощью re
    if re.search(r'\b' + re.escape(norm_phrase) + r'\b', norm_subtitle):
        return 1.0, norm_phrase

    # Используем difflib для оценки частичного совпадения
    matcher = difflib.SequenceMatcher(None, norm_subtitle, norm_phrase)
    similarity = matcher.ratio()
    if similarity >= threshold:
        return similarity, norm_phrase
    return 0.0, None