$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

if (-not (Test-Path ".\.venv\Scripts\python.exe")) {
    throw "Chưa tìm thấy .venv. Hãy tạo môi trường ảo trước khi chạy script này."
}

.\.venv\Scripts\python.exe -m PyInstaller --noconfirm --clean --onefile --windowed --name LibraryManager --add-data "library.db;." main.py

Write-Host "Build xong. File exe ở: $PSScriptRoot\dist\LibraryManager.exe"
