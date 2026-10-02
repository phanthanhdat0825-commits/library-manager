import json
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


class RemoteServiceError(RuntimeError):
    pass


def _request(api_url, path, admin_token=None, method="GET", payload=None):
    base_url = api_url.strip().rstrip("/")
    if not base_url:
        raise RemoteServiceError("Chưa cấu hình địa chỉ dịch vụ online.")
    headers = {"Accept": "application/json"}
    if admin_token:
        headers["X-Admin-Token"] = admin_token
    body = None
    if payload is not None:
        headers["Content-Type"] = "application/json"
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")

    request = Request(f"{base_url}{path}", data=body, headers=headers, method=method)
    try:
        with urlopen(request, timeout=8) as response:
            result = response.read()
    except HTTPError as error:
        try:
            details = json.loads(error.read().decode("utf-8"))
            message = details.get("detail", str(error))
        except (ValueError, UnicodeDecodeError):
            message = str(error)
        raise RemoteServiceError(str(message)) from error
    except (URLError, TimeoutError, OSError) as error:
        raise RemoteServiceError(f"Không kết nối được dịch vụ online: {error}") from error

    if not result:
        return {}
    return json.loads(result.decode("utf-8"))


def sync_catalog(api_url, admin_token, books):
    return _request(api_url, "/api/admin/catalog", admin_token, "PUT", books)


def get_requests(api_url, admin_token, status="pending"):
    result = _request(
        api_url,
        f"/api/admin/requests?status={status}",
        admin_token,
    )
    return result["requests"]


def decide_request(api_url, admin_token, request_id, status, reason="", loan_id=None):
    return _request(
        api_url,
        f"/api/admin/requests/{request_id}",
        admin_token,
        "PATCH",
        {"status": status, "reason": reason, "loan_id": loan_id},
    )
