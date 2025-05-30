import sys
import configparser
import threading
import os
import logging
import subprocess  # Добавлено
from PyQt5.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
                             QFrame, QProgressBar, QCheckBox, QComboBox, QSlider, QTableView, QMenu,
                             QApplication, QMessageBox, QFileDialog, QStyledItemDelegate, QAbstractItemView, QInputDialog)  # Добавлен QInputDialog
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QStandardItemModel, QStandardItem, QFont, QColor
from subtitle_processor import analyze_phrases, generate_excerpts, generate_timestamps
from utils import parse_srt
import pysrt
from PyQt5.QtWidgets import QSizePolicy

class ComboBoxDelegate(QStyledItemDelegate):
    def __init__(self, parent=None):
        super().__init__(parent)

    def createEditor(self, parent, option, index):
        combo = QComboBox(parent)
        combo.addItem("Ничего не выбирать")
        # Динамически добавляем субтитры (например, до 3 вариантов)
        for i in range(1, 4):  # Максимум 3 субтитра
            combo.addItem(f"Субтитр {i}")
        combo.currentTextChanged.connect(lambda: self.commitData.emit(combo))
        return combo

    def setEditorData(self, editor, index):
        value = index.model().data(index, Qt.DisplayRole)
        if value in ["Субтитр 1", "Субтитр 2", "Субтитр 3", "Ничего не выбирать"]:
            editor.setCurrentText(value)
        else:
            editor.setCurrentText("Ничего не выбирать")

    def setModelData(self, editor, model, index):
        model.setData(index, editor.currentText(), Qt.DisplayRole)

    def updateEditorGeometry(self, editor, option, index):
        editor.setGeometry(option.rect)

