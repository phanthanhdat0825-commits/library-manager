from PySide6.QtWidgets import (
    QDialog,
    QFormLayout,
    QLineEdit,
    QComboBox,
    QSpinBox,
    QPlainTextEdit,
    QPushButton,
    QHBoxLayout,
    QVBoxLayout,
    QMessageBox
)


class BookDialog(QDialog):
    def apply_styles(self):

        self.setStyleSheet("""
        QTableWidget {
    background-color: #ffffff;
    color: #1e293b;
    gridline-color: #e2e8f0;
    border: 1px solid #cbd5e1;
    selection-background-color: #dbeafe;
    selection-color: #1e293b;
}

QTableWidget::item {
    color: #1e293b;
    background-color: #ffffff;
    padding: 6px;
}

QTableWidget::item:selected {
    color: #1e293b;
    background-color: #dbeafe;
}

QHeaderView::section {
    background-color: #f1f5f9;
    color: #1e293b;
    font-weight: bold;
    border: 1px solid #cbd5e1;
    padding: 8px;
}
    QDialog {
        background-color: #ffffff;
    }

    QLabel {
        color: #1e293b;
        font-size: 14px;
    }

    QLineEdit,
    QSpinBox,
    QPlainTextEdit,
    QComboBox {
        background-color: #ffffff;
        color: #1e293b;
        border: 1px solid #cbd5e1;
        border-radius: 6px;
        padding: 8px;
        font-size: 14px;
    }

    QLineEdit:focus,
    QSpinBox:focus,
    QPlainTextEdit:focus,
    QComboBox:focus {
        border: 1px solid #2563eb;
    }

    QComboBox QAbstractItemView {
        background-color: #ffffff;
        color: #1e293b;
        selection-background-color: #2563eb;
        selection-color: #ffffff;
        border: 1px solid #cbd5e1;
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
    def __init__(self, parent=None, book=None):
        super().__init__(parent)

        self.book = book

        if book:
            self.setWindowTitle("Sửa sách")
        else:
            self.setWindowTitle("Thêm sách")

        self.setMinimumWidth(500)

        self.create_widgets()
        self.apply_styles()

        if book:
            self.load_book_data()

    def create_widgets(self):

        self.code_edit = QLineEdit()
        self.title_edit = QLineEdit()
        self.author_edit = QLineEdit()
        self.category_edit = QComboBox()
        self.publisher_edit = QComboBox()
        self.category_edit.setEditable(True)
        self.publisher_edit.setEditable(True)
        try:
            from database.database import get_categories, get_publishers
            self.category_edit.addItems([row["name"] for row in get_categories()])
            self.publisher_edit.addItems([row["name"] for row in get_publishers()])
        except Exception:
            pass

        self.year_edit = QSpinBox()
        self.year_edit.setRange(0, 2100)
        self.year_edit.setValue(2026)

        self.quantity_edit = QSpinBox()
        self.quantity_edit.setRange(1, 9999)
        self.quantity_edit.setValue(1)

        self.shelf_edit = QLineEdit()

        self.description_edit = QPlainTextEdit()

        form = QFormLayout()

        form.addRow("Mã sách:", self.code_edit)
        form.addRow("Tên sách:", self.title_edit)
        form.addRow("Tác giả:", self.author_edit)
        form.addRow("Thể loại:", self.category_edit)
        form.addRow("Nhà xuất bản:", self.publisher_edit)
        form.addRow("Năm xuất bản:", self.year_edit)
        form.addRow("Số lượng:", self.quantity_edit)
        form.addRow("Vị trí kệ:", self.shelf_edit)
        form.addRow("Mô tả:", self.description_edit)

        self.cancel_button = QPushButton("Hủy")
        self.save_button = QPushButton("Lưu sách")

        self.cancel_button.clicked.connect(self.reject)
        self.save_button.clicked.connect(self.validate_and_accept)

        buttons = QHBoxLayout()

        buttons.addStretch()
        buttons.addWidget(self.cancel_button)
        buttons.addWidget(self.save_button)

        layout = QVBoxLayout()

        layout.addLayout(form)
        layout.addLayout(buttons)

        self.setLayout(layout)

    def load_book_data(self):

        self.code_edit.setText(self.book["book_code"])
        self.title_edit.setText(self.book["title"])
        self.author_edit.setText(self.book["author"] or "")
        self.category_edit.setCurrentText(self.book["category"] or "")
        self.publisher_edit.setCurrentText(self.book["publisher"] or "")

        if self.book["publish_year"]:
            self.year_edit.setValue(self.book["publish_year"])

        self.quantity_edit.setValue(
            self.book["quantity"] or 1
        )

        self.shelf_edit.setText(
            self.book["shelf"] or ""
        )

        self.description_edit.setPlainText(
            self.book["description"] or ""
        )

    def validate_and_accept(self):

        book_code = self.code_edit.text().strip()
        title = self.title_edit.text().strip()

        if not book_code:
            QMessageBox.warning(
                self,
                "Thiếu thông tin",
                "Vui lòng nhập mã sách."
            )
            return

        if not title:
            QMessageBox.warning(
                self,
                "Thiếu thông tin",
                "Vui lòng nhập tên sách."
            )
            return

        self.accept()

    def get_data(self):

        return {
            "book_code": self.code_edit.text().strip(),
            "title": self.title_edit.text().strip(),
            "author": self.author_edit.text().strip(),
            "category": self.category_edit.currentText().strip(),
            "publisher": self.publisher_edit.currentText().strip(),
            "publish_year": self.year_edit.value(),
            "quantity": self.quantity_edit.value(),
            "shelf": self.shelf_edit.text().strip(),
            "description": self.description_edit.toPlainText().strip()
        }