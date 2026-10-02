import hashlib
import hmac
import json
import os
import secrets
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, Header, HTTPException, Query, Request
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field


BASE_DIR = Path(__file__).resolve().parent
REMOTE_DB_PATH = Path(os.getenv("LIBRARY_REMOTE_DB", BASE_DIR / "remote_data" / "library_remote.db"))
WEB_DIR = BASE_DIR / "web"

app = FastAPI(title="Library Manager Online", docs_url=None, redoc_url=None)
app.mount("/static", StaticFiles(directory=WEB_DIR), name="static")


class RequestItem(BaseModel):
    book_code: str = Field(min_length=1, max_length=40)
    quantity: int = Field(ge=1, le=99)


class BorrowRequestInput(BaseModel):
    reader_code: str = Field(min_length=1, max_length=40)
    name: str = Field(min_length=2, max_length=120)
    requester_type: str = Field(pattern="^(Học sinh|Giáo viên)$")
    class_name: str = Field(default="", max_length=80)
    email: str = Field(default="", max_length=160)
    phone: str = Field(default="", max_length=40)
    note: str = Field(default="", max_length=1000)
    items: list[RequestItem] = Field(min_length=1, max_length=10)


class DecisionInput(BaseModel):
    status: str = Field(pattern="^(approved|rejected)$")
    reason: str = Field(default="", max_length=500)
    loan_id: int | None = Field(default=None, ge=1)


class StatusLookupInput(BaseModel):
    request_id: int = Field(ge=1)
    token: str = Field(min_length=20, max_length=100)


class RateLimitError(ValueError):
    pass


def get_connection():
    REMOTE_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(REMOTE_DB_PATH, timeout=10)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA busy_timeout = 10000")
    return connection


