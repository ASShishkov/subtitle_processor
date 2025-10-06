# core/processing.py
from PyQt5.QtCore import QObject, pyqtSignal
from services.gemini_api import extract_vocabulary_from_srt
import time


class ProcessingWorker(QObject):
    """
    Worker для выполнения фоновой обработки данных.
    """
    finished = pyqtSignal(dict)  # Сигнал об успешном завершении (передает результат)
    error = pyqtSignal(str)  # Сигнал об ошибке (передает текст ошибки)
    progress = pyqtSignal(str)  # Сигнал для обновления статуса в GUI

    def __init__(self, api_key: str, srt_path: str):
        super().__init__()
        self.api_key = api_key
        self.srt_path = srt_path

    def run(self):
        """Основной метод, выполняющий всю работу."""
        try:
            self.progress.emit("Чтение файла субтитров...")
            with open(self.srt_path, 'r', encoding='utf-8') as f:
                srt_content = f.read()

            if not srt_content:
                self.error.emit("Файл субтитров пуст.")
                return

            self.progress.emit("Запрос к Gemini API... Это может занять некоторое время.")

            # Имитация длительной работы для демонстрации
            # time.sleep(5)

            result = extract_vocabulary_from_srt(self.api_key, srt_content)

            if "error" in result:
                self.error.emit(result["error"])
            else:
                self.progress.emit("Обработка успешно завершена!")
                self.finished.emit(result)

        except FileNotFoundError:
            self.error.emit(f"Файл не найден: {self.srt_path}")
        except Exception as e:
            self.error.emit(f"Критическая ошибка в потоке обработки: {str(e)}")