from utils import parse_srt, normalize_text, find_matches, format_srt_entry, calculate_exact_timestamps


def analyze_phrases(subtitles, phrases, threshold):
    """Анализирует фразы, возвращает ненайденные, частичные совпадения и дубли."""
    results = []
    phrase_counts = {}
    subtitle_matches = {}
    not_found_phrases = []
    partial_matches = []

    # Поиск совпадений
    for phrase in phrases:
        found = False
        phrase_matches = []
        norm_phrase = normalize_text(phrase)
        phrase_counts[norm_phrase] = phrase_counts.get(norm_phrase, 0) + 1

        for sub in subtitles:
            similarity, matched_phrase, matched_text = find_matches(sub.text, phrase, threshold)
            if similarity == 1.0:
                found = True
                phrase_matches.append({
                    'subtitle': sub,
                    'phrase': phrase,
                    'similarity': similarity
                })
            elif similarity > 0:
                found = True
                partial_matches.append({
                    'phrase': phrase,
                    'similarity': similarity,
                    'subtitle_index': sub.index,
                    'subtitle_text': matched_text
                })

        if not found:
            not_found_phrases.append(phrase)
        if phrase_matches:
            results.extend(phrase_matches)

    # Анализ дубликатов
    phrase_duplicates = {p: c for p, c in phrase_counts.items() if c > 1}
    for sub in subtitles:
        norm_sub = normalize_text(sub.text)
        subtitle_matches[sub.index] = norm_sub

    subtitle_duplicates = {}
    seen = {}
    for idx, text in subtitle_matches.items():
        if text in seen:
            subtitle_duplicates.setdefault(text, []).append((idx, seen[text]))
        else:
            seen[text] = idx

    return {
        'results': results,
        'not_found': not_found_phrases,
        'partial_matches': partial_matches,
        'phrase_duplicates': phrase_duplicates,
        'subtitle_duplicates': subtitle_duplicates
    }


def generate_excerpts(subtitles, phrases, threshold, output_path):
    """Генерирует отрывки с фразами в формате SRT."""
    with open(output_path, 'w', encoding='utf-8') as f:
        index = 1
        for phrase in phrases:
            for sub in subtitles:
                similarity, _, _ = find_matches(sub.text, phrase, threshold)
                if similarity > 0:
                    f.write(format_srt_entry(index, sub.start, sub.end, sub.text))
                    index += 1


def generate_timestamps(subtitles, phrases, threshold, output_path):
    """Генерирует точные таймкоды для фраз в формате SRT."""
    with open(output_path, 'w', encoding='utf-8') as f:
        index = 1
        for phrase in phrases:
            for sub in subtitles:
                similarity, _, _ = find_matches(sub.text, phrase, threshold)
                if similarity == 1.0:  # Только точные совпадения
                    start, end = calculate_exact_timestamps(sub, phrase)
                    f.write(format_srt_entry(index, start, end, phrase))
                    index += 1