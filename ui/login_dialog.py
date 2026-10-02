from PySide6.QtWidgets import QDialog, QFormLayout, QLineEdit, QMessageBox, QPushButton, QVBoxLayout


class LoginDialog(QDialog):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Đăng nhập Library Manager")
        self.setMinimumWidth(360)

        self.username_edit = QLineEdit()
        self.username_edit.setPlaceholderText("Tên đăng nhập")
        self.password_edit = QLineEdit()
        self.password_edit.setPlaceholderText("Mật khẩu")
        self.password_edit.setEchoMode(QLineEdit.EchoMode.Password)

        form = QFormLayout()
        form.addRow("Tên đăng nhập:", self.username_edit)
        form.addRow("Mật khẩu:", self.password_edit)

        login_button = QPushButton("Đăng nhập")
        login_button.setObjectName("primaryButton")
        login_button.clicked.connect(self.validate_login)
        self.password_edit.returnPressed.connect(self.validate_login)

        layout = QVBoxLayout()
        layout.addLayout(form)
        layout.addWidget(login_button)
        self.setLayout(layout)

    def validate_login(self):
        from database.database import authenticate_user

        user = authenticate_user(
            self.username_edit.text().strip(),
            self.password_edit.text(),
        )
        if user is None:
            QMessageBox.warning(self, "Đăng nhập thất bại", "Tên đăng nhập hoặc mật khẩu không đúng.")
            return

        self.user = user
        self.accept()
