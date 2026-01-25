# logger.py
import logging
import sys
import os

def init_logger(log_to_file=True, log_file="logs/app.log", gui_log_callback=None):
    logger = logging.getLogger("AnkiApp")
    logger.setLevel(logging.INFO)
    logger.handlers.clear()  # Очищаем старые обработчики

    formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    if log_to_file:
        os.makedirs(os.path.dirname(log_file), exist_ok=True)
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    if gui_log_callback:
        class GuiHandler(logging.Handler):
            def emit(self, record):
                msg = self.format(record)
                try:
                    gui_log_callback(msg)
                except Exception as e:
                    print(f"Ошибка в gui_log_callback: {e}")
        gui_handler = GuiHandler()
        gui_handler.setFormatter(formatter)
        logger.addHandler(gui_handler)

    return logger

def get_logger():
    return logging.getLogger("AnkiApp")