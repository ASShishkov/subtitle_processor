# services/gemini_api.py
import google.generativeai as genai


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