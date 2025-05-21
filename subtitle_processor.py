from utils import parse_srt, normalize_text, find_matches, format_srt_entry, calculate_exact_timestamps, \
    sort_subtitles_by_time


def analyze_phrases(subtitles, phrases, threshold):
    results = {}
    phrase_counts = {}
    not_found_phrases = []
    partial_matches = []
    selected_results = {}

    # Подсчет дубликатов фраз
    for phrase in phrases:
        norm_phrase = normalize_text(phrase)
        phrase_counts[norm_phrase] = phrase_counts.get(norm_phrase, 0) + 1

    # Анализ совпадений
    for phrase in phrases:
        norm_phrase = normalize_text(phrase)
        matches = []
        for sub in subtitles:
            similarity, matched_phrase, matched_text = find_matches(sub.text, phrase, threshold)
            if similarity >= 0.95:  # Полные и частичные совпадения
                matches.append({
                    'subtitle': sub,
                    'similarity': similarity,
                    'text': matched_text
                })

        if not matches:
            # Предлагаем до 3 наиболее подходящих субтитров для ненайденных фраз
            best_matches = []
            for sub in subtitles:
                similarity, _, matched_text = find_matches(sub.text, phrase, 0.0)  # Без порога
                if similarity > 0:
                    best_matches.append({
                        'subtitle': sub,
                        'similarity': similarity,
                        'text': matched_text
                    })
            best_matches.sort(key=lambda x: x['similarity'], reverse=True)
            not_found_phrases.append((phrase, best_matches[:3] if best_matches else []))
        else:
            # Учитываем только уникальные субтитры, если несколько вхождений фразы
            unique_matches = []
            seen_texts = set()
            for match in matches:
                norm_text = normalize_text(match['text'])
                if norm_text not in seen_texts:
                    seen_texts.add(norm_text)
                    unique_matches.append(match)
            if len(unique_matches) > 1:
                results[phrase] = unique_matches
            else:
                selected_results[phrase] = unique_matches[0]

            if 0.95 > max(m['similarity'] for m in matches) >= threshold:
                partial_matches.append((phrase, [m for m in matches if 0.95 > m['similarity'] >= threshold]))

    # Дубли в фразах (информационно)
    phrase_duplicates = {p: c for p, c in phrase_counts.items() if c > 1}

    return {
        'full_matches': selected_results,
        'partial_matches': partial_matches,
        'not_found': not_found_phrases,
        'duplicates': phrase_duplicates,
        'multiple_matches': {k: v for k, v in results.items() if len(v) > 1}
    }


def generate_excerpts(subtitles, phrases, threshold, output_path, selected_matches):
    """Генерирует отрывки с фразами в формате SRT, сортируя по времени."""
    with open(output_path, 'w', encoding='utf-8') as f:
        index = 1
        sorted_matches = []
        for phrase, match_list in selected_matches.items():
            for match in match_list:
                sorted_matches.append((phrase, match['subtitle'], match['text']))
        sorted_matches.sort(key=lambda x: x[1].start.ordinal)

        for phrase, sub, text in sorted_matches:
            f.write(format_srt_entry(index, sub.start, sub.end, text))
            index += 1


def generate_timestamps(subtitles, phrases, threshold, output_path, selected_matches):
    """Генерирует точные таймкоды для фраз в формате SRT, сортируя по времени."""
    with open(output_path, 'w', encoding='utf-8') as f:
        index = 1
        sorted_matches = []
        for phrase, match_list in selected_matches.items():
            for match in match_list:
                start, end = calculate_exact_timestamps(match['subtitle'], phrase)
                sorted_matches.append((phrase, start, end, phrase))
        sorted_matches.sort(key=lambda x: x[1].ordinal)

        for phrase, start, end, text in sorted_matches:
            f.write(format_srt_entry(index, start, end, text))
            index += 1