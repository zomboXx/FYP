# Find Your Path

<p align="center">
  <img src="src/app/ui/assets/app-icon.png" alt="Find Your Path logo" width="160" />
</p>

**AI Route Optimizer for Urban Delivery**  
Trợ lý lập lộ trình cho tài xế, shipper và các dịch vụ di chuyển trong đô thị Việt Nam.

Find Your Path là đồ án cuối kỳ của học phần Trí Tuệ Nhân Tạo. Ứng dụng mô phỏng một hệ thống điều phối giao hàng/di chuyển đô thị, nơi tài xế có thể nhận nhiệm vụ, lập tuyến, theo dõi bản đồ, nhận nhắc nhở chăm sóc sức khỏe và xem thống kê thời gian hoạt động. Phần AI tập trung vào việc áp dụng, so sánh và trực quan hóa nhiều nhóm thuật toán tìm đường, tối ưu và ra quyết định trong cùng một bối cảnh vận hành.

## Thông tin đồ án

| Thông tin | Nội dung |
| --- | --- |
| Trường | Trường Đại học Công nghệ Kỹ thuật Thành phố Hồ Chí Minh |
| Mã học phần | `ARIN330585` |
| Lớp học phần | `252ARIN330585_07` |
| Giảng viên hướng dẫn | TS. Phan Thị Huyền Trang |
| Nhóm thực hiện | Nhóm 5 |

| Họ tên | MSSV |
| --- | --- |
| Nguyễn Đức Phát | `24110296` |
| Nguyễn Văn Thi | `24110334` |

## Trải nghiệm ứng dụng

Ứng dụng đã được triển khai tại: <https://find-your-path-fyp.vercel.app>

Khi cần chạy local để phát triển hoặc kiểm tra source:

```powershell
powershell -ExecutionPolicy Bypass -File .\run_app.ps1
```

## Ứng dụng làm được gì?

Find Your Path gom các luồng quan trọng của một hệ thống điều phối đô thị vào một web app có thể thao tác trực tiếp:

| Nhóm chức năng | Mô tả |
| --- | --- |
| Tài xế/shipper | Đăng nhập theo loại tài khoản, xem nhiệm vụ khả dụng, nhận đơn, lập tuyến, hoàn tất đơn và theo dõi thời gian hoạt động. |
| Điều phối tuyến đường | Tính route theo vị trí hiện tại, kho, pickup và dropoff; hiển thị trực quan trên bản đồ Leaflet/OpenStreetMap. |
| AI/Defense Lab | Chạy, so sánh và quan sát các nhóm thuật toán qua path, visited nodes, runtime, metrics và trace/debug. |
| Quản trị và kiểm thử thuật toán | Quản lý nhóm shipper, quyền thuật toán, kịch bản kiểm thử và các luồng giải thích thuật toán. |
| Chăm sóc tài xế | Nhắc nhở sức khỏe và thống kê thời gian chạy theo ngày/tháng để mô phỏng yếu tố vận hành thực tế. |

Các luồng đáng xem nhanh trên web app:

1. Đăng nhập bằng `shipper_a`, nhận đơn và lập tuyến để xem bản đồ tạo route.
2. Đăng nhập bằng `admin`, mở Defense Lab để chạy thuật toán và quan sát metrics/debug.
3. Xem phần thống kê thời gian hoạt động và nhắc nhở sức khỏe trong luồng shipper.

## Tính năng chính

- Đăng nhập theo vai trò admin, shipper cuốc lẻ và shipper kho.
- Tài xế/shipper xem nhiệm vụ khả dụng, nhận đơn, lập tuyến và hoàn tất đơn.
- Lập tuyến theo các điểm hiện tại, kho, pickup và dropoff tùy loại nhiệm vụ.
- Bản đồ Leaflet/OpenStreetMap hiển thị vị trí, điểm nhận, điểm giao và tuyến đường.
- Defense Lab trực quan hóa kết quả, metrics và trace/debug của các nhóm thuật toán AI.
- Hỗ trợ các nhóm thuật toán như Uninformed Search, Informed Search, Local Search, CSP, Complex Environment và Adversarial Search.
- Admin quản lý nhóm shipper, quyền thuật toán và các kịch bản phục vụ phần vấn đáp.
- Nhắc nhở/chăm sóc sức khỏe cho tài xế/shipper trong quá trình hoạt động.
- Thống kê thời gian chạy trong ngày và theo tháng để theo dõi cường độ làm việc.

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

## Minh họa luồng sử dụng

### Luồng shipper: đăng nhập, nhận đơn và lập tuyến

<p align="center">
  <img src="docs/assets/readme/shipper.gif" alt="Shipper đăng nhập, nhận đơn và lập tuyến trên bản đồ" width="760" />
</p>

### Luồng admin: quản trị và quan sát thuật toán

<p align="center">
  <img src="docs/assets/readme/admin.gif" alt="Admin đăng nhập, quản trị và quan sát thuật toán" width="760" />
</p>

## Tài khoản dùng thử

| Username | Password | Vai trò |
| --- | --- | --- |
| `admin` | `admin123` | Quản trị Defense/Admin mode |
| `shipper_a` | `shipper123` | On-demand: Food/Ride, current -> pickup -> dropoff |
| `shipper_b` | `shipper123` | Depot delivery: Parcel/Grocery, xuất phát từ kho |

## Phát triển

Trước khi bàn giao hoặc commit, chạy hook kiểm tra:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\pre_check.ps1
```

Các ghi chú chi tiết về dữ liệu, storage, kịch bản demo, UI/UX và phân tích thuật toán nằm trong thư mục `docs`.

## Tài liệu

- `docs/business-analysis-handover.md`: nghiệp vụ, scope, stakeholder, flow và acceptance criteria.
- `docs/demo-script.md`: kịch bản demo ngắn.
- `docs/algorithm-comparison.md`: so sánh vai trò, điểm mạnh và hạn chế của từng nhóm thuật toán.
- `docs/database-guide.md`: cách xem SQLite local và ghi chú storage trên Vercel.
- `docs/ui-ux-overview.md`: tổng quan UI/UX.
- `docs/report-outline.md`: đề cương báo cáo học thuật.
- `docs/academic-analysis.md`: phân tích học thuật, mô hình state và tính chất thuật toán.
