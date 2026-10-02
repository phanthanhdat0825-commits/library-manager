import csv
import shutil
import sqlite3
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QLineEdit,
    QTableWidget,
    QTableWidgetItem,
    QMessageBox,
    QLabel,
    QHeaderView,
    QFrame,
    QStackedWidget,
    QTabWidget,
    QAbstractItemView,
    QCheckBox,
    QComboBox,
    QDateEdit,
    QFileDialog,
    QFormLayout,
    QInputDialog,
    QPlainTextEdit,
    QSpinBox,
)

from PySide6.QtCore import QDate, QSettings, Qt

from database.database import (
    get_all_books,
    search_books,
    add_book as db_add_book,
    update_book,
    delete_book,
    get_all_readers,
    search_readers,
    add_reader as db_add_reader,
    update_reader,
    delete_reader,
    create_loan,
    get_all_loans,
    get_loan_counts,
    get_report_statistics,
    clear_all_data,
    close_orphaned_loans,
    extend_loan,
    get_fines,
    mark_fine_paid,
    add_category,
    add_publisher,
    DATABASE_PATH,
    return_loan,
)
from remote_client import (
    RemoteServiceError,
    decide_request as decide_remote_request,
    get_requests as get_remote_requests,
    sync_catalog as sync_remote_catalog,
)

from ui.book_dialog import BookDialog
from ui.reader_dialog import ReaderDialog
from ui.loan_dialog import LoanDialog


