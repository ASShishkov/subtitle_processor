import sys
from PyQt5.QtWidgets import QApplication, QMainWindow
from app import SubtitleFilterApp

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = QMainWindow()
    app_instance = SubtitleFilterApp(window)
    window.show()
    sys.exit(app.exec_())