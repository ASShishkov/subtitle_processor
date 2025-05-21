import pysrt
import pymorphy3
import re
import difflib
from datetime import datetime, timedelta

morph = pymorphy3.MorphAnalyzer()


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


def find_matches(subtitle_text, phrase, threshold=0.8):
    norm_subtitle = normalize_text(subtitle_text)
    norm_phrase = normalize_text(phrase)

    if re.search(r'\b' + re.escape(norm_phrase) + r'\b', norm_subtitle):
        return 1.0, norm_phrase, subtitle_text
    matcher = difflib.SequenceMatcher(None, norm_subtitle, norm_phrase)
    similarity = matcher.ratio()
    if similarity >= threshold:
        return similarity, norm_phrase, subtitle_text
    return 0.0, None, None


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
        if ' '.join(sub_words[i:i + phrase_len]) == norm_phrase:
            start_ratio = i / len(sub_words)
            end_ratio = (i + phrase_len) / len(sub_words)
            start_ms = start_time.ordinal + int(total_duration_ms * start_ratio)
            end_ms = start_time.ordinal + int(total_duration_ms * end_ratio)
            return (pysrt.SubRipTime.from_ordinal(start_ms),
                    pysrt.SubRipTime.from_ordinal(end_ms))
    return start_time, end_time


def sort_subtitles_by_time(subtitles):
    return sorted(subtitles, key=lambda x: x.start.ordinal)