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
        self.setup_gui()
        self.setup_logging()
        self.load_config()

    def setup_gui(self):
        # Поля ввода и кнопки обзора
        self.subtitles_path = tk.StringVar()
        self.phrases_path = tk.StringVar()
        self.output_path = tk.StringVar()

        tk.Label(self.root, text="Путь к субтитрам (SRT):").grid(row=0, column=0, padx=5, pady=5)
        tk.Entry(self.root, textvariable=self.subtitles_path, width=50).grid(row=0, column=1, padx=5, pady=5)
        tk.Button(self.root, text="Обзор", command=self.browse_subtitles).grid(row=0, column=2, padx=5, pady=5)

        tk.Label(self.root, text="Путь к файлу фраз (TXT):").grid(row=1, column=0, padx=5, pady=5)
        tk.Entry(self.root, textvariable=self.phrases_path, width=50).grid(row=1, column=1, padx=5, pady=5)
        tk.Button(self.root, text="Обзор", command=self.browse_phrases).grid(row=1, column=2, padx=5, pady=5)

        tk.Label(self.root, text="Папка вывода:").grid(row=2, column=0, padx=5, pady=5)
        tk.Entry(self.root, textvariable=self.output_path, width=50).grid(row=2, column=1, padx=5, pady=5)
        tk.Button(self.root, text="Обзор", command=self.browse_output).grid(row=2, column=2, padx=5, pady=5)

        # Ползунок порога совпадения
        tk.Label(self.root, text="Порог частичного совпадения (%):").grid(row=3, column=0, padx=5, pady=5)
        self.match_threshold = tk.DoubleVar(value=80.0)
        tk.Scale(self.root, from_=50, to=100, resolution=5, orient=tk.HORIZONTAL,
                 variable=self.match_threshold).grid(row=3, column=1, padx=5, pady=5)

        # Чекбоксы (по умолчанию включены)
        self.save_paths = tk.BooleanVar(value=True)
        tk.Checkbutton(self.root, text="Сохранить пути", variable=self.save_paths).grid(row=4, column=0, padx=5, pady=5)
        self.enable_logging = tk.BooleanVar(value=True)
        tk.Checkbutton(self.root, text="Включить логирование", variable=self.enable_logging).grid(row=4, column=1,
                                                                                                  padx=5, pady=5)

        # Кнопки управления
        tk.Button(self.root, text="Проверить", command=self.check_phrases).grid(row=5, column=0, padx=5, pady=5)
        tk.Button(self.root, text="Найти отрывки", command=self.find_excerpts).grid(row=5, column=1, padx=5, pady=5)
        tk.Button(self.root, text="Получить таймкоды", command=self.get_timestamps).grid(row=5, column=2, padx=5,
                                                                                         pady=5)
        tk.Button(self.root, text="Показать отчёт", command=self.show_report).grid(row=6, column=0, padx=5, pady=5)
        tk.Button(self.root, text="Очистить", command=self.clear_fields).grid(row=6, column=1, padx=5, pady=5)
        tk.Button(self.root, text="Стоп", command=self.stop_process).grid(row=6, column=2, padx=5, pady=5)

        # Прогресс-бар
        self.progress = ttk.Progressbar(self.root, length=300, mode='determinate')
        self.progress.grid(row=7, column=0, columnspan=3, padx=5, pady=5)

        # Метка статуса
        self.status_label = tk.Label(self.root, text="Готов к работе", fg="green")
        self.status_label.grid(row=8, column=0, columnspan=3, padx=5, pady=5)

        # Таблица дублей
        self.tree = ttk.Treeview(self.root, columns=("Фраза", "Тип", "Блок/Строка", "Таймкоды/Текст", "Выбор"),
                                 show="headings")
        self.tree.grid(row=9, column=0, columnspan=3, padx=5, pady=5, sticky="nsew")
        self.tree.heading("Фраза", text="Фраза")
        self.tree.heading("Тип", text="Тип")
        self.tree.heading("Блок/Строка", text="Блок/Строка")
        self.tree.heading("Таймкоды/Текст", text="Таймкоды/Текст")
        self.tree.heading("Выбор", text="Выбор")
        self.tree.column("Фраза", width=150)
        self.tree.column("Тип", width=100)
        self.tree.column("Блок/Строка", width=100)
        self.tree.column("Таймкоды/Текст", width=150)
        self.tree.column("Выбор", width=50)

    def setup_logging(self):
        """Настраивает логирование."""
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

    def save_config(self):
        if self.save_paths.get():
            self.config["Paths"] = {
                "subtitles": self.subtitles_path.get(),
                "phrases": self.phrases_path.get(),
                "output": self.output_path.get()
            }
            with open("config.ini", "w", encoding="utf-8") as configfile:
                self.config.write(configfile)

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

            # Формируем отчет
            report_path = os.path.join(self.output_path.get(), "analysis_report.txt")
            with open(report_path, 'w', encoding='utf-8') as f:
                f.write("--- Ненайденные фразы ---\n")
                if analysis['not_found']:
                    f.write(f"Количество ненайденных фраз: {len(analysis['not_found'])}\n")
                    for phrase in analysis['not_found']:
                        f.write(f"Фраза: {phrase}\n")
                else:
                    f.write("Ненайденных фраз нет\n")
                f.write("-----------------------\n")

                f.write("--- Частично совпадающие фразы ---\n")
                if analysis['partial_matches']:
                    for match in analysis['partial_matches']:
                        f.write(f"Фраза: {match['phrase']} (совпадение: {match['similarity'] * 100:.1f}%)\n")
                        f.write(f"Найдено в блоке {match['subtitle_index']}: {match['subtitle_text']}\n")
                else:
                    f.write("Частичных совпадений нет\n")
                f.write("-----------------------\n")

                f.write("--- Дублирующиеся фразы (в phrases.txt) ---\n")
                if analysis['phrase_duplicates']:
                    for phrase, count in analysis['phrase_duplicates'].items():
                        f.write(f"Фраза: {phrase} (встречается {count} раз)\n")
                else:
                    f.write("Дублей среди фраз нет\n")
                f.write("-----------------------\n")

                f.write("--- Дублирующиеся фразы (в субтитрах) ---\n")
                if analysis['subtitle_duplicates']:
                    for text, indices in analysis['subtitle_duplicates'].items():
                        f.write(f"Фраза: {text} (встречается {len(indices) + 1} раз)\n")
                        f.write(f"Блоки: {', '.join(str(idx) for idx, _ in indices)}\n")
                else:
                    f.write("Дублей в субтитрах нет\n")
                f.write("-----------------------\n")

            # Обновляем таблицу дублей
            for item in self.tree.get_children():
                self.tree.delete(item)

            for phrase, count in analysis['phrase_duplicates'].items():
                self.tree.insert("", "end", values=(phrase, "Дубль фразы", f"Кол-во: {count}", "", ""))

            for text, indices in analysis['subtitle_duplicates'].items():
                blocks = ', '.join(str(idx) for idx, _ in indices)
                self.tree.insert("", "end", values=(text, "Дубль субтитра", blocks, "", ""))

            # Обновляем статус
            if not (analysis['not_found'] or analysis['partial_matches'] or analysis['phrase_duplicates'] or analysis[
                'subtitle_duplicates']):
                self.status_label.config(
                    text=f"Проблем нет. Фраз: {len(phrases)}, потенциальных отрывков: {len(analysis['results'])}",
                    fg="green")
            else:
                issues = sum(
                    [len(analysis['not_found']), len(analysis['partial_matches']), len(analysis['phrase_duplicates']),
                     len(analysis['subtitle_duplicates'])])
                self.status_label.config(
                    text=f"Найдено проблем: {issues}. Фраз: {len(phrases)}, потенциальных отрывков: {len(analysis['results'])}",
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
            output_path = os.path.join(self.output_path.get(), "filtered_subtitles.srt")
            generate_excerpts(subs, phrases, threshold, output_path)
            for i in range(len(phrases)):
                if not self.is_running:
                    raise InterruptedError("Процесс остановлен")
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
            output_path = os.path.join(self.output_path.get(), "precise_timestamps.srt")
            generate_timestamps(subs, phrases, threshold, output_path)
            for i in range(len(phrases)):
                if not self.is_running:
                    raise InterruptedError("Процесс остановлен")
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

    def show_report(self):
        report_path = os.path.join(self.output_path.get(), "analysis_report.txt")
        if os.path.exists(report_path):
            os.startfile(report_path)  # Windows
            self.status_label.config(text="Отчет открыт", fg="green")
            if self.enable_logging.get():
                self.logger.info("Отчет открыт")
        else:
            self.status_label.config(text="Отчёт не найден", fg="red")
            if self.enable_logging.get():
                self.logger.error("Отчет не найден")

    def clear_fields(self):
        self.status_label.config(text="Поля очищены", fg="green")
        for item in self.tree.get_children():
            self.tree.delete(item)
        if self.enable_logging.get():
            self.logger.info("Таблица очищена")

    def stop_process(self):
        self.is_running = False
        self.status_label.config(text="Процесс прерван", fg="red")
        if self.enable_logging.get():
            self.logger.info("Процесс прерван")


if __name__ == "__main__":
    root = tk.Tk()
    app = SubtitleFilterApp(root)
    root.mainloop()