class SubtitleFilterApp(QMainWindow):


    def __init__(self, parent=None):
        print("=== ИНИЦИАЛИЗАЦИЯ НАЧАЛАСЬ ===")
        super().__init__(parent)
        print("1. super().__init__ выполнен")
        self.setWindowTitle("Фильтрация субтитров")
        print("2. Заголовок окна установлен")
        # Устанавливаем минимальный размер окна
        self.setMinimumSize(600, 400)

        # Устанавливаем начальный размер (меньше чем было)
        self.resize(950, 800)

        # Позиционируем окно в центре экрана
        self.center_window()

        print("3. Размер и позиция окна установлены")

        self.config = configparser.ConfigParser()
        print("4. ConfigParser создан")

        self.is_running = False
        self.selected_matches = {}
        self.phrase_groups = {}
        self.phrase_order = []
        self.potential_count = 0
        self.modified_subs = None  # Добавлено для хранения обновлённых субтитров
        print("5. Переменные инициализированы")

        print("6. Запуск setup_gui...")
        self.setup_gui()
        print("7. setup_gui завершен")

        print("8. Запуск setup_logging...")
        self.setup_logging()
        print("9. setup_logging завершен")

        print("10. Запуск load_config...")
        self.load_config()
        print("11. load_config завершен")
        print("=== ИНИЦИАЛИЗАЦИЯ ЗАВЕРШЕНА ===")

    def on_single_click(self, index):
        print(f"Single click on index: row={index.row()}, col={index.column()}")
        if index.column() == 2:  # Колонка "Выбрано?"
            current_state = self.table_model.data(index, Qt.CheckStateRole)
            print(f"Current state: {current_state}")
            new_state = Qt.CheckState.Unchecked if current_state == Qt.CheckState.Checked else Qt.CheckState.Checked
            phrase = self.table_model.index(index.row(), 0).data()
            print(f"Switching state to {new_state} for phrase: {phrase}")
            self._set_selection((phrase, self.table_model.index(index.row(), 1).data()), index.row(),
                                new_state == Qt.CheckState.Checked)
    def center_window(self):
        """Центрирует окно на экране"""
        try:
            from PyQt5.QtWidgets import QDesktopWidget

            # Получаем размеры экрана
            desktop = QDesktopWidget()
            screen_geometry = desktop.screenGeometry()

            # Получаем размеры окна
            window_geometry = self.geometry()
        # ... (остальной код без изменений)

            # Вычисляем позицию для центрирования
            x = (screen_geometry.width() - window_geometry.width()) // 2
            y = (screen_geometry.height() - window_geometry.height()) // 2

            # Устанавливаем позицию
            self.move(x, y)

            print(
                f"Окно центрировано: экран {screen_geometry.width()}x{screen_geometry.height()}, окно на позиции ({x}, {y})")

        except Exception as e:
            print(f"Ошибка при центрировании окна: {e}")
            # Фолбэк - просто устанавливаем фиксированную позицию
            self.move(100, 100)

    def setup_gui(self):
        from PyQt5.QtWidgets import QSizePolicy

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(5)  # Минимальные отступы

        # --- Верхний layout для файлов и кнопок ---
        top_layout = QHBoxLayout()
        main_layout.addLayout(top_layout)

        # --- БЛОК ФАЙЛОВ ---
        files_frame = QFrame()
        files_layout = QVBoxLayout(files_frame)
        files_layout.setAlignment(Qt.AlignLeft)

        labels = [
            "Путь к субтитрам (SRT):",
            "Путь к файлу английских фраз (TXT):",
            "Путь к файлу русских фраз (TXT):",
            "Папка вывода:",
            "Имя выходного файла:"
        ]
        self.path_vars = [QLineEdit() for _ in range(5)]
        self.path_vars[4].setText("episodes")

        for i, label_text in enumerate(labels):
            row_layout = QHBoxLayout()
            label = QLabel(label_text)
            label.setMinimumWidth(200)
            label.setAlignment(Qt.AlignLeft)
            entry = self.path_vars[i]
            entry.setFixedWidth(450)  # Фиксированная ширина для всех полей
            entry.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
            browse_button = QPushButton("Обзор")
            browse_button.setFixedSize(100, 30)  # Фиксированный размер кнопок
            browse_button.clicked.connect(lambda checked, idx=i: self.browse_file(idx))
            row_layout.addWidget(label)
            row_layout.addWidget(entry)
            row_layout.addWidget(browse_button)
            row_layout.setAlignment(Qt.AlignLeft)
            files_layout.addLayout(row_layout)

        top_layout.addWidget(files_frame)

        # --- НАСТРОЙКИ И КНОПКИ ---
        self.options_actions_frame = QFrame()
        options_actions_layout = QHBoxLayout(self.options_actions_frame)

        # Чекбоксы
        options_frame = QFrame()
        options_layout = QVBoxLayout(options_frame)
        options_frame.setFrameShape(QFrame.StyledPanel)
        options_frame.setStyleSheet("QFrame { border: 1px solid #ccc; padding: 5px; }")

        self.save_paths = QCheckBox("Сохранять пути")
        self.save_paths.setChecked(True)
        self.save_paths.setFixedWidth(200)  # Одинаковая ширина
        self.enable_logging = QCheckBox("Включить логирование")
        self.enable_logging.setChecked(True)
        self.enable_logging.setFixedWidth(200)
        self.show_matches = QCheckBox("Показать соответствия")
        self.show_matches.setFixedWidth(200)

        sort_label = QLabel("Сортировка:")
        sort_label.setFixedWidth(200)
        self.sort_option = QComboBox()
        self.sort_option.addItems(["time", "file"])
        self.sort_option.setFixedWidth(200)  # Одинаковая ширина
        self.sort_option.currentTextChanged.connect(self.update_sorting)

        self.match_threshold = QSlider(Qt.Horizontal)
        self.match_threshold.setRange(50, 100)
        self.match_threshold.setValue(80)
        self.match_threshold.setFixedWidth(200)

        options_layout.addWidget(self.save_paths)
        options_layout.addWidget(self.enable_logging)
        options_layout.addWidget(self.show_matches)
        options_layout.addWidget(sort_label)
        options_layout.addWidget(self.sort_option)
        options_layout.setAlignment(Qt.AlignLeft)

        # Кнопки
        actions_frame = QFrame()
        actions_layout = QVBoxLayout(actions_frame)
        actions_frame.setFrameShape(QFrame.StyledPanel)
        actions_frame.setStyleSheet("QFrame { border: 1px solid #ccc; padding: 5px; }")

        buttons = [
            QPushButton("Найти совпадения", clicked=self.check_phrases),
            QPushButton("Получить отрывки", clicked=self.find_excerpts),
            QPushButton("Таймкоды", clicked=self.get_timestamps),
            QPushButton("Очистить", clicked=self.clear_fields),
            QPushButton("Найти вручную", clicked=self.manual_find_phrase),
            QPushButton("Изменить таймкоды", clicked=self.modify_timestamps)
        ]

        for button in buttons:
            button.setFixedSize(160, 30)  # Уменьшенный фиксированный размер
            actions_layout.addWidget(button)

        self.adjust_row_height = QCheckBox("Высота по содержимому")
        self.adjust_row_height.setChecked(False)
        self.adjust_row_height.setFixedWidth(160)
        self.adjust_row_height.stateChanged.connect(self.update_row_height)
        actions_layout.addWidget(self.adjust_row_height)
        actions_layout.setAlignment(Qt.AlignLeft)

        options_actions_layout.addWidget(options_frame)
        options_actions_layout.addWidget(actions_frame)
        options_actions_layout.setAlignment(Qt.AlignLeft)

        # Изначально добавляем options_actions_frame в main_layout
        self.is_maximized = False
        main_layout.addWidget(self.options_actions_frame)

        # --- Таблица ---
        self.table_frame = QFrame()
        table_layout = QVBoxLayout(self.table_frame)
        self.table_model = QStandardItemModel()
        self.table_model.setHorizontalHeaderLabels(["Фраза", "Субтитр", "Выбрано?", "Русская фраза"])

        self.table_view = QTableView()
        self.table_view.setModel(self.table_model)
        self.table_view.setSelectionBehavior(QTableView.SelectRows)
        self.table_view.setSelectionMode(QTableView.MultiSelection)
        self.table_view.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table_view.customContextMenuRequested.connect(self.show_context_menu)
        self.table_view.setEditTriggers(QAbstractItemView.AllEditTriggers)
        self.table_view.clicked.connect(self.on_single_click)
        table_layout.addWidget(self.table_view)

        self.table_view.setStyleSheet("QTableView { margin: 0px; padding: 0px; border: 0px; }")
        self.table_view.setContentsMargins(0, 0, 0, 0)
        self.table_view.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.table_view.setHorizontalScrollMode(QTableView.ScrollPerPixel)

        self.update_column_widths()

        main_layout.addWidget(self.table_frame, stretch=2)

        self.progress = QProgressBar()
        self.progress.setMaximum(100)
        main_layout.addWidget(self.progress)

        self.status_label = QLabel("Готов")
        self.status_label.setStyleSheet("color: green")
        main_layout.addWidget(self.status_label)

        self.potential_label = QLabel("Потенциальных отрывков: 0")
        main_layout.addWidget(self.potential_label)

        self.resize_timer = QTimer()
        self.resize_timer.timeout.connect(self.update_column_widths)
        self.resize_timer.start(100)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        # Определяем, развернуто ли окно или его ширина больше 1000 px
        new_maximized = self.isMaximized() or self.width() > 1000
        if new_maximized != self.is_maximized:
            self.is_maximized = new_maximized
            # Удаляем options_actions_frame из текущего layout
            main_layout = self.centralWidget().layout()
            top_layout = main_layout.itemAt(0).layout()
            if self.is_maximized:
                # Перемещаем в top_layout
                main_layout.removeWidget(self.options_actions_frame)
                top_layout.addWidget(self.options_actions_frame)
                top_layout.addStretch()  # Растяжка слева
                top_layout.setAlignment(self.options_actions_frame, Qt.AlignRight | Qt.AlignTop)
                # Увеличиваем stretch таблицы
                main_layout.addWidget(self.table_frame, stretch=4)
            else:
                # Возвращаем в main_layout
                top_layout.removeWidget(self.options_actions_frame)
                top_layout.takeAt(top_layout.count() - 1)  # Удаляем stretch
                main_layout.insertWidget(1, self.options_actions_frame)
                main_layout.addWidget(self.table_frame, stretch=2)

    def update_column_widths(self):
        # Получаем ширину видимой области таблицы (viewport)
        viewport_width = self.table_view.viewport().width()
        if viewport_width > 0:
            # Учитываем ширину вертикальной полосы прокрутки, если она видима
            scrollbar_width = self.table_view.verticalScrollBar().width() if self.table_view.verticalScrollBar().isVisible() else 0
            available_width = viewport_width - scrollbar_width

            # Устанавливаем ширину колонок пропорционально
            col1_width = int(available_width * 0.35)  # Фраза
            col2_width = int(available_width * 0.35)  # Субтитр
            col4_width = int(available_width * 0.20)  # Русская фраза

            # Общая ширина трёх колонок
            used_width = col1_width + col2_width + col4_width
            remaining_width = available_width - used_width

            # Корректируем ширину, если места не хватает
            if remaining_width < 0:
                col1_width = int(available_width * 0.37)
                col2_width = int(available_width * 0.37)
                col4_width = int(available_width * 0.22)
                remaining_width = available_width - col1_width - col2_width - col4_width

            self.table_view.setColumnWidth(0, col1_width)  # Фраза
            self.table_view.setColumnWidth(1, col2_width)  # Субтитр
            self.table_view.setColumnWidth(2, max(remaining_width, 10))  # Выбор (минимальная ширина 10 пикселей)
            self.table_view.setColumnWidth(3, col4_width)  # Русская фраза

            # Принудительное обновление, чтобы избежать визуальных артефактов
            self.table_view.update()

    def update_row_height(self):
        if self.adjust_row_height.isChecked():
            self.table_view.resizeRowsToContents()
        else:
            for row in range(self.table_model.rowCount()):
                self.table_view.setRowHeight(row, 20)

    def update_threshold(self, value):
        pass  # Логика обновления порога будет в check_phrases

    # 3. В setup_logging добавьте:
    def setup_logging(self):
        print("Настройка логирования...")
        self.logger = logging.getLogger('SubtitleFilterApp')
        self.logger.setLevel(logging.INFO)
        print("Logger создан")

        output_path = self.output_path() or 'output'
        print(f"Output path: {output_path}")

        try:
            if not os.path.exists(output_path):
                os.makedirs(output_path)
                print(f"Создана директория: {output_path}")

            log_file = os.path.join(output_path, 'log.txt')
            print(f"Путь к лог-файлу: {log_file}")

            handler = logging.FileHandler(log_file, encoding='utf-8')
            handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
            self.logger.addHandler(handler)
            print("FileHandler добавлен")
        except Exception as e:
            print(f"Ошибка при настройке логирования: {e}")

    def browse_file(self, idx):
        if idx == 0:
            path, _ = QFileDialog.getOpenFileName(self, "Выберите SRT-файл", filter="SRT files (*.srt)")
            if path:
                self.path_vars[idx].setText(path)
        elif idx in [1, 2]:  # Оба файла фраз
            path, _ = QFileDialog.getOpenFileName(self, "Выберите TXT-файл", filter="Text files (*.txt)")
            if path:
                self.path_vars[idx].setText(path)
        elif idx == 3:
            path = QFileDialog.getExistingDirectory(self, "Выберите папку вывода")
            if path:
                self.path_vars[idx].setText(path)

    def output_path(self):
        return self.path_vars[2].text()

    def load_config(self):
        print("Загрузка конфига...")
        self.stop_words = set([
            "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for", "of", "with", "by",
            "is", "are", "was", "were", "be", "have", "has", "had", "do", "does", "did",
            "will", "would", "shall", "should", "can", "could", "may", "might",
            "don't", "won't", "can't", "didn't", "doesn't", "i'm", "you're", "he's", "she's", "it's",
            "и", "в", "на", "с", "к", "у", "по", "из", "а", "но", "что", "это", "как", "для"
        ])
        if os.path.exists("stop_words.txt"):
            with open("stop_words.txt", "r", encoding="utf-8") as f:
                additional_stop_words = {word.strip().lower() for word in f.read().splitlines() if word.strip()}
                self.stop_words.update(additional_stop_words)
                print("Дополнительные стоп-слова загружены из stop_words.txt")
        if os.path.exists("config.ini"):
            print("Файл config.ini найден")
            try:
                self.config.read("config.ini", encoding='utf-8')
                if "Paths" in self.config:
                    self.path_vars[0].setText(self.config["Paths"].get("subtitles", ""))
                    self.path_vars[1].setText(self.config["Paths"].get("phrases_en", ""))
                    self.path_vars[2].setText(self.config["Paths"].get("phrases_ru", ""))
                    self.path_vars[3].setText(self.config["Paths"].get("output", ""))
                    self.path_vars[4].setText(self.config["Paths"].get("filename", "episodes"))
                if "StopWords" in self.config:
                    self.stop_words.update(set(self.config["StopWords"].get("words", "").split(",")))
            except Exception as e:
                print(f"Ошибка при чтении конфига: {e}")

    def save_config(self):
        if self.save_paths.isChecked():
            self.config["Paths"] = {
                "subtitles": self.path_vars[0].text(),
                "phrases_en": self.path_vars[1].text(),  # Английский файл
                "phrases_ru": self.path_vars[2].text(),  # Русский файл
                "output": self.path_vars[3].text(),
                "filename": self.path_vars[4].text()
            }
            with open("config.ini", "w", encoding="utf-8") as configfile:
                self.config.write(configfile)

    def show_context_menu(self, pos):
        index = self.table_view.indexAt(pos)
        if not index.isValid() or index.column() != 2:  # Столбец "Выбор"
            return

        row = index.row()
        model = self.table_model
        phrase = model.index(row, 0).data()
        subtitle_text = model.index(row, 1).data()
        key = (phrase, subtitle_text)

        # Проверяем, является ли строка ручной
        is_manual = model.index(row, 2).data(Qt.UserRole + 1)

        menu = QMenu()
        menu.addAction("Да", lambda: self._set_selection(key, row, True))
        menu.addAction("Нет", lambda: self._set_selection(key, row, False))
        if is_manual:
            menu.addAction("Удалить строку", lambda: self._delete_row(row, key, phrase))
        menu.exec_(self.table_view.viewport().mapToGlobal(pos))

    def _set_selection(self, key, row, value):
        model = self.table_model
        phrase = model.index(row, 0).data()
        subtitle_text = model.index(row, 1).data()

        # Собираем данные таблицы
        data = [model.index(r, c).data() for r in range(model.rowCount()) for c in range(model.columnCount())]
        data = [data[i:i + 3] for i in range(0, len(data), 3)]

        # Проверяем, находится ли строка в блоке "Ненайденные фразы"
        in_not_found_section = False
        for i in range(row, -1, -1):
            if data[i][0] == "Ненайденные фразы":
                in_not_found_section = True
                break
            if data[i][0] in ["Полностью совпадающие фразы", "Частично совпадающие фразы"]:
                break

        if in_not_found_section and value:  # Если выбрано "Да" в блоке "Ненайденные фразы"
            # Снимаем выбор "Да" с других строк с той же фразой
            for r, row_data in enumerate(data):
                if row_data[0] == phrase and r != row:
                    current_state = model.data(model.index(r, 2), Qt.CheckStateRole)
                    if current_state == Qt.CheckState.Checked:
                        model.setData(model.index(r, 2), Qt.CheckState.Unchecked, Qt.CheckStateRole)

        # Обновляем текущее значение только для чекбокса, текст не трогаем
        model.setData(model.index(row, 2), Qt.CheckState.Checked if value else Qt.CheckState.Unchecked,
                      Qt.CheckStateRole)

        self.selected_matches[key] = value
        self.update_potential_count()

    def update_potential_count(self):
        count = 0
        selected_phrases = set()
        for row in range(self.table_model.rowCount()):
            phrase = self.table_model.index(row, 0).data()
            choice = self.table_model.index(row, 2).data()
            if phrase not in ["Полностью совпадающие фразы", "Частично совпадающие фразы", "Ненайденные фразы",
                              "Дубли в фразах"] and choice.startswith("Субтитр"):
                if phrase not in selected_phrases:
                    selected_phrases.add(phrase)
                    count += 1
        self.potential_count = count
        self.potential_label.setText(f"Потенциальных отрывков: {count}")

    def update_sorting(self):
        self.check_phrases()

    def check_phrases(self):
        self.status_label.setText("Проверка...")
        self.status_label.setStyleSheet("color: black")
        threading.Thread(target=self._check_phrases_thread).start()

    def _check_phrases_thread(self):
        try:
            subs = parse_srt(self.path_vars[0].text())
            with open(self.path_vars[1].text(), 'r', encoding='utf-8') as f_en:
                english_phrases = [line.strip() for line in f_en if line.strip()]
            with open(self.path_vars[2].text(), 'r', encoding='utf-8') as f_ru:
                russian_phrases = [line.strip() for line in f_ru if line.strip()]
            if not subs or not english_phrases or not russian_phrases:
                raise ValueError("Файлы пусты или некорректны")

            threshold = 0.5
            analysis = analyze_phrases(subs, english_phrases, russian_phrases, threshold, stop_words=self.stop_words)
            self.phrase_order = analysis['phrase_order']

            self.selected_matches.clear()
            self.phrase_groups.clear()

            full_matches_items = []
            partial_matches_items = []
            not_found_items = []

            # Полные совпадения
            for phrase, match in analysis['full_matches'].items():
                key = (phrase, match['text'])
                self.selected_matches[key] = True
                full_matches_items.append(
                    (phrase, match['text'], "Да", match['subtitle'].start.ordinal, match['rus_phrase']))

            # Частичные совпадения
            for phrase, rus_phrase, matches in analysis['partial_matches']:
                for match in matches:
                    key = (phrase, match['text'])
                    self.selected_matches[key] = False
                    sort_key = match['subtitle'].start.ordinal if match['subtitle'] else 0
                    partial_matches_items.append(
                        (phrase, match['text'], "Нет", sort_key, rus_phrase))

            # Ненайденные фразы
            for phrase, rus_phrase, best_matches in analysis['not_found']:
                key = (phrase, "нет ни одного совпадающего слова")
                self.selected_matches[key] = False
                not_found_items.append(
                    (phrase, "нет ни одного совпадающего слова", "Нет", 0, rus_phrase, key))
                if phrase not in self.phrase_groups:
                    self.phrase_groups[phrase] = {}
                self.phrase_groups[phrase][key] = None

            # Сортировка
            if self.sort_option.currentText() == "time":
                full_matches_items.sort(key=lambda x: x[3])
                partial_matches_items.sort(key=lambda x: x[3])
                not_found_items.sort(key=lambda x: x[3])
            else:
                full_matches_items.sort(key=lambda x: self.phrase_order.index(x[0]))
                partial_matches_items.sort(key=lambda x: self.phrase_order.index(x[0]))
                not_found_items.sort(key=lambda x: self.phrase_order.index(x[0]))

            # Формирование данных для таблицы
            data = [
                ["Полностью совпадающие фразы", f"Кол-во: {len(full_matches_items)}", "", ""],
                # Добавлена пустая строка для русской фразы
                *[(phrase, text, selected, rus) for phrase, text, selected, _, rus in full_matches_items],
                ["Частично совпадающие фразы", f"Кол-во: {len(partial_matches_items)}", "", ""],
                # Добавлена пустая строка
                *[(phrase, text, selected, rus) for phrase, text, selected, _, rus in partial_matches_items],
                ["Ненайденные фразы", f"Кол-во: {len(analysis['not_found'])}", "", ""],  # Добавлена пустая строка
            ]
            row_index = len(data)
            for phrase, text, selected, _, rus_phrase, key in not_found_items:
                data.append([phrase, text, selected, rus_phrase])
                if phrase in self.phrase_groups and key in self.phrase_groups[phrase]:
                    self.phrase_groups[phrase][key] = row_index
                row_index += 1

            data.append(["Дубли в фразах (информационно)", f"Кол-во: {len(analysis['duplicates'])}", "",
                         ""])  # Добавлена пустая строка
            for phrase, count in analysis['duplicates'].items():
                data.append([phrase, f"Встречается {count} раз", "", ""])  # Пустая строка для русских фраз

            self._update_table(data)

            if not (analysis['not_found'] or analysis['partial_matches'] or analysis['duplicates']):
                total_phrases = analysis['total_unique_phrases'] + len(analysis['duplicates'])
                self.status_label.setText(
                    f"Проблем нет. Фраз: {total_phrases}, потенциальных отрывков: {self.potential_count}")
                self.status_label.setStyleSheet("color: green")
            else:
                issues = sum([len(analysis['not_found']), len(partial_matches_items),
                              len(analysis['duplicates'])])
                total_phrases = analysis['total_unique_phrases'] + len(analysis['duplicates'])
                self.status_label.setText(
                    f"Найдено проблем: {issues}. Фраз: {total_phrases}, потенциальных отрывков: {self.potential_count}")
                self.status_label.setStyleSheet("color: red")

            if self.enable_logging.isChecked():
                self.logger.info("Проверка завершена")

        except Exception as e:
            self.status_label.setText(f"Ошибка: {e}")
            self.status_label.setStyleSheet("color: red")
            if self.enable_logging.isChecked():
                self.logger.error(f"Ошибка при проверке: {e}")

    def manual_find_phrase(self):
        """Функция для ручного поиска и добавления отрывка."""
        srt_path = self.path_vars[0].text()
        if not os.path.exists(srt_path):
            QMessageBox.warning(self, "Ошибка", "Файл субтитров не найден!")
            return

        subprocess.Popen(['notepad.exe', srt_path])

        phrase, ok = QInputDialog.getText(self, "Ручной поиск", "Введите текст отрывка, найденного вручную:")
        if ok and phrase:
            subs = parse_srt(srt_path)
            for sub in subs:
                if phrase.lower() in sub.text.lower():
                    key = (phrase, sub.text)
                    self.selected_matches[key] = True
                    self.phrase_groups[phrase] = {key: self.table_model.rowCount()}
                    self._update_table_row(phrase, sub.text, "Да", sub.start.ordinal, "",
                                           is_manual=True)  # Добавлен флаг
                    QMessageBox.information(self, "Успех", f"Отрывок '{phrase}' добавлен с временем {sub.start}!")
                    return

            key = (phrase, "Ручное добавление")
            self.selected_matches[key] = False
            self.phrase_groups[phrase] = {key: self.table_model.rowCount()}
            self._update_table_row(phrase, "Ручное добавление", "Нет", 0, "", is_manual=True)  # Добавлен флаг
            QMessageBox.warning(self, "Предупреждение",
                                f"Точное совпадение для '{phrase}' не найдено. Добавлено как ручное.")

        subprocess.Popen(['notepad.exe', srt_path])

        # Запрашиваем у пользователя текст отрывка
        phrase, ok = QInputDialog.getText(self, "Ручной поиск", "Введите текст отрывка, найденного вручную:")
        if ok and phrase:
            # Поиск точного совпадения в субтитрах
            subs = parse_srt(srt_path)
            for sub in subs:
                if phrase.lower() in sub.text.lower():
                    # Добавляем в таблицу как полное совпадение
                    key = (phrase, sub.text)
                    self.selected_matches[key] = True
                    self.phrase_groups[phrase] = {key: self.table_model.rowCount()}
                    self._update_table_row(phrase, sub.text, "Да", sub.start.ordinal, "")
                    QMessageBox.information(self, "Успех", f"Отрывок '{phrase}' добавлен с временем {sub.start}!")
                    return

            # Если совпадение не найдено, добавляем как частичное
            key = (phrase, "Ручное добавление")
            self.selected_matches[key] = False
            self.phrase_groups[phrase] = {key: self.table_model.rowCount()}
            self._update_table_row(phrase, "Ручное добавление", "Нет", 0, "")
            QMessageBox.warning(self, "Предупреждение",
                                f"Точное совпадение для '{phrase}' не найдено. Добавлено как ручное.")

    def _update_table_row(self, phrase, text, selected, sort_key, rus_phrase, is_manual=False):
        """Обновление таблицы с новой строкой."""
        row_position = self.table_model.rowCount()
        self.table_model.insertRow(row_position)

        phrase_item = QStandardItem(phrase)
        text_item = QStandardItem(text)
        selected_item = QStandardItem("")
        rus_item = QStandardItem(rus_phrase if rus_phrase else "")

        selected_item.setData(Qt.CheckState.Checked if selected == "Да" else Qt.CheckState.Unchecked, Qt.CheckStateRole)
        selected_item.setEditable(False)
        selected_item.setData(sort_key, Qt.UserRole)
        selected_item.setData(is_manual, Qt.UserRole + 1)  # Флаг ручного добавления

        self.table_model.setItem(row_position, 0, phrase_item)
        self.table_model.setItem(row_position, 1, text_item)
        self.table_model.setItem(row_position, 2, selected_item)
        self.table_model.setItem(row_position, 3, rus_item)

        self.table_view.resizeRowsToContents()
        self.update_column_widths()

    def _update_table(self, data):
        self.table_model.removeRows(0, self.table_model.rowCount())
        # Обновляем заголовки, добавляя колонку для русских фраз
        self.table_model.setHorizontalHeaderLabels(["Фраза", "Субтитр", "Выбрано?", "Русская фраза"])

        for row in data:
            # Создаём элементы строки
            items = [QStandardItem(str(cell)) if i < 2 else QStandardItem("") for i, cell in enumerate(row[:3])]
            # Добавляем русскую фразу, если она есть
            if len(row) > 3:
                items.append(QStandardItem(row[3] if row[3] else ""))
            else:
                items.append(QStandardItem(""))

            if row[0] not in ["Полностью совпадающие фразы", "Частично совпадающие фразы", "Ненайденные фразы",
                              "Дубли в фразах (информационно)"] and (row[0] or row[1]):
                item = items[2]
                item.setData(Qt.CheckState.Checked if row[2] == "Да" else Qt.CheckState.Unchecked, Qt.CheckStateRole)
                item.setData("", Qt.DisplayRole)
                item.setEditable(False)
                if len(row) > 3 and isinstance(row[3], (int, float)):
                    items[2].setData(row[3], Qt.UserRole)
                if self.show_matches.isChecked():
                    # Выделяем совпадающие слова
                    phrase = row[0]
                    subtitle = row[1]
                    matched_words = self._get_matched_words(phrase, subtitle)
                    phrase_html = self._highlight_words(phrase, matched_words)
                    subtitle_html = self._highlight_words(subtitle, matched_words)
                    items[0].setText(phrase_html)
                    items[1].setText(subtitle_html)
            self.table_model.appendRow(items)

        for row in range(self.table_model.rowCount()):
            if self.table_model.index(row, 0).data() in ["Полностью совпадающие фразы", "Частично совпадающие фразы",
                                                         "Ненайденные фразы", "Дубли в фразах (информационно)"]:
                for col in range(4):  # Обновлено до 4 колонок
                    item = self.table_model.item(row, col)
                    if item:
                        font = QFont()
                        font.setBold(True)
                        item.setFont(font)

        self.table_view.resizeColumnsToContents()
        self.table_view.resizeRowsToContents()
        self.table_view.doubleClicked.connect(self.on_double_click)
        self.table_view.update()
        self.update_column_widths()

    def on_double_click(self, index):
        if index.column() == 2:  # Колонка "Выбор"
            current_state = self.table_model.data(index, Qt.CheckStateRole)
            new_state = Qt.CheckState.Unchecked if current_state == Qt.CheckState.Checked else Qt.CheckState.Checked
            phrase = self.table_model.index(index.row(), 0).data()
            self._set_selection((phrase, self.table_model.index(index.row(), 1).data()), index.row(),
                                new_state == Qt.CheckState.Checked)

    def find_excerpts(self):
        if not self.path_vars[0].text() or not self.path_vars[1].text():
            QMessageBox.critical(self, "Ошибка", "Укажите пути к файлам")
            return
        self.is_running = True
        self.status_label.setText("Поиск отрывков...")
        self.status_label.setStyleSheet("color: black")
        threading.Thread(target=self._find_excerpts_thread).start()

    def _find_excerpts_thread(self):
        try:
            # Используем modified_subs, если доступен, иначе загружаем исходный файл
            subs = self.modified_subs if self.modified_subs is not None else parse_srt(self.path_vars[0].text())
            with open(self.path_vars[1].text(), 'r', encoding='utf-8') as f_en:
                english_phrases = [line.strip() for line in f_en if line.strip()]
            with open(self.path_vars[2].text(), 'r', encoding='utf-8') as f_ru:
                russian_phrases = [line.strip() for line in f_ru if line.strip()]
            threshold = 0.5
            self.progress.setMaximum(len(english_phrases))

            selected = {}
            phrase_pairs = dict(zip(english_phrases, russian_phrases))

            selected_phrases_with_time = []

            for row in range(self.table_model.rowCount()):
                phrase = self.table_model.index(row, 0).data()
                choice = self.table_model.index(row, 2).data(Qt.CheckStateRole)
                if phrase in ["Полностью совпадающие фразы", "Частично совпадающие фразы",
                              "Ненайденные фразы", "Дубли в фразах"] or choice != Qt.CheckState.Checked:
                    continue

                subtitle_text = self.table_model.index(row, 1).data()
                for sub in subs:
                    if sub.text == subtitle_text:
                        if phrase not in selected:
                            selected[phrase] = []
                        selected[phrase].append({'subtitle': sub, 'text': subtitle_text})
                        selected_phrases_with_time.append((
                            sub.start.ordinal,
                            phrase,
                            phrase_pairs.get(phrase, ""),
                            sub
                        ))
                        break

            selected_phrases_with_time.sort(key=lambda x: x[0])
            selected_eng_phrases = [item[1] for item in selected_phrases_with_time]
            selected_rus_phrases = [item[2] for item in selected_phrases_with_time]

            selected_count = len(selected_eng_phrases)
            filename = f"{self.path_vars[4].text()}_sub-{selected_count}"
            output_dir = self.path_vars[3].text()
            if not os.path.exists(output_dir):
                os.makedirs(output_dir)
            output_path = os.path.join(output_dir, f"Timestamps_{filename}.srt")
            generate_excerpts(subs, english_phrases, threshold, output_path, selected)

            rus_words_file = os.path.join(output_dir, f"russian_words_{filename}.txt")
            with open(rus_words_file, 'w', encoding='utf-8') as f_rus:
                for rus_phrase in selected_rus_phrases:
                    f_rus.write(f"{rus_phrase}\n")

            eng_words_file = os.path.join(output_dir, f"english_words_{filename}.txt")
            with open(eng_words_file, 'w', encoding='utf-8') as f_eng:
                for eng_phrase in selected_eng_phrases:
                    f_eng.write(f"{eng_phrase}\n")

            for i in range(len(english_phrases)):
                self.progress.setValue(i + 1)
                QApplication.processEvents()

            self.status_label.setText("Отрывки найдены")
            self.status_label.setStyleSheet("color: green")
            if self.enable_logging.isChecked():
                self.logger.info("Отрывки найдены")
        except Exception as e:
            self.status_label.setText(f"Ошибка: {e}")
            self.status_label.setStyleSheet("color: red")
            if self.enable_logging.isChecked():
                self.logger.error(f"Ошибка при поиске отрывков: {e}")
        finally:
            self.is_running = False
            self.save_config()
            QApplication.processEvents()

    def get_timestamps(self):
        if not self.path_vars[0].text() or not self.path_vars[1].text():
            QMessageBox.critical(self, "Ошибка", "Укажите пути к файлам")
            return
        self.is_running = True
        self.status_label.setText("Получение таймкодов...")
        self.status_label.setStyleSheet("color: black")
        threading.Thread(target=self._get_timestamps_thread).start()

    def _get_timestamps_thread(self):
        try:
            subs = self.modified_subs if self.modified_subs is not None else parse_srt(self.path_vars[0].text())
            with open(self.path_vars[1].text(), 'r', encoding='utf-8') as f:
                phrases = [line.strip() for line in f if line.strip()]
            threshold = self.match_threshold.value() / 100.0
            self.progress.setMaximum(len(phrases))

            selected = {}
            for (phrase, subtitle_text), is_selected in self.selected_matches.items():
                if is_selected:
                    for sub in subs:
                        if sub.text == subtitle_text:
                            if phrase not in selected:
                                selected[phrase] = []
                            selected[phrase].append({'subtitle': sub, 'text': phrase})

            selected_count = len([k for k, v in self.selected_matches.items() if v])
            import re
            clean_filename = re.sub(r'[^a-zA-Z0-9_-]', '', self.path_vars[3].text())
            if not clean_filename:
                clean_filename = "episodes"
            filename = f"{clean_filename}_sub-{selected_count}"
            output_path = os.path.join(self.path_vars[2].text(), f"FinalExcerpts_{filename}.srt")
            generate_timestamps(subs, phrases, threshold, output_path, selected)
            for i in range(len(phrases)):
                self.progress.setValue(i + 1)
                QApplication.processEvents()
            self.status_label.setText("Таймкоды получены")
            self.status_label.setStyleSheet("color: green")
            if self.enable_logging.isChecked():
                self.logger.info("Таймкоды получены")
        except Exception as e:
            self.status_label.setText(f"Ошибка: {e}")
            self.status_label.setStyleSheet("color: red")
            if self.enable_logging.isChecked():
                self.logger.error(f"Ошибка при получении таймкодов: {e}")
        finally:
            self.is_running = False
            self.save_config()

    def modify_timestamps(self):
        """Изменение таймкодов выбранных субтитров."""
        selected_rows = [index.row() for index in self.table_view.selectionModel().selectedRows()]
        if not selected_rows:
            QMessageBox.warning(self, "Ошибка", "Выберите хотя бы одну строку!")
            return

        # Загружаем субтитры для модификации
        subs = parse_srt(self.path_vars[0].text())
        # Запрашиваем количество секунд для начала и конца
        start_secs, ok1 = QInputDialog.getDouble(self, "Изменить таймкоды",
                                                 "Секунды в начало (положительное или отрицательное):", 0, -60, 60, 2)
        if not ok1:
            return
        end_secs, ok2 = QInputDialog.getDouble(self, "Изменить таймкоды",
                                               "Секунды в конец (положительное или отрицательное):", 0, -60, 60, 2)
        if not ok2:
            return

        # Обрабатываем каждую выбранную строку
        modified_subs = subs[:]  # Копируем список для модификации
        modified_dict = {}  # Словарь для быстрого доступа к обновлённым субтитрам
        for row in selected_rows:
            phrase = self.table_model.index(row, 0).data()
            subtitle_text = self.table_model.index(row, 1).data()
            key = (phrase, subtitle_text)

            if phrase in ["Полностью совпадающие фразы", "Частично совпадающие фразы", "Ненайденные фразы",
                          "Дубли в фразах (информационно)"]:
                continue

            for sub in modified_subs:
                if sub.text == subtitle_text:
                    start_time = sub.start
                    end_time = sub.end

                    start_ms = start_time.ordinal + int(start_secs * 1000)
                    end_ms = end_time.ordinal + int(end_secs * 1000)

                    start_ms = max(0, start_ms)
                    end_ms = max(start_ms + 1, end_ms)

                    sub.start = pysrt.SubRipTime.from_ordinal(start_ms)
                    sub.end = pysrt.SubRipTime.from_ordinal(end_ms)
                    modified_dict[sub.index] = sub
                    self.table_model.setItem(row, 1, QStandardItem(sub.text))
                    self.table_model.item(row, 2).setData(sub.start.ordinal, Qt.UserRole)
                    break

        # Сохраняем обновлённый список
        self.modified_subs = modified_subs

        QMessageBox.information(self, "Успех", f"Таймкоды изменены для {len(selected_rows)} строк!")
        if self.enable_logging.isChecked():
            self.logger.info(
                f"Изменены таймкоды для {len(selected_rows)} строк: {start_secs} сек в начало, {end_secs} сек в конец")


    def clear_fields(self):
        self.table_model.removeRows(0, self.table_model.rowCount())
        self.selected_matches.clear()
        self.phrase_groups.clear()
        self.update_potential_count()
        self.status_label.setText("Очищено")
        self.status_label.setStyleSheet("color: black")
        if self.enable_logging.isChecked():
            self.logger.info("Таблица очищена")


print("=== ДОШЛИ ДО MAIN БЛОКА ===")
print(f"Проверка: __name__ == '__main__' ? {__name__ == '__main__'}")

if __name__ == "__main__":
    print("=== MAIN БЛОК ЗАПУЩЕН ===")

    try:
        print("1. Создание QApplication...")
        app = QApplication(sys.argv)
        print("2. QApplication создан успешно")

        print("3. Создание экземпляра SubtitleFilterApp...")
        app_instance = SubtitleFilterApp()  # Без параметра window
        print("4. SubtitleFilterApp создан успешно")

        print("5. Показ окна...")
        app_instance.show()
        print("6. Окно показано")

        print("7. Запуск event loop...")
        result = app.exec_()
        print(f"8. Event loop завершен с кодом: {result}")
        print("Проверка: приложение должно остаться открытым, если нет ошибок.")

        sys.exit(result)

    except Exception as e:
        print(f"ОШИБКА В MAIN: {e}")
        import traceback

        traceback.print_exc()
else:
    print("=== MAIN БЛОК НЕ ЗАПУЩЕН (файл импортирован) ===")