import sys

from PySide6.QtWidgets import QApplication

from UI.main_window import MainWindow
from UI.styles import STYLESHEET


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("LectureAI")
    app.setStyleSheet(STYLESHEET)

    window = MainWindow()
    window.show()
    sys.exit(app.exec())


# The guard matters: transcription spawns worker processes that re-import this file
if __name__ == "__main__":
    main()
