$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

if (-not $env:LIBRARY_ADMIN_TOKEN) {
    throw "Hãy đặt biến môi trường LIBRARY_ADMIN_TOKEN bằng một chuỗi ngẫu nhiên dài trước khi chạy."
}

if (-not $env:LIBRARY_REMOTE_DB) {
    $dataDirectory = Join-Path $env:LOCALAPPDATA "LibraryManager\Online"
    New-Item -ItemType Directory -Force -Path $dataDirectory | Out-Null
    $env:LIBRARY_REMOTE_DB = Join-Path $dataDirectory "library_remote.db"
}

.\.venv\Scripts\python.exe -m uvicorn web_portal:app --host 0.0.0.0 --port 8000
