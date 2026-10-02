# Dịch vụ thư viện trực tuyến

Dịch vụ này cung cấp danh mục sách và nhận phiếu yêu cầu mượn từ giáo viên/học sinh. Ứng dụng desktop vẫn là nơi quản lý tồn kho và lập phiếu mượn chính thức. Yêu cầu online không giữ chỗ; khi duyệt, desktop kiểm tra lại mã độc giả và tồn kho hiện tại.

## Chạy thử trên máy thư viện

1. Cài dependency trong môi trường ảo:

   ```powershell
   .\.venv\Scripts\python.exe -m pip install -r server_requirements.txt
   ```

2. Tạo khóa quản trị ngẫu nhiên, rồi đặt vào biến môi trường PowerShell. Không đưa khóa này vào mã nguồn:

   ```powershell
   $env:LIBRARY_ADMIN_TOKEN = (& .\.venv\Scripts\python.exe -c "import secrets; print(secrets.token_urlsafe(48))")
   ```

3. Chạy máy chủ:

   ```powershell
   .\run_online_server.ps1
   ```

4. Mở `http://127.0.0.1:8000` để thử portal. Trong desktop, vào **Cài đặt**, nhập địa chỉ API `http://127.0.0.1:8000` và cùng khóa quản trị. Mở **Yêu cầu trực tuyến** rồi chọn **Đồng bộ danh mục web**.

Đây chỉ là chạy thử trên máy hiện tại. Người ở nhà không thể dùng `127.0.0.1` của máy thư viện.

## Cho phép truy cập qua Internet

Triển khai `web_portal.py`, thư mục `web/` và `server_requirements.txt` lên một máy chủ Internet hoặc dịch vụ hosting Python. Cấu hình:

- Start command: `uvicorn web_portal:app --host 0.0.0.0 --port $PORT` (thay `$PORT` theo biến cổng của nhà cung cấp).
- `LIBRARY_ADMIN_TOKEN`: chuỗi ngẫu nhiên dài, giữ bí mật.
- `LIBRARY_REMOTE_DB`: đường dẫn SQLite nằm trên ổ đĩa lưu trữ bền vững của dịch vụ.
- Bật HTTPS cho domain; không mở dịch vụ quản trị ra Internet qua HTTP.

### Cấu hình deploy sẵn trong repo

- `.env.example`: mẫu biến môi trường cần cấu hình
- `render.yaml`: template cho Render
- `Dockerfile`: template deploy cho Docker-compatible host

Sau khi có URL HTTPS, nhập URL đó và `LIBRARY_ADMIN_TOKEN` vào Cài đặt của desktop, lưu, rồi đồng bộ danh mục. Người dùng truy cập URL để xem sách và gửi yêu cầu. Dịch vụ cần ổ đĩa bền vững; nếu host xóa filesystem khi redeploy thì danh mục và yêu cầu sẽ mất. Nên giới hạn truy cập khóa quản trị, sao lưu database online định kỳ và chỉ chạy một instance khi dùng SQLite.

## Luồng sử dụng

- Desktop đồng bộ danh mục sách và số lượng hiện có lên dịch vụ.
- Người dùng tra cứu sách, gửi yêu cầu bằng mã độc giả và thông tin liên hệ; portal cấp mã yêu cầu và mã tra cứu riêng.
- Thủ thư mở **Yêu cầu trực tuyến**, kiểm tra thông tin, rồi duyệt hoặc từ chối với lý do.
- Khi duyệt thành công, desktop tạo phiếu mượn hiện có, trừ số lượng tại database thư viện và cập nhật trạng thái cho người gửi. Nếu mất kết nối lúc xác nhận, có thể làm mới và duyệt lại; ứng dụng chống tạo phiếu trùng.
