# Quy tắc làm việc cho Find Your Path

## Cấu trúc project

- Source chính nằm trong `src/app`.
- API routers nằm trong `src/app/api`.
- UI Python/Flet và Leaflet nằm trong `src/app/ui`.
- Thuật toán nằm trong `src/app/algorithms`.
- Service nghiệp vụ nằm trong `src/app/services`.
- Schema API nằm trong `src/app/models`.
- Dữ liệu cache/demo nằm trong `src/app/data`.
- Tests nằm trong `tests`.
- Scripts hỗ trợ nằm trong `scripts`.

## Quy tắc code

- Giữ package import là `app.*`.
- Không đưa logic thuật toán vào UI.
- Không gọi Google Directions, OSRM hoặc routing service bên ngoài để thay thuật toán của project.
- Comment chỉ dùng để giải thích “vì sao” có quyết định thiết kế đó; không comment lại điều tên hàm/biến đã nói rõ.
- Không để code comment-out, `TODO`, `FIXME`, debug `print` hoặc file runtime trong source.
- Không commit `__pycache__`, `.pytest_cache`, `.venv`, log hoặc SQLite runtime.

## Quy tắc dữ liệu

- SQLite hiện lưu user, nhóm shipper, permission thuật toán, đơn hàng và đơn đã nhận.
- OSM graph cache nằm ở `src/app/data/osm_hcm_q1.json`.
- Nếu thêm custom node/edge bền vững, ưu tiên thiết kế bảng DB riêng thay vì ghi đè file cache OSM.

## Kiểm tra trước khi bàn giao

Chạy hook:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\pre_check.ps1
```

Hook cần pass trước khi demo hoặc commit.
