import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import configparser
import threading
import os
from subtitle_processor import search_phrases, calculate_timestamps, analyze_duplicates
from utils import parse_srt


class SubtitleFilterApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Фильтрация субтитров")
        self.config = configparser.ConfigParser()
        self.is_running = False
        self.setup_gui()
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

        # Чекбоксы
        self.save_paths = tk.BooleanVar()
        tk.Checkbutton(self.root, text="Сохранить пути", variable=self.save_paths).grid(row=4, column=0, padx=5, pady=5)
        self.enable_logging = tk.BooleanVar()
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
            self.config.read("config.ini")
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
            self.root.after(0, lambda: self.status_label.config(text="Все файлы корректны", fg="green"))
        except Exception as e:
            self.root.after(0, lambda: self.status_label.config(text=f"Ошибка: {e}", fg="red"))

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
            self.progress['maximum'] = len(subs)
            results = search_phrases(subs, phrases, threshold)
            for i, _ in enumerate(subs):
                if not self.is_running:
                    raise InterruptedError("Процесс остановлен")
                self.progress['value'] = i + 1
                self.root.update_idletasks()
            with open(os.path.join(self.output_path.get(), "results.txt"), 'w', encoding='utf-8') as f:
                for res in results:
                    f.write(f"Блок {res['subtitle'].index}: {res['phrase']} (совпадение: {res['similarity']:.2f})\n")
            self.root.after(0, lambda: self.status_label.config(text="Отрывки найдены", fg="green"))
        except Exception as e:
            self.root.after(0, lambda: self.status_label.config(text=f"Ошибка: {e}", fg="red"))
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
            results = search_phrases(subs, phrases, threshold)
            self.progress['maximum'] = len(results)
            timestamps = []
            for i, res in enumerate(results):
                if not self.is_running:
                    raise InterruptedError("Процесс остановлен")
                start, end = calculate_timestamps(res['subtitle'], res['phrase'])
                timestamps.append((res['phrase'], start, end))
                self.progress['value'] = i + 1
                self.root.update_idletasks()
            with open(os.path.join(self.output_path.get(), "timestamps.txt"), 'w', encoding='utf-8') as f:
                for phrase, start, end in timestamps:
                    f.write(f"{phrase}: {start} - {end}\n")
            self.root.after(0, lambda: self.status_label.config(text="Таймкоды получены", fg="green"))
        except Exception as e:
            self.root.after(0, lambda: self.status_label.config(text=f"Ошибка: {e}", fg="red"))
        finally:
            self.is_running = False
            self.save_config()

    def show_report(self):
        self.status_label.config(text="Анализ дублей...", fg="black")
        threading.Thread(target=self._show_report_thread).start()

    def _show_report_thread(self):
        try:
            subs = parse_srt(self.subtitles_path.get())
            with open(self.phrases_path.get(), 'r', encoding='utf-8') as f:
                phrases = [line.strip() for line in f if line.strip()]
            duplicates = analyze_duplicates(subs, phrases)

            # Очистка таблицы
            for item in self.tree.get_children():
                self.tree.delete(item)

            # Заполнение таблицы дублями фраз
            for phrase, count in duplicates['phrase_duplicates'].items():
                self.tree.insert("", "end", values=(phrase, "Дубль фразы", f"Кол-во: {count}", "", ""))

            # Заполнение таблицы дублями субтитров
            for text, indices in duplicates['subtitle_duplicates'].items():
                blocks = ', '.join(str(idx) for idx, _ in indices)
                self.tree.insert("", "end", values=(text, "Дубль субтитра", blocks, "", ""))

            report_path = os.path.join(self.output_path.get(), "analysis_report.txt")
            with open(report_path, 'w', encoding='utf-8') as f:
                f.write("Отчет по дублям:\n\nДубли фраз:\n")
                for p, c in duplicates['phrase_duplicates'].items():
                    f.write(f"{p}: {c} раз\n")
                f.write("\nДубли субтитров:\n")
                for t, idxs in duplicates['subtitle_duplicates'].items():
                    f.write(f"{t}: блоки {', '.join(str(i) for i, _ in idxs)}\n")
            self.root.after(0, lambda: os.startfile(report_path) if os.path.exists(report_path) else None)
            self.root.after(0, lambda: self.status_label.config(text="Отчет готов", fg="green"))
        except Exception as e:
            self.root.after(0, lambda: self.status_label.config(text=f"Ошибка: {e}", fg="red"))

    def clear_fields(self):
        self.subtitles_path.set("")
        self.phrases_path.set("")
        self.output_path.set("")
        self.status_label.config(text="Поля очищены", fg="green")
        for item in self.tree.get_children():
            self.tree.delete(item)

    def stop_process(self):
        self.is_running = False
        self.status_label.config(text="Процесс прерван", fg="red")


if __name__ == "__main__":
    root = tk.Tk()
    app = SubtitleFilterApp(root)
    root.mainloop()