from utils import parse_srt, normalize_text, find_matches


def search_phrases(subtitles, phrases, threshold):
    """Ищет фразы в субтитрах и возвращает совпадения."""
    results = []
    for sub in subtitles:
        sub_text = sub.text
        for phrase in phrases:
            similarity, matched_phrase = find_matches(sub_text, phrase, threshold)
            if similarity > 0:
                results.append({
                    'subtitle': sub,
                    'phrase': phrase,
                    'similarity': similarity,
                    'matched_text': matched_phrase
                })
    return results


def calculate_timestamps(subtitle, phrase):
    """Вычисляет точные таймкоды для фразы в субтитре."""
    start_time = subtitle.start.to_time()
    end_time = subtitle.end.to_time()
    total_duration = (end_time - start_time).total_seconds()

    # Нормализуем текст и фразу
    norm_subtitle = normalize_text(subtitle.text)
    norm_phrase = normalize_text(phrase)

    # Находим позицию фразы в тексте субтитра
    sub_words = norm_subtitle.split()
    phrase_words = norm_phrase.split()
    phrase_len = len(phrase_words)

    for i in range(len(sub_words) - phrase_len + 1):
        if ' '.join(sub_words[i:i + phrase_len]) == norm_phrase:
            # Вычисляем пропорциональные таймкоды
            start_ratio = i / len(sub_words)
            end_ratio = (i + phrase_len) / len(sub_words)
            phrase_start = start_time + (end_time - start_time) * start_ratio
            phrase_end = start_time + (end_time - start_time) * end_ratio
            return phrase_start, phrase_end
    # Если точное совпадение не найдено, возвращаем границы субтитра
    return start_time, end_time


def analyze_duplicates(subtitles, phrases):
    """Анализирует дубликаты фраз в субтитрах и среди самих фраз."""
    phrase_counts = {}
    subtitle_matches = {}

    # Анализ дублей среди фраз
    norm_phrases = [normalize_text(p) for p in phrases]
    for i, norm_p in enumerate(norm_phrases):
        phrase_counts[norm_p] = phrase_counts.get(norm_p, 0) + 1

    # Анализ совпадений в субтитрах
    for sub in subtitles:
        norm_sub = normalize_text(sub.text)
        subtitle_matches[sub.index] = norm_sub

    duplicates = {
        'phrase_duplicates': {p: c for p, c in phrase_counts.items() if c > 1},
        'subtitle_duplicates': {}
    }

    # Поиск дублей среди субтитров
    seen = {}
    for idx, text in subtitle_matches.items():
        if text in seen:
            duplicates['subtitle_duplicates'].setdefault(text, []).append((idx, seen[text]))
        else:
            seen[text] = idx

    return duplicates