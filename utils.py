import pysrt
import pymorphy3
import re
import difflib
from datetime import datetime, timedelta

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
    text = text.strip().lower()
    words = re.findall(r'\w+', text)
    normalized = [morph.parse(word)[0].normal_form for word in words]
    return ' '.join(normalized)


def find_matches(subtitle_text, phrase, threshold=0.8):
    """Ищет совпадения между текстом субтитра и фразой с учетом порога."""
    norm_subtitle = normalize_text(subtitle_text)
    norm_phrase = normalize_text(phrase)

    # Проверяем точное совпадение
    if re.search(r'\b' + re.escape(norm_phrase) + r'\b', norm_subtitle):
        return 1.0, norm_phrase, subtitle_text

    # Оценка частичного совпадения
    matcher = difflib.SequenceMatcher(None, norm_subtitle, norm_phrase)
    similarity = matcher.ratio()
    if similarity >= threshold:
        return similarity, norm_phrase, subtitle_text
    return 0.0, None, None


def format_srt_entry(index, start, end, text):
    """Форматирует запись в формате SRT."""
    start_str = f"{start.hours:02d}:{start.minutes:02d}:{start.seconds:02d},{start.milliseconds:03d}"
    end_str = f"{end.hours:02d}:{end.minutes:02d}:{end.seconds:02d},{end.milliseconds:03d}"
    return f"{index}\n{start_str} --> {end_str}\n{text}\n\n"


def calculate_exact_timestamps(subtitle, phrase):
    """Вычисляет точные таймкоды для фразы в субтитре."""
    start_time = subtitle.start
    end_time = subtitle.end
    total_duration_ms = (end_time - start_time).ordinal  # Длительность в миллисекундах

    # Нормализуем текст и фразу
    norm_subtitle = normalize_text(subtitle.text)
    norm_phrase = normalize_text(phrase)

    # Разбиваем текст на слова
    sub_words = norm_subtitle.split()
    phrase_words = norm_phrase.split()
    phrase_len = len(phrase_words)

    # Ищем позицию фразы в тексте
    for i in range(len(sub_words) - phrase_len + 1):
        if ' '.join(sub_words[i:i + phrase_len]) == norm_phrase:
            # Пропорционально вычисляем таймкоды
            start_ratio = i / len(sub_words)
            end_ratio = (i + phrase_len) / len(sub_words)
            start_ms = start_time.ordinal + int(total_duration_ms * start_ratio)
            end_ms = start_time.ordinal + int(total_duration_ms * end_ratio)
            return (pysrt.SubRipTime.from_ordinal(start_ms),
                    pysrt.SubRipTime.from_ordinal(end_ms))
    # Если точное совпадение не найдено, возвращаем границы субтитра
    return start_time, end_time