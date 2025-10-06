# services/gemini_api.py
import google.generativeai as genai
import json


def test_gemini_connection(api_key: str) -> (bool, str):
    """Проверяет соединение с Gemini API."""
    if not api_key:
        return False, "API ключ не может быть пустым."
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-pro')
        response = model.generate_content("Say 'Hello, Gemini is working!'")

        if "Hello, Gemini is working!" in response.text:
            return True, "Соединение с Gemini API успешно установлено!"
        else:
            return False, f"Получен неожиданный ответ: {response.text}"
    except Exception as e:
        return False, f"Ошибка соединения: {str(e)}"


def extract_vocabulary_from_srt(api_key: str, srt_content: str) -> dict:
    """
    Извлекает лексику из текста субтитров с помощью Gemini API.

    Args:
        api_key: Ключ для доступа к Gemini API.
        srt_content: Текст SRT-файла в виде одной строки.

    Returns:
        Словарь с извлеченной лексикой или словарь с ошибкой.
    """
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-pro')

        prompt = f"""
        Analyze the following Russian subtitles from a movie or TV series. Your task is to act as a language tutor and extract vocabulary suitable for a language learner (level B1-C1).

        Extract the following:
        1.  **Single Words:** Interesting or advanced individual words.
        2.  **Idioms:** Common idioms or fixed expressions.
        3.  **Phrases:** Useful phrases or colloquial expressions.

        For each item, provide:
        - `term`: The Russian word, idiom, or phrase.
        - `translation`: A concise English translation.
        - `type`: "word", "idiom", or "phrase".
        - `example`: The original sentence from the subtitles where the term appeared.

        Return the output as a single valid JSON object with one key "vocabulary", which is a list of these items. Do not include any text or explanations outside of the JSON object.

        Example of the desired output format:
        {{
          "vocabulary": [
            {{
              "term": "чертовщина",
              "translation": "devilry, some weird stuff",
              "type": "word",
              "example": "Что это за чертовщина?"
            }},
            {{
              "term": "надрать задницу",
              "translation": "to kick someone's ass",
              "type": "idiom",
              "example": "Я должен надрать ему задницу за одни такие мысли."
            }},
            {{
              "term": "В чём дело?",
              "translation": "What's the matter?",
              "type": "phrase",
              "example": "В чём дело, сынок?"
            }}
          ]
        }}

        Subtitles text:
        ---
        {srt_content}
        ---
        """

        response = model.generate_content(prompt)

        # Очистка ответа от возможных "```json" и "```"
        cleaned_response_text = response.text.strip().replace("```json", "").replace("```", "").strip()

        parsed_json = json.loads(cleaned_response_text)
        return parsed_json

    except json.JSONDecodeError as e:
        return {"error": f"Ошибка декодирования JSON: {e}", "raw_response": response.text}
    except Exception as e:
        return {"error": f"Неизвестная ошибка Gemini API: {str(e)}"}