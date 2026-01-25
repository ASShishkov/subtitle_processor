# gui_base.py
import tkinter as tk
from tkinter import ttk
from logger import init_logger

class AnkiAppBase:
    def __init__(self, root):
        self.root = root
        self.root.title("Anki Card Creator")
        self.root.geometry("800x600")
        init_logger(log_to_file=True, log_file="logs/app.log", gui_log_callback=self.deck_log)
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill="both", expand=True)
        self.deck_log_text = None

    def deck_log(self, message):
        if self.deck_log_text:
            self.deck_log_text.configure(state="normal")
            self.deck_log_text.insert(tk.END, message + "\n")
            self.deck_log_text.configure(state="disabled")
            self.deck_log_text.see(tk.END)
            self.root.update()