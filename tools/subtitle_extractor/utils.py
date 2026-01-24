import pysrt
import pymorphy3
import re
from datetime import datetime, timedelta
from difflib import SequenceMatcher

# Инициализация моделей
morph = pymorphy3.MorphAnalyzer()

def find_matches(subtitle_text, phrase, threshold=0.5, stop_words=None, whitelist=None):
    """
    Поиск совпадений между фразой и субтитром с использованием точного и частичного совпадения.
    """
    if stop_words is None:
        stop_words = set()
    if whitelist is None:
        whitelist = set(["not", "yes", "out", "i", "im", "is", "are", "a", "an", "the"])

    # Очистка текста для точного совпадения
    def clean_text_exact(text):
        if not text or not isinstance(text, str):
            return ""
        text = re.sub(r'[^\w\s\'-]', ' ', text.lower()).strip()
        return text

    # Точное совпадение
    norm_subtitle_exact = clean_text_exact(subtitle_text)
    norm_phrase_exact = clean_text_exact(phrase)
    if norm_phrase_exact in norm_subtitle_exact:
        return 1.0, norm_phrase_exact, subtitle_text

    # Частичное совпадение с SequenceMatcher
    norm_subtitle_clean = clean_text_exact(subtitle_text)
    norm_phrase_clean = clean_text_exact(phrase)
    matcher = SequenceMatcher(None, norm_subtitle_clean.split(), norm_phrase_clean.split())
    match = matcher.find_longest_match(0, len(norm_subtitle_clean.split()), 0, len(norm_phrase_clean.split()))
    if match.size > 0:
        partial_similarity = match.size / len(norm_phrase_clean.split()) if norm_phrase_clean.split() else 0.0
        if partial_similarity >= threshold:
            start_idx = match.a
            end_idx = match.a + match.size
            matched_text = " ".join(norm_subtitle_clean.split()[start_idx:end_idx])
            return partial_similarity, matched_text, subtitle_text

    return 0.0, None, None

# Оставшиеся функции остаются без изменений
def parse_srt(file_path):
    try:
        return pysrt.open(file_path)
    except Exception as e:
        raise ValueError(f"Ошибка при парсинге SRT-файла: {e}")

def normalize_text(text):
    text = text.strip().lower()
    words = re.findall(r'\w+', text)
    normalized = [morph.parse(word)[0].normal_form for word in words]
    return ' '.join(normalized)

def format_srt_entry(index, start, end, text):
    start_str = f"{start.hours:02d}:{start.minutes:02d}:{start.seconds:02d},{start.milliseconds:03d}"
    end_str = f"{end.hours:02d}:{end.minutes:02d}:{end.seconds:02d},{end.milliseconds:03d}"
    return f"{index}\n{start_str} --> {end_str}\n{text}\n\n"

def calculate_exact_timestamps(subtitle, phrase):
    start_time = subtitle.start
    end_time = subtitle.end
    total_duration_ms = (end_time - start_time).ordinal

    norm_subtitle = normalize_text(subtitle.text)
    norm_phrase = normalize_text(phrase)

    sub_words = norm_subtitle.split()
    phrase_words = norm_phrase.split()
    phrase_len = len(phrase_words)

    for i in range(len(sub_words) - phrase_len + 1):
        window = ' '.join(sub_words[i:i + phrase_len])
        if window == norm_phrase:
            start_ratio = i / len(sub_words)
            end_ratio = (i + phrase_len) / len(sub_words)
            start_ms = start_time.ordinal + int(total_duration_ms * start_ratio)
            end_ms = start_time.ordinal + int(total_duration_ms * end_ratio)
            return (pysrt.SubRipTime.from_ordinal(start_ms),
                    pysrt.SubRipTime.from_ordinal(end_ms))

    from difflib import SequenceMatcher
    matcher = SequenceMatcher(None, norm_subtitle, norm_phrase)
    match = matcher.find_longest_match(0, len(norm_subtitle), 0, len(norm_phrase))
    if match.size > 0:
        start_ratio = match.a / len(norm_subtitle)
        end_ratio = (match.a + match.size) / len(norm_subtitle)
        start_ms = start_time.ordinal + int(total_duration_ms * start_ratio)
        end_ms = start_time.ordinal + int(total_duration_ms * end_ratio)
        return (pysrt.SubRipTime.from_ordinal(start_ms),
                pysrt.SubRipTime.from_ordinal(end_ms))

    return start_time, end_time

def sort_subtitles_by_time(subtitles):
    return sorted(subtitles, key=lambda x: x.start.ordinal)