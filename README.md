# Find Your Path

**Smart Urban Delivery Planner**  
Trợ lý lập lộ trình giao hàng xe máy trong đô thị Việt Nam.

Find Your Path là MVP cho đồ án AI cuối khóa. Ứng dụng mô phỏng quy trình giao hàng, cho phép admin bật/tắt nhóm thuật toán theo nhóm shipper, shipper nhận đơn và hệ thống lập lộ trình bằng các thuật toán được cài đặt trong project.

## Demo

Web app: <https://find-your-path-fyp.vercel.app>

Bản deploy hiện tại dùng SQLite tạm thời cho mục đích demo. Dữ liệu trên Vercel có thể reset khi cold start, redeploy hoặc function instance thay đổi.

## Tính năng chính

- Đăng nhập với vai trò admin và shipper.
- Admin quản lý quyền sử dụng thuật toán theo nhóm shipper.
- Shipper xem đơn khả dụng, nhận đơn, lập tuyến và hoàn tất đơn.
- Bản đồ Leaflet/OpenStreetMap hiển thị điểm nhận, điểm giao và tuyến đường.
- Defense Lab hỗ trợ quan sát kết quả và debug từng nhóm thuật toán.
- Nhóm Complex Environment có Online Replanning và AND-OR Search để trình bày partial observation, belief update và conditional plan.

Route được tính bởi code Python trong project, không gọi Google Directions, OSRM hoặc routing service bên ngoài để thay thế thuật toán.

## Công nghệ

- Python 3.11+
- FastAPI, Pydantic
- Flet/Flet Web
- Leaflet/OpenStreetMap
- SQLite cho dữ liệu demo/runtime
- pytest cho kiểm thử

## Cấu trúc thư mục

```text
src/app/api          API routers
src/app/ui           UI Flet và Leaflet
src/app/algorithms   Thuật toán lập tuyến và AI
src/app/services     Service nghiệp vụ
src/app/models       Schema API
src/app/data         Dữ liệu cache/demo
tests                Kiểm thử
scripts              Script hỗ trợ
docs                 Tài liệu BA, demo, thuật toán và báo cáo
```

## Chạy local

Cách khuyến nghị trên Windows:

```powershell
powershell -ExecutionPolicy Bypass -File .\run_app.ps1
```

Script sẽ kiểm tra dependency, chọn port phù hợp nếu `8000` đang bận và in URL trên terminal.

Cách chạy thủ công:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
$env:PYTHONPATH = ".\src"
uvicorn app.main:app --reload
```

Mở app tại `http://127.0.0.1:8000`. API nằm dưới prefix `/api`.

## Hướng dẫn bằng hình ảnh

Khu vực này được dành cho GIF hoặc video hướng dẫn cài đặt và chạy demo.

Gợi ý nội dung nên bổ sung sau:

- Cài môi trường và chạy `run_app.ps1`.
- Đăng nhập bằng tài khoản demo.
- Admin bật/tắt thuật toán cho nhóm shipper.
- Shipper nhận đơn, lập tuyến và xem kết quả trên bản đồ.
- Defense Lab quan sát trace/debug của thuật toán.

## Tài khoản demo

| Username | Password | Vai trò |
| --- | --- | --- |
| `admin` | `admin123` | Quản trị Defense/Admin mode |
| `shipper_a` | `shipper123` | On-demand: Food/Ride, current -> pickup -> dropoff |
| `shipper_b` | `shipper123` | Depot delivery: Parcel/Grocery, xuất phát từ kho |

## Kiểm tra

Chạy hook trước khi demo, commit hoặc deploy:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\pre_check.ps1
```

Hook sẽ compile source, chạy test và scan các dấu hiệu code chưa sạch như `TODO`, `FIXME`, debug `print`, `console.log` hoặc code bị comment-out.

## Deploy

Vercel hiện phù hợp cho demo, chưa phải cấu hình production storage.

Biến môi trường cần có:

```text
FYP_JWT_SECRET=<chuỗi-bí-mật-dài-ngẫu-nhiên>
PYTHONPATH=src
```

Tùy chọn:

```text
FYP_DB_PATH=/tmp/fyp.sqlite
```

Nếu không set `FYP_DB_PATH`, app dùng `src/app/data/fyp.sqlite` khi chạy local và `/tmp/fyp.sqlite` khi chạy trên Vercel.

## Tài liệu

- `docs/business-analysis-handover.md`: nghiệp vụ, scope, stakeholder, flow và acceptance criteria.
- `docs/demo-script.md`: kịch bản demo ngắn.
- `docs/algorithm-comparison.md`: so sánh vai trò, điểm mạnh và hạn chế của từng nhóm thuật toán.
- `docs/database-guide.md`: cách xem SQLite local và ghi chú storage trên Vercel.
- `docs/ui-ux-overview.md`: tổng quan UI/UX.
- `docs/report-outline.md`: đề cương báo cáo học thuật.
- `docs/academic-analysis.md`: phân tích học thuật, mô hình state và tính chất thuật toán.

## Ghi chú dữ liệu bản đồ

OSM graph cache nằm ở `src/app/data/osm_hcm_q1.json`. Khi demo, app dùng cache local để tránh phụ thuộc mạng.

Chỉ cần tái tạo cache khi muốn lấy lại dữ liệu từ OpenStreetMap/Overpass:

```powershell
python -m pip install osmnx
python scripts/import_osm_graph.py
```
