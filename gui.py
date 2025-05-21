import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import configparser
import threading
import os
import logging
from subtitle_processor import analyze_phrases, generate_excerpts, generate_timestamps
from utils import parse_srt


class SubtitleFilterApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Фильтрация субтитров")
        self.config = configparser.ConfigParser()
        self.is_running = False
        self.selected_matches = {}  # Хранит выбор (True/False)
        self.phrase_groups = {}  # Хранит группы фраз для выбора одного варианта
        self.phrase_order = []  # Сохраняем порядок фраз
        self.setup_gui()
        self.setup_logging()
        self.load_config()

    def setup_gui(self):
        # Поля ввода и кнопки обзора
        self.subtitles_path = tk.StringVar()
        self.phrases_path = tk.StringVar()
        self.output_path = tk.StringVar()
        self.output_filename = tk.StringVar(value="series")

        tk.Label(self.root, text="Путь к субтитрам (SRT):").grid(row=0, column=0, padx=5, pady=5)
        tk.Entry(self.root, textvariable=self.subtitles_path, width=50).grid(row=0, column=1, padx=5, pady=5)
        tk.Button(self.root, text="Обзор", command=self.browse_subtitles).grid(row=0, column=2, padx=5, pady=5)

        tk.Label(self.root, text="Путь к файлу фраз (TXT):").grid(row=1, column=0, padx=5, pady=5)
        tk.Entry(self.root, textvariable=self.phrases_path, width=50).grid(row=1, column=1, padx=5, pady=5)
        tk.Button(self.root, text="Обзор", command=self.browse_phrases).grid(row=1, column=2, padx=5, pady=5)

        tk.Label(self.root, text="Папка вывода:").grid(row=2, column=0, padx=5, pady=5)
        tk.Entry(self.root, textvariable=self.output_path, width=50).grid(row=2, column=1, padx=5, pady=5)
        tk.Button(self.root, text="Обзор", command=self.browse_output).grid(row=2, column=2, padx=5, pady=5)

        tk.Label(self.root, text="Имя выходного файла:").grid(row=3, column=0, padx=5, pady=5)
        tk.Entry(self.root, textvariable=self.output_filename, width=50).grid(row=3, column=1, padx=5, pady=5)

        # Ползунок порога совпадения
        tk.Label(self.root, text="Порог частичного совпадения (%):").grid(row=4, column=0, padx=5, pady=5)
        self.match_threshold = tk.DoubleVar(value=80.0)
        tk.Scale(self.root, from_=50, to=100, resolution=5, orient=tk.HORIZONTAL,
                 variable=self.match_threshold).grid(row=4, column=1, padx=5, pady=5)

        # Выбор сортировки
        tk.Label(self.root, text="Сортировка:").grid(row=5, column=0, padx=5, pady=5)
        self.sort_option = tk.StringVar(value="time")
        sort_menu = ttk.Combobox(self.root, textvariable=self.sort_option, values=["time", "file"], state="readonly")
        sort_menu.grid(row=5, column=1, padx=5, pady=5)
        sort_menu.bind("<<ComboboxSelected>>", self.update_sorting)

        # Чекбоксы
        self.save_paths = tk.BooleanVar(value=True)
        tk.Checkbutton(self.root, text="Сохранить пути", variable=self.save_paths).grid(row=6, column=0, padx=5, pady=5)
        self.enable_logging = tk.BooleanVar(value=True)
        tk.Checkbutton(self.root, text="Включить логирование", variable=self.enable_logging).grid(row=6, column=1,
                                                                                                  padx=5, pady=5)

        # Кнопки управления
        tk.Button(self.root, text="Проверить", command=self.check_phrases).grid(row=7, column=0, padx=5, pady=5)
        tk.Button(self.root, text="Найти отрывки", command=self.find_excerpts).grid(row=7, column=1, padx=5, pady=5)
        tk.Button(self.root, text="Получить таймкоды", command=self.get_timestamps).grid(row=7, column=2, padx=5,
                                                                                         pady=5)
        tk.Button(self.root, text="Очистить", command=self.clear_fields).grid(row=8, column=1, padx=5, pady=5)

        # Прогресс-бар
        self.progress = ttk.Progressbar(self.root, length=300, mode='determinate')
        self.progress.grid(row=9, column=0, columnspan=3, padx=5, pady=5)

        # Метка статуса и потенциальных отрывков
        self.status_label = tk.Label(self.root, text="Готов к работе", fg="green")
        self.status_label.grid(row=10, column=0, columnspan=3, padx=5, pady=5)
        self.potential_label = tk.Label(self.root, text="Потенциальных отрывков: 0", fg="black")
        self.potential_label.grid(row=11, column=0, columnspan=3, padx=5, pady=5)

        # Таблица с прокруткой
        tree_frame = ttk.Frame(self.root)
        tree_frame.grid(row=12, column=0, columnspan=3, padx=5, pady=5, sticky="nsew")
        self.tree = ttk.Treeview(tree_frame, columns=("Фраза", "Субтитр", "Выбор"), show="headings", height=15)
        self.tree.heading("Фраза", text="Фраза")
        self.tree.heading("Субтитр", text="Субтитр")
        self.tree.heading("Выбор", text="Выбор")
        self.tree.column("Фраза", width=200, stretch=True)
        self.tree.column("Субтитр", width=400, stretch=True)
        self.tree.column("Выбор", width=50)

        # Прокрутка
        vsb = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        hsb = ttk.Scrollbar(tree_frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")
        tree_frame.grid_rowconfigure(0, weight=1)
        tree_frame.grid_columnconfigure(0, weight=1)

        # Стили для жирного текста
        style = ttk.Style()
        style.configure("Bold.Treeview", font=("Helvetica", 10, "bold"))
        self.tree.tag_configure("bold", font=("Helvetica", 10, "bold"))

        # Обработчик клика для выбора
        self.tree.bind("<ButtonRelease-1>", self.toggle_selection)

    def setup_logging(self):
        self.logger = logging.getLogger('SubtitleFilterApp')
        self.logger.setLevel(logging.INFO)
        handler = logging.FileHandler(os.path.join(self.output_path.get() or 'output', 'log.txt'), encoding='utf-8')
        handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
        self.logger.addHandler(handler)

    def browse_subtitles(self):
        path = filedialog.askopenfilename(filetypes=[("SRT files", "*.srt")])
        if path:
            self.subtitles_path.set(path)

    def browse_phrases(self):
        path = filedialog.askopenfilename(filetypes=[("Text files", "*.txt")])
        if path:
            self.phrases_path.set(path)

    def browse_output(self):
        path = filedialog.askdirectory()
        if path:
            self.output_path.set(path)

    def load_config(self):
        if os.path.exists("config.ini"):
            self.config.read("config.ini", encoding='utf-8')
            if "Paths" in self.config:
                self.subtitles_path.set(self.config["Paths"].get("subtitles", ""))
                self.phrases_path.set(self.config["Paths"].get("phrases", ""))
                self.output_path.set(self.config["Paths"].get("output", ""))
                self.output_filename.set(self.config["Paths"].get("filename", "series"))

    def save_config(self):
        if self.save_paths.get():
            self.config["Paths"] = {
                "subtitles": self.subtitles_path.get(),
                "phrases": self.phrases_path.get(),
                "output": self.output_path.get(),
                "filename": self.output_filename.get()
            }
            with open("config.ini", "w", encoding="utf-8") as configfile:
                self.config.write(configfile)

    def toggle_selection(self, event):
        item = self.tree.selection()
        if not item:
            return
        item = item[0]
        values = self.tree.item(item, "values")
        if not values[0]:  # Игнорируем заголовки
            return

        phrase = values[0]
        subtitle_text = values[1]
        key = (phrase, subtitle_text)

        # Если это группа с несколькими вариантами
        if phrase in self.phrase_groups:
            group = self.phrase_groups[phrase]
            if key in group:
                # Если уже выбрано "Да", снимаем выбор (все "Нет")
                if self.selected_matches[key]:
                    for k in group:
                        self.selected_matches[k] = False
                        item_id = group[k]
                        self.tree.item(item_id, values=(self.tree.item(item_id, "values")[0],
                                                        self.tree.item(item_id, "values")[1], "Нет"))
                else:
                    # Выбираем текущий вариант, остальные "Нет"
                    for k in group:
                        self.selected_matches[k] = (k == key)
                        item_id = group[k]
                        self.tree.item(item_id, values=(self.tree.item(item_id, "values")[0],
                                                        self.tree.item(item_id, "values")[1],
                                                        "Да" if k == key else "Нет"))
        else:
            # Одиночный выбор
            current_state = self.selected_matches.get(key, True)
            self.selected_matches[key] = not current_state
            self.tree.item(item, values=(values[0], values[1], "Да" if not current_state else "Нет"))

    def wrap_text(self, text, max_length=50):
        if len(text) <= max_length:
            return text
        words = text.split()
        lines = []
        current_line = []
        current_length = 0
        for word in words:
            if current_length + len(word) + len(current_line) <= max_length:
                current_line.append(word)
                current_length += len(word)
            else:
                lines.append(" ".join(current_line))
                current_line = [word]
                current_length = len(word)
        if current_line:
            lines.append(" ".join(current_line))
        return "\n".join(lines[:2])

    def update_sorting(self, event=None):
        self.check_phrases()  # Перестраиваем таблицу при изменении сортировки

    def check_phrases(self):
        self.status_label.config(text="Проверка файлов...", fg="black")
        threading.Thread(target=self._check_phrases_thread).start()

    def _check_phrases_thread(self):
        try:
            subs = parse_srt(self.subtitles_path.get())
            with open(self.phrases_path.get(), 'r', encoding='utf-8') as f:
                phrases = [line.strip() for line in f if line.strip()]
            if not subs or not phrases:
                raise ValueError("Файлы пусты или некорректны")

            threshold = self.match_threshold.get() / 100.0
            analysis = analyze_phrases(subs, phrases, threshold)
            self.phrase_order = analysis['phrase_order']

            # Очищаем таблицу и выбор
            for item in self.tree.get_children():
                self.tree.delete(item)
            self.selected_matches.clear()
            self.phrase_groups.clear()

            # Подготовка данных для сортировки
            full_matches_items = []
            partial_matches_items = []
            not_found_items = []

            # Полные совпадения
            for phrase, match in analysis['full_matches'].items():
                wrapped_phrase = self.wrap_text(phrase)
                wrapped_text = self.wrap_text(match['text'])
                key = (phrase, match['text'])
                self.selected_matches[key] = True
                full_matches_items.append((phrase, wrapped_phrase, wrapped_text, "Да", match['subtitle'].start.ordinal))

            # Частично совпадающие
            for phrase, matches in analysis['partial_matches']:
                best_match = max(matches, key=lambda x: x['similarity'])
                wrapped_phrase = self.wrap_text(phrase)
                wrapped_text = self.wrap_text(best_match['text'])
                key = (phrase, best_match['text'])
                self.selected_matches[key] = True
                partial_matches_items.append(
                    (phrase, wrapped_phrase, wrapped_text, "Да", best_match['subtitle'].start.ordinal))

            # Ненайденные фразы
            for phrase, best_matches in analysis['not_found']:
                wrapped_phrase = self.wrap_text(phrase)
                group = {}
                for i, match in enumerate(best_matches[:3]):
                    wrapped_text = self.wrap_text(match['text'])
                    key = (phrase, match['text'])
                    self.selected_matches[key] = (i == 0)  # Выбираем первый по умолчанию
                    not_found_items.append((phrase, wrapped_phrase, wrapped_text, "Да" if i == 0 else "Нет",
                                            match['subtitle'].start.ordinal, key))
                    group[key] = None  # Заполним ID позже
                if group:
                    self.phrase_groups[phrase] = group

            # Сортировка
            if self.sort_option.get() == "time":
                full_matches_items.sort(key=lambda x: x[4])  # По времени
                partial_matches_items.sort(key=lambda x: x[4])
                not_found_items.sort(key=lambda x: x[4])
            else:  # По порядку в файле
                full_matches_items.sort(key=lambda x: self.phrase_order.index(x[0]))
                partial_matches_items.sort(key=lambda x: self.phrase_order.index(x[0]))
                not_found_items.sort(key=lambda x: self.phrase_order.index(x[0]))

            # Отображение
            self.tree.insert("", "end",
                             values=("", f"Полностью совпадающие фразы (кол-во: {len(full_matches_items)})", ""),
                             tags=("bold",))
            for _, wrapped_phrase, wrapped_text, selected, _ in full_matches_items:
                self.tree.insert("", "end", values=(wrapped_phrase, wrapped_text, selected))

            self.tree.insert("", "end",
                             values=("", f"Частично совпадающие фразы (кол-во: {len(partial_matches_items)})", ""),
                             tags=("bold",))
            for _, wrapped_phrase, wrapped_text, selected, _ in partial_matches_items:
                self.tree.insert("", "end", values=(wrapped_phrase, wrapped_text, selected))

            self.tree.insert("", "end", values=("", f"Ненайденные фразы (кол-во: {len(analysis['not_found'])})", ""),
                             tags=("bold",))
            for phrase, wrapped_phrase, wrapped_text, selected, _, key in not_found_items:
                item_id = self.tree.insert("", "end", values=(wrapped_phrase, wrapped_text, selected))
                if phrase in self.phrase_groups:
                    self.phrase_groups[phrase][key] = item_id

            # Дубли в фразах
            self.tree.insert("", "end",
                             values=("", f"Дубли в фразах (информационно, кол-во: {len(analysis['duplicates'])})", ""),
                             tags=("bold",))
            for phrase, count in analysis['duplicates'].items():
                wrapped_phrase = self.wrap_text(phrase)
                self.tree.insert("", "end", values=(wrapped_phrase, f"Встречается {count} раз", ""))

            # Потенциальные отрывки
            total_potential = analysis['total_unique_phrases']
            self.potential_label.config(text=f"Потенциальных отрывков: {total_potential}")

            # Статус
            if not (analysis['not_found'] or analysis['partial_matches'] or analysis['duplicates']):
                self.status_label.config(
                    text=f"Проблем нет. Фраз: {analysis['total_unique_phrases']}, потенциальных отрывков: {total_potential}",
                    fg="green")
            else:
                issues = sum([len(analysis['not_found']), sum(len(m) for _, m in analysis['partial_matches']),
                              len(analysis['duplicates'])])
                self.status_label.config(
                    text=f"Найдено проблем: {issues}. Фраз: {analysis['total_unique_phrases']}, потенциальных отрывков: {total_potential}",
                    fg="red")

            if self.enable_logging.get():
                self.logger.info("Проверка завершена")
        except Exception as e:
            self.root.after(0, lambda: self.status_label.config(text=f"Ошибка: {e}", fg="red"))
            if self.enable_logging.get():
                self.logger.error(f"Ошибка при проверке: {e}")

    def find_excerpts(self):
        if not self.subtitles_path.get() or not self.phrases_path.get():
            messagebox.showerror("Ошибка", "Укажите пути к файлам")
            return
        self.is_running = True
        self.status_label.config(text="Поиск отрывков...", fg="black")
        threading.Thread(target=self._find_excerpts_thread).start()

    def _find_excerpts_thread(self):
        try:
            subs = parse_srt(self.subtitles_path.get())
            with open(self.phrases_path.get(), 'r', encoding='utf-8') as f:
                phrases = [line.strip() for line in f if line.strip()]
            threshold = self.match_threshold.get() / 100.0
            self.progress['maximum'] = len(phrases)

            filename = self.output_filename.get() or "series"
            output_path = os.path.join(self.output_path.get(), f"FinalExcerpts_{filename}.srt")

            selected = {}
            for (phrase, subtitle_text), is_selected in self.selected_matches.items():
                if is_selected:
                    for sub in subs:
                        if sub.text == subtitle_text:  # Сравниваем оригинальный текст
                            if phrase not in selected:
                                selected[phrase] = []
                            selected[phrase].append({'subtitle': sub, 'text': sub.text})

            generate_excerpts(subs, phrases, threshold, output_path, selected)
            for i in range(len(phrases)):
                self.progress['value'] = i + 1
                self.root.update_idletasks()
            self.root.after(0, lambda: self.status_label.config(text="Отрывки найдены", fg="green"))
            if self.enable_logging.get():
                self.logger.info("Отрывки найдены")
        except Exception as e:
            self.root.after(0, lambda: self.status_label.config(text=f"Ошибка: {e}", fg="red"))
            if self.enable_logging.get():
                self.logger.error(f"Ошибка при поиске отрывков: {e}")
        finally:
            self.is_running = False
            self.save_config()

    def get_timestamps(self):
        if not self.subtitles_path.get() or not self.phrases_path.get():
            messagebox.showerror("Ошибка", "Укажите пути к файлам")
            return
        self.is_running = True
        self.status_label.config(text="Получение таймкодов...", fg="black")
        threading.Thread(target=self._get_timestamps_thread).start()

    def _get_timestamps_thread(self):
        try:
            subs = parse_srt(self.subtitles_path.get())
            with open(self.phrases_path.get(), 'r', encoding='utf-8') as f:
                phrases = [line.strip() for line in f if line.strip()]
            threshold = self.match_threshold.get() / 100.0
            self.progress['maximum'] = len(phrases)

            filename = self.output_filename.get() or "series"
            output_path = os.path.join(self.output_path.get(), f"precise_timestamps_{filename}.srt")

            selected = {}
            for (phrase, subtitle_text), is_selected in self.selected_matches.items():
                if is_selected:
                    for sub in subs:
                        if sub.text == subtitle_text:
                            if phrase not in selected:
                                selected[phrase] = []
                            selected[phrase].append({'subtitle': sub, 'text': phrase})

            generate_timestamps(subs, phrases, threshold, output_path, selected)
            for i in range(len(phrases)):
                self.progress['value'] = i + 1
                self.root.update_idletasks()
            self.root.after(0, lambda: self.status_label.config(text="Таймкоды получены", fg="green"))
            if self.enable_logging.get():
                self.logger.info("Таймкоды получены")
        except Exception as e:
            self.root.after(0, lambda: self.status_label.config(text=f"Ошибка: {e}", fg="red"))
            if self.enable_logging.get():
                self.logger.error(f"Ошибка при получении таймкодов: {e}")
        finally:
            self.is_running = False
            self.save_config()

    def clear_fields(self):
        self.status_label.config(text="Поля очищены", fg="green")
        for item in self.tree.get_children():
            self.tree.delete(item)
        self.selected_matches.clear()
        self.phrase_groups.clear()
        if self.enable_logging.get():
            self.logger.info("Таблица очищена")


if __name__ == "__main__":
    root = tk.Tk()
    app = SubtitleFilterApp(root)
    root.mainloop()