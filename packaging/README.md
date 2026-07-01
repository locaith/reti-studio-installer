# Đóng gói RETI Studio thành installer Windows

Bộ công cụ này đóng gói app (FastAPI + render worker + ffmpeg) thành **một ứng dụng desktop**
(cửa sổ riêng qua pywebview) rồi tạo **file cài đặt `.exe`** bằng Inno Setup. Người dùng cuối
**không cần cài Python hay ffmpeg**.

## Thành phần

| File | Vai trò |
|------|---------|
| `../launcher.py` | Điểm khởi động: bật server + worker ở luồng nền, mở cửa sổ desktop. |
| `reti_studio.spec` | Cấu hình PyInstaller (one-folder, kèm template/static/ffmpeg). |
| `installer/reti-studio.iss` | Script Inno Setup tạo file cài đặt. |
| `build.ps1` | Tự động: cài deps → freeze bằng PyInstaller → biên dịch installer. |
| `../requirements-build.txt` | PyInstaller + pywebview. |
| `../vendor/ffmpeg/ffmpeg.exe` | ffmpeg đi kèm (lấy từ imageio-ffmpeg). |

## Dữ liệu chạy (sau khi cài)

App cài vào `C:\Program Files\RETI Studio\` (chỉ đọc). Mọi dữ liệu ghi ra
**`%LOCALAPPDATA%\RETI Studio\`**:

```
%LOCALAPPDATA%\RETI Studio\
├── .env                 # cấu hình + API key (tự tạo từ .env.example lần đầu)
├── data\db.sqlite3      # cơ sở dữ liệu
├── data\uploads\        # ảnh upload
└── data\renders\        # video xuất ra
```

Muốn dùng AI cao cấp (Google Veo) hay agent Gemini: mở `%LOCALAPPDATA%\RETI Studio\.env`,
điền `GEMINI_API_KEY` / `VEO_API_KEY` và đặt `ALLOW_PAID_AI_RENDER=true`.

## Build

Yêu cầu: Windows x64, đã có `.venv` của dự án. Inno Setup là tuỳ chọn (chỉ cần khi muốn ra file cài).

```powershell
# Từ thư mục gốc dự án
powershell -ExecutionPolicy Bypass -File packaging\build.ps1
```

Kết quả:
- `dist\RETI Studio\RETI Studio.exe` — bản portable chạy ngay.
- `dist\installer\RETI-Studio-Setup-1.0.0.exe` — file cài đặt (nếu có Inno Setup).

Cài Inno Setup: `winget install JRSoftware.InnoSetup` rồi chạy lại `build.ps1`,
hoặc thủ công: `ISCC packaging\installer\reti-studio.iss`.

## Kiểm tra nhanh bản đã đóng gói (không mở cửa sổ)

```powershell
& "dist\RETI Studio\RETI Studio.exe" --selftest
```
Lệnh này bật server, gọi thử HTTP rồi thoát; kết quả ghi ở
`%LOCALAPPDATA%\RETI Studio\selftest_result.txt`.

## Ghi chú

- `ffprobe` là tuỳ chọn — nếu thiếu, app vẫn render, chỉ bỏ qua bước kiểm tra file.
  Muốn có, đặt `ffprobe.exe` vào `vendor\ffmpeg\` trước khi build.
- Đổi version: sửa `MyAppVersion` trong `installer\reti-studio.iss`.
- Icon: đặt `packaging\app.ico` để spec và installer tự dùng.
- Debug bản freeze: build biến môi trường `RETI_BUILD_CONSOLE=1` để có cửa sổ console.
