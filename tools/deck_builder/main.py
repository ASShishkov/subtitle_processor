# main.py
import tkinter as tk
from gui_deck import AnkiAppDeck
from utils.db import clear_database

def run_gui():
    root = tk.Tk()
    # Теперь AnkiAppDeck сам создаст все необходимое, включая вкладку
    app_deck = AnkiAppDeck(root)

    def on_closing():
        clear_database(app_deck.db_path)
        root.destroy()

    root.protocol("WM_DELETE_WINDOW", on_closing)
    root.mainloop()

if __name__ == "__main__":
    run_gui()