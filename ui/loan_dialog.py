from PySide6.QtCore import QDate, Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDateEdit,
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QCheckBox,
    QAbstractItemView,
    QHeaderView,
    QLineEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QSpinBox,
    QMessageBox,
    QWidget,
)


class LoanDialog(QDialog):

    def __init__(self, readers, books, parent=None):
        super().__init__(parent)
        self.readers = readers
        self.books = books
        self.reader_combo_rows = []
        self.quantity_spins = []
        self.setWindowTitle("Lập phiếu mượn sách")
        self.setMinimumWidth(980)
        self.resize(1080, 620)
        self.create_widgets()

    def create_widgets(self):
        layout = QVBoxLayout()

        reader_layout = QHBoxLayout()
        reader_layout.addWidget(QLabel("Tìm độc giả:"))
        self.reader_search_edit = QLineEdit()
        self.reader_search_edit.setPlaceholderText(
            "Nhập mã độc giả, họ tên hoặc số điện thoại..."
        )
        self.reader_search_edit.textChanged.connect(self.filter_readers)
        reader_layout.addWidget(self.reader_search_edit)
        self.reader_combo = QComboBox()
        for reader in self.readers:
            self.reader_combo.addItem(
                f'{reader["reader_code"]} - {reader["name"]} - {reader["phone"] or "Chưa có SĐT"}',
                reader["id"],
            )
            self.reader_combo_rows.append(reader)
        reader_layout.addWidget(self.reader_combo)
        layout.addLayout(reader_layout)

        date_layout = QHBoxLayout()
        date_layout.addWidget(QLabel("Ngày mượn:"))
        self.borrow_date_edit = QDateEdit(QDate.currentDate())
        self.borrow_date_edit.setCalendarPopup(True)
        date_layout.addWidget(self.borrow_date_edit)
        date_layout.addWidget(QLabel("Hạn trả:"))
        self.due_date_edit = QDateEdit(QDate.currentDate().addDays(14))
        self.due_date_edit.setCalendarPopup(True)
        date_layout.addWidget(self.due_date_edit)
        layout.addLayout(date_layout)

        book_search_layout = QHBoxLayout()
        book_search_layout.addWidget(QLabel("Tìm sách:"))
        self.book_search_edit = QLineEdit()
        self.book_search_edit.setPlaceholderText("Nhập mã sách hoặc tên sách...")
        self.book_search_edit.textChanged.connect(self.filter_books)
        book_search_layout.addWidget(self.book_search_edit)
        layout.addLayout(book_search_layout)
        layout.addWidget(QLabel("Chọn một hoặc nhiều sách:"))
        self.book_table = QTableWidget()
        self.book_table.setColumnCount(5)
        self.book_table.setHorizontalHeaderLabels(
            ["Chọn", "Mã sách", "Tên sách", "Còn lại", "Số lượng mượn"]
        )
        self.book_table.setSelectionMode(
            QAbstractItemView.SelectionMode.NoSelection
        )
        self.book_table.verticalHeader().setVisible(False)
        self.book_table.setWordWrap(False)
        self.book_table.setMinimumHeight(300)
        self.book_table.setColumnWidth(0, 58)
        self.book_table.setColumnWidth(1, 110)
        self.book_table.setColumnWidth(3, 80)
        self.book_table.setColumnWidth(4, 155)
        header = self.book_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Fixed)
        self.book_table.setRowCount(len(self.books))

        for row, book in enumerate(self.books):
            checkbox = QCheckBox()
            checkbox.setToolTip("Chọn sách này")
            checkbox_layout = QHBoxLayout()
            checkbox_layout.setContentsMargins(0, 0, 0, 0)
            checkbox_layout.addWidget(checkbox, alignment=Qt.AlignmentFlag.AlignCenter)
            checkbox_container = QWidget()
            checkbox_container.setLayout(checkbox_layout)
            self.book_table.setCellWidget(row, 0, checkbox_container)
            self.book_table.setItem(row, 1, QTableWidgetItem(book["book_code"]))
            title_item = QTableWidgetItem(book["title"])
            title_item.setToolTip(book["title"])
            self.book_table.setItem(row, 2, title_item)
            self.book_table.setItem(row, 3, QTableWidgetItem(str(book["quantity"])))

            quantity_spin = QSpinBox()
            quantity_spin.setRange(1, book["quantity"])
            quantity_spin.setValue(1)
            quantity_spin.setButtonSymbols(QSpinBox.ButtonSymbols.NoButtons)
            quantity_spin.setAlignment(Qt.AlignmentFlag.AlignCenter)
            quantity_spin.setFixedSize(48, 32)
            quantity_spin.setObjectName("quantitySpin")
            quantity_spin.setToolTip(
                f"Nhập số lượng từ 1 đến {book['quantity']}"
            )

            decrease_button = QPushButton("-")
            increase_button = QPushButton("+")
            decrease_button.setFixedSize(30, 30)
            increase_button.setFixedSize(30, 30)
            decrease_button.setObjectName("quantityDecrease")
            increase_button.setObjectName("quantityIncrease")
            decrease_button.setToolTip("Giảm số lượng")
            increase_button.setToolTip("Tăng số lượng")
            decrease_button.clicked.connect(
                lambda _checked=False, spin=quantity_spin: spin.setValue(spin.value() - 1)
            )
            increase_button.clicked.connect(
                lambda _checked=False, spin=quantity_spin: spin.setValue(spin.value() + 1)
            )

            quantity_layout = QHBoxLayout()
            quantity_layout.setContentsMargins(2, 2, 2, 2)
            quantity_layout.setSpacing(2)
            quantity_layout.addWidget(decrease_button)
            quantity_layout.addWidget(quantity_spin)
            quantity_layout.addWidget(increase_button)
            quantity_container = QWidget()
            quantity_container.setLayout(quantity_layout)
            quantity_container.setFixedSize(148, 38)
            self.book_table.setCellWidget(row, 4, quantity_container)
            self.quantity_spins.append(quantity_spin)

        layout.addWidget(self.book_table)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Cancel
            | QDialogButtonBox.StandardButton.Ok
        )
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText("Xác nhận mượn")
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText("Hủy")
        buttons.accepted.connect(self.validate_and_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self.setLayout(layout)
        self.setStyleSheet("""
            QDialog {
                background-color: #ffffff;
            }

            QTableWidget {
                background-color: #ffffff;
                color: #172033;
                gridline-color: #e7ebf0;
            }

            QHeaderView::section {
                background-color: #f1f5f9;
                color: #344054;
                font-weight: 700;
                padding: 8px;
            }

            #quantitySpin {
                background-color: #ffffff;
                color: #172033;
                border: 1px solid #94a3b8;
                border-radius: 5px;
                padding: 2px;
                font-size: 15px;
                font-weight: 700;
            }

            #quantityDecrease, #quantityIncrease {
                background-color: #0f766e;
                color: #ffffff;
                border: none;
                border-radius: 5px;
                padding: 0;
                font-size: 17px;
                font-weight: 700;
            }

            #quantityDecrease:hover, #quantityIncrease:hover {
                background-color: #115e59;
            }
        """)

    def filter_readers(self, text):
        keyword = text.strip().lower()
        current_reader_id = self.reader_combo.currentData()
        self.reader_combo.blockSignals(True)
        self.reader_combo.clear()

        for reader in self.reader_combo_rows:
            searchable = " ".join([
                reader["reader_code"] or "",
                reader["name"] or "",
                reader["phone"] or "",
            ]).lower()
            if keyword and keyword not in searchable:
                continue

            self.reader_combo.addItem(
                f'{reader["reader_code"]} - {reader["name"]} - {reader["phone"] or "Chưa có SĐT"}',
                reader["id"],
            )

        selected_index = self.reader_combo.findData(current_reader_id)
        self.reader_combo.setCurrentIndex(max(selected_index, 0))
        self.reader_combo.blockSignals(False)

    def filter_books(self, text):
        keyword = text.strip().lower()
        for row, book in enumerate(self.books):
            searchable = " ".join([
                book["book_code"] or "",
                book["title"] or "",
                book["author"] or "",
            ]).lower()
            self.book_table.setRowHidden(
                row,
                bool(keyword and keyword not in searchable),
            )

    def validate_and_accept(self):
        if self.reader_combo.currentIndex() < 0:
            QMessageBox.warning(self, "Thiếu thông tin", "Vui lòng chọn độc giả.")
            return

        if self.due_date_edit.date() < self.borrow_date_edit.date():
            QMessageBox.warning(
                self,
                "Ngày không hợp lệ",
                "Hạn trả không được trước ngày mượn.",
            )
            return

        if not any(
            self.book_table.cellWidget(row, 0).findChild(QCheckBox).isChecked()
            for row in range(self.book_table.rowCount())
        ):
            QMessageBox.warning(
                self,
                "Chưa chọn sách",
                "Vui lòng chọn ít nhất một sách.",
            )
            return

        self.accept()

    def get_data(self):
        items = []
        for row, book in enumerate(self.books):
            checkbox = self.book_table.cellWidget(row, 0).findChild(QCheckBox)
            if not checkbox.isChecked():
                continue

            items.append((book["id"], self.quantity_spins[row].value()))

        return {
            "reader_id": self.reader_combo.currentData(),
            "borrow_date": self.borrow_date_edit.date().toString("yyyy-MM-dd"),
            "due_date": self.due_date_edit.date().toString("yyyy-MM-dd"),
            "items": items,
        }
