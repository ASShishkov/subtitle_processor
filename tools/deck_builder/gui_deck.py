# gui_deck.py
import config
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import os
import re
from datetime import datetime
from gui_base import AnkiAppBase
from config import RU_TEXT, EN_TEXT, FREE_LIMIT, ELEMENT_SPACING, MEDIA_SIZE, MEDIA_PROCESSING
from tts import get_audio_files
from anki import create_deck
from utils.db import init_db, add_phrase, get_all_phrases, add_media
from logger import get_logger, init_logger
from utils.file_utils import sanitize_filename, normalize_path


class AnkiAppDeck(AnkiAppBase):
    def __init__(self, root):
        super().__init__(root)
        self.db_path = "anki.db"
        init_db(self.db_path)
        self.input_dir = tk.StringVar(value=os.path.dirname(RU_TEXT))
        self.deck_type = tk.StringVar(value="front-back")
        self.use_google_tts = tk.BooleanVar(value=True)
        self.answer_position = tk.StringVar(value="below")
        self.spacing = tk.StringVar(value=str(ELEMENT_SPACING))

        self.front_order_vars = [tk.StringVar() for _ in range(4)]
        self.back_order_vars = [tk.StringVar() for _ in range(4)]

        self.media_width = tk.StringVar(value=str(MEDIA_SIZE["width"]))
        self.media_height = tk.StringVar(value=str(MEDIA_SIZE["height"]))
        self.media_processing = tk.StringVar(value=MEDIA_PROCESSING)
        self.deck_name = tk.StringVar(value="МояКолода")
        self.video_format = tk.StringVar(value="mp4")

        self.deck_name_preview_var = tk.StringVar()
        self.phrases_status_var = tk.StringVar(value="Фраз: 0")
        self.videos_status_var = tk.StringVar(value="Видео: 0")

        self.deck_name.trace_add("write", self.update_deck_name_preview)
        self.deck_type.trace_add("write", self.update_deck_name_preview)
        self.video_format.trace_add("write", self.update_deck_name_preview)

        for var in self.front_order_vars:
            var.trace_add("write", self.update_deck_name_preview)
        for var in self.back_order_vars:
            var.trace_add("write", self.update_deck_name_preview)

        self.deck_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.deck_frame, text="Создание колоды")
        self.create_deck_widgets()
        init_logger(log_to_file=True, log_file="logs/app.log", gui_log_callback=self.deck_log)

        self.update_deck_name_preview()

    def update_deck_name_preview(self, *args):
        try:
            PLATFORM_MAP = {"mp4": "iOS-Android", "m4v": "iOS", "webm": "PC-Android"}

            base_name = self.deck_name.get()

            front_order = [v.get() for v in self.front_order_vars if v.get() and v.get() != "(пусто)"]
            back_order = [v.get() for v in self.back_order_vars if v.get() and v.get() != "(пусто)"]
            front_str = ",".join(front_order)
            back_str = ",".join(back_order)

            current_date = datetime.now().strftime("%Y-%m-%d")

            phrases = get_all_phrases(self.db_path)
            phrase_count = len(phrases)
            deck_type = self.deck_type.get()
            card_count = phrase_count * 2 if deck_type == "mixed" else phrase_count

            video_format = self.video_format.get()
            platform = PLATFORM_MAP.get(video_format, "N/A")

            sanitized_name = sanitize_filename(base_name)

            preview_text = f"{sanitized_name}_(front-{front_str}_back-{back_str})_{phrase_count}p_{card_count}c_{platform}_{video_format}_{current_date}.apkg"

            self.deck_name_preview_var.set(f"Имя файла: {preview_text}")
        except Exception:
            self.deck_name_preview_var.set("Имя файла: (требуется импорт фраз)")

    def import_videos(self):
        logger = get_logger()
        from utils.db import clear_videos
        clear_videos(self.db_path)
        logger.info("База видео очищена перед импортом")

        input_dir = normalize_path(config.VIDEO_DIR)
        os.makedirs(input_dir, exist_ok=True)
        extension = "." + self.video_format.get()
        video_files = [f for f in os.listdir(input_dir) if f.lower().endswith(extension)]

        imported_count = 0
        for video_file in video_files:
            video_path = normalize_path(os.path.join(input_dir, video_file))
            match = re.search(r'(\d+)\.' + re.escape(self.video_format.get()) + '$', video_file, re.IGNORECASE)
            if not match:
                base, ext = os.path.splitext(video_file)
                sanitized_base = sanitize_filename(base)
                match = re.search(r'(\d+)$', sanitized_base)
                if not match:
                    logger.error(
                        f"Файл {video_path} не соответствует формату имени (например, 001.{self.video_format.get()})")
                    continue
                new_filename = f"{match.group(1)}.{self.video_format.get()}"
                new_path = normalize_path(os.path.join(input_dir, new_filename))
                try:
                    os.rename(video_path, new_path)
                    logger.info(f"Переименован файл: {video_path} -> {new_path}")
                    video_path = new_path
                    video_file = new_filename
                    match = re.search(r'(\d+)\.' + re.escape(self.video_format.get()) + '$', video_file, re.IGNORECASE)
                except Exception as e:
                    logger.error(f"Ошибка переименования {video_path}: {str(e)}")
                    continue

            phrase_id = int(match.group(1))
            if os.path.exists(video_path):
                add_media(phrase_id, "video", video_path, self.db_path)
                imported_count += 1
            else:
                logger.error(f"Видеофайл не найден: {video_path}")

        self.videos_status_var.set(f"Видео: {imported_count}")
        success_msg = f"Импортировано {imported_count} видео"
        logger.info(success_msg)
        self.deck_log(success_msg)
        messagebox.showinfo("Успех", success_msg)

    def deck_log(self, message):
        if self.deck_log_text:
            self.deck_log_text.configure(state="normal")
            self.deck_log_text.insert(tk.END, message + "\n")
            self.deck_log_text.configure(state="disabled")
            self.deck_log_text.see(tk.END)
            self.root.update()

    def add_context_menu(self, widget):
        menu = tk.Menu(widget, tearoff=0)
        menu.add_command(label="Копировать", command=lambda: widget.event_generate("<<Copy>>"))
        menu.add_command(label="Вставить", command=lambda: widget.event_generate("<<Paste>>"))
        widget.bind("<Button-3>", lambda event: menu.tk_popup(event.x_root, event.y_root))
        widget.bind("<Control-c>", lambda e: widget.event_generate("<<Copy>>"))
        widget.bind("<Control-v>", lambda e: widget.event_generate("<<Paste>>"))

    def add_log_context_menu(self, widget):
        menu = tk.Menu(widget, tearoff=0)
        menu.add_command(label="Копировать", command=lambda: self.copy_log_text(widget))
        widget.bind("<Button-3>", lambda event: menu.tk_popup(event.x_root, event.y_root))
        widget.bind("<Control-c>", lambda e: self.copy_log_text(widget))

    def copy_log_text(self, widget):
        try:
            log_text = widget.get("1.0", tk.END).strip()
            self.root.clipboard_clear()
            self.root.clipboard_append(log_text)
            get_logger().info("Лог скопирован")
        except Exception as e:
            get_logger().error(f"Ошибка копирования лога: {str(e)}")

    def create_deck_widgets(self):
        canvas = tk.Canvas(self.deck_frame)
        scrollbar = ttk.Scrollbar(self.deck_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)

        scrollable_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))

        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        frame_input = ttk.LabelFrame(scrollable_frame, text="Папка и импорт", padding=10)
        frame_input.pack(fill="x", padx=5, pady=5)

        top_frame = ttk.Frame(frame_input)
        top_frame.pack(fill="x")
        status_frame = ttk.Frame(frame_input)
        status_frame.pack(fill="x", pady=4)

        ttk.Label(top_frame, text="Папка с данными:").pack(anchor="w")
        vcmd = (self.root.register(self.validate_length), '%P')
        entry_input_dir = ttk.Entry(top_frame, textvariable=self.input_dir, width=50, validate="key",
                                    validatecommand=vcmd)
        entry_input_dir.pack(side="left", padx=5)
        self.add_context_menu(entry_input_dir)

        ttk.Button(top_frame, text="Выбрать", command=self.choose_input_dir).pack(side="left")

        btn_phrases = ttk.Button(top_frame, text="Импортировать фразы", command=self.import_phrases)
        btn_phrases.pack(side="left", padx=5)
        status_phrases = ttk.Label(status_frame, textvariable=self.phrases_status_var, foreground="blue")
        status_phrases.pack(side="left", padx=70)

        btn_videos = ttk.Button(top_frame, text="Импортировать видео", command=self.import_videos)
        btn_videos.pack(side="left", padx=5)
        status_videos = ttk.Label(status_frame, textvariable=self.videos_status_var, foreground="blue")
        status_videos.pack(side="left", padx=40)

        frame_deck_name = ttk.LabelFrame(scrollable_frame, text="Название колоды", padding=10)
        frame_deck_name.pack(fill="x", padx=5, pady=5)
        entry_deck_name = ttk.Entry(frame_deck_name, textvariable=self.deck_name, width=50, validate="key",
                                    validatecommand=vcmd)
        entry_deck_name.pack(anchor="w", fill="x")
        self.add_context_menu(entry_deck_name)

        preview_label = ttk.Label(frame_deck_name, textvariable=self.deck_name_preview_var, foreground="grey",
                                  wraplength=700)
        preview_label.pack(anchor="w", padx=2, pady=2)

        frame_deck = ttk.LabelFrame(scrollable_frame, text="Тип колоды и Платформа", padding=10)
        frame_deck.pack(fill="x", padx=5, pady=5)

        deck_options_frame = ttk.Frame(frame_deck)
        deck_options_frame.pack(side="left", fill="y", padx=5)

        platform_frame = ttk.Frame(frame_deck)
        platform_frame.pack(side="left", fill="y", padx=5)

        checklist_frame = ttk.Frame(frame_deck)
        checklist_frame.pack(side="right", fill="y", padx=20)
        checklist_text = "Чек-лист:\n1. Выбрать папку\n2. Импорт фраз\n3. Настроить поля"
        ttk.Label(checklist_frame, text=checklist_text, justify=tk.LEFT).pack(anchor="w")

        ttk.Combobox(deck_options_frame, textvariable=self.deck_type, values=["front-back", "back-front", "mixed"],
                     state="readonly").pack(anchor="w")

        ttk.Radiobutton(platform_frame, text="iOS/Android (.mp4)", variable=self.video_format, value="mp4").pack(
            anchor="w")
        ttk.Radiobutton(platform_frame, text="iOS (.m4v)", variable=self.video_format, value="m4v").pack(anchor="w")
        ttk.Radiobutton(platform_frame, text="PC/Android (.webm)", variable=self.video_format, value="webm").pack(
            anchor="w")

        frame_fields = ttk.LabelFrame(scrollable_frame, text="Настройка полей карточки", padding=10)
        frame_fields.pack(fill="x", padx=5, pady=5)

        options = ["(пусто)", "ru_text", "en_text", "ru_audio", "en_audio", "image", "video"]

        frame_front = ttk.Frame(frame_fields)
        frame_front.pack(fill="x", pady=2)
        ttk.Label(frame_front, text="Front:", width=15).pack(side="left")
        for i in range(4):
            combo = ttk.Combobox(frame_front, textvariable=self.front_order_vars[i], values=options, state="readonly",
                                 width=10)
            combo.pack(side="left", padx=2)

        frame_back = ttk.Frame(frame_fields)
        frame_back.pack(fill="x", pady=2)
        ttk.Label(frame_back, text="Back:", width=15).pack(side="left")
        for i in range(4):
            combo = ttk.Combobox(frame_back, textvariable=self.back_order_vars[i], values=options, state="readonly",
                                 width=10)
            combo.pack(side="left", padx=2)

        frame_position = ttk.LabelFrame(scrollable_frame, text="Позиция ответа", padding=10)
        frame_position.pack(fill="x", padx=5, pady=5)
        ttk.Combobox(frame_position, textvariable=self.answer_position, values=["replace", "below", "right"],
                     state="readonly").pack(anchor="w")

        frame_audio = ttk.LabelFrame(scrollable_frame, text="Источник аудио", padding=10)
        frame_audio.pack(fill="x", padx=5, pady=5)
        ttk.Checkbutton(frame_audio, text="Использовать Google TTS", variable=self.use_google_tts).pack(anchor="w")

        ttk.Button(scrollable_frame, text="Создать колоду", command=self.run_deck).pack(pady=10)
        log_frame = ttk.Frame(scrollable_frame)
        log_frame.pack(fill="x", expand=True, padx=5, pady=5)
        self.deck_log_text = tk.Text(log_frame, height=10, width=70, state="disabled")
        self.deck_log_text.pack(side="left", fill="x", expand=True)
        self.add_log_context_menu(self.deck_log_text)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

    # --- МЕТОД ВОССТАНОВЛЕН ---
    def validate_length(self, new_value):
        max_length = 1000
        if len(new_value) > max_length:
            get_logger().warning(f"Текст превышает {max_length} символов, обрезан")
            return False
        return True

    def choose_input_dir(self):
        logger = get_logger()
        directory = filedialog.askdirectory()
        if directory:
            self.input_dir.set(directory)
            logger.info(f"Выбрана входная папка: {directory}")

    def import_phrases(self):
        logger = get_logger()
        input_dir = self.input_dir.get()
        ru_text_file = os.path.join(input_dir, "ru_text.txt")
        en_text_file = os.path.join(input_dir, "en_text.txt")
        try:
            from utils.db import clear_database
            clear_database(self.db_path)
            with open(ru_text_file, "r", encoding="utf-8") as f:
                ru_texts = [line.strip() for line in f if line.strip()]
            with open(en_text_file, "r", encoding="utf-8") as f:
                en_texts = [line.strip() for line in f if line.strip()]
            if len(ru_texts) != len(en_texts):
                logger.error("Количество фраз не совпадает!")
                messagebox.showerror("Ошибка", "Количество фраз не совпадает!")
                return
            for ru, en in zip(ru_texts, en_texts):
                add_phrase(ru, en, self.db_path)

            self.phrases_status_var.set(f"Фраз: {len(ru_texts)}")
            self.videos_status_var.set("Видео: 0")

            logger.info(f"Импортировано {len(ru_texts)} фраз")
            messagebox.showinfo("Успех", f"Импортировано {len(ru_texts)} фраз")

            self.update_deck_name_preview()

        except Exception as e:
            logger.error(f"Ошибка: {str(e)}")
            messagebox.showerror("Ошибка", f"Ошибка: {str(e)}")

    def run_deck(self):
        logger = get_logger()
        logger.info("Начало создания колоды...")
        try:
            phrases = get_all_phrases(self.db_path)
            if not phrases:
                logger.error("База данных пуста! Импортируйте фразы.")
                messagebox.showerror("Ошибка", "База данных пуста!")
                return

            front_order = [v.get() for v in self.front_order_vars if v.get() and v.get() != "(пусто)"]
            if not front_order:
                messagebox.showerror("Ошибка", "Лицевая сторона (Front) не может быть пустой!")
                return

            ru_texts = [p[1] for p in phrases]
            en_texts = [p[2] for p in phrases]
            audio_files, _ = get_audio_files(ru_texts, en_texts, self.use_google_tts.get())

            back_order = [v.get() for v in self.back_order_vars if v.get() and v.get() != "(пусто)"]
            logger.info(f"Порядок Front: {front_order}")
            logger.info(f"Порядок Back: {back_order}")

            create_deck(
                audio_files=audio_files,
                deck_type=self.deck_type.get(),
                answer_position=self.answer_position.get(),
                spacing=int(self.spacing.get()),
                front_order=front_order,
                back_order=back_order,
                media_size={"width": int(self.media_width.get()), "height": int(self.media_height.get())},
                media_processing=self.media_processing.get(),
                deck_name=self.deck_name.get(),
                db_path=self.db_path,
                video_format=self.video_format.get()
            )
            logger.info("Колода успешно создана!")
            messagebox.showinfo("Успех", "Колода создана!")
        except Exception as e:
            logger.error(f"Ошибка при создании колоды: {str(e)}")
            messagebox.showerror("Ошибка", f"Ошибка: {str(e)}")