@contextmanager
def database_session():
    connection = get_connection()
    try:
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def initialize_remote_database():
    with database_session() as connection:
        connection.execute("""
            CREATE TABLE IF NOT EXISTS online_books (
                book_code TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                author TEXT NOT NULL DEFAULT '',
                category TEXT NOT NULL DEFAULT '',
                publisher TEXT NOT NULL DEFAULT '',
                available INTEGER NOT NULL DEFAULT 0,
                synced_at TEXT NOT NULL
            )
        """)
        connection.execute("""
            CREATE TABLE IF NOT EXISTS borrow_requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                reader_code TEXT NOT NULL,
                name TEXT NOT NULL,
                requester_type TEXT NOT NULL,
                class_name TEXT NOT NULL DEFAULT '',
                email TEXT NOT NULL DEFAULT '',
                phone TEXT NOT NULL DEFAULT '',
                note TEXT NOT NULL DEFAULT '',
                items_json TEXT NOT NULL,
                tracking_hash TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending',
                decision_reason TEXT NOT NULL DEFAULT '',
                loan_id INTEGER,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)
        connection.execute("""
            CREATE INDEX IF NOT EXISTS idx_borrow_requests_status_created
            ON borrow_requests(status, created_at DESC)
        """)
        connection.execute("""
            CREATE TABLE IF NOT EXISTS public_request_limits (
                source_hash TEXT PRIMARY KEY,
                window_started TEXT NOT NULL,
                request_count INTEGER NOT NULL
            )
        """)


def replace_catalog(books):
    timestamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
    with database_session() as connection:
        connection.execute("BEGIN IMMEDIATE")
        connection.execute("DELETE FROM online_books")
        connection.executemany("""
            INSERT INTO online_books
                (book_code, title, author, category, publisher, available, synced_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, [
            (
                str(book["book_code"]).strip(),
                str(book.get("title") or "").strip(),
                str(book.get("author") or "").strip(),
                str(book.get("category") or "").strip(),
                str(book.get("publisher") or "").strip(),
                max(0, int(book.get("quantity") or 0)),
                timestamp,
            )
            for book in books
        ])
    return timestamp


def list_catalog(search=""):
    with database_session() as connection:
        rows = connection.execute("""
            SELECT book_code, title, author, category, publisher, available, synced_at
            FROM online_books
            WHERE ? = '' OR book_code LIKE ? OR title LIKE ? OR author LIKE ?
                OR category LIKE ? OR publisher LIKE ?
            ORDER BY title COLLATE NOCASE
        """, (search, *([f"%{search}%"] * 5))).fetchall()
        return [dict(row) for row in rows]


def submit_request(payload, source_address=""):
    items = []
    with database_session() as connection:
        connection.execute("BEGIN IMMEDIATE")
        requested = {}
        for item in payload.items:
            code = item.book_code.strip()
            requested[code] = requested.get(code, 0) + item.quantity
        for book_code, quantity in requested.items():
            row = connection.execute(
                "SELECT book_code, title, available FROM online_books WHERE book_code = ?",
                (book_code,),
            ).fetchone()
            if row is None:
                raise ValueError(f"Không tìm thấy sách có mã {book_code}.")
            if row["available"] < quantity:
                raise ValueError(f"Sách '{row['title']}' hiện không đủ số lượng theo yêu cầu.")
            items.append({
                "book_code": row["book_code"],
                "title": row["title"],
                "quantity": quantity,
            })

        token = secrets.token_urlsafe(24)
        token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        source_hash = hashlib.sha256(
            f'{os.getenv("LIBRARY_ADMIN_TOKEN", "")}|{source_address}'.encode("utf-8")
        ).hexdigest()
        limit = connection.execute(
            "SELECT window_started, request_count FROM public_request_limits WHERE source_hash = ?",
            (source_hash,),
        ).fetchone()
        if limit and (
            datetime.now(timezone.utc) - datetime.fromisoformat(limit["window_started"])
        ).total_seconds() < 3600:
            if limit["request_count"] >= 50:
                raise RateLimitError("Đã gửi quá nhiều phiếu từ mạng này. Vui lòng thử lại sau.")
            connection.execute(
                "UPDATE public_request_limits SET request_count = request_count + 1 WHERE source_hash = ?",
                (source_hash,),
            )
        else:
            connection.execute("""
                INSERT INTO public_request_limits (source_hash, window_started, request_count)
                VALUES (?, ?, 1)
                ON CONFLICT(source_hash) DO UPDATE SET
                    window_started = excluded.window_started,
                    request_count = excluded.request_count
            """, (source_hash, now))
        cursor = connection.execute("""
            INSERT INTO borrow_requests (
                reader_code, name, requester_type, class_name, email, phone, note,
                items_json, tracking_hash, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            payload.reader_code.strip(), payload.name.strip(), payload.requester_type,
            payload.class_name.strip(), payload.email.strip(), payload.phone.strip(),
            payload.note.strip(), json.dumps(items, ensure_ascii=False), token_hash,
            now, now,
        ))
        request_id = cursor.lastrowid
    return {"request_id": request_id, "tracking_token": token}
def get_request_status(request_id, token):
    token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
    with database_session() as connection:
        row = connection.execute("""
            SELECT id, status, decision_reason, created_at, updated_at
            FROM borrow_requests
            WHERE id = ? AND tracking_hash = ?
        """, (request_id, token_hash)).fetchone()
    if row is None:
        return None
    return dict(row)


def list_requests(status="pending"):
    with database_session() as connection:
        query = """
            SELECT id, reader_code, name, requester_type, class_name, email, phone,
                note, items_json, status, decision_reason, loan_id, created_at
            FROM borrow_requests
        """
        if status != "all":
            query += " WHERE status = ?"
        query += " ORDER BY created_at DESC"
        rows = connection.execute(query, () if status == "all" else (status,)).fetchall()
    result = []
    for row in rows:
        item = dict(row)
        item["items"] = json.loads(item.pop("items_json"))
        result.append(item)
    return result


def decide_request(request_id, decision):
    if decision.status == "rejected" and not decision.reason.strip():
        raise ValueError("Cần nhập lý do từ chối.")
    if decision.status == "approved" and decision.loan_id is None:
        raise ValueError("Phiếu mượn nội bộ chưa được tạo.")

    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    with database_session() as connection:
        connection.execute("BEGIN IMMEDIATE")
        row = connection.execute(
            "SELECT status, decision_reason, loan_id FROM borrow_requests WHERE id = ?",
            (request_id,),
        ).fetchone()
        if row is None:
            return False
        if row["status"] != "pending":
            if (
                row["status"] == decision.status
                and row["decision_reason"] == decision.reason.strip()
                and row["loan_id"] == decision.loan_id
            ):
                return True
            raise RuntimeError("Yêu cầu này đã được xử lý.")
        connection.execute("""
            UPDATE borrow_requests
            SET status = ?, decision_reason = ?, loan_id = ?, updated_at = ?
            WHERE id = ?
        """, (
            decision.status, decision.reason.strip(), decision.loan_id, now, request_id,
        ))
    return True


def require_admin_token(x_admin_token: str | None):
    expected = os.getenv("LIBRARY_ADMIN_TOKEN", "")
    if not expected:
        raise HTTPException(status_code=503, detail="Dịch vụ chưa cấu hình khóa quản trị.")
    if not x_admin_token or not hmac.compare_digest(x_admin_token, expected):
        raise HTTPException(status_code=401, detail="Không được phép.")


@app.on_event("startup")
def startup():
    initialize_remote_database()


@app.get("/")
def home():
    return FileResponse(WEB_DIR / "index.html")


@app.get("/api/catalog")
def catalog(q: str = Query(default="", max_length=120)):
    return {"books": list_catalog(q.strip())}


@app.post("/api/requests")
def create_public_request(payload: BorrowRequestInput, request: Request):
    try:
        return submit_request(payload, request.client.host if request.client else "")
    except RateLimitError as error:
        raise HTTPException(status_code=429, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


@app.post("/api/requests/status")
def request_status(payload: StatusLookupInput):
    status = get_request_status(payload.request_id, payload.token)
    if status is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy yêu cầu hoặc mã tra cứu không đúng.")
    return status


@app.put("/api/admin/catalog")
def sync_catalog(payload: list[dict], x_admin_token: str | None = Header(default=None)):
    require_admin_token(x_admin_token)
    if len(payload) > 20000:
        raise HTTPException(status_code=413, detail="Danh mục quá lớn.")
    try:
        timestamp = replace_catalog(payload)
    except (KeyError, TypeError, ValueError) as error:
        raise HTTPException(status_code=400, detail="Dữ liệu danh mục không hợp lệ.") from error
    return {"count": len(payload), "synced_at": timestamp}


@app.get("/api/admin/requests")
def admin_requests(
    status: str = Query(default="pending", pattern="^(pending|approved|rejected|all)$"),
    x_admin_token: str | None = Header(default=None),
):
    require_admin_token(x_admin_token)
    return {"requests": list_requests(status)}


@app.patch("/api/admin/requests/{request_id}")
def admin_decision(
    request_id: int,
    decision: DecisionInput,
    x_admin_token: str | None = Header(default=None),
):
    require_admin_token(x_admin_token)
    try:
        changed = decide_request(request_id, decision)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    except RuntimeError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    if not changed:
        raise HTTPException(status_code=404, detail="Không tìm thấy yêu cầu.")
    return {"ok": True}
