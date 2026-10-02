from PySide6.QtWidgets import (
    QDialog,
    QFormLayout,
    QLineEdit,
    QPushButton,
    QHBoxLayout,
    QVBoxLayout,
    QMessageBox
)


class ReaderDialog(QDialog):

    def __init__(self, parent=None, reader=None):
        super().__init__(parent)

        self.reader = reader

        if reader:
            self.setWindowTitle("Sửa độc giả")
        else:
            self.setWindowTitle("Thêm độc giả")

        self.setMinimumWidth(500)

        self.create_widgets()
        self.apply_styles()

        if reader:
            self.load_reader_data()

    def create_widgets(self):

        self.code_edit = QLineEdit()
        self.name_edit = QLineEdit()
        self.phone_edit = QLineEdit()
        self.email_edit = QLineEdit()
        self.class_edit = QLineEdit()

        form = QFormLayout()

        form.addRow(
            "Mã độc giả:",
            self.code_edit
        )

        form.addRow(
            "Họ và tên:",
            self.name_edit
        )

        form.addRow(
            "Số điện thoại:",
            self.phone_edit
        )

        form.addRow(
            "Email:",
            self.email_edit
        )

        form.addRow(
            "Lớp / Đơn vị:",
            self.class_edit
        )

        self.cancel_button = QPushButton("Hủy")
        self.save_button = QPushButton("Lưu độc giả")

        self.cancel_button.clicked.connect(
            self.reject
        )

        self.save_button.clicked.connect(
            self.validate_and_accept
        )

        buttons = QHBoxLayout()

        buttons.addStretch()

        buttons.addWidget(
            self.cancel_button
        )

        buttons.addWidget(
            self.save_button
        )

        layout = QVBoxLayout()

        layout.addLayout(form)
        layout.addLayout(buttons)

        self.setLayout(layout)

    def apply_styles(self):

        self.setStyleSheet("""
            QDialog {
                background-color: #ffffff;
            }

            QLabel {
                color: #1e293b;
                font-size: 14px;
            }

            QLineEdit {
                background-color: #ffffff;
                color: #1e293b;
                border: 1px solid #cbd5e1;
                border-radius: 6px;
                padding: 8px;
                font-size: 14px;
                selection-background-color: #2563eb;
                selection-color: #ffffff;
            }

            QLineEdit:focus {
                border: 1px solid #2563eb;
            }

            QPushButton {
                background-color: #ffffff;
                color: #1e293b;
                border: 1px solid #cbd5e1;
                border-radius: 6px;
                padding: 8px 16px;
                font-size: 14px;
            }

            QPushButton:hover {
                background-color: #f1f5f9;
            }

            QPushButton:pressed {
                background-color: #e2e8f0;
            }
        """)

    def load_reader_data(self):

        self.code_edit.setText(
            self.reader["reader_code"]
        )

        self.name_edit.setText(
            self.reader["name"]
        )

        self.phone_edit.setText(
            self.reader["phone"] or ""
        )

        self.email_edit.setText(
            self.reader["email"] or ""
        )

        self.class_edit.setText(
            self.reader["class_name"] or ""
        )

    def validate_and_accept(self):

        reader_code = self.code_edit.text().strip()
        name = self.name_edit.text().strip()

        if not reader_code:
            QMessageBox.warning(
                self,
                "Thiếu thông tin",
                "Vui lòng nhập mã độc giả."
            )
            return

        if not name:
            QMessageBox.warning(
                self,
                "Thiếu thông tin",
                "Vui lòng nhập họ và tên."
            )
            return

        self.accept()

    def get_data(self):

        return {
            "reader_code": self.code_edit.text().strip(),
            "name": self.name_edit.text().strip(),
            "phone": self.phone_edit.text().strip(),
            "email": self.email_edit.text().strip(),
            "class_name": self.class_edit.text().strip()
        }