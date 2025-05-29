from utils import parse_srt, normalize_text, find_matches, format_srt_entry, calculate_exact_timestamps, sort_subtitles_by_time
import re

def analyze_phrases(subtitles, english_phrases, russian_phrases, threshold, stop_words=None):
    results = {}
    phrase_counts = {}
    not_found_phrases = []
    partial_matches = []
    selected_results = {}
    unique_phrases = set()
    phrase_order = []

    # Исключаем дубли фраз до поиска
    unique_phrase_pairs = list(dict.fromkeys(zip(english_phrases, russian_phrases)))
    english_phrases, russian_phrases = zip(*unique_phrase_pairs) if unique_phrase_pairs else ([], [])
    phrase_pairs = list(zip(english_phrases, russian_phrases))

    # Подсчет дублей фраз
    for phrase in english_phrases:
        norm_phrase = normalize_text(phrase)
        phrase_counts[norm_phrase] = phrase_counts.get(norm_phrase, 0) + 1
        if phrase not in unique_phrases:
            unique_phrases.add(phrase)
            phrase_order.append(phrase)

    if len(english_phrases) != len(russian_phrases):
        raise ValueError("Количество английских и русских фраз должно совпадать")

    # Исключаем дубли субтитров
    unique_subtitles = []
    seen_texts = set()
    for sub in subtitles:
        norm_text = normalize_text(sub.text)
        if norm_text not in seen_texts:
            seen_texts.add(norm_text)
            unique_subtitles.append(sub)

    # Поиск совпадений
    for eng_phrase, rus_phrase in phrase_pairs:
        norm_phrase = normalize_text(eng_phrase)
        matches = []
        seen_texts.clear()  # Очищаем для каждой фразы
        for sub in unique_subtitles:
            similarity, matched_phrase, matched_text = find_matches(sub.text, eng_phrase, threshold, stop_words)
            if similarity >= 0.95 and matched_text not in seen_texts:
                matches.append({
                    'subtitle': sub,
                    'similarity': similarity,
                    'text': sub.text,
                    'rus_phrase': rus_phrase
                })
                seen_texts.add(matched_text)
            elif 0.5 <= similarity < 0.95 and matched_text not in seen_texts:
                matches.append({
                    'subtitle': sub,
                    'similarity': similarity,
                    'text': sub.text,
                    'rus_phrase': rus_phrase
                })
                seen_texts.add(matched_text)

        if not matches:
            # Проверяем пересечение слов длиннее 2 букв (исключая стоп-слова)
            def get_valid_words(text):
                words = re.sub(r'[^\w\s\']', '', text.lower()).split()
                return set(w for w in words if len(w) > 2 and w not in stop_words)

            phrase_words = get_valid_words(eng_phrase)
            has_overlap = False
            for sub in unique_subtitles:
                sub_words = get_valid_words(sub.text)
                if phrase_words & sub_words:  # Есть пересечение
                    has_overlap = True
                    break

            if not has_overlap:
                not_found_phrases.append((eng_phrase, rus_phrase, [{
                    'subtitle': None,
                    'similarity': 0.0,
                    'text': "нет ни одного совпадающего слова",
                    'rus_phrase': rus_phrase
                }]))
            else:
                best_matches = []
                seen_texts.clear()
                for sub in unique_subtitles:
                    similarity, _, matched_text = find_matches(sub.text, eng_phrase, 0.0, stop_words)
                    if similarity > 0 and matched_text not in seen_texts:
                        best_matches.append({
                            'subtitle': sub,
                            'similarity': similarity,
                            'text': matched_text,
                            'rus_phrase': rus_phrase
                        })
                        seen_texts.add(matched_text)
                best_matches.sort(key=lambda x: x['similarity'], reverse=True)
                not_found_phrases.append((eng_phrase, rus_phrase, best_matches[:3]))
        else:
            unique_matches = []
            seen_texts.clear()
            for match in matches:
                norm_text = normalize_text(match['text'])
                if norm_text not in seen_texts:
                    seen_texts.add(norm_text)
                    unique_matches.append(match)
            if len(unique_matches) > 1:
                results[eng_phrase] = unique_matches
            else:
                selected_results[eng_phrase] = unique_matches[0]

            partial = [m for m in unique_matches if 0.5 <= m['similarity'] < 0.95]
            if partial:
                partial_matches.append((eng_phrase, rus_phrase, partial))

    # Сортировка частичных совпадений по схожести
    partial_matches.sort(key=lambda x: max(m['similarity'] for m in x[2]), reverse=True)

    # Подсчет дублей для вывода
    phrase_duplicates = {p: c for p, c in phrase_counts.items() if c > 1}

    return {
        'full_matches': selected_results,
        'partial_matches': partial_matches,
        'not_found': not_found_phrases,
        'duplicates': phrase_duplicates,
        'multiple_matches': {k: v for k, v in results.items() if len(v) > 1},
        'total_unique_phrases': len(unique_phrases),
        'phrase_order': phrase_order
    }

def generate_excerpts(subtitles, phrases, threshold, output_path, selected_matches):
    with open(output_path, 'w', encoding='utf-8') as f:
        index = 1
        sorted_matches = []
        for phrase, match_list in selected_matches.items():
            for match in match_list:
                sorted_matches.append((phrase, match['subtitle'], match['text']))  # Используем текст из selected
        sorted_matches.sort(key=lambda x: x[1].start.ordinal)

        for phrase, sub, text in sorted_matches:
            f.write(format_srt_entry(index, sub.start, sub.end, text))  # Записываем текст из таблицы
            index += 1

def generate_timestamps(subtitles, phrases, threshold, output_path, selected_matches):
    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            index = 1
            sorted_matches = []
            for phrase, match_list in selected_matches.items():
                for match in match_list:
                    subtitle = match['subtitle']
                    start, end = calculate_exact_timestamps(subtitle, phrase)
                    sorted_matches.append((phrase, start, end, phrase))
            sorted_matches.sort(key=lambda x: x[1].ordinal)

            for phrase, start, end, text in sorted_matches:
                f.write(format_srt_entry(index, start, end, text))
                index += 1
    except Exception as e:
        print(f"Error writing timestamps file: {e}")
        raise