# gui/main_window.py
from PyQt5.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                             QLineEdit, QPushButton, QTabWidget, QMessageBox, QFormLayout)
from PyQt5.QtCore import Qt, QThread
from services.gemini_api import test_gemini_connection
from gui.drop_zone import DropZone
from core.processing import ProcessingWorker # Убедитесь, что импорт правильный


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("AnkiForge - Мастер Создания Колоды")
        self.resize(800, 600)
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.layout = QVBoxLayout(self.central_widget)

        self.project_files = {"video": None, "srt": None}
        self.processing_thread = None
        self.processing_worker = None
        self.extracted_data = None  # Для хранения данных от API

        self.tabs = QTabWidget()
        self.layout.addWidget(self.tabs)

        self.tab1 = QWidget()
        self.tab2 = QWidget()
        self.tab3 = QWidget()
        self.tab4 = QWidget()

        self.tabs.addTab(self.tab1, "1. Проект и Ресурсы")
        self.tabs.addTab(self.tab2, "2. Редактирование")
        self.tabs.addTab(self.tab3, "3. Конструктор Колод")
        self.tabs.addTab(self.tab4, "4. Генерация")

        self.tabs.setTabEnabled(1, False)
        self.tabs.setTabEnabled(2, False)
        self.tabs.setTabEnabled(3, False)

        self.setup_tab1()
        self.setup_tab2()  # Создадим заглушку для второй вкладки

    def setup_tab1(self):
        layout = QVBoxLayout(self.tab1)
        layout.setAlignment(Qt.AlignTop)

        form_layout = QFormLayout()

        self.project_name_input = QLineEdit()
        self.project_name_input.setPlaceholderText("Например: Breaking_Bad_S01E01")
        self.project_name_input.textChanged.connect(self.check_if_ready_to_start)
        form_layout.addRow(QLabel("Название проекта:"), self.project_name_input)

        self.api_key_input = QLineEdit()
        self.api_key_input.setPlaceholderText("Введите ваш ключ API")
        self.api_key_input.setEchoMode(QLineEdit.Password)
        api_hbox = QHBoxLayout()
        api_hbox.addWidget(self.api_key_input)
        self.test_api_button = QPushButton("Проверить")
        self.test_api_button.clicked.connect(self.on_test_api_connection)
        api_hbox.addWidget(self.test_api_button)
        form_layout.addRow(QLabel("Ключ Gemini API:"), api_hbox)

        self.api_status_label = QLabel("Статус: Не проверено")
        form_layout.addRow("", self.api_status_label)

        layout.addLayout(form_layout)

        drop_zones_layout = QHBoxLayout()
        self.video_drop_zone = DropZone("Перетащите сюда видеофайл\n(mp4, mkv...)")
        self.video_drop_zone.fileDropped.connect(lambda path: self.on_file_dropped("video", path))
        self.srt_drop_zone = DropZone("Перетащите сюда файл субтитров\n(srt)")
        self.srt_drop_zone.fileDropped.connect(lambda path: self.on_file_dropped("srt", path))
        drop_zones_layout.addWidget(self.video_drop_zone)
        drop_zones_layout.addWidget(self.srt_drop_zone)
        layout.addLayout(drop_zones_layout)

        self.start_processing_button = QPushButton("▶️ Начать обработку")
        self.start_processing_button.setFixedHeight(40)
        self.start_processing_button.setStyleSheet("font-size: 16px; background-color: #ccc;")
        self.start_processing_button.setEnabled(False)
        self.start_processing_button.clicked.connect(self.on_start_processing)  # *** НОВЫЙ КОД ***
        layout.addStretch()
        layout.addWidget(self.start_processing_button)

    # *** НОВЫЙ МЕТОД ***
    def setup_tab2(self):
        """Создает базовую структуру для второй вкладки."""
        layout = QVBoxLayout(self.tab2)
        self.tab2_label = QLabel("Здесь будут отображены результаты обработки от AI.")
        self.tab2_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.tab2_label)
        # В будущем здесь будет таблица для редактирования

    def on_file_dropped(self, file_type, filepath):
        print(f"Файл получен: Тип='{file_type}', Путь='{filepath}'")
        self.project_files[file_type] = filepath
        self.check_if_ready_to_start()

    def on_test_api_connection(self):
        api_key = self.api_key_input.text()
        self.api_status_label.setText("Статус: Проверка...")
        self.api_status_label.setStyleSheet("color: black;")
        success, message = test_gemini_connection(api_key)
        if success:
            self.api_status_label.setStyleSheet("color: green;")
            self.api_status_label.setText(f"Статус: ✔️ {message}")
        else:
            self.api_status_label.setStyleSheet("color: red;")
            self.api_status_label.setText(f"Статус: ❌ {message}")
            QMessageBox.critical(self, "Ошибка соединения", message)
        self.check_if_ready_to_start()

    def check_if_ready_to_start(self):
        # Проверяем, не идет ли уже обработка
        if self.processing_thread and self.processing_thread.isRunning():
            return

        project_name_ok = bool(self.project_name_input.text())
        api_ok = "✔️" in self.api_status_label.text()
        video_ok = self.project_files["video"] is not None
        srt_ok = self.project_files["srt"] is not None

        if project_name_ok and api_ok and video_ok and srt_ok:
            self.start_processing_button.setEnabled(True)
            self.start_processing_button.setStyleSheet("font-size: 16px; background-color: #4CAF50; color: white;")
        else:
            self.start_processing_button.setEnabled(False)
            self.start_processing_button.setStyleSheet("font-size: 16px; background-color: #ccc;")

    # *** НОВЫЕ МЕТОДЫ НИЖЕ ***

    def on_start_processing(self):
        """Запускает фоновый процесс извлечения лексики."""
        self.start_processing_button.setEnabled(False)
        self.tabs.setTabEnabled(0, False)  # Блокируем текущую вкладку
        self.start_processing_button.setText("Идет обработка...")

        self.processing_thread = QThread()
        self.processing_worker = ProcessingWorker(
            api_key=self.api_key_input.text(),
            srt_path=self.project_files["srt"]
        )
        self.processing_worker.moveToThread(self.processing_thread)

        # Подключаем сигналы
        self.processing_thread.started.connect(self.processing_worker.run)
        self.processing_worker.finished.connect(self.on_processing_finished)
        self.processing_worker.error.connect(self.on_processing_error)
        self.processing_worker.progress.connect(lambda msg: self.start_processing_button.setText(msg))

        # Очистка после завершения
        self.processing_worker.finished.connect(self.processing_thread.quit)
        self.processing_worker.finished.connect(self.processing_worker.deleteLater)
        self.processing_thread.finished.connect(self.processing_thread.deleteLater)

        self.processing_thread.start()

    def on_processing_finished(self, result):
        """Обрабатывает успешное завершение извлечения лексики."""
        print("Обработка завершена. Результат:", result)
        self.extracted_data = result

        # TODO: Реализовать полноценное наполнение второй вкладки
        # Например, передать self.extracted_data в метод setup_tab2
        self.tab2_label.setText(
            f"Получено {len(self.extracted_data.get('vocabulary', []))} записей. Готово к редактированию.")

        self.tabs.setTabEnabled(1, True)  # Разблокируем вторую вкладку
        self.tabs.setCurrentIndex(1)  # Переключаемся на нее

        # Сбрасываем состояние кнопки и первой вкладки (на случай, если пользователь вернется)
        self.start_processing_button.setText("▶️ Начать обработку")
        self.tabs.setTabEnabled(0, True)
        self.check_if_ready_to_start()

    def on_processing_error(self, error_message):
        """Обрабатывает ошибку во время извлечения лексики."""
        QMessageBox.critical(self, "Ошибка обработки", error_message)

        # Возвращаем интерфейс в исходное состояние
        self.start_processing_button.setText("▶️ Начать обработку")
        self.tabs.setTabEnabled(0, True)
        self.check_if_ready_to_start()