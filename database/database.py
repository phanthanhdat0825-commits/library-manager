import hashlib
import shutil
import sqlite3
import sys
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent


def resolve_database_path(frozen=None):
    is_frozen = getattr(sys, "frozen", False) if frozen is None else frozen
    if is_frozen:
        return Path.home() / "AppData" / "Local" / "LibraryManager" / "library.db"
    return BASE_DIR / "library.db"


def ensure_database_file_exists():
    database_path = resolve_database_path()
    database_path.parent.mkdir(parents=True, exist_ok=True)

    if getattr(sys, "frozen", False):
        bundled_path = Path(sys._MEIPASS) / "library.db" if hasattr(sys, "_MEIPASS") else Path(sys.executable).resolve().parent / "library.db"
        if not database_path.exists() and bundled_path.exists():
            shutil.copy2(bundled_path, database_path)
    elif not database_path.exists() and (BASE_DIR / "library.db").exists():
        shutil.copy2(BASE_DIR / "library.db", database_path)

    return database_path


DATABASE_PATH = ensure_database_file_exists()


def get_connection():
    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def initialize_database():
    connection = get_connection()

    cursor = connection.cursor()

    # =========================
    # BẢNG SÁCH
    # =========================
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS books (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            book_code TEXT UNIQUE NOT NULL,
            title TEXT NOT NULL,
            author TEXT,
            category TEXT,
            publisher TEXT,
            publish_year INTEGER,
            quantity INTEGER DEFAULT 1,
            shelf TEXT,
            description TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # =========================
    # BẢNG ĐỘC GIẢ
    # =========================
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS readers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            reader_code TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            phone TEXT,
            email TEXT,
            class_name TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # =========================
    # BẢNG MƯỢN / TRẢ
    # =========================
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS loans (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            reader_id INTEGER NOT NULL,
            borrow_date TEXT NOT NULL,
            due_date TEXT NOT NULL,
            return_date TEXT,
            status TEXT NOT NULL DEFAULT 'Đang mượn',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (reader_id) REFERENCES readers(id)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS loan_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            loan_id INTEGER NOT NULL,
            book_id INTEGER NOT NULL,
            quantity INTEGER NOT NULL CHECK (quantity > 0),
            FOREIGN KEY (loan_id) REFERENCES loans(id),
            FOREIGN KEY (book_id) REFERENCES books(id)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'librarian',
            display_name TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS loan_extensions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            loan_id INTEGER NOT NULL,
            old_due_date TEXT NOT NULL,
            new_due_date TEXT NOT NULL,
            reason TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (loan_id) REFERENCES loans(id)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS fines (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            loan_id INTEGER NOT NULL,
            amount REAL NOT NULL DEFAULT 0,
            reason TEXT NOT NULL,
            paid INTEGER NOT NULL DEFAULT 0,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (loan_id) REFERENCES loans(id)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS publishers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS remote_request_links (
            request_id INTEGER PRIMARY KEY,
            loan_id INTEGER NOT NULL UNIQUE,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (loan_id) REFERENCES loans(id)
        )
    """)

    _add_column_if_missing(cursor, "loans", "extension_count", "INTEGER NOT NULL DEFAULT 0")
    _add_column_if_missing(cursor, "loans", "fine_paid", "INTEGER NOT NULL DEFAULT 0")

    cursor.execute("""
        INSERT OR IGNORE INTO users (username, password_hash, role, display_name)
        VALUES ('admin', '8c6976e5b5410415bde908bd4dee15dfb167a9c873fc4bb8a81f6f2ab448a918', 'admin', 'Quản trị viên')
    """)

    connection.commit()
    connection.close()

    # Close active loans whose books were removed before the loan was returned.
    close_orphaned_loans()


def _add_column_if_missing(cursor, table_name, column_name, definition):
    columns = [row[1] for row in cursor.execute(f"PRAGMA table_info({table_name})")]
    if column_name not in columns:
        cursor.execute(
            f"ALTER TABLE {table_name} ADD COLUMN {column_name} {definition}"
        )


# =========================================================
# SÁCH
# =========================================================

def get_all_books():
    connection = get_connection()

    cursor = connection.cursor()

    cursor.execute("""
        SELECT *
        FROM books
        ORDER BY id DESC
    """)

    books = cursor.fetchall()

    connection.close()

    return books


def search_books(keyword):
    connection = get_connection()

    cursor = connection.cursor()

    keyword = f"%{keyword}%"

    cursor.execute("""
        SELECT *
        FROM books
        WHERE book_code LIKE ?
           OR title LIKE ?
           OR author LIKE ?
           OR category LIKE ?
           OR publisher LIKE ?
        ORDER BY id DESC
    """, (
        keyword,
        keyword,
        keyword,
        keyword,
        keyword
    ))

    books = cursor.fetchall()

    connection.close()

    return books


def add_book(
    book_code,
    title,
    author,
    category,
    publisher,
    publish_year,
    quantity,
    shelf,
    description
):
    connection = get_connection()

    cursor = connection.cursor()

    cursor.execute("""
        INSERT INTO books (
            book_code,
            title,
            author,
            category,
            publisher,
            publish_year,
            quantity,
            shelf,
            description
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        book_code,
        title,
        author,
        category,
        publisher,
        publish_year,
        quantity,
        shelf,
        description
    ))

    if category and category.strip():
        cursor.execute("INSERT OR IGNORE INTO categories (name) VALUES (?)", (category.strip(),))
    if publisher and publisher.strip():
        cursor.execute("INSERT OR IGNORE INTO publishers (name) VALUES (?)", (publisher.strip(),))

    connection.commit()
    connection.close()


def update_book(
    book_id,
    book_code,
    title,
    author,
    category,
    publisher,
    publish_year,
    quantity,
    shelf,
    description
):
    connection = get_connection()

    cursor = connection.cursor()

    cursor.execute("""
        UPDATE books
        SET
            book_code = ?,
            title = ?,
            author = ?,
            category = ?,
            publisher = ?,
            publish_year = ?,
            quantity = ?,
            shelf = ?,
            description = ?
        WHERE id = ?
    """, (
        book_code,
        title,
        author,
        category,
        publisher,
        publish_year,
        quantity,
        shelf,
        description,
        book_id
    ))

    connection.commit()
    connection.close()


def delete_book(book_id):
    connection = get_connection()

    cursor = connection.cursor()

    cursor.execute("""
        SELECT 1
        FROM loan_items
        JOIN loans ON loans.id = loan_items.loan_id
        WHERE loan_items.book_id = ?
          AND loans.return_date IS NULL
        LIMIT 1
    """, (book_id,))
    if cursor.fetchone():
        connection.close()
        raise ValueError("Không thể xóa sách đang nằm trong phiếu mượn chưa trả.")

    cursor.execute("""
        DELETE FROM books
        WHERE id = ?
    """, (book_id,))

    connection.commit()
    connection.close()


# =========================================================
# ĐỘC GIẢ
# =========================================================

def get_all_readers():
    connection = get_connection()

    cursor = connection.cursor()

    cursor.execute("""
        SELECT
            id,
            reader_code,
            name,
            phone,
            email,
            class_name,
            created_at
        FROM readers
        ORDER BY id DESC
    """)

    readers = cursor.fetchall()

    connection.close()

    return readers


def search_readers(keyword):
    connection = get_connection()

    cursor = connection.cursor()

    keyword = f"%{keyword}%"

    cursor.execute("""
        SELECT
            id,
            reader_code,
            name,
            phone,
            email,
            class_name,
            created_at
        FROM readers
        WHERE
            reader_code LIKE ?
            OR name LIKE ?
            OR phone LIKE ?
            OR email LIKE ?
            OR class_name LIKE ?
        ORDER BY id DESC
    """, (
        keyword,
        keyword,
        keyword,
        keyword,
        keyword
    ))

    readers = cursor.fetchall()

    connection.close()

    return readers


def add_reader(
    reader_code,
    name,
    phone="",
    email="",
    class_name=""
):
    connection = get_connection()

    cursor = connection.cursor()

    cursor.execute("""
        INSERT INTO readers (
            reader_code,
            name,
            phone,
            email,
            class_name
        )
        VALUES (?, ?, ?, ?, ?)
    """, (
        reader_code,
        name,
        phone,
        email,
        class_name
    ))

    connection.commit()
    connection.close()


def update_reader(
    reader_id,
    reader_code,
    name,
    phone="",
    email="",
    class_name=""
):
    connection = get_connection()

    cursor = connection.cursor()

    cursor.execute("""
        UPDATE readers
        SET
            reader_code = ?,
            name = ?,
            phone = ?,
            email = ?,
            class_name = ?
        WHERE id = ?
    """, (
        reader_code,
        name,
        phone,
        email,
        class_name,
        reader_id
    ))

    connection.commit()
    connection.close()


def delete_reader(reader_id):
    connection = get_connection()

    cursor = connection.cursor()

    cursor.execute("""
        DELETE FROM readers
        WHERE id = ?
    """, (reader_id,))

    connection.commit()
    connection.close()


# =========================================================
# MƯỢN / TRẢ SÁCH
# =========================================================

def create_loan(reader_id, borrow_date, due_date, items, remote_request_id=None):
    connection = get_connection()

    try:
        cursor = connection.cursor()
        cursor.execute("BEGIN")

        if remote_request_id is not None:
            cursor.execute(
                "SELECT loan_id FROM remote_request_links WHERE request_id = ?",
                (remote_request_id,),
            )
            existing_link = cursor.fetchone()
            if existing_link:
                return existing_link["loan_id"]

        if due_date < borrow_date:
            raise ValueError("Hạn trả không được trước ngày mượn.")

        if not items:
            raise ValueError("Vui lòng chọn ít nhất một sách.")

        cursor.execute(
            "INSERT INTO loans (reader_id, borrow_date, due_date) VALUES (?, ?, ?)",
            (reader_id, borrow_date, due_date),
        )
        loan_id = cursor.lastrowid

        for book_id, quantity in items:
            cursor.execute(
                "SELECT quantity FROM books WHERE id = ?",
                (book_id,),
            )
            book = cursor.fetchone()

            if book is None:
                raise ValueError("Sách được chọn không tồn tại.")

            if quantity < 1 or book["quantity"] < quantity:
                raise ValueError("Số lượng sách hiện có không đủ.")

            cursor.execute(
                "UPDATE books SET quantity = quantity - ? WHERE id = ?",
                (quantity, book_id),
            )
            cursor.execute(
                "INSERT INTO loan_items (loan_id, book_id, quantity) VALUES (?, ?, ?)",
                (loan_id, book_id, quantity),
            )

        if remote_request_id is not None:
            cursor.execute(
                "INSERT INTO remote_request_links (request_id, loan_id) VALUES (?, ?)",
                (remote_request_id, loan_id),
            )

        connection.commit()
        return loan_id
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def get_all_loans():
    connection = get_connection()

    cursor = connection.cursor()
    cursor.execute("""
        SELECT
            loans.id,
            COALESCE(readers.reader_code, '[Đã xóa]') AS reader_code,
            COALESCE(readers.name, '[Độc giả đã xóa]') AS reader_name,
            loans.borrow_date,
            loans.due_date,
            loans.return_date,
            CASE
                WHEN loans.return_date IS NOT NULL THEN 'Đã trả'
                WHEN date(loans.due_date) < date('now') THEN 'Quá hạn'
                ELSE 'Đang mượn'
            END AS status,
            COALESCE(SUM(loan_items.quantity), 0) AS book_count,
            GROUP_CONCAT(books.book_code, ', ') AS book_codes,
            GROUP_CONCAT(books.title, ', ') AS book_titles
        FROM loans
        LEFT JOIN readers ON readers.id = loans.reader_id
        LEFT JOIN loan_items ON loan_items.loan_id = loans.id
        LEFT JOIN books ON books.id = loan_items.book_id
        GROUP BY loans.id
        ORDER BY loans.id DESC
    """)
    loans = cursor.fetchall()
    connection.close()
    return loans


def return_loan(loan_id):
    connection = get_connection()

    try:
        cursor = connection.cursor()
        cursor.execute("BEGIN")
        cursor.execute(
            "SELECT status FROM loans WHERE id = ?",
            (loan_id,),
        )
        loan = cursor.fetchone()

        if loan is None:
            raise ValueError("Phiếu mượn không tồn tại.")

        if loan["status"] == "Đã trả":
            raise ValueError("Phiếu mượn này đã được trả.")

        cursor.execute(
            "SELECT book_id, quantity FROM loan_items WHERE loan_id = ?",
            (loan_id,),
        )
        for item in cursor.fetchall():
            cursor.execute(
                "UPDATE books SET quantity = quantity + ? WHERE id = ?",
                (item["quantity"], item["book_id"]),
            )

        cursor.execute("""
            UPDATE loans
            SET return_date = CURRENT_TIMESTAMP, status = 'Đã trả'
            WHERE id = ?
        """, (loan_id,))
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def get_loan_counts():
    connection = get_connection()

    cursor = connection.cursor()
    cursor.execute("""
        SELECT
            (SELECT COALESCE(SUM(quantity), 0) FROM books) AS total_copies,
            COUNT(DISTINCT CASE WHEN return_date IS NULL THEN loans.id END) AS borrowed_count,
            COUNT(DISTINCT CASE
                WHEN return_date IS NULL AND date(due_date) < date('now') THEN loans.id
            END) AS overdue_count
        FROM loans
    """)
    counts = cursor.fetchone()
    connection.close()
    return counts


def get_report_statistics():
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("SELECT COUNT(*) AS total_titles FROM books")
    books = cursor.fetchone()

    cursor.execute("SELECT COUNT(*) AS total_readers FROM readers")
    readers = cursor.fetchone()

    cursor.execute("SELECT COUNT(*) AS total_loans FROM loans")
    loans = cursor.fetchone()

    cursor.execute("SELECT COUNT(*) AS returned_loans FROM loans WHERE return_date IS NOT NULL")
    returned = cursor.fetchone()

    cursor.execute("""
        SELECT
            books.book_code,
            books.title,
            COALESCE(SUM(loan_items.quantity), 0) AS borrowed_count
        FROM loan_items
        JOIN books ON books.id = loan_items.book_id
        GROUP BY books.id
        ORDER BY borrowed_count DESC, books.title
        LIMIT 10
    """)
    popular_books = cursor.fetchall()

    cursor.execute("""
        SELECT
            readers.reader_code,
            readers.name,
            COALESCE(SUM(loan_items.quantity), 0) AS borrowed_count
        FROM loan_items
        JOIN loans ON loans.id = loan_items.loan_id
        JOIN readers ON readers.id = loans.reader_id
        GROUP BY readers.id
        ORDER BY borrowed_count DESC, readers.name
        LIMIT 10
    """)
    popular_readers = cursor.fetchall()

    cursor.execute("""
        SELECT
            strftime('%Y-%m', loans.borrow_date) AS month,
            COUNT(DISTINCT loans.id) AS loan_count,
            COALESCE(SUM(loan_items.quantity), 0) AS book_count
        FROM loans
        LEFT JOIN loan_items ON loan_items.loan_id = loans.id
        GROUP BY month
        ORDER BY month DESC
        LIMIT 12
    """)
    monthly = cursor.fetchall()

    cursor.execute("""
        SELECT
            COALESCE(NULLIF(TRIM(category), ''), 'Chưa phân loại') AS category,
            COUNT(*) AS title_count,
            COALESCE(SUM(quantity), 0) AS copy_count
        FROM books
        GROUP BY COALESCE(NULLIF(TRIM(category), ''), 'Chưa phân loại')
        ORDER BY copy_count DESC, category
    """)
    categories = cursor.fetchall()

    cursor.execute("""
        SELECT
            (SELECT COALESCE(SUM(quantity), 0) FROM books) AS total_copies,
            COUNT(CASE WHEN return_date IS NULL THEN 1 END) AS borrowed_count,
            COUNT(CASE
                WHEN return_date IS NULL AND date(due_date) < date('now') THEN 1
            END) AS overdue_count
        FROM loans
    """)
    loan_counts = cursor.fetchone()

    connection.close()
    return {
        "total_titles": books["total_titles"],
        "total_copies": loan_counts["total_copies"],
        "total_readers": readers["total_readers"],
        "total_loans": loans["total_loans"],
        "returned_loans": returned["returned_loans"],
        "borrowed_count": loan_counts["borrowed_count"],
        "overdue_count": loan_counts["overdue_count"],
        "popular_books": popular_books,
        "popular_readers": popular_readers,
        "monthly": monthly,
        "categories": categories,
    }


def close_orphaned_loans():
    connection = get_connection()

    try:
        cursor = connection.cursor()
        cursor.execute("""
            UPDATE loans
            SET return_date = CURRENT_TIMESTAMP,
                status = 'Đã trả'
            WHERE return_date IS NULL
              AND EXISTS (
                  SELECT 1
                  FROM loan_items
                  WHERE loan_items.loan_id = loans.id
              )
              AND NOT EXISTS (
                  SELECT 1
                  FROM loan_items
                  JOIN books ON books.id = loan_items.book_id
                  WHERE loan_items.loan_id = loans.id
              )
        """)
        closed_count = cursor.rowcount
        connection.commit()
        return closed_count
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def clear_all_data():
    connection = get_connection()

    try:
        cursor = connection.cursor()
        cursor.execute("DELETE FROM loan_items")
        cursor.execute("DELETE FROM loans")
        cursor.execute("DELETE FROM books")
        cursor.execute("DELETE FROM readers")
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def hash_password(password):
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def authenticate_user(username, password):
    connection = get_connection()
    cursor = connection.cursor()
    cursor.execute("""
        SELECT id, username, role, display_name
        FROM users
        WHERE username = ? AND password_hash = ?
    """, (username, hash_password(password)))
    user = cursor.fetchone()
    connection.close()
    return user


def extend_loan(loan_id, new_due_date, reason=""):
    connection = get_connection()
    try:
        cursor = connection.cursor()
        cursor.execute(
            "SELECT due_date, return_date, extension_count FROM loans WHERE id = ?",
            (loan_id,),
        )
        loan = cursor.fetchone()
        if loan is None:
            raise ValueError("Phiếu mượn không tồn tại.")
        if loan["return_date"] is not None:
            raise ValueError("Không thể gia hạn phiếu đã trả.")
        if new_due_date <= loan["due_date"]:
            raise ValueError("Hạn mới phải sau hạn trả hiện tại.")

        cursor.execute("""
            INSERT INTO loan_extensions (loan_id, old_due_date, new_due_date, reason)
            VALUES (?, ?, ?, ?)
        """, (loan_id, loan["due_date"], new_due_date, reason))
        cursor.execute("""
            UPDATE loans
            SET due_date = ?, extension_count = extension_count + 1
            WHERE id = ?
        """, (new_due_date, loan_id))
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def create_fine(loan_id, amount, reason):
    connection = get_connection()
    cursor = connection.cursor()
    cursor.execute(
        "INSERT INTO fines (loan_id, amount, reason) VALUES (?, ?, ?)",
        (loan_id, amount, reason),
    )
    connection.commit()
    connection.close()


def mark_fine_paid(fine_id):
    connection = get_connection()
    cursor = connection.cursor()
    cursor.execute("UPDATE fines SET paid = 1 WHERE id = ?", (fine_id,))
    connection.commit()
    connection.close()


def get_fines():
    connection = get_connection()
    cursor = connection.cursor()
    cursor.execute("""
        SELECT fines.*, loans.id AS loan_id, readers.name AS reader_name
        FROM fines
        JOIN loans ON loans.id = fines.loan_id
        LEFT JOIN readers ON readers.id = loans.reader_id
        ORDER BY fines.id DESC
    """)
    fines = cursor.fetchall()
    connection.close()
    return fines


def get_categories():
    connection = get_connection()
    rows = connection.execute("SELECT * FROM categories ORDER BY name").fetchall()
    connection.close()
    return rows


def get_publishers():
    connection = get_connection()
    rows = connection.execute("SELECT * FROM publishers ORDER BY name").fetchall()
    connection.close()
    return rows


def add_category(name):
    connection = get_connection()
    connection.execute("INSERT INTO categories (name) VALUES (?)", (name.strip(),))
    connection.commit()
    connection.close()


def add_publisher(name):
    connection = get_connection()
    connection.execute("INSERT INTO publishers (name) VALUES (?)", (name.strip(),))
    connection.commit()
    connection.close()