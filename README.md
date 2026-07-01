# RETI Studio — Installer

Ứng dụng desktop tạo video AI (thin client, kết nối backend cloud của RETI).

## Cài đặt
1. Tải **`RETI-Studio-Setup-1.2.0.exe`**.
2. Chạy file → Next → Install. (Nếu Windows SmartScreen cảnh báo: "More info" → "Run anyway".)
3. Mở **RETI Studio** từ Start Menu / Desktop.
4. Dán **mã kích hoạt (token)** được cấp → bắt đầu tạo video.

## Yêu cầu
- Windows 10/11 64-bit.
- Kết nối Internet (app gọi backend cloud).
- Máy chủ RETI đang bật (backend + cloudflared tunnel).

## Ghi chú
- Không cần cài Python/FFmpeg — client gọn nhẹ (~22 MB), mọi xử lý AI chạy trên server.
- API key nằm ở server, không có trong app.
- Dữ liệu cục bộ (mã kích hoạt) lưu tại `%LOCALAPPDATA%\RETI Studio\`.

_Phiên bản: 1.2.0_
