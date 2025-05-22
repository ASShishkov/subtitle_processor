import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import configparser
import threading
import os
import logging
from tksheet import Sheet
from subtitle_processor import analyze_phrases, generate_excerpts, generate_timestamps
from utils import parse_srt

class SubtitleFilterApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Фильтрация субтитров")
        self.config = configparser.ConfigParser()
        self.is_running = False
        self.selected_matches = {}
        self.phrase_groups = {}
        self.phrase_order = []
        self.potential_count = 0
        self.setup_gui()
        self.setup_logging()
        self.load_config()

    def setup_gui(self):
        self.root.geometry("1100x700")  # Устанавливаем ширину окна через 20px после слова "логирование"
        self.subtitles_path = tk.StringVar()
        self.phrases_path = tk.StringVar()
        self.output_path = tk.StringVar()
        self.output_filename = tk.StringVar(value="episodes")

        files_frame = ttk.LabelFrame(self.root, text="Файлы")
        files_frame.pack(fill="x", padx=10, pady=5)

        ttk.Label(files_frame, text="Путь к субтитрам (SRT):").grid(row=0, column=0, padx=5, pady=5)
        ttk.Entry(files_frame, textvariable=self.subtitles_path, width=70).grid(row=0, column=1, padx=5, pady=5)
        ttk.Button(files_frame, text="Обзор", command=self.browse_subtitles).grid(row=0, column=2, padx=5, pady=5)

        ttk.Label(files_frame, text="Путь к файлу фраз (TXT):").grid(row=1, column=0, padx=5, pady=5)
        ttk.Entry(files_frame, textvariable=self.phrases_path, width=70).grid(row=1, column=1, padx=5, pady=5)
        ttk.Button(files_frame, text="Обзор", command=self.browse_phrases).grid(row=1, column=2, padx=5, pady=5)

        ttk.Label(files_frame, text="Папка вывода:").grid(row=2, column=0, padx=5, pady=5)
        ttk.Entry(files_frame, textvariable=self.output_path, width=70).grid(row=2, column=1, padx=5, pady=5)
        ttk.Button(files_frame, text="Обзор", command=self.browse_output).grid(row=2, column=2, padx=5, pady=5)

        ttk.Label(files_frame, text="Имя выходного файла:").grid(row=3, column=0, padx=5, pady=5)
        ttk.Entry(files_frame, textvariable=self.output_filename, width=70).grid(row=3, column=1, padx=5, pady=5)

        options_frame = ttk.LabelFrame(self.root, text="Настройки")
        options_frame.pack(fill="x", padx=10, pady=5)

        self.match_threshold = tk.DoubleVar(value=80.0)
        ttk.Label(options_frame, text="Порог совпадения (%):").grid(row=0, column=0, padx=5, pady=5)
        ttk.Scale(options_frame, from_=50, to=100, variable=self.match_threshold, orient="horizontal").grid(row=0, column=1, padx=5, pady=5)

        self.sort_option = tk.StringVar(value="time")
        ttk.Label(options_frame, text="Сортировка:").grid(row=0, column=2, padx=5, pady=5)
        sort_menu = ttk.Combobox(options_frame, textvariable=self.sort_option, values=["time", "file"], state="readonly")
        sort_menu.grid(row=0, column=3, padx=5, pady=5)
        sort_menu.bind("<<ComboboxSelected>>", self.update_sorting)

        self.save_paths = tk.BooleanVar(value=True)
        ttk.Checkbutton(options_frame, text="Сохранять пути", variable=self.save_paths).grid(row=0, column=4, padx=5, pady=5)
        self.enable_logging = tk.BooleanVar(value=True)
        ttk.Checkbutton(options_frame, text="Включить логирование", variable=self.enable_logging).grid(row=0, column=5, padx=5, pady=5)

        actions_frame = ttk.LabelFrame(self.root, text="Действия")

        # Ползунок для высоты ячейки
        self.row_height = tk.IntVar(value=20)
        ttk.Label(options_frame, text="Высота ячейки (px):").grid(row=1, column=0, padx=5, pady=5)
        ttk.Scale(options_frame, from_=20, to=60, variable=self.row_height, orient="horizontal",
                  command=self.update_row_height).grid(row=1, column=1, padx=5, pady=5)
        actions_frame.pack(fill="x", padx=10, pady=5)

        ttk.Button(actions_frame, text="Найти совпадения", command=self.check_phrases).grid(row=0, column=0, padx=5, pady=5)
        ttk.Button(actions_frame, text="Получить отрывки", command=self.find_excerpts).grid(row=0, column=1, padx=5, pady=5)
        ttk.Button(actions_frame, text="Таймкоды", command=self.get_timestamps).grid(row=0, column=2, padx=5, pady=5)
        ttk.Button(actions_frame, text="Очистить", command=self.clear_fields).grid(row=0, column=3, padx=5, pady=5)

        self.progress = ttk.Progressbar(self.root, length=400, mode='determinate')
        self.progress.pack(padx=10, pady=5)

        self.status_label = tk.Label(self.root, text="Готов", fg="green")
        self.status_label.pack(padx=10, pady=5)

        self.potential_label = tk.Label(self.root, text="Потенциальных отрывков: 0", fg="black")
        self.potential_label.pack(padx=10, pady=5)

        self.table_frame = ttk.Frame(self.root)
        self.table_frame.pack(fill="both", expand=True, padx=10, pady=5)
        self.sheet = Sheet(self.table_frame, headers=["Фраза", "Субтитр", "Выбор"])
        self.sheet.set_options(row_height=self.row_height.get())  # Изначальная высота
        # Растягиваем таблицу на всю ширину области
        self.sheet.pack(fill="both", expand=True)

        # Обновляем ширину колонок при изменении размера окна
        def update_column_widths(event):
            total_width = self.table_frame.winfo_width()
            self.sheet.column_width(column=0, width=int(total_width * 0.45))
            self.sheet.column_width(column=1, width=int(total_width * 0.45))
            self.sheet.column_width(column=2, width=int(total_width * 0.10))
            self.sheet.refresh()

        self.table_frame.bind("<Configure>", update_column_widths)
        # Устанавливаем ширину колонок в процентах
        total_width = self.table_frame.winfo_width() or 1000  # Фallback, если ширина еще не определена
        self.sheet.column_width(column=0, width=int(total_width * 0.45))  # 45% для "Фраза"
        self.sheet.column_width(column=1, width=int(total_width * 0.45))  # 45% для "Субтитр"
        self.sheet.column_width(column=2, width=int(total_width * 0.10))  # 10% для "Выбор"
        self.sheet.enable_bindings(
            "single_select",
            "row_select",
            "column_width_resize",
            "double_click_column_resize",
            "arrowkeys",
            "right_click_popup_menu",
            "rc_select",
            "copy",
            "paste",
            "delete",
            "edit_cell"
        )
        self.sheet.pack(fill="both", expand=True)

        # Настройка контекстного меню для столбца "Выбор"
        self.sheet.bind("<Button-3>", self.show_context_menu)

    def update_row_height(self, value):
        self.sheet.row_height(row="all", height=int(value))
        self.sheet.redraw()
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
                self.output_filename.set(self.config["Paths"].get("filename", "episodes"))

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

    def show_context_menu(self, event):
        # Проверяем, что клик был в столбце "Выбор" (индекс 2)
        cell = self.sheet.get_cell_coords(event)
        if cell is None or cell[1] != 2:  # Столбец "Выбор" — это индекс 2
            return

        row = cell[0]
        data = self.sheet.get_sheet_data()
        if not data or row >= len(data):
            return

        phrase = data[row][0]
        subtitle_text = data[row][1]
        key = (phrase, subtitle_text)

        # Создаем контекстное меню
        menu = tk.Menu(self.root, tearoff=0)
        menu.add_command(label="Да", command=lambda: self._set_selection(key, row, True))
        menu.add_command(label="Нет", command=lambda: self._set_selection(key, row, False))
        menu.post(event.x_root, event.y_root)

    def _set_selection(self, key, row, value):
        phrase = self.sheet.get_cell_data(row, 0)
        data = self.sheet.get_sheet_data()

        if phrase in self.phrase_groups:
            group = self.phrase_groups[phrase]
            if key in group:
                for k in group:
                    self.selected_matches[k] = (k == key and value)
                    group_row = group[k]
                    if group_row is not None:
                        data[group_row][2] = "Да" if (k == key and value) else "Нет"
        else:
            # Обеспечиваем эксклюзивность выбора: только один субтитр на фразу
            for (p, subtitle_text), selected in list(self.selected_matches.items()):
                if p == phrase and (p, subtitle_text) != key:
                    self.selected_matches[(p, subtitle_text)] = False
                    for r, row_data in enumerate(data):
                        if row_data[0] == phrase and row_data[1] == subtitle_text:
                            data[r][2] = "Нет"
                            break
            self.selected_matches[key] = value
            data[row][2] = "Да" if value else "Нет"

        self.sheet.set_sheet_data(data)
        self.update_potential_count()

    def update_potential_count(self):
        count = 0
        selected_phrases = set()
        # Подсчитываем уникальные выбранные фразы вне групп
        for (phrase, _) in self.selected_matches:
            if self.selected_matches.get((phrase, _), False) and phrase not in self.phrase_groups:
                if phrase not in selected_phrases:
                    selected_phrases.add(phrase)
                    count += 1
        # Подсчитываем выбранные группы
        for phrase, group in self.phrase_groups.items():
            if any(self.selected_matches.get(k, False) for k in group):
                count += 1
        self.potential_count = count
        self.potential_label.config(text=f"Потенциальных отрывков: {count}")

    def update_sorting(self, event=None):
        self.check_phrases()

    def check_phrases(self):
        self.status_label.config(text="Проверка...", fg="black")
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
                    group[key] = None  # Будет обновлено после добавления строки
                if group:
                    self.phrase_groups[phrase] = group

            # Сортировка
            if self.sort_option.get() == "time":
                full_matches_items.sort(key=lambda x: x[3])
                partial_matches_items.sort(key=lambda x: x[3])
                not_found_items.sort(key=lambda x: x[3])
            else:
                full_matches_items.sort(key=lambda x: self.phrase_order.index(x[0]))
                partial_matches_items.sort(key=lambda x: self.phrase_order.index(x[0]))
                not_found_items.sort(key=lambda x: self.phrase_order.index(x[0]))

            # Формируем данные для таблицы
            data = []
            data.append(["Полностью совпадающие фразы", f"Кол-во: {len(full_matches_items)}", ""])
            for phrase, text, selected, _ in full_matches_items:
                data.append([phrase, text, selected])

            data.append(["Частично совпадающие фразы", f"Кол-во: {len(partial_matches_items)}", ""])
            for phrase, text, selected, _ in partial_matches_items:
                data.append([phrase, text, selected])

            data.append(["Ненайденные фразы", f"Кол-во: {len(analysis['not_found'])}", ""])
            row_index = len(data)
            for phrase, text, selected, _, key in not_found_items:
                data.append([phrase, text, selected])
                if phrase in self.phrase_groups and key in self.phrase_groups[phrase]:
                    self.phrase_groups[phrase][key] = row_index
                row_index += 1

            data.append(["Дубли в фразах (информационно)", f"Кол-во: {len(analysis['duplicates'])}", ""])
            for phrase, count in analysis['duplicates'].items():
                data.append([phrase, f"Встречается {count} раз", ""])

            # Обновление UI из основного потока
            self.root.after(0, lambda: self.sheet.set_sheet_data(data, reset_col_positions=True, reset_row_positions=True))
            self.update_potential_count()

            if not (analysis['not_found'] or analysis['partial_matches'] or analysis['duplicates']):
                total_phrases = analysis['total_unique_phrases'] + len(analysis['duplicates'])
                self.root.after(0, lambda: self.status_label.config(
                    text=f"Проблем нет. Фраз: {total_phrases}, потенциальных отрывков: {self.potential_count}",
                    fg="green"))
            else:
                issues = sum([len(analysis['not_found']), sum(len(m) for _, m in analysis['partial_matches']),
                              len(analysis['duplicates'])])
                total_phrases = analysis['total_unique_phrases'] + len(analysis['duplicates'])
                self.root.after(0, lambda: self.status_label.config(
                    text=f"Найдено проблем: {issues}. Фраз: {total_phrases}, потенциальных отрывков: {self.potential_count}",
                    fg="red"))

            if self.enable_logging.get():
                self.logger.info("Проверка завершена")
        except Exception as e:
            self.root.after(0, lambda: self.status_label.config(text=f"Ошибка: {e}", fg="red"))
            if self.enable_logging.get():
                self.logger.error(f"Ошибка при проверке: {e}")

    def bold_headers(self, data):
        for i, row in enumerate(data):
            if row[0] in ["Полностью совпадающие фразы", "Частично совпадающие фразы", "Ненайденные фразы",
                          "Дубли в фразах"]:
                self.sheet.set_cell_data(i, 0, row[0], font=("Helvetica", 10, "bold"))
                self.sheet.merge_cells(start_row=i, start_col=0, end_row=i, end_col=2)

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

            selected = {}
            for (phrase, subtitle_text), is_selected in self.selected_matches.items():
                if is_selected:
                    for sub in subs:
                        if sub.text == subtitle_text:
                            if phrase not in selected:
                                selected[phrase] = []
                            selected[phrase].append({'subtitle': sub, 'text': sub.text})

            selected_count = len([k for k, v in self.selected_matches.items() if v])
            filename = f"{self.output_filename.get()}_sub-{selected_count}"
            # Убедимся, что директория существует
            output_dir = self.output_path.get()
            if not os.path.exists(output_dir):
                os.makedirs(output_dir)
            output_path = os.path.join(output_dir, f"Timestamps_{filename}.srt")
            print(f"Final output path: {output_path}")
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

            selected = {}
            for (phrase, subtitle_text), is_selected in self.selected_matches.items():
                if is_selected:
                    for sub in subs:
                        if sub.text == subtitle_text:
                            if phrase not in selected:
                                selected[phrase] = []
                            selected[phrase].append({'subtitle': sub, 'text': phrase})

            selected_count = len([k for k, v in self.selected_matches.items() if v])
            # Очищаем имя файла от некорректных символов
            import re
            clean_filename = re.sub(r'[^a-zA-Z0-9_-]', '', self.output_filename.get())
            if not clean_filename:
                clean_filename = "episodes"  # Fallback, если имя пустое после очистки
            filename = f"{clean_filename}_sub-{selected_count}"
            output_path = os.path.join(self.output_path.get(), f"FinalExcerpts_{filename}.srt")
            print(f"Selected items for timestamps: {selected}")
            print(f"Output path: {output_path}")
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
        self.sheet.set_sheet_data([])
        self.selected_matches.clear()
        self.phrase_groups.clear()
        self.update_potential_count()
        self.status_label.config(text="Очищено", fg="black")
        if self.enable_logging.get():
            self.logger.info("Таблица очищена")