class MainWindow(QMainWindow):

    def __init__(self, user=None):
        super().__init__()

        self.current_user = user

        self.setWindowTitle("Library Manager")
        self.resize(1280, 750)

        self.setup_ui()
        self.load_books()

    # =====================================================
    # GIAO DIỆN CHÍNH
    # =====================================================

    def setup_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QHBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # =================================================
        # SIDEBAR
        # =================================================
        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(220)

        sidebar_layout = QVBoxLayout()
        sidebar_layout.setContentsMargins(15, 20, 15, 20)

        logo = QLabel("📚  LIBRARY")
        logo.setObjectName("logo")
        sidebar_layout.addWidget(logo)
        sidebar_layout.addSpacing(30)

        self.dashboard_button = QPushButton("🏠   Tổng quan")
        self.books_button = QPushButton("📖   Sách / Tài liệu")
        self.readers_button = QPushButton("👥  Độc giả")
        self.loans_button = QPushButton("🔄  Mượn / Trả sách")
        self.remote_requests_button = QPushButton("🌐  Yêu cầu trực tuyến")
        self.history_button = QPushButton("🕘  Lịch sử mượn / trả")
        self.reports_button = QPushButton("📊  Báo cáo / Thống kê")
        self.settings_button = QPushButton("⚙   Cài đặt")

        navigation_buttons = [
            self.dashboard_button,
            self.books_button,
            self.readers_button,
            self.loans_button,
            self.remote_requests_button,
            self.history_button,
            self.reports_button,
            self.settings_button,
        ]
        for button in navigation_buttons:
            button.setCheckable(True)
            button.setToolTip(button.text().strip())

        self.dashboard_button.setObjectName("menuButton")
        self.books_button.setObjectName("menuButton")
        self.readers_button.setObjectName("menuButton")
        self.loans_button.setObjectName("menuButton")
        self.remote_requests_button.setObjectName("menuButton")
        self.history_button.setObjectName("menuButton")
        self.reports_button.setObjectName("menuButton")
        self.settings_button.setObjectName("menuButton")

        sidebar_layout.addWidget(self.dashboard_button)
        sidebar_layout.addWidget(self.books_button)
        sidebar_layout.addWidget(self.readers_button)
        sidebar_layout.addWidget(self.loans_button)
        sidebar_layout.addWidget(self.remote_requests_button)
        sidebar_layout.addWidget(self.history_button)
        sidebar_layout.addWidget(self.reports_button)
        sidebar_layout.addWidget(self.settings_button)
        sidebar_layout.addStretch()

        version = QLabel("Library Manager\nV1.0")
        version.setObjectName("version")
        sidebar_layout.addWidget(version)

        sidebar.setLayout(sidebar_layout)

        # =================================================
        # CONTENT
        # =================================================
        content = QWidget()
        content_layout = QVBoxLayout()
        content_layout.setContentsMargins(30, 25, 30, 25)

        header_layout = QHBoxLayout()
        self.page_title = QLabel("Tổng quan")
        self.page_title.setObjectName("pageTitle")
        header_layout.addWidget(self.page_title)
        header_layout.addStretch()
        content_layout.addLayout(header_layout)

        self.pages = QStackedWidget()
        self.dashboard_page = self.create_dashboard_page()
        self.books_page = self.create_books_page()
        self.readers_page = self.create_readers_page()
        self.loans_page = self.create_loans_page()
        self.remote_requests_page = self.create_remote_requests_page()
        self.history_page = self.create_history_page()
        self.reports_page = self.create_reports_page()
        self.settings_page = self.create_settings_page()

        self.pages.addWidget(self.dashboard_page)
        self.pages.addWidget(self.books_page)
        self.pages.addWidget(self.readers_page)
        self.pages.addWidget(self.loans_page)
        self.pages.addWidget(self.remote_requests_page)
        self.pages.addWidget(self.history_page)
        self.pages.addWidget(self.reports_page)
        self.pages.addWidget(self.settings_page)

        content_layout.addWidget(self.pages)
        content.setLayout(content_layout)

        main_layout.addWidget(sidebar)
        main_layout.addWidget(content)
        central_widget.setLayout(main_layout)

        # =================================================
        # EVENTS
        # =================================================
        self.dashboard_button.clicked.connect(self.show_dashboard)
        self.books_button.clicked.connect(self.show_books)
        self.readers_button.clicked.connect(self.show_readers)
        self.loans_button.clicked.connect(self.show_loans)
        self.remote_requests_button.clicked.connect(self.show_remote_requests)
        self.history_button.clicked.connect(self.show_history)
        self.reports_button.clicked.connect(self.show_reports)
        self.settings_button.clicked.connect(self.show_settings)

        self.apply_styles()
        self.apply_saved_theme()
        self.set_active_navigation(self.dashboard_button)
        if self.current_user and self.current_user["role"] != "admin":
            self.settings_button.setEnabled(False)

    def set_active_navigation(self, active_button):
        for button in (
            self.dashboard_button,
            self.books_button,
            self.readers_button,
            self.loans_button,
            self.remote_requests_button,
            self.history_button,
            self.reports_button,
            self.settings_button,
        ):
            button.setChecked(button is active_button)

    # =====================================================
    # DASHBOARD
    # =====================================================

    def create_dashboard_page(self):
        page = QWidget()
        layout = QVBoxLayout()
        layout.setSpacing(20)

        dashboard_header = QHBoxLayout()
        dashboard_heading = QLabel("Tổng quan thư viện")
        dashboard_heading.setObjectName("sectionTitle")
        dashboard_header.addWidget(dashboard_heading)
        dashboard_header.addStretch()
        self.dashboard_refresh_button = QPushButton("↻  Cập nhật")
        self.dashboard_refresh_button.setToolTip("Làm mới toàn bộ số liệu tổng quan")
        self.dashboard_refresh_button.clicked.connect(self.update_dashboard)
        dashboard_header.addWidget(self.dashboard_refresh_button)
        layout.addLayout(dashboard_header)

        quick_actions = QHBoxLayout()
        quick_actions.addWidget(QLabel("Truy cập nhanh:"))
        self.dashboard_add_book_button = QPushButton("＋  Thêm sách")
        self.dashboard_add_reader_button = QPushButton("＋  Thêm độc giả")
        self.dashboard_create_loan_button = QPushButton("🔄  Lập phiếu mượn")
        self.dashboard_add_book_button.setObjectName("primaryButton")
        self.dashboard_add_reader_button.setObjectName("primaryButton")
        self.dashboard_create_loan_button.setObjectName("editButton")
        self.dashboard_add_book_button.clicked.connect(self.add_book)
        self.dashboard_add_reader_button.clicked.connect(self.add_reader)
        self.dashboard_create_loan_button.clicked.connect(self.add_loan)
        quick_actions.addWidget(self.dashboard_add_book_button)
        quick_actions.addWidget(self.dashboard_add_reader_button)
        quick_actions.addWidget(self.dashboard_create_loan_button)
        quick_actions.addStretch()
        layout.addLayout(quick_actions)

        self.dashboard_alert_label = QLabel("Đang kiểm tra cảnh báo...")
        self.dashboard_alert_label.setObjectName("statusLabel")
        layout.addWidget(self.dashboard_alert_label)

        # -----------------------------------------------
        # Cards
        # -----------------------------------------------

        cards_layout = QVBoxLayout()

        first_row = QHBoxLayout()
        self.total_card = self.create_stat_card("📚", "Tổng số đầu sách", "0")
        self.quantity_card = self.create_stat_card("📦", "Tổng số bản sách", "0")
        self.reader_card = self.create_stat_card("👥", "Tổng số độc giả", "0")

        first_row.addWidget(self.total_card)
        first_row.addWidget(self.quantity_card)
        first_row.addWidget(self.reader_card)

        second_row = QHBoxLayout()
        self.category_card = self.create_stat_card("🏷", "Số lượng thể loại", "0")
        self.borrowed_card = self.create_stat_card("📖", "Phiếu đang mượn", "0")
        self.overdue_card = self.create_stat_card("⚠", "Phiếu quá hạn", "0")

        second_row.addWidget(self.category_card)
        second_row.addWidget(self.borrowed_card)
        second_row.addWidget(self.overdue_card)

        cards_layout.addLayout(first_row)
        cards_layout.addLayout(second_row)
        layout.addLayout(cards_layout)

        # -----------------------------------------------
        # Recent activities
        # -----------------------------------------------

        activity_box = QFrame()
        activity_box.setObjectName("welcomeBox")
        activity_layout = QVBoxLayout()

        activity_title = QLabel("Các hoạt động gần đây")
        activity_title.setObjectName("sectionTitle")
        activity_layout.addWidget(activity_title)

        self.activity_table = QTableWidget()
        self.activity_table.setColumnCount(3)
        self.activity_table.setHorizontalHeaderLabels(["Hoạt động", "Đối tượng", "Thời gian"])
        self.activity_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.activity_table.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        self.activity_table.setAlternatingRowColors(True)
        self.activity_table.verticalHeader().setVisible(False)
        self.activity_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )
        activity_layout.addWidget(self.activity_table)

        activity_box.setLayout(activity_layout)
        layout.addWidget(activity_box)

        page.setLayout(layout)
        return page

    # =====================================================
    # STAT CARD
    # =====================================================

    def create_stat_card(self, icon, title, value):
        card = QFrame()
        card.setObjectName("statCard")

        card_layout = QVBoxLayout()

        icon_label = QLabel(icon)
        icon_label.setObjectName("cardIcon")

        title_label = QLabel(title)
        title_label.setObjectName("cardTitle")

        value_label = QLabel(value)
        value_label.setObjectName("cardValue")

        card_layout.addWidget(icon_label)
        card_layout.addWidget(title_label)
        card_layout.addWidget(value_label)

        card.setLayout(card_layout)
        card.value_label = value_label
        return card

    # =====================================================
    # TRANG SÁCH
    # =====================================================

    def create_books_page(self):
        page = QWidget()
        layout = QVBoxLayout()
        self.book_page = 1
        self.book_page_size = 25
        self.book_list = []
        self.filtered_books = []

        # -----------------------------------------------
        # Search
        # -----------------------------------------------

        search_layout = QHBoxLayout()
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Tìm theo mã sách, tên sách, tác giả, thể loại...")

        self.search_button = QPushButton("🔍  Tìm kiếm")
        self.reset_button = QPushButton("↻  Hiển thị tất cả")

        search_layout.addWidget(self.search_edit)
        search_layout.addWidget(self.search_button)
        search_layout.addWidget(self.reset_button)
        layout.addLayout(search_layout)

        filter_layout = QHBoxLayout()
        filter_layout.addWidget(QLabel("Thể loại:"))
        self.category_filter = QComboBox()
        self.category_filter.addItem("Tất cả thể loại")
        self.category_filter.setMinimumWidth(150)
        filter_layout.addWidget(self.category_filter)

        filter_layout.addWidget(QLabel("Sắp xếp:"))
        self.book_sort_combo = QComboBox()
        self.book_sort_combo.addItems([
            "Tên sách A-Z",
            "Tên sách Z-A",
            "Mới thêm trước",
            "Số lượng cao-thấp",
            "Số lượng thấp-cao",
        ])
        self.book_sort_combo.setMinimumWidth(165)
        filter_layout.addWidget(self.book_sort_combo)

        filter_layout.addWidget(QLabel("Hiển thị:"))
        self.book_page_size_combo = QComboBox()
        self.book_page_size_combo.addItems(["25 dòng", "50 dòng", "100 dòng"])
        filter_layout.addWidget(self.book_page_size_combo)
        filter_layout.addStretch()
        layout.addLayout(filter_layout)

        # -----------------------------------------------
        # Buttons
        # -----------------------------------------------

        button_layout = QHBoxLayout()
        self.add_button = QPushButton("＋  Thêm sách")
        self.add_button.setObjectName("primaryButton")
        self.add_button.setToolTip("Thêm sách mới vào thư viện")

        self.edit_button = QPushButton("Sửa sách")
        self.edit_button.setObjectName("editButton")
        self.edit_button.setToolTip("Sửa thông tin sách đang chọn")

        self.delete_button = QPushButton("🗑  Xóa")
        self.delete_button.setObjectName("deleteButton")
        self.delete_button.setToolTip("Xóa sách đang chọn")
        self.book_qr_button = QPushButton("▦  QR sách")
        self.book_qr_button.setToolTip("Tạo mã QR cho sách đang chọn")

        button_layout.addWidget(self.add_button)
        button_layout.addWidget(self.edit_button)
        button_layout.addWidget(self.delete_button)
        button_layout.addWidget(self.book_qr_button)
        button_layout.addStretch()
        layout.addLayout(button_layout)

        # -----------------------------------------------
        # Table
        # -----------------------------------------------

        self.table = QTableWidget()
        columns = [
            "Mã sách",
            "Tên sách",
            "Thể loại",
            "Số lượng",
            "Vị trí kệ",
            "Tác giả",
            "Nhà xuất bản",
            "Năm xuất bản",
        ]
        self.table.setColumnCount(len(columns))
        self.table.setHorizontalHeaderLabels(columns)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        self.table.setWordWrap(False)
        self.table.setHorizontalScrollMode(
            QAbstractItemView.ScrollMode.ScrollPerPixel
        )

        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Interactive)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Interactive)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.Interactive)
        header.setSectionResizeMode(6, QHeaderView.ResizeMode.Interactive)
        header.setSectionResizeMode(7, QHeaderView.ResizeMode.Fixed)
        header.resizeSection(0, 105)
        header.resizeSection(1, 300)
        header.resizeSection(2, 160)
        header.resizeSection(3, 80)
        header.resizeSection(4, 95)
        header.resizeSection(5, 180)
        header.resizeSection(6, 155)
        header.resizeSection(7, 105)

        layout.addWidget(self.table)

        # -----------------------------------------------
        # Status
        # -----------------------------------------------

        self.status_label = QLabel("Sẵn sàng")
        layout.addWidget(self.status_label)

        pagination_layout = QHBoxLayout()
        self.previous_books_button = QPushButton("‹ Trang trước")
        self.next_books_button = QPushButton("Trang sau ›")
        self.book_page_label = QLabel("Trang 1 / 1")
        pagination_layout.addStretch()
        pagination_layout.addWidget(self.previous_books_button)
        pagination_layout.addWidget(self.book_page_label)
        pagination_layout.addWidget(self.next_books_button)
        layout.addLayout(pagination_layout)

        page.setLayout(layout)

        # -----------------------------------------------
        # Events
        # -----------------------------------------------

        self.add_button.clicked.connect(self.add_book)
        self.edit_button.clicked.connect(self.edit_book)
        self.delete_button.clicked.connect(self.delete_selected_book)
        self.book_qr_button.clicked.connect(self.create_book_qr)
        self.search_button.clicked.connect(self.search)
        self.reset_button.clicked.connect(self.reset_book_filters)
        self.search_edit.returnPressed.connect(self.search)
        self.category_filter.currentIndexChanged.connect(self.apply_book_filters)
        self.book_sort_combo.currentIndexChanged.connect(self.apply_book_filters)
        self.book_page_size_combo.currentIndexChanged.connect(self.apply_book_filters)
        self.previous_books_button.clicked.connect(self.previous_book_page)
        self.next_books_button.clicked.connect(self.next_book_page)
        self.table.doubleClicked.connect(self.edit_book)

        return page

    # =====================================================
    # TRANG ĐỘC GIẢ
    # =====================================================

    def create_readers_page(self):
        page = QWidget()
        layout = QVBoxLayout()

        # =========================
        # TIÊU ĐỀ
        # =========================

        title = QLabel("Danh sách độc giả")
        title.setObjectName("pageTitle")
        layout.addWidget(title)

        # =========================
        # THANH TÌM KIẾM
        # =========================

        search_layout = QHBoxLayout()
        self.reader_search_edit = QLineEdit()
        self.reader_search_edit.setPlaceholderText(
            "Tìm kiếm theo mã, họ tên, số điện thoại, email..."
        )

        self.reader_search_button = QPushButton("🔍  Tìm kiếm")
        self.reader_reset_button = QPushButton("↻  Hiển thị tất cả")

        search_layout.addWidget(self.reader_search_edit)
        search_layout.addWidget(self.reader_search_button)
        search_layout.addWidget(self.reader_reset_button)
        layout.addLayout(search_layout)

        # =========================
        # CÁC NÚT CHỨC NĂNG
        # =========================

        button_layout = QHBoxLayout()
        self.reader_add_button = QPushButton("＋  Thêm độc giả")
        self.reader_add_button.setObjectName("primaryButton")
        self.reader_add_button.setToolTip("Thêm độc giả mới")

        self.reader_edit_button = QPushButton("Sửa độc giả")
        self.reader_edit_button.setObjectName("editButton")
        self.reader_edit_button.setToolTip("Sửa thông tin độc giả đang chọn")

        self.reader_delete_button = QPushButton("🗑  Xóa")
        self.reader_delete_button.setObjectName("deleteButton")
        self.reader_delete_button.setToolTip("Xóa độc giả đang chọn")
        self.reader_qr_button = QPushButton("▦  QR độc giả")
        self.reader_qr_button.setToolTip("Tạo mã QR cho độc giả đang chọn")

        button_layout.addWidget(self.reader_add_button)
        button_layout.addWidget(self.reader_edit_button)
        button_layout.addWidget(self.reader_delete_button)
        button_layout.addWidget(self.reader_qr_button)
        button_layout.addStretch()
        layout.addLayout(button_layout)

        # =========================
        # BẢNG ĐỘC GIẢ
        # =========================

        self.reader_table = QTableWidget()
        columns = [
            "ID",
            "Mã độc giả",
            "Họ và tên",
            "Số điện thoại",
            "Email",
            "Lớp / Đơn vị",
            "Ngày tạo",
        ]
        self.reader_table.setColumnCount(len(columns))
        self.reader_table.setHorizontalHeaderLabels(columns)
        self.reader_table.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows
        )
        self.reader_table.setSelectionMode(
            QAbstractItemView.SelectionMode.SingleSelection
        )
        self.reader_table.setEditTriggers(
            QAbstractItemView.EditTrigger.NoEditTriggers
        )
        self.reader_table.setAlternatingRowColors(True)
        self.reader_table.verticalHeader().setVisible(False)

        header = self.reader_table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.reader_table)

        # =========================
        # TRẠNG THÁI
        # =========================

        self.reader_status_label = QLabel("Chưa có dữ liệu")
        self.reader_status_label.setObjectName("statusLabel")
        layout.addWidget(self.reader_status_label)

        page.setLayout(layout)

        self.reader_add_button.clicked.connect(self.add_reader)
        self.reader_edit_button.clicked.connect(self.edit_reader)
        self.reader_delete_button.clicked.connect(self.delete_selected_reader)
        self.reader_qr_button.clicked.connect(self.create_reader_qr)
        self.reader_search_button.clicked.connect(self.search_readers)
        self.reader_reset_button.clicked.connect(self.load_readers)
        self.reader_table.doubleClicked.connect(self.edit_reader)

        return page

    # =====================================================
    # TRANG CÀI ĐẶT
    # =====================================================

    def create_settings_page(self):
        page = QWidget()
        layout = QVBoxLayout()

        title = QLabel("Cài đặt")
        title.setObjectName("sectionTitle")
        layout.addWidget(title)

        settings = QSettings("LibraryManager", "LibraryManager")
        form = QFormLayout()

        self.library_name_edit = QLineEdit(settings.value("library/name", "Library Manager"))
        self.library_info_edit = QPlainTextEdit(settings.value("library/info", ""))
        self.library_info_edit.setMaximumHeight(80)
        self.loan_days_spin = QSpinBox()
        self.loan_days_spin.setRange(1, 365)
        self.loan_days_spin.setValue(int(settings.value("loan/days", 14)))
        self.overdue_rule_edit = QLineEdit(
            settings.value("loan/overdue_rule", "Phạt theo quy định thư viện")
        )
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["Sáng", "Tối"])
        self.theme_combo.setCurrentText(settings.value("appearance/theme", "Sáng"))
        self.remote_api_url_edit = QLineEdit(settings.value("remote/api_url", ""))
        self.remote_api_url_edit.setPlaceholderText("https://thu-vien.example.edu")
        self.remote_admin_token_edit = QLineEdit(settings.value("remote/admin_token", ""))
        self.remote_admin_token_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.remote_admin_token_edit.setPlaceholderText("Khóa quản trị do máy chủ cấp")

        form.addRow(self.create_setting_label("Tên thư viện:"), self.library_name_edit)
        form.addRow(self.create_setting_label("Thông tin thư viện:"), self.library_info_edit)
        form.addRow(self.create_setting_label("Số ngày được mượn:"), self.loan_days_spin)
        form.addRow(self.create_setting_label("Quy định quá hạn:"), self.overdue_rule_edit)
        form.addRow(self.create_setting_label("Thiết lập giao diện:"), self.theme_combo)
        form.addRow(self.create_setting_label("Địa chỉ dịch vụ online:"), self.remote_api_url_edit)
        form.addRow(self.create_setting_label("Khóa quản trị online:"), self.remote_admin_token_edit)
        layout.addLayout(form)

        save_button = QPushButton("Lưu thiết lập")
        save_button.setObjectName("primaryButton")
        save_button.clicked.connect(self.save_settings)
        layout.addWidget(save_button)

        data_layout = QHBoxLayout()
        backup_button = QPushButton("Sao lưu cơ sở dữ liệu")
        restore_button = QPushButton("Khôi phục dữ liệu")
        repair_button = QPushButton("Dọn phiếu sách đã xóa")
        clear_button = QPushButton("Xóa dữ liệu")
        clear_button.setObjectName("deleteButton")
        backup_button.clicked.connect(self.backup_database)
        restore_button.clicked.connect(self.restore_database)
        repair_button.clicked.connect(self.repair_orphaned_loans)
        clear_button.clicked.connect(self.clear_database)
        data_layout.addWidget(backup_button)
        data_layout.addWidget(restore_button)
        data_layout.addWidget(repair_button)
        data_layout.addWidget(clear_button)
        data_layout.addStretch()
        layout.addLayout(data_layout)

        io_layout = QHBoxLayout()
        import_books_button = QPushButton("📥 Nhập sách CSV")
        import_readers_button = QPushButton("📥 Nhập độc giả CSV")
        export_books_button = QPushButton("📤 Xuất sách CSV")
        export_readers_button = QPushButton("📤 Xuất độc giả CSV")
        import_books_button.clicked.connect(self.import_books_csv)
        import_readers_button.clicked.connect(self.import_readers_csv)
        export_books_button.clicked.connect(self.export_books_csv)
        export_readers_button.clicked.connect(self.export_readers_csv)
        io_layout.addWidget(import_books_button)
        io_layout.addWidget(import_readers_button)
        io_layout.addWidget(export_books_button)
        io_layout.addWidget(export_readers_button)
        io_layout.addStretch()
        layout.addLayout(io_layout)

        version = QLabel("Library Manager phiên bản 1.0")
        version.setObjectName("statusLabel")
        layout.addWidget(version)
        layout.addStretch()

        page.setLayout(layout)
        return page

    def create_setting_label(self, text):
        label = QLabel(text)
        label.setObjectName("settingLabel")
        return label

    # =====================================================
    # TRANG MƯỢN / TRẢ SÁCH
    # =====================================================

    def create_loans_page(self):
        page = QWidget()
        layout = QVBoxLayout()
        self.loan_status_filter = "Tất cả"
        self.loan_sort_mode = "date"

        title = QLabel("Quản lý mượn / trả sách")
        title.setObjectName("pageTitle")
        layout.addWidget(title)

        search_layout = QHBoxLayout()
        search_layout.addWidget(QLabel("Tìm độc giả:"))
        self.loan_reader_search_edit = QLineEdit()
        self.loan_reader_search_edit.setPlaceholderText(
            "Nhập mã độc giả hoặc họ tên..."
        )
        self.loan_reader_search_edit.returnPressed.connect(self.load_loans)
        search_layout.addWidget(self.loan_reader_search_edit)
        self.search_loans_button = QPushButton("🔍  Tìm kiếm")
        self.search_loans_button.clicked.connect(self.load_loans)
        search_layout.addWidget(self.search_loans_button)
        self.reset_loan_search_button = QPushButton("↻  Hiển thị tất cả")
        self.reset_loan_search_button.clicked.connect(self.reset_loan_search)
        search_layout.addWidget(self.reset_loan_search_button)
        layout.addLayout(search_layout)

        button_layout = QHBoxLayout()
        self.create_loan_button = QPushButton("＋  Lập phiếu mượn")
        self.create_loan_button.setObjectName("primaryButton")
        self.create_loan_button.setToolTip("Tạo phiếu mượn mới")
        self.return_loan_button = QPushButton("↩  Trả sách")
        self.return_loan_button.setObjectName("editButton")
        self.return_loan_button.setToolTip("Xác nhận trả sách cho phiếu đã chọn")
        self.refresh_loans_button = QPushButton("↻  Làm mới")
        self.refresh_loans_button.setToolTip("Tải lại danh sách phiếu mượn")
        self.extend_loan_button = QPushButton("📅  Gia hạn")
        self.extend_loan_button.setToolTip("Gia hạn phiếu đang chọn")
        self.fine_loan_button = QPushButton("💰  Tạo phạt")
        self.fine_loan_button.setToolTip("Tạo phạt cho phiếu quá hạn")

        button_layout.addWidget(self.create_loan_button)
        button_layout.addWidget(self.return_loan_button)
        button_layout.addWidget(self.refresh_loans_button)
        button_layout.addWidget(self.extend_loan_button)
        button_layout.addWidget(self.fine_loan_button)
        button_layout.addStretch()
        layout.addLayout(button_layout)

        filter_layout = QHBoxLayout()
        filter_layout.addWidget(QLabel("Lọc trạng thái:"))
        self.all_loans_button = QPushButton("Tất cả")
        self.returned_loans_button = QPushButton("Đã trả")
        self.active_loans_button = QPushButton("Đang mượn")
        filter_layout.addWidget(self.all_loans_button)
        filter_layout.addWidget(self.returned_loans_button)
        filter_layout.addWidget(self.active_loans_button)
        filter_layout.addSpacing(18)
        filter_layout.addWidget(QLabel("Sắp xếp:"))
        self.sort_by_date_button = QPushButton("Theo ngày")
        self.sort_by_due_button = QPushButton("Gần tới hạn")
        filter_layout.addWidget(self.sort_by_date_button)
        filter_layout.addWidget(self.sort_by_due_button)
        filter_layout.addStretch()
        layout.addLayout(filter_layout)

        self.loan_table = QTableWidget()
        self.loan_table.setColumnCount(7)
        self.loan_table.setHorizontalHeaderLabels([
            "Độc giả",
            "Sách",
            "Số lượng",
            "Ngày mượn",
            "Hạn trả",
            "Ngày trả",
            "Trạng thái",
        ])
        self.loan_table.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows
        )
        self.loan_table.setSelectionMode(
            QAbstractItemView.SelectionMode.SingleSelection
        )
        self.loan_table.setEditTriggers(
            QAbstractItemView.EditTrigger.NoEditTriggers
        )
        self.loan_table.setAlternatingRowColors(True)
        self.loan_table.verticalHeader().setVisible(False)
        self.loan_table.setWordWrap(False)
        loan_header = self.loan_table.horizontalHeader()
        loan_header.setSectionResizeMode(0, QHeaderView.ResizeMode.Interactive)
        loan_header.setSectionResizeMode(1, QHeaderView.ResizeMode.Interactive)
        loan_header.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        loan_header.setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
        loan_header.setSectionResizeMode(4, QHeaderView.ResizeMode.Fixed)
        loan_header.setSectionResizeMode(5, QHeaderView.ResizeMode.Fixed)
        loan_header.setSectionResizeMode(6, QHeaderView.ResizeMode.Fixed)
        loan_header.resizeSection(0, 190)
        loan_header.resizeSection(1, 310)
        loan_header.resizeSection(2, 75)
        loan_header.resizeSection(3, 105)
        loan_header.resizeSection(4, 105)
        loan_header.resizeSection(5, 105)
        loan_header.resizeSection(6, 105)
        layout.addWidget(self.loan_table)

        self.loan_status_label = QLabel("Chưa có phiếu mượn")
        self.loan_status_label.setObjectName("statusLabel")
        layout.addWidget(self.loan_status_label)

        self.create_loan_button.clicked.connect(self.add_loan)
        self.return_loan_button.clicked.connect(self.return_selected_loan)
        self.refresh_loans_button.clicked.connect(self.load_loans)
        self.extend_loan_button.clicked.connect(self.extend_selected_loan)
        self.fine_loan_button.clicked.connect(self.fine_selected_loan)
        self.all_loans_button.clicked.connect(lambda: self.set_loan_status_filter("Tất cả"))
        self.returned_loans_button.clicked.connect(lambda: self.set_loan_status_filter("Đã trả"))
        self.active_loans_button.clicked.connect(lambda: self.set_loan_status_filter("Đang mượn"))
        self.sort_by_date_button.clicked.connect(lambda: self.set_loan_sort("date"))
        self.sort_by_due_button.clicked.connect(lambda: self.set_loan_sort("due"))

        page.setLayout(layout)
        return page

    def create_remote_requests_page(self):
        page = QWidget()
        layout = QVBoxLayout()

        title_row = QHBoxLayout()
        title = QLabel("Yêu cầu mượn trực tuyến")
        title.setObjectName("pageTitle")
        title_row.addWidget(title)
        title_row.addStretch()
        self.remote_request_filter = QComboBox()
        self.remote_request_filter.addItem("Đang chờ", "pending")
        self.remote_request_filter.addItem("Đã duyệt", "approved")
        self.remote_request_filter.addItem("Đã từ chối", "rejected")
        self.remote_request_filter.addItem("Tất cả", "all")
        title_row.addWidget(self.remote_request_filter)
        self.sync_remote_catalog_button = QPushButton("Đồng bộ danh mục web")
        title_row.addWidget(self.sync_remote_catalog_button)
        self.refresh_remote_requests_button = QPushButton("Làm mới yêu cầu")
        title_row.addWidget(self.refresh_remote_requests_button)
        layout.addLayout(title_row)

        self.remote_request_table = QTableWidget()
        self.remote_request_table.setColumnCount(6)
        self.remote_request_table.setHorizontalHeaderLabels([
            "Mã yêu cầu", "Người yêu cầu", "Mã độc giả", "Tài liệu", "Ngày gửi", "Trạng thái",
        ])
        self.remote_request_table.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows
        )
        self.remote_request_table.setSelectionMode(
            QAbstractItemView.SelectionMode.SingleSelection
        )
        self.remote_request_table.setEditTriggers(
            QAbstractItemView.EditTrigger.NoEditTriggers
        )
        self.remote_request_table.setAlternatingRowColors(True)
        self.remote_request_table.verticalHeader().setVisible(False)
        self.remote_request_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )
        layout.addWidget(self.remote_request_table, 3)

        self.remote_request_details = QPlainTextEdit()
        self.remote_request_details.setReadOnly(True)
        self.remote_request_details.setMaximumHeight(135)
        self.remote_request_details.setPlaceholderText("Chọn một yêu cầu để xem thông tin chi tiết.")
        layout.addWidget(self.remote_request_details)

        action_row = QHBoxLayout()
        self.approve_remote_request_button = QPushButton("Duyệt và lập phiếu mượn")
        self.approve_remote_request_button.setObjectName("primaryButton")
        self.reject_remote_request_button = QPushButton("Từ chối yêu cầu")
        self.reject_remote_request_button.setObjectName("deleteButton")
        self.remote_request_status_label = QLabel("Chưa tải yêu cầu")
        self.remote_request_status_label.setObjectName("statusLabel")
        action_row.addWidget(self.approve_remote_request_button)
        action_row.addWidget(self.reject_remote_request_button)
        action_row.addStretch()
        action_row.addWidget(self.remote_request_status_label)
        layout.addLayout(action_row)

        self.remote_request_cache = []
        self.remote_request_filter.currentIndexChanged.connect(self.load_remote_requests)
        self.refresh_remote_requests_button.clicked.connect(self.load_remote_requests)
        self.sync_remote_catalog_button.clicked.connect(self.sync_online_catalog)
        self.approve_remote_request_button.clicked.connect(self.approve_remote_request)
        self.reject_remote_request_button.clicked.connect(self.reject_remote_request)
        self.remote_request_table.itemSelectionChanged.connect(self.show_remote_request_details)
        self.remote_request_table.itemSelectionChanged.connect(self.update_remote_request_actions)

        page.setLayout(layout)
        return page

    def create_history_page(self):
        page = QWidget()
        layout = QVBoxLayout()

        title = QLabel("Lịch sử mượn / trả")
        title.setObjectName("pageTitle")
        layout.addWidget(title)

        first_filter_row = QHBoxLayout()
        first_filter_row.addWidget(QLabel("Mã phiếu:"))
        self.history_loan_search = QLineEdit()
        self.history_loan_search.setPlaceholderText("Ví dụ: PM001")
        first_filter_row.addWidget(self.history_loan_search)

        first_filter_row.addWidget(QLabel("Độc giả:"))
        self.history_reader_search = QLineEdit()
        self.history_reader_search.setPlaceholderText("Mã hoặc tên độc giả")
        first_filter_row.addWidget(self.history_reader_search)

        first_filter_row.addWidget(QLabel("Trạng thái:"))
        self.history_status_combo = QComboBox()
        self.history_status_combo.addItems([
            "Tất cả",
            "Đang mượn",
            "Đã trả",
            "Quá hạn",
        ])
        first_filter_row.addWidget(self.history_status_combo)
        layout.addLayout(first_filter_row)

        second_filter_row = QHBoxLayout()
        second_filter_row.addWidget(QLabel("Sách:"))
        self.history_book_search = QLineEdit()
        self.history_book_search.setPlaceholderText("Mã sách hoặc tên sách")
        second_filter_row.addWidget(self.history_book_search)

        self.history_from_check = QCheckBox("Từ ngày")
        self.history_from_date = QDateEdit(QDate.currentDate())
        self.history_from_date.setCalendarPopup(True)
        self.history_from_date.setEnabled(False)
        self.history_from_check.toggled.connect(self.history_from_date.setEnabled)
        second_filter_row.addWidget(self.history_from_check)
        second_filter_row.addWidget(self.history_from_date)

        self.history_to_check = QCheckBox("Đến ngày")
        self.history_to_date = QDateEdit(QDate.currentDate())
        self.history_to_date.setCalendarPopup(True)
        self.history_to_date.setEnabled(False)
        self.history_to_check.toggled.connect(self.history_to_date.setEnabled)
        second_filter_row.addWidget(self.history_to_check)
        second_filter_row.addWidget(self.history_to_date)
        layout.addLayout(second_filter_row)

        action_row = QHBoxLayout()
        self.history_search_button = QPushButton("🔍  Tra cứu")
        self.history_reset_button = QPushButton("↻  Xóa bộ lọc")
        action_row.addWidget(self.history_search_button)
        action_row.addWidget(self.history_reset_button)
        action_row.addStretch()
        layout.addLayout(action_row)

        self.history_table = QTableWidget()
        self.history_table.setColumnCount(8)
        self.history_table.setHorizontalHeaderLabels([
            "Mã phiếu",
            "Độc giả",
            "Sách",
            "Số lượng",
            "Ngày mượn",
            "Hạn trả",
            "Ngày trả",
            "Trạng thái",
        ])
        self.history_table.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows
        )
        self.history_table.setSelectionMode(
            QAbstractItemView.SelectionMode.SingleSelection
        )
        self.history_table.setEditTriggers(
            QAbstractItemView.EditTrigger.NoEditTriggers
        )
        self.history_table.setAlternatingRowColors(True)
        self.history_table.verticalHeader().setVisible(False)
        self.history_table.setWordWrap(False)
        history_header = self.history_table.horizontalHeader()
        history_header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        history_header.setSectionResizeMode(1, QHeaderView.ResizeMode.Interactive)
        history_header.setSectionResizeMode(2, QHeaderView.ResizeMode.Interactive)
        history_header.setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
        history_header.setSectionResizeMode(4, QHeaderView.ResizeMode.Fixed)
        history_header.setSectionResizeMode(5, QHeaderView.ResizeMode.Fixed)
        history_header.setSectionResizeMode(6, QHeaderView.ResizeMode.Fixed)
        history_header.setSectionResizeMode(7, QHeaderView.ResizeMode.Fixed)
        history_header.resizeSection(0, 85)
        history_header.resizeSection(1, 190)
        history_header.resizeSection(2, 310)
        history_header.resizeSection(3, 75)
        history_header.resizeSection(4, 105)
        history_header.resizeSection(5, 105)
        history_header.resizeSection(6, 105)
        history_header.resizeSection(7, 105)
        layout.addWidget(self.history_table)

        self.history_status_label = QLabel("Chưa có giao dịch")
        self.history_status_label.setObjectName("statusLabel")
        layout.addWidget(self.history_status_label)

        self.history_search_button.clicked.connect(self.load_history)
        self.history_reset_button.clicked.connect(self.reset_history_filters)
        self.history_loan_search.returnPressed.connect(self.load_history)
        self.history_reader_search.returnPressed.connect(self.load_history)
        self.history_book_search.returnPressed.connect(self.load_history)
        self.history_status_combo.currentIndexChanged.connect(self.load_history)

        page.setLayout(layout)
        return page

    def create_reports_page(self):
        page = QWidget()
        layout = QVBoxLayout()

        title_row = QHBoxLayout()
        title = QLabel("Báo cáo / Thống kê")
        title.setObjectName("pageTitle")
        title_row.addWidget(title)
        title_row.addStretch()
        refresh_button = QPushButton("↻  Cập nhật")
        refresh_button.clicked.connect(self.load_reports)
        title_row.addWidget(refresh_button)
        layout.addLayout(title_row)

        cards_layout = QVBoxLayout()
        first_row = QHBoxLayout()
        self.report_titles_card = self.create_stat_card("📚", "Tổng số sách", "0")
        self.report_readers_card = self.create_stat_card("👥", "Tổng số độc giả", "0")
        self.report_loans_card = self.create_stat_card("📄", "Số lượt mượn", "0")
        self.report_returns_card = self.create_stat_card("↩", "Số lượt trả", "0")
        first_row.addWidget(self.report_titles_card)
        first_row.addWidget(self.report_readers_card)
        first_row.addWidget(self.report_loans_card)
        first_row.addWidget(self.report_returns_card)

        second_row = QHBoxLayout()
        self.report_borrowed_card = self.create_stat_card("📖", "Sách đang mượn", "0")
        self.report_overdue_card = self.create_stat_card("⚠", "Sách quá hạn", "0")
        second_row.addWidget(self.report_borrowed_card)
        second_row.addWidget(self.report_overdue_card)
        second_row.addStretch()
        cards_layout.addLayout(first_row)
        cards_layout.addLayout(second_row)
        layout.addLayout(cards_layout)

        ranking_layout = QHBoxLayout()
        self.popular_books_table = self.create_report_table(
            ["Mã sách", "Tên sách", "Lượt mượn"]
        )
        self.popular_readers_table = self.create_report_table(
            ["Mã độc giả", "Độc giả", "Số sách mượn"]
        )
        ranking_layout.addWidget(self.popular_books_table)
        ranking_layout.addWidget(self.popular_readers_table)
        layout.addLayout(ranking_layout)

        detail_tabs = QTabWidget()
        self.monthly_table = self.create_report_table(
            ["Tháng", "Số lượt mượn", "Số sách mượn"]
        )
        self.category_table = self.create_report_table(
            ["Thể loại", "Đầu sách", "Số bản"]
        )
        detail_tabs.addTab(self.monthly_table, "Theo tháng")
        detail_tabs.addTab(self.category_table, "Theo thể loại")
        layout.addWidget(detail_tabs)

        page.setLayout(layout)
        return page

    def create_report_table(self, headers):
        table = QTableWidget()
        table.setColumnCount(len(headers))
        table.setHorizontalHeaderLabels(headers)
        table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        table.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        table.setAlternatingRowColors(True)
        table.verticalHeader().setVisible(False)
        table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        return table

    # =====================================================
    # NAVIGATION
    # =====================================================

    def show_dashboard(self):
        self.pages.setCurrentWidget(self.dashboard_page)
        self.page_title.setText("Tổng quan")
        self.set_active_navigation(self.dashboard_button)
        self.update_dashboard()

    def show_books(self):
        self.pages.setCurrentWidget(self.books_page)
        self.page_title.setText("Sách / Tài liệu")
        self.set_active_navigation(self.books_button)

    def show_readers(self):
        self.pages.setCurrentWidget(self.readers_page)
        self.page_title.setText("Độc giả")
        self.set_active_navigation(self.readers_button)
        self.load_readers()

    def show_loans(self):
        self.pages.setCurrentWidget(self.loans_page)
        self.page_title.setText("Mượn / Trả sách")
        self.set_active_navigation(self.loans_button)
        self.load_loans()

    def show_history(self):
        self.pages.setCurrentWidget(self.history_page)
        self.page_title.setText("Lịch sử mượn / trả")
        self.set_active_navigation(self.history_button)
        self.load_history()

    def show_reports(self):
        self.pages.setCurrentWidget(self.reports_page)
        self.page_title.setText("Báo cáo / Thống kê")
        self.set_active_navigation(self.reports_button)
        self.load_reports()

    def show_settings(self):
        self.pages.setCurrentWidget(self.settings_page)
        self.page_title.setText("Cài đặt")
        self.set_active_navigation(self.settings_button)

    def show_remote_requests(self):
        self.pages.setCurrentWidget(self.remote_requests_page)
        self.page_title.setText("Yêu cầu trực tuyến")
        self.set_active_navigation(self.remote_requests_button)
        self.load_remote_requests()

    def remote_service_settings(self):
        settings = QSettings("LibraryManager", "LibraryManager")
        return (
            str(settings.value("remote/api_url", "")).strip(),
            str(settings.value("remote/admin_token", "")).strip(),
        )

    def load_remote_requests(self):
        api_url, admin_token = self.remote_service_settings()
        if not api_url or not admin_token:
            self.remote_request_cache = []
            self.remote_request_table.setRowCount(0)
            self.remote_request_details.clear()
            self.remote_request_status_label.setText(
                "Cấu hình địa chỉ API và khóa quản trị trong Cài đặt."
            )
            self.update_remote_request_actions()
            return

        status = self.remote_request_filter.currentData()
        try:
            self.remote_request_cache = get_remote_requests(api_url, admin_token, status)
            self.remote_request_cache.sort(
                key=lambda request: request["created_at"], reverse=True
            )
            self.remote_request_table.setRowCount(0)
            state_names = {
                "pending": "Đang chờ",
                "approved": "Đã duyệt",
                "rejected": "Đã từ chối",
            }
            for request in self.remote_request_cache:
                row = self.remote_request_table.rowCount()
                self.remote_request_table.insertRow(row)
                values = [
                    request["id"],
                    f'{request["name"]} ({request["requester_type"]})',
                    request["reader_code"],
                    ", ".join(
                        f'{item["title"]} ×{item["quantity"]}'
                        for item in request["items"]
                    ),
                    request["created_at"].replace("T", " ")[:19],
                    state_names.get(request["status"], request["status"]),
                ]
                for column, value in enumerate(values):
                    item = QTableWidgetItem(str(value))
                    if column == 0:
                        item.setData(Qt.ItemDataRole.UserRole, request["id"])
                    self.remote_request_table.setItem(row, column, item)
            self.remote_request_status_label.setText(
                f"{len(self.remote_request_cache)} yêu cầu"
            )
            if self.remote_request_cache:
                self.remote_request_table.selectRow(0)
            else:
                self.remote_request_details.clear()
            self.update_remote_request_actions()
        except RemoteServiceError as error:
            self.remote_request_status_label.setText(f"Không tải được: {error}")

    def selected_remote_request(self):
        row = self.remote_request_table.currentRow()
        if row < 0:
            return None
        request_id = self.remote_request_table.item(row, 0).data(Qt.ItemDataRole.UserRole)
        return next(
            (request for request in self.remote_request_cache if request["id"] == request_id),
            None,
        )

    def show_remote_request_details(self):
        request = self.selected_remote_request()
        if request is None:
            self.remote_request_details.clear()
            return
        item_lines = [
            f'• {item["title"]} ({item["book_code"]}) × {item["quantity"]}'
            for item in request["items"]
        ]
        details = [
            f'Người yêu cầu: {request["name"]} · {request["requester_type"]}',
            f'Mã độc giả: {request["reader_code"]} · Lớp/bộ môn: {request["class_name"] or "—"}',
            f'Liên hệ: {request["email"] or request["phone"] or "—"}',
            f'Ghi chú: {request["note"] or "—"}',
            "Tài liệu: " + "; ".join(item_lines),
        ]
        if request["decision_reason"]:
            details.append(f'Lý do xử lý: {request["decision_reason"]}')
        self.remote_request_details.setPlainText("\n".join(details))

    def update_remote_request_actions(self):
        request = self.selected_remote_request()
        can_review = bool(request and request["status"] == "pending")
        self.approve_remote_request_button.setEnabled(can_review)
        self.reject_remote_request_button.setEnabled(can_review)

    def sync_online_catalog(self):
        api_url, admin_token = self.remote_service_settings()
        if not api_url or not admin_token:
            QMessageBox.warning(
                self, "Thiếu cấu hình", "Nhập địa chỉ API và khóa quản trị trong Cài đặt trước."
            )
            return
        try:
            books = get_all_books()
            result = sync_remote_catalog(api_url, admin_token, [
                {
                    "book_code": book["book_code"],
                    "title": book["title"],
                    "author": book["author"],
                    "category": book["category"],
                    "publisher": book["publisher"],
                    "quantity": book["quantity"],
                }
                for book in books
            ])
            QMessageBox.information(
                self,
                "Đồng bộ thành công",
                f'Đã đồng bộ {result["count"]} đầu sách lên danh mục trực tuyến.',
            )
        except RemoteServiceError as error:
            QMessageBox.critical(self, "Lỗi đồng bộ", str(error))

    def approve_remote_request(self):
        request = self.selected_remote_request()
        if request is None or request["status"] != "pending":
            return

        readers = get_all_readers()
        reader = next(
            (reader for reader in readers
             if reader["reader_code"].strip().casefold() == request["reader_code"].strip().casefold()),
            None,
        )
        if reader is None:
            QMessageBox.warning(
                self,
                "Không tìm thấy độc giả",
                f'Mã độc giả {request["reader_code"]} chưa có trong danh sách. '
                "Hãy kiểm tra thông tin hoặc từ chối yêu cầu kèm lý do.",
            )
            return

        books_by_code = {book["book_code"]: book for book in get_all_books()}
        items = []
        for requested_item in request["items"]:
            book = books_by_code.get(requested_item["book_code"])
            if book is None:
                QMessageBox.warning(
                    self, "Không còn sách", f'Sách {requested_item["book_code"]} đã bị xóa khỏi danh mục.'
                )
                return
            items.append((book["id"], requested_item["quantity"]))

        answer = QMessageBox.question(
            self,
            "Duyệt yêu cầu",
            "Duyệt yêu cầu này và lập phiếu mượn theo quy định hiện tại?",
        )
        if answer != QMessageBox.StandardButton.Yes:
            return

        api_url, admin_token = self.remote_service_settings()
        borrow_date = QDate.currentDate().toString(Qt.DateFormat.ISODate)
        due_date = QDate.currentDate().addDays(self.loan_days_spin.value()).toString(
            Qt.DateFormat.ISODate
        )
        try:
            loan_id = create_loan(
                reader["id"], borrow_date, due_date, items,
                remote_request_id=request["id"],
            )
            decide_remote_request(
                api_url, admin_token, request["id"], "approved", loan_id=loan_id
            )
            self.load_books()
            self.load_loans()
            self.load_remote_requests()
            QMessageBox.information(
                self, "Đã duyệt", f"Đã tạo phiếu mượn nội bộ số {loan_id} và duyệt yêu cầu online."
            )
            try:
                sync_remote_catalog(api_url, admin_token, [
                    {
                        "book_code": book["book_code"],
                        "title": book["title"],
                        "author": book["author"],
                        "category": book["category"],
                        "publisher": book["publisher"],
                        "quantity": book["quantity"],
                    }
                    for book in get_all_books()
                ])
            except RemoteServiceError:
                self.remote_request_status_label.setText(
                    "Đã duyệt; cần đồng bộ lại danh mục trực tuyến."
                )
        except (ValueError, RemoteServiceError) as error:
            QMessageBox.critical(
                self,
                "Chưa thể hoàn tất duyệt",
                f"{error}\n\nNếu phiếu mượn đã được tạo, hãy thử làm mới rồi duyệt lại; "
                "ứng dụng sẽ không tạo trùng phiếu.",
            )

    def reject_remote_request(self):
        request = self.selected_remote_request()
        if request is None or request["status"] != "pending":
            return
        reason, accepted = QInputDialog.getText(
            self, "Từ chối yêu cầu", "Lý do từ chối:"
        )
        if not accepted:
            return
        if not reason.strip():
            QMessageBox.warning(self, "Thiếu lý do", "Hãy nhập lý do để người gửi biết kết quả.")
            return
        api_url, admin_token = self.remote_service_settings()
        try:
            decide_remote_request(
                api_url, admin_token, request["id"], "rejected", reason=reason.strip()
            )
            self.load_remote_requests()
            QMessageBox.information(self, "Đã từ chối", "Đã gửi kết quả và lý do cho người yêu cầu.")
        except RemoteServiceError as error:
            QMessageBox.critical(self, "Lỗi xử lý", str(error))

    def save_settings(self):
        settings = QSettings("LibraryManager", "LibraryManager")
        settings.setValue("library/name", self.library_name_edit.text().strip())
        settings.setValue("library/info", self.library_info_edit.toPlainText().strip())
        settings.setValue("loan/days", self.loan_days_spin.value())
        settings.setValue("loan/overdue_rule", self.overdue_rule_edit.text().strip())
        settings.setValue("appearance/theme", self.theme_combo.currentText())
        settings.setValue("remote/api_url", self.remote_api_url_edit.text().strip().rstrip("/"))
        settings.setValue("remote/admin_token", self.remote_admin_token_edit.text().strip())
        self.apply_saved_theme()
        QMessageBox.information(self, "Thành công", "Đã lưu thiết lập.")

    def apply_saved_theme(self):
        if self.theme_combo.currentText() == "Tối":
            self.setStyleSheet("""
                QMainWindow, QWidget {
                    background-color: #0f172a;
                    color: #e2e8f0;
                }
                QLineEdit, QPlainTextEdit, QSpinBox, QComboBox, QTableWidget {
                    background-color: #1e293b;
                    color: #e2e8f0;
                    border: 1px solid #475569;
                }
                QHeaderView::section {
                    background-color: #334155;
                    color: #f8fafc;
                }
                QPushButton {
                    background-color: #334155;
                    color: #f8fafc;
                    border: 1px solid #64748b;
                }
                QPushButton:hover {
                    background-color: #475569;
                }
                QLabel {
                    color: #e2e8f0;
                }
                #sidebar {
                    background-color: #0b1220;
                    border-right: 1px solid #26344d;
                }
                #menuButton {
                    color: #b9c5d6;
                    background-color: transparent;
                    border: 1px solid transparent;
                }
                #menuButton:hover {
                    background-color: #26344d;
                    color: #ffffff;
                }
                #logo, #pageTitle, #sectionTitle, #settingLabel {
                    color: #f8fafc;
                }
                #version, #statusLabel, #cardTitle, #welcomeText {
                    color: #a5b4c7;
                }
                #statCard, #welcomeBox {
                    background-color: #1e293b;
                    border: 1px solid #334155;
                }
                #cardValue, #welcomeTitle {
                    color: #f8fafc;
                }
                QTableWidget::item {
                    background-color: #1e293b;
                    color: #e2e8f0;
                }
                QTableWidget::item:selected {
                    background-color: #115e59;
                    color: #ffffff;
                }
                QCheckBox {
                    color: #e2e8f0;
                }
                #settingLabel, #sectionTitle, #pageTitle {
                    color: #f8fafc;
                }
                QPlainTextEdit, QLineEdit, QSpinBox, QComboBox {
                    selection-background-color: #2563eb;
                    selection-color: #ffffff;
                }
            """)
        else:
            self.apply_styles()

    def backup_database(self):
        destination, _ = QFileDialog.getSaveFileName(
            self,
            "Sao lưu cơ sở dữ liệu",
            "library_backup.db",
            "Database (*.db)",
        )
        if not destination:
            return

        try:
            shutil.copy2(DATABASE_PATH, destination)
            QMessageBox.information(self, "Thành công", "Đã sao lưu cơ sở dữ liệu.")
        except Exception as error:
            QMessageBox.critical(self, "Lỗi", f"Không thể sao lưu dữ liệu.\n\n{error}")

    def restore_database(self):
        source, _ = QFileDialog.getOpenFileName(
            self,
            "Khôi phục cơ sở dữ liệu",
            "",
            "Database (*.db)",
        )
        if not source:
            return

        answer = QMessageBox.question(
            self,
            "Xác nhận khôi phục",
            "Dữ liệu hiện tại sẽ được thay thế. Bạn có muốn tiếp tục không?",
        )
        if answer != QMessageBox.StandardButton.Yes:
            return

        try:
            shutil.copy2(source, DATABASE_PATH)
            QMessageBox.information(
                self,
                "Đã khôi phục",
                "Đã khôi phục dữ liệu. Vui lòng khởi động lại phần mềm.",
            )
        except Exception as error:
            QMessageBox.critical(self, "Lỗi", f"Không thể khôi phục dữ liệu.\n\n{error}")

    def clear_database(self):
        answer = QMessageBox.warning(
            self,
            "Xóa toàn bộ dữ liệu",
            "Tất cả sách, độc giả và lịch sử mượn/trả sẽ bị xóa vĩnh viễn. Tiếp tục?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return

        try:
            clear_all_data()
            self.load_books()
            self.load_readers()
            self.load_loans()
            self.load_history()
            self.load_reports()
            QMessageBox.information(self, "Thành công", "Đã xóa toàn bộ dữ liệu.")
        except Exception as error:
            QMessageBox.critical(self, "Lỗi", f"Không thể xóa dữ liệu.\n\n{error}")

    def import_books_csv(self):
        source, _ = QFileDialog.getOpenFileName(self, "Nhập sách CSV", "", "CSV (*.csv)")
        if not source:
            return

        try:
            added = 0
            with open(source, "r", encoding="utf-8-sig", newline="") as file:
                for row in csv.DictReader(file):
                    if not row.get("book_code") or not row.get("title"):
                        continue
                    db_add_book(
                        row["book_code"], row["title"], row.get("author", ""),
                        row.get("category", ""), row.get("publisher", ""),
                        int(row.get("publish_year") or 0), int(row.get("quantity") or 1),
                        row.get("shelf", ""), row.get("description", ""),
                    )
                    added += 1
            self.load_books()
            QMessageBox.information(self, "Nhập thành công", f"Đã nhập {added} sách.")
        except Exception as error:
            QMessageBox.critical(self, "Lỗi", f"Không thể nhập CSV.\n\n{error}")

    def export_books_csv(self):
        destination, _ = QFileDialog.getSaveFileName(self, "Xuất sách CSV", "books.csv", "CSV (*.csv)")
        if not destination:
            return
        try:
            books = get_all_books()
            fields = ["book_code", "title", "author", "category", "publisher", "publish_year", "quantity", "shelf", "description"]
            with open(destination, "w", encoding="utf-8-sig", newline="") as file:
                writer = csv.DictWriter(file, fieldnames=fields)
                writer.writeheader()
                writer.writerows({field: book[field] for field in fields} for book in books)
            QMessageBox.information(self, "Xuất thành công", "Đã xuất danh sách sách.")
        except Exception as error:
            QMessageBox.critical(self, "Lỗi", f"Không thể xuất CSV.\n\n{error}")

    def import_readers_csv(self):
        source, _ = QFileDialog.getOpenFileName(self, "Nhập độc giả CSV", "", "CSV (*.csv)")
        if not source:
            return

        try:
            added = 0
            with open(source, "r", encoding="utf-8-sig", newline="") as file:
                for row in csv.DictReader(file):
                    if not row.get("reader_code") or not row.get("name"):
                        continue
                    db_add_reader(
                        row["reader_code"], row["name"], row.get("phone", ""),
                        row.get("email", ""), row.get("class_name", ""),
                    )
                    added += 1
            self.load_readers()
            QMessageBox.information(self, "Nhập thành công", f"Đã nhập {added} độc giả.")
        except Exception as error:
            QMessageBox.critical(self, "Lỗi", f"Không thể nhập CSV.\n\n{error}")

    def export_readers_csv(self):
        destination, _ = QFileDialog.getSaveFileName(self, "Xuất độc giả CSV", "readers.csv", "CSV (*.csv)")
        if not destination:
            return
        try:
            readers = get_all_readers()
            fields = ["reader_code", "name", "phone", "email", "class_name", "created_at"]
            with open(destination, "w", encoding="utf-8-sig", newline="") as file:
                writer = csv.DictWriter(file, fieldnames=fields)
                writer.writeheader()
                writer.writerows({field: reader[field] for field in fields} for reader in readers)
            QMessageBox.information(self, "Xuất thành công", "Đã xuất danh sách độc giả.")
        except Exception as error:
            QMessageBox.critical(self, "Lỗi", f"Không thể xuất CSV.\n\n{error}")

    def repair_orphaned_loans(self):
        try:
            closed_count = close_orphaned_loans()
            self.load_loans()
            self.load_history()
            self.load_reports()
            self.update_dashboard()
            QMessageBox.information(
                self,
                "Đã kiểm tra dữ liệu",
                f"Đã đóng {closed_count} phiếu mượn không còn sách trong danh mục.",
            )
        except Exception as error:
            QMessageBox.critical(self, "Lỗi", f"Không thể dọn dữ liệu.\n\n{error}")

    # =====================================================
    # LOAD BOOKS
    # =====================================================

    def load_books(self):
        self.book_list = get_all_books()
        categories = sorted({
            book["category"].strip()
            for book in self.book_list
            if book["category"] and book["category"].strip()
        }, key=str.lower)
        current_category = self.category_filter.currentText()
        self.category_filter.blockSignals(True)
        self.category_filter.clear()
        self.category_filter.addItem("Tất cả thể loại")
        self.category_filter.addItems(categories)
        self.category_filter.setCurrentText(
            current_category if current_category in categories else "Tất cả thể loại"
        )
        self.category_filter.blockSignals(False)
        self.book_page = 1
        self.apply_book_filters()
        self.update_dashboard()

    # =====================================================
    # DISPLAY BOOKS
    # =====================================================

    def display_books(self, books):
        self.table.setRowCount(0)

        for book in books:
            row = self.table.rowCount()
            self.table.insertRow(row)

            values = [
                book["book_code"],
                book["title"],
                book["category"] or "",
                book["quantity"],
                book["shelf"] or "",
                book["author"] or "",
                book["publisher"] or "",
                book["publish_year"] or "",
            ]

            for column, value in enumerate(values):
                item = QTableWidgetItem(str(value))
                item.setTextAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
                item.setForeground(QColor("#1e293b"))
                item.setBackground(QColor("#ffffff"))
                if column in (1, 2, 4, 5, 6):
                    item.setToolTip(str(value))
                self.table.setItem(row, column, item)

        total_quantity = sum(book["quantity"] or 0 for book in self.filtered_books)
        total_pages = max(
            1,
            (len(self.filtered_books) + self.book_page_size - 1)
            // self.book_page_size,
        )
        self.book_page = min(self.book_page, total_pages)
        self.book_page_label.setText(f"Trang {self.book_page} / {total_pages}")
        self.previous_books_button.setEnabled(self.book_page > 1)
        self.next_books_button.setEnabled(self.book_page < total_pages)
        start_index = (self.book_page - 1) * self.book_page_size + 1
        end_index = min(start_index + len(books) - 1, len(self.filtered_books))
        visible_range = f"{start_index}-{end_index}" if books else "0"
        self.status_label.setText(
            f"Đang hiển thị {visible_range} / {len(self.filtered_books)} đầu sách | "
            f"Tổng số bản: {total_quantity}"
        )

    def apply_book_filters(self):
        keyword = self.search_edit.text().strip().lower()
        category = self.category_filter.currentText()
        sort_mode = self.book_sort_combo.currentText()

        self.book_page_size = int(self.book_page_size_combo.currentText().split()[0])
        self.filtered_books = [
            book for book in self.book_list
            if (
                not keyword
                or keyword in (book["book_code"] or "").lower()
                or keyword in (book["title"] or "").lower()
                or keyword in (book["author"] or "").lower()
                or keyword in (book["category"] or "").lower()
                or keyword in (book["publisher"] or "").lower()
            )
            and (
                category == "Tất cả thể loại"
                or (book["category"] or "").strip() == category
            )
        ]

        if sort_mode == "Tên sách A-Z":
            self.filtered_books.sort(key=lambda book: (book["title"] or "").lower())
        elif sort_mode == "Tên sách Z-A":
            self.filtered_books.sort(
                key=lambda book: (book["title"] or "").lower(), reverse=True
            )
        elif sort_mode == "Số lượng cao-thấp":
            self.filtered_books.sort(key=lambda book: book["quantity"] or 0, reverse=True)
        elif sort_mode == "Số lượng thấp-cao":
            self.filtered_books.sort(key=lambda book: book["quantity"] or 0)

        total_pages = max(
            1,
            (len(self.filtered_books) + self.book_page_size - 1)
            // self.book_page_size,
        )
        self.book_page = min(self.book_page, total_pages)
        start = (self.book_page - 1) * self.book_page_size
        end = start + self.book_page_size
        self.display_books(self.filtered_books[start:end])

    def reset_book_filters(self):
        self.search_edit.clear()
        self.category_filter.setCurrentIndex(0)
        self.book_sort_combo.setCurrentIndex(0)
        self.book_page_size_combo.setCurrentIndex(0)
        self.book_page = 1
        self.apply_book_filters()

    def previous_book_page(self):
        if self.book_page > 1:
            self.book_page -= 1
            self.apply_book_filters()

    def next_book_page(self):
        total_pages = max(
            1,
            (len(self.filtered_books) + self.book_page_size - 1)
            // self.book_page_size,
        )
        if self.book_page < total_pages:
            self.book_page += 1
            self.apply_book_filters()

    # =====================================================
    # UPDATE DASHBOARD
    # =====================================================

    def update_dashboard(self):
        books = get_all_books()
        readers = get_all_readers()
        loans = get_all_loans()
        loan_counts = get_loan_counts()

        total_books = len(books)
        total_quantity = loan_counts["total_copies"]
        categories = set()

        for book in books:
            if book["category"]:
                categories.add(book["category"].strip().lower())

        self.total_card.value_label.setText(str(total_books))
        self.quantity_card.value_label.setText(str(total_quantity))
        self.reader_card.value_label.setText(str(len(readers)))
        self.category_card.value_label.setText(str(len(categories)))
        self.borrowed_card.value_label.setText(str(loan_counts["borrowed_count"]))
        self.overdue_card.value_label.setText(str(loan_counts["overdue_count"]))
        low_stock_count = sum(1 for book in books if (book["quantity"] or 0) <= 1)
        alerts = []
        if loan_counts["overdue_count"]:
            alerts.append(f'{loan_counts["overdue_count"]} phiếu quá hạn')
        if low_stock_count:
            alerts.append(f'{low_stock_count} sách sắp hết')
        self.dashboard_alert_label.setText(
            "⚠  " + " | ".join(alerts) if alerts else "✓  Không có cảnh báo cần xử lý"
        )
        self.update_recent_activities(books, readers, loans)

    def update_recent_activities(self, books, readers, loans):
        activities = []

        for book in books:
            activities.append((book["created_at"], "Thêm sách", book["title"]))

        for reader in readers:
            activities.append((reader["created_at"], "Thêm độc giả", reader["name"]))

        for loan in loans:
            activities.append((loan["borrow_date"], "Lập phiếu mượn", loan["reader_name"]))
            if loan["return_date"]:
                activities.append((loan["return_date"], "Trả sách", loan["reader_name"]))

        activities.sort(key=lambda activity: activity[0] or "", reverse=True)
        self.activity_table.setRowCount(0)

        for created_at, action, subject in activities[:10]:
            row = self.activity_table.rowCount()
            self.activity_table.insertRow(row)
            values = [action, subject, created_at or ""]

            for column, value in enumerate(values):
                self.activity_table.setItem(row, column, QTableWidgetItem(str(value)))

    # =====================================================
    # ADD BOOK
    # =====================================================

    def add_book(self):
        dialog = BookDialog(self)

        if dialog.exec() != BookDialog.DialogCode.Accepted:
            return

        data = dialog.get_data()

        try:
            db_add_book(
                data["book_code"],
                data["title"],
                data["author"],
                data["category"],
                data["publisher"],
                data["publish_year"],
                data["quantity"],
                data["shelf"],
                data["description"],
            )
            QMessageBox.information(self, "Thành công", "Đã thêm sách.")
            self.load_books()
        except sqlite3.IntegrityError:
            QMessageBox.warning(
                self,
                "Mã sách đã tồn tại",
                "Mã sách này đã được sử dụng.\nVui lòng nhập mã sách khác.",
            )
        except Exception as error:
            QMessageBox.critical(self, "Lỗi", f"Không thể thêm sách.\n\n{error}")

    # =====================================================
    # GET SELECTED BOOK
    # =====================================================

    def get_selected_book(self):
        row = self.table.currentRow()

        if row < 0:
            return None

        book_code = self.table.item(row, 0).text()
        books = get_all_books()

        for book in books:
            if book["book_code"] == book_code:
                return book

        return None

    # =====================================================
    # EDIT BOOK
    # =====================================================

    def edit_book(self):
        book = self.get_selected_book()

        if not book:
            QMessageBox.warning(self, "Chưa chọn sách", "Vui lòng chọn một cuốn sách.")
            return

        dialog = BookDialog(self, book)
        result = dialog.exec()

        if result != BookDialog.DialogCode.Accepted:
            return

        data = dialog.get_data()

        try:
            update_book(
                book["id"],
                data["book_code"],
                data["title"],
                data["author"],
                data["category"],
                data["publisher"],
                data["publish_year"],
                data["quantity"],
                data["shelf"],
                data["description"],
            )
            QMessageBox.information(self, "Thành công", "Đã cập nhật sách.")
            self.load_books()
        except sqlite3.IntegrityError:
            QMessageBox.warning(
                self,
                "Mã sách đã tồn tại",
                "Mã sách này đã được sử dụng cho tài liệu khác.\nVui lòng nhập một mã sách khác.",
            )
        except Exception as error:
            QMessageBox.critical(self, "Lỗi", f"Không thể cập nhật sách.\n\n{error}")

    # =====================================================
    # DELETE BOOK
    # =====================================================

    def delete_selected_book(self):
        book = self.get_selected_book()

        if not book:
            QMessageBox.warning(self, "Chưa chọn sách", "Vui lòng chọn một cuốn sách.")
            return

        answer = QMessageBox.question(
            self,
            "Xác nhận xóa",
            f'Bạn có chắc muốn xóa "{book["title"]}" không?',
        )

        if answer != QMessageBox.StandardButton.Yes:
            return

        try:
            delete_book(book["id"])
            QMessageBox.information(self, "Thành công", "Đã xóa sách.")
            self.load_books()
        except Exception as error:
            QMessageBox.critical(self, "Lỗi", f"Không thể xóa sách.\n\n{error}")

    def create_book_qr(self):
        book = self.get_selected_book()
        if not book:
            QMessageBox.warning(self, "Chưa chọn sách", "Vui lòng chọn sách cần tạo QR.")
            return
        destination, _ = QFileDialog.getSaveFileName(
            self, "Lưu QR sách", f'{book["book_code"]}.png', "PNG (*.png)"
        )
        if not destination:
            return
        try:
            import qrcode
            payload = "\n".join([
                f'Mã sách: {book["book_code"]}',
                f'Tên sách: {book["title"]}',
                f'Tác giả: {book["author"] or ""}',
            ])
            qrcode.make(payload).save(destination)
            QMessageBox.information(self, "Thành công", "Đã tạo mã QR cho sách.")
        except Exception as error:
            QMessageBox.critical(self, "Lỗi", f"Không thể tạo QR.\n\n{error}")

    # =====================================================
    # SEARCH
    # =====================================================

    def search(self):
        self.book_page = 1
        self.apply_book_filters()

    # =====================================================
    # READERS
    # =====================================================

    def load_readers(self):
        readers = get_all_readers()
        self.display_readers(readers)

    def display_readers(self, readers):
        self.reader_table.setRowCount(0)

        for reader in readers:
            row = self.reader_table.rowCount()
            self.reader_table.insertRow(row)

            values = [
                reader["id"],
                reader["reader_code"],
                reader["name"],
                reader["phone"] or "",
                reader["email"] or "",
                reader["class_name"] or "",
                reader["created_at"] or "",
            ]

            for column, value in enumerate(values):
                item = QTableWidgetItem(str(value))
                item.setTextAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
                item.setForeground(QColor("#1e293b"))
                item.setBackground(QColor("#ffffff"))
                self.reader_table.setItem(row, column, item)

        self.reader_status_label.setText(f"Tổng số độc giả: {len(readers)}")

    def search_readers(self):
        keyword = self.reader_search_edit.text().strip()

        if not keyword:
            self.load_readers()
            return

        readers = search_readers(keyword)
        self.display_readers(readers)

    def add_reader(self):
        dialog = ReaderDialog(self)

        if dialog.exec() != ReaderDialog.DialogCode.Accepted:
            return

        data = dialog.get_data()

        try:
            db_add_reader(
                data["reader_code"],
                data["name"],
                data["phone"],
                data["email"],
                data["class_name"],
            )
            QMessageBox.information(self, "Thành công", "Đã thêm độc giả.")
            self.load_readers()
        except sqlite3.IntegrityError:
            QMessageBox.warning(
                self,
                "Mã độc giả đã tồn tại",
                "Mã độc giả này đã được sử dụng.\nVui lòng nhập mã khác.",
            )
        except Exception as error:
            QMessageBox.critical(self, "Lỗi", f"Không thể thêm độc giả.\n\n{error}")

    def get_selected_reader(self):
        row = self.reader_table.currentRow()

        if row < 0:
            return None

        reader_id = int(self.reader_table.item(row, 0).text())
        readers = get_all_readers()

        for reader in readers:
            if reader["id"] == reader_id:
                return reader

        return None

    def edit_reader(self):
        reader = self.get_selected_reader()

        if not reader:
            QMessageBox.warning(
                self,
                "Chưa chọn độc giả",
                "Vui lòng chọn một độc giả."
            )
            return

        dialog = ReaderDialog(self, reader)

        if dialog.exec() != ReaderDialog.DialogCode.Accepted:
            return

        data = dialog.get_data()

        try:
            update_reader(
                reader["id"],
                data["reader_code"],
                data["name"],
                data["phone"],
                data["email"],
                data["class_name"],
            )
            QMessageBox.information(self, "Thành công", "Đã cập nhật độc giả.")
            self.load_readers()
        except sqlite3.IntegrityError:
            QMessageBox.warning(
                self,
                "Mã độc giả đã tồn tại",
                "Mã độc giả này đã được sử dụng.\nVui lòng nhập mã khác.",
            )
        except Exception as error:
            QMessageBox.critical(self, "Lỗi", f"Không thể cập nhật độc giả.\n\n{error}")

    def delete_selected_reader(self):
        reader = self.get_selected_reader()

        if not reader:
            QMessageBox.warning(
                self,
                "Chưa chọn độc giả",
                "Vui lòng chọn một độc giả."
            )
            return

        answer = QMessageBox.question(
            self,
            "Xác nhận xóa",
            f'Bạn có chắc muốn xóa độc giả "{reader["name"]}" không?',
        )

        if answer != QMessageBox.StandardButton.Yes:
            return

        try:
            delete_reader(reader["id"])
            QMessageBox.information(self, "Thành công", "Đã xóa độc giả.")
            self.load_readers()
        except Exception as error:
            QMessageBox.critical(self, "Lỗi", f"Không thể xóa độc giả.\n\n{error}")

    def create_reader_qr(self):
        reader = self.get_selected_reader()
        if not reader:
            QMessageBox.warning(self, "Chưa chọn độc giả", "Vui lòng chọn độc giả cần tạo QR.")
            return
        destination, _ = QFileDialog.getSaveFileName(
            self, "Lưu QR độc giả", f'{reader["reader_code"]}.png', "PNG (*.png)"
        )
        if not destination:
            return
        try:
            import qrcode
            payload = "\n".join([
                f'Mã độc giả: {reader["reader_code"]}',
                f'Họ tên: {reader["name"]}',
                f'Số điện thoại: {reader["phone"] or ""}',
            ])
            qrcode.make(payload).save(destination)
            QMessageBox.information(self, "Thành công", "Đã tạo mã QR cho độc giả.")
        except Exception as error:
            QMessageBox.critical(self, "Lỗi", f"Không thể tạo QR.\n\n{error}")

    # =====================================================
    # LOANS
    # =====================================================

    def load_reports(self):
        statistics = get_report_statistics()

        self.report_titles_card.value_label.setText(
            f'{statistics["total_titles"]} / {statistics["total_copies"]} bản'
        )
        self.report_readers_card.value_label.setText(str(statistics["total_readers"]))
        self.report_loans_card.value_label.setText(str(statistics["total_loans"]))
        self.report_returns_card.value_label.setText(str(statistics["returned_loans"]))
        self.report_borrowed_card.value_label.setText(str(statistics["borrowed_count"]))
        self.report_overdue_card.value_label.setText(str(statistics["overdue_count"]))

        self.fill_report_table(
            self.popular_books_table,
            [
                (row["book_code"], row["title"], row["borrowed_count"])
                for row in statistics["popular_books"]
            ],
        )
        self.fill_report_table(
            self.popular_readers_table,
            [
                (row["reader_code"], row["name"], row["borrowed_count"])
                for row in statistics["popular_readers"]
            ],
        )
        self.fill_report_table(
            self.monthly_table,
            [
                (row["month"], row["loan_count"], row["book_count"])
                for row in statistics["monthly"]
            ],
        )
        self.fill_report_table(
            self.category_table,
            [
                (row["category"], row["title_count"], row["copy_count"])
                for row in statistics["categories"]
            ],
        )

    def fill_report_table(self, table, rows):
        table.setRowCount(0)
        for values in rows:
            row = table.rowCount()
            table.insertRow(row)
            for column, value in enumerate(values):
                table.setItem(row, column, QTableWidgetItem(str(value)))

    def load_loans(self):
        keyword = self.loan_reader_search_edit.text().strip().lower()
        all_loans = get_all_loans()
        loans = [
            loan for loan in all_loans
            if not keyword
            or keyword in (loan["reader_code"] or "").lower()
            or keyword in (loan["reader_name"] or "").lower()
            and (
                self.loan_status_filter == "Tất cả"
                or loan["status"] == self.loan_status_filter
            )
        ]
        if self.loan_status_filter != "Tất cả":
            loans = [loan for loan in loans if loan["status"] == self.loan_status_filter]
        if self.loan_sort_mode == "due":
            loans.sort(key=lambda loan: (loan["status"] == "Đã trả", loan["due_date"]))
        else:
            loans.sort(key=lambda loan: loan["borrow_date"], reverse=True)
        self.loan_table.setRowCount(0)

        for loan in loans:
            row = self.loan_table.rowCount()
            self.loan_table.insertRow(row)
            values = [
                loan["reader_name"],
                loan["book_titles"] or "",
                loan["book_count"],
                loan["borrow_date"],
                loan["due_date"],
                loan["return_date"] or "",
                loan["status"],
            ]

            for column, value in enumerate(values):
                item = QTableWidgetItem(str(value))
                item.setTextAlignment(
                    Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft
                )
                if column in (0, 1, 6):
                    item.setToolTip(str(value))
                self.loan_table.setItem(row, column, item)

            self.loan_table.item(row, 0).setData(Qt.ItemDataRole.UserRole, loan["id"])

        loan_counts = get_loan_counts()
        self.loan_status_label.setText(
            f"Đang hiển thị {len(loans)} / {len(all_loans)} phiếu | "
            f"Đang mượn: {loan_counts['borrowed_count']} phiếu | "
            f"Quá hạn: {loan_counts['overdue_count']} phiếu"
        )
        self.update_dashboard()

    def reset_loan_search(self):
        self.loan_reader_search_edit.clear()
        self.loan_status_filter = "Tất cả"
        self.loan_sort_mode = "date"
        self.load_loans()

    def set_loan_status_filter(self, status):
        self.loan_status_filter = status
        self.load_loans()

    def set_loan_sort(self, sort_mode):
        self.loan_sort_mode = sort_mode
        self.load_loans()

    def load_history(self):
        all_loans = get_all_loans()
        loan_keyword = self.history_loan_search.text().strip().lower()
        reader_keyword = self.history_reader_search.text().strip().lower()
        book_keyword = self.history_book_search.text().strip().lower()
        selected_status = self.history_status_combo.currentText()
        from_date = (
            self.history_from_date.date().toString("yyyy-MM-dd")
            if self.history_from_check.isChecked()
            else ""
        )
        to_date = (
            self.history_to_date.date().toString("yyyy-MM-dd")
            if self.history_to_check.isChecked()
            else ""
        )

        filtered_loans = []
        for loan in all_loans:
            formatted_id = f"PM{loan['id']:03d}".lower()
            if loan_keyword and loan_keyword not in formatted_id and loan_keyword not in str(loan["id"]):
                continue

            reader_text = " ".join([
                loan["reader_code"] or "",
                loan["reader_name"] or "",
            ]).lower()
            if reader_keyword and reader_keyword not in reader_text:
                continue

            book_text = " ".join([
                loan["book_codes"] or "",
                loan["book_titles"] or "",
            ]).lower()
            if book_keyword and book_keyword not in book_text:
                continue

            if selected_status != "Tất cả" and loan["status"] != selected_status:
                continue
            if from_date and loan["borrow_date"] < from_date:
                continue
            if to_date and loan["borrow_date"] > to_date:
                continue

            filtered_loans.append(loan)

        self.history_table.setRowCount(0)
        for loan in filtered_loans:
            row = self.history_table.rowCount()
            self.history_table.insertRow(row)
            values = [
                f"PM{loan['id']:03d}",
                f"{loan['reader_code']} - {loan['reader_name']}",
                loan["book_titles"] or "",
                loan["book_count"],
                loan["borrow_date"],
                loan["due_date"],
                loan["return_date"] or "",
                loan["status"],
            ]

            for column, value in enumerate(values):
                item = QTableWidgetItem(str(value))
                item.setTextAlignment(
                    Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft
                )
                if column in (1, 2, 7):
                    item.setToolTip(str(value))
                self.history_table.setItem(row, column, item)

        self.history_status_label.setText(
            f"Đang hiển thị {len(filtered_loans)} / {len(all_loans)} giao dịch"
        )

    def reset_history_filters(self):
        self.history_loan_search.clear()
        self.history_reader_search.clear()
        self.history_book_search.clear()
        self.history_status_combo.setCurrentIndex(0)
        self.history_from_check.setChecked(False)
        self.history_to_check.setChecked(False)
        self.load_history()

    def add_loan(self):
        readers = get_all_readers()
        books = [book for book in get_all_books() if book["quantity"] > 0]

        if not readers:
            QMessageBox.warning(
                self,
                "Chưa có độc giả",
                "Vui lòng thêm độc giả trước khi lập phiếu mượn.",
            )
            return

        if not books:
            QMessageBox.warning(
                self,
                "Không có sách khả dụng",
                "Hiện không còn sách để cho mượn.",
            )
            return

        dialog = LoanDialog(readers, books, self)
        if dialog.exec() != LoanDialog.DialogCode.Accepted:
            return

        data = dialog.get_data()

        try:
            create_loan(
                data["reader_id"],
                data["borrow_date"],
                data["due_date"],
                data["items"],
            )
            QMessageBox.information(self, "Thành công", "Đã lập phiếu mượn.")
            self.load_loans()
            self.load_books()
        except Exception as error:
            QMessageBox.critical(self, "Lỗi", f"Không thể lập phiếu mượn.\n\n{error}")

    def return_selected_loan(self):
        row = self.loan_table.currentRow()

        if row < 0:
            QMessageBox.warning(
                self,
                "Chưa chọn phiếu",
                "Vui lòng chọn phiếu mượn cần trả.",
            )
            return

        loan_id = self.loan_table.item(row, 0).data(Qt.ItemDataRole.UserRole)
        status = self.loan_table.item(row, 6).text()

        if status == "Đã trả":
            QMessageBox.information(self, "Thông tin", "Phiếu này đã được trả.")
            return

        answer = QMessageBox.question(
            self,
            "Xác nhận trả sách",
            "Bạn có chắc muốn xác nhận trả sách cho phiếu này không?",
        )

        if answer != QMessageBox.StandardButton.Yes:
            return

        try:
            return_loan(loan_id)
            QMessageBox.information(self, "Thành công", "Đã trả sách.")
            self.load_loans()
            self.load_books()
        except Exception as error:
            QMessageBox.critical(self, "Lỗi", f"Không thể trả sách.\n\n{error}")

    def selected_loan_id(self):
        row = self.loan_table.currentRow()
        if row < 0:
            return None
        return self.loan_table.item(row, 0).data(Qt.ItemDataRole.UserRole)

    def extend_selected_loan(self):
        loan_id = self.selected_loan_id()
        if loan_id is None:
            QMessageBox.warning(self, "Chưa chọn phiếu", "Vui lòng chọn phiếu cần gia hạn.")
            return

        new_date, accepted = QInputDialog.getText(
            self,
            "Gia hạn phiếu mượn",
            "Hạn trả mới (YYYY-MM-DD):",
        )
        if not accepted or not new_date.strip():
            return

        try:
            extend_loan(loan_id, new_date.strip(), "Gia hạn tại màn hình Mượn/Trả")
            QMessageBox.information(self, "Thành công", "Đã gia hạn phiếu mượn.")
            self.load_loans()
            self.load_history()
            self.load_reports()
        except Exception as error:
            QMessageBox.warning(self, "Không thể gia hạn", str(error))

    def fine_selected_loan(self):
        loan_id = self.selected_loan_id()
        row = self.loan_table.currentRow()
        if loan_id is None or row < 0:
            QMessageBox.warning(self, "Chưa chọn phiếu", "Vui lòng chọn phiếu cần tạo phạt.")
            return

        status = self.loan_table.item(row, 6).text()
        if status != "Quá hạn":
            QMessageBox.information(self, "Thông tin", "Chỉ có thể tạo phạt cho phiếu quá hạn.")
            return

        amount, accepted = QInputDialog.getDouble(
            self,
            "Tạo tiền phạt",
            "Số tiền phạt:",
            1000.0,
            0.0,
            100000000.0,
            0,
        )
        if not accepted:
            return

        try:
            from database.database import create_fine
            create_fine(loan_id, amount, "Trả sách quá hạn")
            QMessageBox.information(self, "Thành công", "Đã tạo khoản phạt.")
        except Exception as error:
            QMessageBox.critical(self, "Lỗi", f"Không thể tạo phạt.\n\n{error}")

    # =====================================================
    # STYLE
    # =====================================================

    def apply_styles(self):
        self.setStyleSheet("""
            QMainWindow {
                background-color: #f5f7fb;
            }

            #sidebar {
                background-color: #1e293b;
            }

            #logo {
                color: white;
                font-size: 22px;
                font-weight: bold;
                padding: 10px;
            }

            #menuButton {
                color: #cbd5e1;
                background-color: transparent;
                border: none;
                text-align: left;
                padding: 13px;
                border-radius: 8px;
                font-size: 14px;
            }

            #menuButton:hover {
                background-color: #334155;
                color: white;
            }

            #version {
                color: #64748b;
                padding: 10px;
                font-size: 12px;
            }

            #pageTitle {
                font-size: 28px;
                font-weight: bold;
                color: #0f172a;
            }

            #sectionTitle {
                font-size: 22px;
                font-weight: bold;
                color: #0f172a;
            }

            #settingLabel {
                color: #334155;
                font-size: 14px;
                font-weight: 600;
            }

            QLineEdit {
                background-color: #ffffff;
                color: #1e293b;
                border: 1px solid #d1d5db;
                border-radius: 8px;
                padding: 10px;
                font-size: 14px;
            }

            QLineEdit:focus {
                border: 1px solid #2563eb;
                color: #0f172a;
            }

            QPushButton {
                background-color: #ffffff;
                color: #1e293b;
                border: 1px solid #d1d5db;
                border-radius: 8px;
                padding: 9px 15px;
                font-size: 13px;
                font-weight: 600;
            }

            QPushButton:hover {
                background-color: #f1f5f9;
                color: #0f172a;
            }

            QPushButton:pressed {
                background-color: #e2e8f0;
                color: #0f172a;
            }

            #primaryButton {
                background-color: #2563eb;
                color: #ffffff;
                border: none;
                font-weight: bold;
            }

            #primaryButton:hover {
                background-color: #1d4ed8;
                color: #ffffff;
            }

            #primaryButton:pressed {
                background-color: #1e40af;
                color: #ffffff;
            }

            #deleteButton {
                background-color: #dc2626;
                color: #ffffff;
                border: none;
                font-weight: bold;
            }

            #deleteButton:hover {
                background-color: #b91c1c;
                color: #ffffff;
            }

            #deleteButton:pressed {
                background-color: #991b1b;
                color: #ffffff;
            }

            #editButton {
                background-color: #2563eb;
                color: #ffffff;
                border: none;
                font-weight: bold;
            }

            #editButton:hover {
                background-color: #1d4ed8;
                color: #ffffff;
            }

            QTableWidget {
                background-color: #ffffff;
                color: #1e293b;
                border: 1px solid #e2e8f0;
                border-radius: 10px;
                gridline-color: #e5e7eb;
                font-size: 13px;
            }

            QTableWidget::item {
                color: #1e293b;
                background-color: #ffffff;
                padding: 8px;
            }

            QTableWidget::item:selected {
                background-color: #dbeafe;
                color: #0f172a;
            }

            QHeaderView::section {
                background-color: #f8fafc;
                color: #334155;
                padding: 10px;
                border: none;
                border-bottom: 1px solid #e2e8f0;
                font-weight: bold;
            }

            QMessageBox {
                background-color: #ffffff;
            }

            QMessageBox QLabel {
                color: #1e293b;
                font-size: 14px;
            }

            QMessageBox QPushButton {
                background-color: #ffffff;
                color: #1e293b;
                border: 1px solid #cbd5e1;
                border-radius: 6px;
                padding: 7px 20px;
                min-width: 70px;
                font-weight: 600;
            }

            QMessageBox QPushButton:hover {
                background-color: #f1f5f9;
                color: #0f172a;
            }

            #statusLabel {
                color: #64748b;
                padding: 5px;
            }

            #statCard {
                background-color: white;
                border: 1px solid #e2e8f0;
                border-radius: 12px;
                min-height: 130px;
            }

            #cardIcon {
                font-size: 24px;
            }

            #cardTitle {
                color: #64748b;
                font-size: 13px;
            }

            #cardValue {
                color: #0f172a;
                font-size: 28px;
                font-weight: bold;
            }

            #welcomeBox {
                background-color: white;
                border: 1px solid #e2e8f0;
                border-radius: 12px;
                padding: 15px;
            }

            #welcomeTitle {
                font-size: 20px;
                font-weight: bold;
                color: #0f172a;
            }

            #welcomeText {
                color: #64748b;
                font-size: 14px;
            }
        """)

        self.setStyleSheet(self.styleSheet() + """
            QWidget {
                color: #172033;
                font-family: "Segoe UI";
            }

            QMainWindow {
                background-color: #eef2f6;
            }

            #sidebar {
                background-color: #172033;
                border-right: 1px solid #26344d;
            }

            #logo {
                color: #f8fafc;
                font-size: 21px;
                font-weight: 700;
                padding: 10px;
            }

            #menuButton {
                color: #b9c5d6;
                background-color: transparent;
                border: 1px solid transparent;
                text-align: left;
                padding: 12px 13px;
                border-radius: 7px;
                font-size: 13px;
                font-weight: 600;
            }

            #menuButton:hover {
                background-color: #26344d;
                color: #ffffff;
                border-color: #344665;
            }

            #menuButton:checked {
                background-color: #0f766e;
                color: #ffffff;
                border-color: #5eead4;
            }

            #version {
                color: #8190a6;
                padding: 10px;
                font-size: 12px;
            }

            #pageTitle {
                color: #172033;
                font-size: 27px;
                font-weight: 700;
                padding-bottom: 6px;
            }

            #sectionTitle {
                color: #172033;
                font-size: 20px;
                font-weight: 700;
            }

            #settingLabel {
                color: #344054;
                font-size: 13px;
                font-weight: 600;
            }

            QLineEdit, QPlainTextEdit, QSpinBox, QDateEdit, QComboBox {
                background-color: #ffffff;
                color: #172033;
                border: 1px solid #cbd5e1;
                border-radius: 7px;
                padding: 8px 10px;
                selection-background-color: #0f766e;
                selection-color: #ffffff;
            }

            QLineEdit:focus, QPlainTextEdit:focus, QSpinBox:focus,
            QDateEdit:focus, QComboBox:focus {
                border: 1px solid #0f766e;
                background-color: #ffffff;
            }

            QComboBox QAbstractItemView {
                background-color: #ffffff;
                color: #172033;
                selection-background-color: #d9f3ef;
                selection-color: #172033;
            }

            QPushButton {
                background-color: #ffffff;
                color: #243047;
                border: 1px solid #cbd5e1;
                border-radius: 7px;
                padding: 8px 14px;
                font-size: 13px;
                font-weight: 600;
            }

            QPushButton:hover {
                background-color: #f0fdfa;
                color: #115e59;
                border-color: #5eead4;
            }

            QPushButton:pressed {
                background-color: #ccfbf1;
            }

            QToolTip {
                background-color: #172033;
                color: #ffffff;
                border: 1px solid #5eead4;
                padding: 5px 8px;
            }

            #primaryButton, #editButton {
                background-color: #0f766e;
                color: #ffffff;
                border: 1px solid #0f766e;
            }

            #primaryButton:hover, #editButton:hover {
                background-color: #115e59;
                color: #ffffff;
                border-color: #115e59;
            }

            #deleteButton {
                background-color: #b42318;
                color: #ffffff;
                border: 1px solid #b42318;
            }

            #deleteButton:hover {
                background-color: #912018;
                color: #ffffff;
            }

            QTableWidget {
                background-color: #ffffff;
                color: #172033;
                border: 1px solid #d7dee8;
                border-radius: 8px;
                gridline-color: #e7ebf0;
                font-size: 13px;
                alternate-background-color: #f8fafc;
            }

            QTableWidget::item {
                color: #172033;
                background-color: #ffffff;
                padding: 7px;
            }

            QTableWidget::item:alternate {
                background-color: #f8fafc;
            }

            QTableWidget::item:selected {
                background-color: #d9f3ef;
                color: #134e4a;
            }

            QHeaderView::section {
                background-color: #f1f5f9;
                color: #344054;
                padding: 9px 8px;
                border: none;
                border-bottom: 1px solid #d7dee8;
                font-weight: 700;
            }

            QTabWidget::pane {
                background-color: #ffffff;
                border: 1px solid #d7dee8;
                border-radius: 7px;
            }

            QTabBar::tab {
                background-color: #e9eef4;
                color: #526173;
                padding: 8px 15px;
                border: 1px solid transparent;
            }

            QTabBar::tab:selected {
                background-color: #ffffff;
                color: #0f766e;
                border-color: #d7dee8;
                border-bottom-color: #ffffff;
                font-weight: 700;
            }

            QCheckBox {
                color: #243047;
                spacing: 7px;
            }

            #statCard, #welcomeBox {
                background-color: #ffffff;
                border: 1px solid #d7dee8;
                border-radius: 9px;
            }

            #statCard {
                min-height: 118px;
            }

            #cardIcon {
                color: #0f766e;
                font-size: 23px;
            }

            #cardTitle, #statusLabel, #welcomeText {
                color: #667085;
                font-size: 13px;
            }

            #cardValue {
                color: #172033;
                font-size: 26px;
                font-weight: 700;
            }

            QMessageBox {
                background-color: #ffffff;
            }

            QMessageBox QLabel {
                color: #172033;
            }
        """)