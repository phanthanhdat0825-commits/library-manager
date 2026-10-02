import sys
import sqlite3

from PySide6.QtWidgets import QApplication

from database.database import initialize_database
from ui.main_window import MainWindow
from ui.login_dialog import LoginDialog


def main():

    initialize_database()

    app = QApplication(sys.argv)

    login = LoginDialog()
    if login.exec() != LoginDialog.DialogCode.Accepted:
        return

    window = MainWindow(login.user)

    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()

    