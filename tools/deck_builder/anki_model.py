# anki_model.py
import genanki
from logger import get_logger


def create_model(deck_type, answer_position="below", spacing=10, front_order=["title", "image", "audio"],
                 back_order=["title", "video", "audio", "image"], css=""):
    logger = get_logger()
    logger.debug(
        f"Создание модели карточек: deck_type={deck_type}, answer_position={answer_position}, spacing={spacing}, front_order={front_order}, back_order={back_order}")

    model_id = 123456789
    fields = [
        {"name": "Russian_Text"}, {"name": "English_Text"}, {"name": "Russian_Audio"},
        {"name": "English_Audio"}, {"name": "Image"}, {"name": "Video"},
    ]
    base_css = f"""
.card {{ font-family: Arial; font-size: 20px; text-align: center; color: black; background-color: white; }}
.text, .image, .audio, .video {{ margin: {spacing}px 0; }}
img, video {{ max-width: 100%; height: auto; display: inline-block; }}
"""
    combined_css = base_css + "\n" + css

    autoplay_script_back = """
<script>
    var audio = document.querySelector('.back .audio audio');
    if (audio) {
        // Запускаем аудио, как только пользователь взаимодействует со страницей
        // или когда оно становится видимым, в зависимости от версии Anki
        setTimeout(function() { audio.play(); }, 100);
    }
</script>
"""

    # --- КЛЮЧЕВЫЕ ИЗМЕНЕНИЯ В ЛОГИКЕ ---
    # Эта функция теперь напрямую сопоставляет выбранный элемент с полем Anki
    def build_template(order):
        template = ""
        for element in order:
            if element == "ru_text":
                template += '<div class="text">{{Russian_Text}}</div>'
            elif element == "en_text":
                template += '<div class="text">{{English_Text}}</div>'
            elif element == "image":
                template += '<div class="image">{{Image}}</div>'
            elif element == "ru_audio":
                template += '<div class="audio">{{Russian_Audio}}</div>'
            elif element == "en_audio":
                template += '<div class="audio">{{English_Audio}}</div>'
            elif element == "video":
                template += '<div class="video">{{Video}}</div>'
        return template

    # --- КОНЕЦ КЛЮЧЕВЫХ ИЗМЕНЕНИЙ ---

    # Формируем лицевую и оборотную стороны
    qfmt_content_ru = build_template(front_order)
    afmt_content_ru = build_template(back_order)

    qfmt_content_en = build_template(front_order)
    afmt_content_en = build_template(back_order)

    # В зависимости от типа колоды, возможно, понадобится поменять местами ru/en
    # Но с текущей гибкой настройкой это менее актуально, т.к. пользователь сам все выбирает.
    # Оставляем логику для "mixed" типа.
    qfmt_ru_to_en = build_template(front_order)
    afmt_ru_to_en = "{{FrontSide}}" + f'<hr id=answer style="margin: {spacing}px 0;">' + build_template(
        back_order) + autoplay_script_back

    # Для mixed типа, вторая карточка (En->Ru) просто меняет местами поля, которые пользователь указал
    qfmt_en_to_ru = build_template(back_order)
    afmt_en_to_ru = "{{FrontSide}}" + f'<hr id=answer style="margin: {spacing}px 0;">' + build_template(
        front_order) + autoplay_script_back

    if deck_type == "front-back":
        templates = [{"name": "Front to Back", "qfmt": qfmt_ru_to_en, "afmt": afmt_ru_to_en}]
    elif deck_type == "back-front":
        templates = [{"name": "Back to Front", "qfmt": qfmt_en_to_ru, "afmt": afmt_en_to_ru}]
    else:  # mixed
        templates = [
            {"name": "Front to Back", "qfmt": qfmt_ru_to_en, "afmt": afmt_ru_to_en},
            {"name": "Back to Front", "qfmt": qfmt_en_to_ru, "afmt": afmt_en_to_ru}
        ]

    logger.debug(f"Созданы шаблоны для колоды: {deck_type}")

    return genanki.Model(model_id, "Language Card v2", fields=fields, templates=templates, css=combined_css)