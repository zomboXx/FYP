# FYP: Find Your Path

**Smart Urban Delivery Planner**  
**Trợ lý tối ưu giao hàng xe máy đô thị**

Find Your Path là MVP cho đồ án AI cuối khóa: mô phỏng bài toán giao hàng xe máy trong đô thị Việt Nam và so sánh 6 nhóm thuật toán AI trong cùng một bối cảnh giao hàng có ràng buộc.

Bản hiện tại tập trung vào demo bảo vệ đồ án: đăng nhập, admin bật/tắt thuật toán theo nhóm shipper, shipper nhận đơn và lập lộ trình, bản đồ, và Defense Lab để debug từng bước thuật toán.

## Demo đã triển khai

URL web app: https://find-your-path-fyp.vercel.app

Ghi chú: bản deploy hiện tại dùng SQLite tạm thời cho demo/vấn đáp AI. Dữ liệu trên Vercel có thể reset khi cold start, redeploy hoặc function instance thay đổi.

## Kiến trúc

- Backend: Python 3.11+, FastAPI, Pydantic, pytest.
- UI: Python Flet single-page UI mounted vào FastAPI tại `/`.
- Map: Leaflet/Flet map, OpenStreetMap tile, route do thuật toán Python của project tính.
- AI core: Uninformed Search, Informed Search, Local Search, Complex Environment, CSP, Adversarial Search.
- Auth/database: JWT HS256, PBKDF2 password hash, SQLite demo/runtime.
- Source: `src/app`; tests: `tests`; scripts: `scripts`; docs: `docs`.
- OSM cache: `src/app/data/osm_hcm_q1.json`.

Project không cần Node/npm để chạy local demo. Browser nhận Flet web client, UI state được cập nhật từ Python qua WebSocket.

## Cài đặt và chạy local

```powershell
cd D:\TAI_LIEU_HOC_TAP_DAI_HOC\PersonalPrj\FYP
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
$env:PYTHONPATH = ".\src"
uvicorn app.main:app --reload
```

Mở app tại `http://127.0.0.1:8000`. API nằm dưới prefix `/api`.

## Chạy ổn định trên Windows

Nên dùng script này khi demo để tránh sai Python, thiếu dependency hoặc port 8000 đang bận:

```powershell
cd D:\TAI_LIEU_HOC_TAP_DAI_HOC\PersonalPrj\FYP
powershell -ExecutionPolicy Bypass -File .\run_app.ps1
```

Script sẽ cài dependency nếu thiếu, tự chuyển port nếu 8000 đang bận, và in URL trên terminal.

## Tài khoản demo

| Username | Password | Vai trò |
| --- | --- | --- |
| `admin` | `admin123` | Quản trị Defense/Admin mode |
| `shipper_a` | `shipper123` | On-demand: Food/Ride, current -> pickup -> dropoff |
| `shipper_b` | `shipper123` | Depot delivery: Parcel/Grocery, xuất phát từ kho |

## Kiểm thử

Chạy hook bắt buộc trước demo, commit hoặc deploy:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\pre_check.ps1
```

Hook compile source, chạy pytest, và scan `src`/`api`/`tests` để tránh `TODO`, `FIXME`, debug `print`, `console.log`, hoặc code bị comment-out.

## Deploy Vercel

Vercel deploy hiện tại phù hợp cho demo, không phải production storage.

Biến môi trường cần có trên Vercel:

```text
FYP_JWT_SECRET=<chuỗi-bí-mật-dài-ngẫu-nhiên>
PYTHONPATH=src
```

Tùy chọn:

```text
FYP_DB_PATH=/tmp/fyp.sqlite
```

Nếu không set `FYP_DB_PATH`, app tự dùng:

- Local: `src/app/data/fyp.sqlite`
- Vercel: `/tmp/fyp.sqlite`

Domain riêng chưa cần cho giai đoạn vấn đáp. Sau này có thể thêm domain trong Vercel Project Settings -> Domains.

## Lộ trình storage

SQLite hiện tại phù hợp cho demo thuật toán vì app tự seed user, permission và đơn hàng. Trên Vercel, SQLite chỉ nên dùng tạm thời vì filesystem function là read-only ngoài `/tmp`, và `/tmp` không phải storage bền vững.

Hướng mở rộng sản phẩm:

1. Tách lớp data-access cho users, permissions, orders và assignments.
2. Chuyển storage bền vững sang Postgres, ưu tiên Neon hoặc Supabase.
3. Giữ OSM cache là JSON read-only.
4. Nếu thêm custom node/edge bền vững, tạo bảng DB riêng thay vì ghi đè `osm_hcm_q1.json`.

## API chính

- `POST /api/auth/login`
- `GET /api/auth/me`
- `GET /api/admin/permissions`
- `PATCH /api/admin/permissions`
- `GET /api/orders/available`
- `POST /api/shipper/orders/accept`
- `POST /api/shipper/orders/complete`
- `POST /api/shipper/routes/plan`
- `GET /api/scenario/default`
- `POST /api/pathfinding/run`
- `POST /api/delivery/optimize`
- `POST /api/constraints/check`
- `POST /api/csp/solve`
- `POST /api/complex/run`
- `POST /api/events/simulate`
- `POST /api/adversarial/run`
- `GET /api/health`

Mỗi response thuật toán gồm `path`, `visitedNodes`, `metrics`, `runtimeMs`, và `explanation`. Khi gửi `debug=true`, response có thêm `traceSteps` và `debugData` để UI trình bày frontier/visited, g-h-f, belief state, CSP domain/assignment hoặc alpha-beta.

## Tài liệu

- `docs/business-analysis-handover.md`: nghiệp vụ, scope, stakeholder, flow, acceptance criteria.
- `docs/database-guide.md`: cách xem SQLite local và ghi chú storage Vercel.
- `docs/demo-script.md`: kịch bản demo 5-7 phút.
- `docs/algorithm-comparison.md`: vai trò, điểm mạnh và hạn chế của từng thuật toán.
- `docs/ui-ux-overview.md`: tổng quan UI/UX.
- `docs/report-outline.md`: đề cương báo cáo học thuật.

## Tái tạo OSM cache

Chỉ cần chạy khi muốn lấy lại dữ liệu từ OpenStreetMap/Overpass:

```powershell
python -m pip install osmnx
python scripts/import_osm_graph.py
```

Lúc demo, app dùng cache local để tránh lỗi mạng.
