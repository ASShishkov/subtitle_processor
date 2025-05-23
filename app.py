import sys
import configparser
import threading
import os
import logging
from PyQt5.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
                             QFrame, QProgressBar, QCheckBox, QComboBox, QSlider, QTableView, QMenu,
                             QApplication, QMessageBox, QFileDialog)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QStandardItemModel, QStandardItem, QFont
from subtitle_processor import analyze_phrases, generate_excerpts, generate_timestamps
from utils import parse_srt

print("=== ФАЙЛ app.py ЗАГРУЖАЕТСЯ ===")
print(f"__name__ = {__name__}")



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
        self.resize(800, 600)

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

    def center_window(self):
        """Центрирует окно на экране"""
        try:
            from PyQt5.QtWidgets import QDesktopWidget

            # Получаем размеры экрана
            desktop = QDesktopWidget()
            screen_geometry = desktop.screenGeometry()

            # Получаем размеры окна
            window_geometry = self.geometry()

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
        # Центральный виджет и основной макет
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        # Фрейм для файлов (вертикальное расположение)
        files_frame = QFrame()
        files_layout = QVBoxLayout(files_frame)  # Используем QVBoxLayout для вертикального размещения
        main_layout.addWidget(files_frame)

        labels = ["Путь к субтитрам (SRT):", "Путь к файлу фраз (TXT):", "Папка вывода:", "Имя выходного файла:"]
        self.path_vars = [QLineEdit() for _ in range(4)]
        self.path_vars[3].setText("episodes")

        for i, label_text in enumerate(labels):
            row_layout = QHBoxLayout()  # Горизонтальный макет для каждой строки
            label = QLabel(label_text)
            entry = self.path_vars[i]
            entry.setMinimumWidth(500)  # Увеличиваем ширину поля ввода
            browse_button = QPushButton("Обзор")
            browse_button.clicked.connect(lambda checked, idx=i: self.browse_file(idx))
            row_layout.addWidget(label)
            row_layout.addWidget(entry)
            row_layout.addWidget(browse_button)
            files_layout.addLayout(row_layout)

        # Фрейм для настроек и действий (на одной линии)
        options_actions_frame = QFrame()
        options_actions_layout = QHBoxLayout(options_actions_frame)
        main_layout.addWidget(options_actions_frame)

        # Подфрейм для настроек
        options_frame = QFrame()
        options_layout = QHBoxLayout(options_frame)
        options_actions_layout.addWidget(options_frame)

        self.match_threshold = QSlider(Qt.Horizontal)
        self.match_threshold.setRange(50, 100)
        self.match_threshold.setValue(80)
        self.match_threshold.setMinimumWidth(150)

        self.sort_option = QComboBox()
        self.sort_option.addItems(["time", "file"])
        self.sort_option.currentTextChanged.connect(self.update_sorting)
        self.sort_option.setMinimumWidth(100)

        self.save_paths = QCheckBox("Сохранять пути")
        self.save_paths.setChecked(True)
        self.enable_logging = QCheckBox("Включить логирование")
        self.enable_logging.setChecked(True)

        options_layout.addWidget(QLabel("Порог совпадения (%):"))
        options_layout.addWidget(self.match_threshold)
        options_layout.addWidget(QLabel("Сортировка:"))
        options_layout.addWidget(self.sort_option)
        options_layout.addWidget(self.save_paths)
        options_layout.addWidget(self.enable_logging)
        options_layout.addStretch()

        # Подфрейм для действий
        actions_frame = QFrame()
        actions_layout = QHBoxLayout(actions_frame)
        options_actions_layout.addWidget(actions_frame)

        self.row_height = QSlider(Qt.Horizontal)
        self.row_height.setRange(20, 60)
        self.row_height.setValue(20)
        self.row_height.valueChanged.connect(self.update_row_height)
        self.row_height.setMinimumWidth(150)

        buttons = [
            QPushButton("Найти совпадения", clicked=self.check_phrases),
            QPushButton("Получить отрывки", clicked=self.find_excerpts),
            QPushButton("Таймкоды", clicked=self.get_timestamps),
            QPushButton("Очистить", clicked=self.clear_fields)
        ]
        for button in buttons:
            actions_layout.addWidget(button)
        actions_layout.addWidget(QLabel("Высота ячейки (px):"))
        actions_layout.addWidget(self.row_height)
        actions_layout.addStretch()

        # Оставшаяся часть метода остается без изменений
        # Прогресс-бар и статус
        self.progress = QProgressBar()
        self.progress.setMaximum(100)
        main_layout.addWidget(self.progress)

        self.status_label = QLabel("Готов")
        self.status_label.setStyleSheet("color: green")
        main_layout.addWidget(self.status_label)

        self.potential_label = QLabel("Потенциальных отрывков: 0")
        main_layout.addWidget(self.potential_label)

        # Таблица
        self.table_frame = QFrame()
        layout = QVBoxLayout(self.table_frame)
        main_layout.addWidget(self.table_frame, stretch=1)

        self.table_model = QStandardItemModel()
        self.table_model.setHorizontalHeaderLabels(["Фраза", "Субтитр", "Выбор"])
        self.table_view = QTableView()
        self.table_view.setModel(self.table_model)
        self.table_view.setSelectionBehavior(QTableView.SelectRows)
        self.table_view.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table_view.customContextMenuRequested.connect(self.show_context_menu)
        layout.addWidget(self.table_view)
        self.update_column_widths()
        self.table_view.setStyleSheet("QTableView { margin: 0px; padding: 0px; border: 0px; border-width: 0px; }")
        self.table_view.setContentsMargins(0, 0, 0, 0)
        self.table_view.horizontalHeader().setStyleSheet("QHeaderView { margin: 0px; padding: 0px; }")
        self.table_view.setContentsMargins(0, 0, 0, 0)
        self.table_view.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.table_view.setHorizontalScrollMode(QTableView.ScrollPerPixel)
        self.table_view.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        # Устанавливаем начальные размеры колонок
        self.update_column_widths()

        # Таймер для обновления размеров при изменении окна
        self.resize_timer = QTimer()
        self.resize_timer.timeout.connect(self.update_column_widths)
        self.resize_timer.start(100)

    def update_column_widths(self):
        # Получаем ширину видимой области таблицы (viewport)
        viewport_width = self.table_view.viewport().width()
        if viewport_width > 0:
            # Учитываем ширину вертикальной полосы прокрутки, если она видима
            scrollbar_width = self.table_view.verticalScrollBar().width() if self.table_view.verticalScrollBar().isVisible() else 0
            available_width = viewport_width - scrollbar_width

            # Устанавливаем ширину первых двух колонок пропорционально
            col1_width = int(available_width * 0.45)  # Фраза
            col2_width = int(available_width * 0.45)  # Субтитр

            # Общая ширина двух колонок
            used_width = col1_width + col2_width
            remaining_width = available_width - used_width

            # Корректируем ширину, если места не хватает
            if remaining_width < 0:
                col1_width = int(available_width * 0.47)
                col2_width = int(available_width * 0.47)
                remaining_width = available_width - col1_width - col2_width

            self.table_view.setColumnWidth(0, col1_width)  # Фраза
            self.table_view.setColumnWidth(1, col2_width)  # Субтитр
            self.table_view.setColumnWidth(2, max(remaining_width, 10))  # Выбор (минимальная ширина 10 пикселей)

            # Принудительное обновление, чтобы избежать визуальных артефактов
            self.table_view.update()

    def update_row_height(self, value):
        for row in range(self.table_model.rowCount()):
            self.table_view.setRowHeight(row, value)
        self.table_view.resizeRowsToContents()

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
        elif idx == 1:
            path, _ = QFileDialog.getOpenFileName(self, "Выберите TXT-файл", filter="Text files (*.txt)")
            if path:
                self.path_vars[idx].setText(path)
        elif idx == 2:
            path = QFileDialog.getExistingDirectory(self, "Выберите папку вывода")
            if path:
                self.path_vars[idx].setText(path)

    def output_path(self):
        return self.path_vars[2].text()

    def load_config(self):
        print("Загрузка конфига...")
        if os.path.exists("config.ini"):
            print("Файл config.ini найден")
            try:
                self.config.read("config.ini", encoding='utf-8')
                print("Конфиг прочитан")
                if "Paths" in self.config:
                    print("Секция Paths найдена")
                    self.path_vars[0].setText(self.config["Paths"].get("subtitles", ""))
                    self.path_vars[1].setText(self.config["Paths"].get("phrases", ""))
                    self.path_vars[2].setText(self.config["Paths"].get("output", ""))
                    self.path_vars[3].setText(self.config["Paths"].get("filename", "episodes"))
                    print("Пути загружены из конфига")
                else:
                    print("Секция Paths не найдена")
            except Exception as e:
                print(f"Ошибка при чтении конфига: {e}")
        else:
            print("Файл config.ini не найден")

    def save_config(self):
        if self.save_paths.isChecked():
            self.config["Paths"] = {
                "subtitles": self.path_vars[0].text(),
                "phrases": self.path_vars[1].text(),
                "output": self.path_vars[2].text(),
                "filename": self.path_vars[3].text()
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

        menu = QMenu()
        menu.addAction("Да", lambda: self._set_selection(key, row, True))
        menu.addAction("Нет", lambda: self._set_selection(key, row, False))
        menu.exec_(self.table_view.viewport().mapToGlobal(pos))

    def _set_selection(self, key, row, value):
        model = self.table_model
        phrase = model.index(row, 0).data()
        data = [model.index(r, c).data() for r in range(model.rowCount()) for c in range(model.columnCount())]
        data = [data[i:i + 3] for i in range(0, len(data), 3)]

        # Определяем, находится ли строка в блоке "Ненайденные фразы"
        in_not_found_section = False
        for i in range(row, -1, -1):
            if data[i][0] == "Ненайденные фразы":
                in_not_found_section = Trque
                break
            if data[i][0] in ["Полностью совпадающие фразы", "Частично совпадающие фразы"]:
                break

        if in_not_found_section and value:  # Если выбрано "Да" в блоке "Ненайденные фразы"
            # Снимаем выбор "Да" с других строк с той же фразой
            for r, row_data in enumerate(data):
                if row_data[0] == phrase and r != row:
                    other_key = (phrase, row_data[1])
                    self.selected_matches[other_key] = False
                    model.setData(model.index(r, 2), Qt.CheckState.Unchecked, Qt.CheckStateRole)

        if phrase in self.phrase_groups:
            group = self.phrase_groups[phrase]
            if key in group:
                for k in group:
                    self.selected_matches[k] = (k == key and value)
                    group_row = group[k]
                    if group_row is not None:
                        data[group_row][2] = "Да" if (k == key and value) else "Нет"
                        model.setData(model.index(group_row, 2), data[group_row][2])
        else:
            for (p, subtitle_text), selected in list(self.selected_matches.items()):
                if p == phrase and (p, subtitle_text) != key:
                    self.selected_matches[(p, subtitle_text)] = False
                    for r, row_data in enumerate(data):
                        if row_data[0] == phrase and row_data[1] == subtitle_text:
                            data[r][2] = "Нет"
                            model.setData(model.index(r, 2), "Нет")
                            break
            self.selected_matches[key] = value
            data[row][2] = "Да" if value else "Нет"
            model.setData(model.index(row, 2), data[row][2])

        self.update_potential_count()

    def update_potential_count(self):
        count = 0
        selected_phrases = set()
        for (phrase, _) in self.selected_matches:
            if self.selected_matches.get((phrase, _), False) and phrase not in self.phrase_groups:
                if phrase not in selected_phrases:
                    selected_phrases.add(phrase)
                    count += 1
        for phrase, group in self.phrase_groups.items():
            if any(self.selected_matches.get(k, False) for k in group):
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
            with open(self.path_vars[1].text(), 'r', encoding='utf-8') as f:
                phrases = [line.strip() for line in f if line.strip()]
            if not subs or not phrases:
                raise ValueError("Файлы пусты или некорректны")

            threshold = self.match_threshold.value() / 100.0
            analysis = analyze_phrases(subs, phrases, threshold)
            self.phrase_order = analysis['phrase_order']

            self.selected_matches.clear()
            self.phrase_groups.clear()

            full_matches_items = []
            partial_matches_items = []
            not_found_items = []

            for phrase, match in analysis['full_matches'].items():
                key = (phrase, match['text'])
                self.selected_matches[key] = True
                full_matches_items.append((phrase, match['text'], "Да", match['subtitle'].start.ordinal))

            for phrase, matches in analysis['partial_matches']:
                best_match = max(matches, key=lambda x: x['similarity'])
                key = (phrase, best_match['text'])
                self.selected_matches[key] = True
                partial_matches_items.append((phrase, best_match['text'], "Да", best_match['subtitle'].start.ordinal))

            for phrase, best_matches in analysis['not_found']:
                group = {}
                for i, match in enumerate(best_matches[:3]):
                    key = (phrase, match['text'])
                    self.selected_matches[key] = (i == 0)
                    not_found_items.append((phrase, match['text'], "Да" if i == 0 else "Нет", match['subtitle'].start.ordinal, key))
                    group[key] = None
                if group:
                    self.phrase_groups[phrase] = group

            if self.sort_option.currentText() == "time":
                full_matches_items.sort(key=lambda x: x[3])
                partial_matches_items.sort(key=lambda x: x[3])
                not_found_items.sort(key=lambda x: x[3])
            else:
                full_matches_items.sort(key=lambda x: self.phrase_order.index(x[0]))
                partial_matches_items.sort(key=lambda x: self.phrase_order.index(x[0]))
                not_found_items.sort(key=lambda x: self.phrase_order.index(x[0]))

            data = [
                ["Полностью совпадающие фразы", f"Кол-во: {len(full_matches_items)}", ""],
                *[(phrase, text, selected) for phrase, text, selected, _ in full_matches_items],
                ["Частично совпадающие фразы", f"Кол-во: {len(partial_matches_items)}", ""],
                *[(phrase, text, selected) for phrase, text, selected, _ in partial_matches_items],
                ["Ненайденные фразы", f"Кол-во: {len(analysis['not_found'])}", ""]
            ]
            row_index = len(data)
            for phrase, text, selected, _, key in not_found_items:
                data.append([phrase, text, selected])
                if phrase in self.phrase_groups and key in self.phrase_groups[phrase]:
                    self.phrase_groups[phrase][key] = row_index
                row_index += 1

            data.append(["Дубли в фразах (информационно)", f"Кол-во: {len(analysis['duplicates'])}", ""])
            for phrase, count in analysis['duplicates'].items():
                data.append([phrase, f"Встречается {count} раз", ""])

            self._update_table(data)

            if not (analysis['not_found'] or analysis['partial_matches'] or analysis['duplicates']):
                total_phrases = analysis['total_unique_phrases'] + len(analysis['duplicates'])
                self.status_label.setText(f"Проблем нет. Фраз: {total_phrases}, потенциальных отрывков: {self.potential_count}")
                self.status_label.setStyleSheet("color: green")
            else:
                issues = sum([len(analysis['not_found']), sum(len(m) for _, m in analysis['partial_matches']),
                              len(analysis['duplicates'])])
                total_phrases = analysis['total_unique_phrases'] + len(analysis['duplicates'])
                self.status_label.setText(f"Найдено проблем: {issues}. Фраз: {total_phrases}, потенциальных отрывков: {self.potential_count}")
                self.status_label.setStyleSheet("color: red")

            if self.enable_logging.isChecked():
                self.logger.info("Проверка завершена")
        except Exception as e:
            self.status_label.setText(f"Ошибка: {e}")
            self.status_label.setStyleSheet("color: red")
            if self.enable_logging.isChecked():
                self.logger.error(f"Ошибка при проверке: {e}")

    def _update_table(self, data):
        self.table_model.removeRows(0, self.table_model.rowCount())
        for row in data:
            items = [QStandardItem(str(cell)) for cell in row]
            if row[0] not in ["Полностью совпадающие фразы", "Частично совпадающие фразы", "Ненайденные фразы",
                              "Дубли в фразах"] and (row[0] or row[1]):
                item = items[2]
                item.setData(Qt.CheckState.Checked if row[2] == "Да" else Qt.CheckState.Unchecked, Qt.CheckStateRole)
                item.setEditable(False)
            self.table_model.appendRow(items)

        for row in range(self.table_model.rowCount()):
            if self.table_model.index(row, 0).data() in ["Полностью совпадающие фразы", "Частично совпадающие фразы",
                                                         "Ненайденные фразы", "Дубли в фразах"]:
                for col in range(3):
                    item = self.table_model.item(row, col)
                    if item:
                        font = item.font()
                        font.setBold(True)
                        item.setFont(font)

        # Принудительное обновление размеров колонок после добавления данных
        self.table_view.resizeColumnsToContents()
        self.table_view.resizeRowsToContents()
        self.table_view.doubleClicked.connect(self.on_double_click)
        # Принудительное обновление виджета перед пересчетом ширины
        QApplication.processEvents()
        self.update_column_widths()

    def on_double_click(self, index):
        if index.column() == 2:  # Столбец "Выбор"
            row = index.row()
            model = self.table_model
            phrase = model.index(row, 0).data()
            subtitle_text = model.index(row, 1).data()
            key = (phrase, subtitle_text)
            current_state = model.data(index, Qt.CheckStateRole)
            new_state = Qt.CheckState.Unchecked if current_state == Qt.CheckState.Checked else Qt.CheckState.Checked
            model.setData(index, new_state, Qt.CheckStateRole)
            self._set_selection(key, row, new_state == Qt.CheckState.Checked)

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
            subs = parse_srt(self.path_vars[0].text())
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
                            selected[phrase].append({'subtitle': sub, 'text': sub.text})

            selected_count = len([k for k, v in self.selected_matches.items() if v])
            filename = f"{self.path_vars[3].text()}_sub-{selected_count}"
            output_dir = self.path_vars[2].text()
            if not os.path.exists(output_dir):
                os.makedirs(output_dir)
            output_path = os.path.join(output_dir, f"Timestamps_{filename}.srt")
            generate_excerpts(subs, phrases, threshold, output_path, selected)
            for i in range(len(phrases)):
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
            subs = parse_srt(self.path_vars[0].text())
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

        sys.exit(result)

    except Exception as e:
        print(f"ОШИБКА В MAIN: {e}")
        import traceback

        traceback.print_exc()
else:
    print("=== MAIN БЛОК НЕ ЗАПУЩЕН (файл импортирован) ===")