from utils import parse_srt, normalize_text, find_matches, format_srt_entry, calculate_exact_timestamps, sort_subtitles_by_time
import re

def analyze_phrases(subtitles, english_phrases, russian_phrases, threshold, stop_words=None):
    results = {}  # Для хранения множественных совпадений
    phrase_counts = {}  # Для подсчета дублей
    not_found_phrases = []  # Ненайденные фразы
    partial_matches = []  # Частичные совпадения
    selected_results = {}  # Полные совпадения
    unique_phrases = set()  # Уникальные фразы для порядка
    phrase_order = []  # Порядок фраз
    processed_phrases = set()  # Отслеживание обработанных фраз

    # Исключаем дубли фраз до поиска
    unique_phrase_pairs = list(dict.fromkeys(zip(english_phrases, russian_phrases)))
    english_phrases, russian_phrases = zip(*unique_phrase_pairs) if unique_phrase_pairs else ([], [])
    phrase_pairs = list(zip(english_phrases, russian_phrases))

    # Подсчет дублей фраз
    for phrase in english_phrases:
        phrase_counts[phrase] = phrase_counts.get(phrase, 0) + 1
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
        if eng_phrase in processed_phrases:
            continue

        norm_phrase = normalize_text(eng_phrase)
        matches = []
        seen_texts.clear()

        # Поиск совпадений по всем субтитрам
        for sub in unique_subtitles:
            similarity, matched_phrase, matched_text = find_matches(sub.text, eng_phrase, threshold, stop_words)
            if similarity >= 0.5 and matched_text not in seen_texts:
                matches.append({
                    'subtitle': sub,
                    'similarity': similarity,
                    'text': sub.text,
                    'rus_phrase': rus_phrase
                })
                seen_texts.add(matched_text)

        # Сортируем совпадения по убыванию схожести
        matches.sort(key=lambda x: x['similarity'], reverse=True)

        if not matches:
            # Проверяем пересечение слов длиннее 2 букв
            def get_valid_words(text):
                words = re.sub(r'[^\w\s\'-]', ' ', text.lower()).split()
                return set(w for w in words if len(w) > 2 and w not in stop_words)

            phrase_words = get_valid_words(eng_phrase)
            has_overlap = False
            for sub in unique_subtitles:
                sub_words = get_valid_words(sub.text)
                if phrase_words & sub_words:
                    has_overlap = True
                    break

            if not has_overlap:
                not_found_phrases.append((eng_phrase, rus_phrase, [{
                    'subtitle': None,
                    'similarity': 0.0,
                    'text': "нет ни одного совпадающего слова",
                    'rus_phrase': rus_phrase
                }]))
                processed_phrases.add(eng_phrase)
        else:
            # Удаляем дубли совпадений
            unique_matches = []
            seen_texts.clear()
            for match in matches:
                norm_text = normalize_text(match['text'])
                if norm_text not in seen_texts:
                    seen_texts.add(norm_text)
                    unique_matches.append(match)

            # Выбираем лучшее совпадение
            best_match = unique_matches[0]
            if best_match['similarity'] >= 0.95:
                selected_results[eng_phrase] = best_match
                processed_phrases.add(eng_phrase)
            elif 0.5 <= best_match['similarity'] < 0.95:
                partial_matches.append((eng_phrase, rus_phrase, unique_matches[:3]))
                processed_phrases.add(eng_phrase)

            if len(unique_matches) > 1:
                results[eng_phrase] = unique_matches[:3]

    # Добавляем все нераспределенные фразы в ненайденные
    for eng_phrase, rus_phrase in phrase_pairs:
        if eng_phrase not in processed_phrases:
            not_found_phrases.append((eng_phrase, rus_phrase, [{
                'subtitle': None,
                'similarity': 0.0,
                'text': "нет ни одного совпадающего слова",
                'rus_phrase': rus_phrase
            }]))
            processed_phrases.add(eng_phrase)

    # Сортировка частичных совпадений по схожести
    partial_matches.sort(key=lambda x: max(m['similarity'] for m in x[2]), reverse=True)

    # Подсчет дублей для вывода
    phrase_duplicates = {p: c for p, c in phrase_counts.items() if c > 1}

    return {
        'full_matches': selected_results,
        'partial_matches': partial_matches,
        'not_found': not_found_phrases,
        'duplicates': phrase_duplicates,
        'multiple_matches': results,
        'total_unique_phrases': len(unique_phrases),
        'phrase_order': phrase_order
    }

def generate_excerpts(subtitles, phrases, threshold, output_path, selected_matches):
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