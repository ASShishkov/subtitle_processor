# gui/drop_zone.py
from PyQt5.QtWidgets import QLabel
from PyQt5.QtCore import Qt, pyqtSignal

class DropZone(QLabel):
    fileDropped = pyqtSignal(str)

    def __init__(self, title="Перетащите файл сюда"):
        super().__init__()
        self.title = title
        self.setAcceptDrops(True)
        self.setAlignment(Qt.AlignCenter)
        self.setStyleSheet("""
            QLabel {
                border: 2px dashed #aaa;
                border-radius: 5px;
                font-size: 14px;
                color: #aaa;
                min-height: 100px;
            }
        """)
        self.setText(self.title)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.accept()
            self.setStyleSheet("border: 2px dashed #1e90ff;")
        else:
            event.ignore()

    def dragLeaveEvent(self, event):
        self.setStyleSheet("border: 2px dashed #aaa;")

    def dropEvent(self, event):
        self.setStyleSheet("border: 2px dashed #aaa;")
        files = [u.toLocalFile() for u in event.mimeData().urls()]
        if files:
            filepath = files[0]
            self.fileDropped.emit(filepath)
            filename = filepath.split('/')[-1].split('\\')[-1]
            self.setText(f"✔️ Файл:\n{filename}")
            self.setStyleSheet("""
                QLabel {
                    border: 2px solid green;
                    border-radius: 5px;
                    font-size: 14px;
                    color: #333;
                }
            """)