# gui/main_window.py
from PyQt5.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                             QLineEdit, QPushButton, QTabWidget, QMessageBox)
from PyQt5.QtCore import Qt
from services.gemini_api import test_gemini_connection


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("AnkiForge - Мастер Создания Колоды")
        self.resize(800, 600)
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.layout = QVBoxLayout(self.central_widget)

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

    def setup_tab1(self):
        layout = QVBoxLayout(self.tab1)
        layout.setAlignment(Qt.AlignTop)

        api_layout = QHBoxLayout()
        api_label = QLabel("Ключ Gemini API:")
        self.api_key_input = QLineEdit()
        self.api_key_input.setPlaceholderText("Введите ваш ключ API от Google AI Studio")
        self.api_key_input.setEchoMode(QLineEdit.Password)

        self.test_api_button = QPushButton("Проверить соединение")
        self.test_api_button.clicked.connect(self.on_test_api_connection)

        api_layout.addWidget(api_label)
        api_layout.addWidget(self.api_key_input)
        api_layout.addWidget(self.test_api_button)

        layout.addLayout(api_layout)

        self.api_status_label = QLabel("Статус: Не проверено")
        layout.addWidget(self.api_status_label)

    def on_test_api_connection(self):
        api_key = self.api_key_input.text()
        self.api_status_label.setText("Статус: Проверка...")

        success, message = test_gemini_connection(api_key)

        if success:
            self.api_status_label.setStyleSheet("color: green;")
            self.api_status_label.setText(f"Статус: ✔️ {message}")
        else:
            self.api_status_label.setStyleSheet("color: red;")
            self.api_status_label.setText(f"Статус: ❌ {message}")
            QMessageBox.critical(self, "Ошибка соединения", message)