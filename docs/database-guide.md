# Hướng dẫn truy xuất dữ liệu

## Có cần cài SQLite không?

Không cần cài SQLite riêng để ứng dụng hoạt động. Python đã có sẵn module chuẩn sqlite3, và project đang sử dụng module này để tạo, đọc và ghi database.

File database nằm tại:

~~~text
src/app/data/fyp.sqlite
~~~

## Hai chế độ lưu trữ hiện tại

| Môi trường | Đường dẫn DB mặc định | Mục đích |
| --- | --- | --- |
| Local | `src/app/data/fyp.sqlite` | Demo và kiểm thử trên máy cá nhân. |
| Vercel preview | `/tmp/fyp.sqlite` | Demo tạm thời, tránh ghi vào filesystem read-only. |

Có thể override bằng biến môi trường:

~~~text
FYP_DB_PATH=<duong-dan-sqlite>
~~~

Lưu ý: SQLite trên Vercel chỉ phù hợp cho demo thuật toán. `/tmp` không phải storage bền vững, nên dữ liệu có thể reset khi cold start, redeploy hoặc function instance thay đổi. Khi mở rộng thành sản phẩm thật, nên chuyển user, permission, orders và assignments sang Postgres như Neon hoặc Supabase.

## Xem danh sách bảng

Chạy từ thư mục gốc project:

~~~powershell
.\.venv\Scripts\python.exe .\scripts\inspect_db.py
~~~

Kết quả hiển thị tên bảng và số dòng hiện có.

## Xem dữ liệu một bảng

~~~powershell
.\.venv\Scripts\python.exe .\scripts\inspect_db.py --table users
.\.venv\Scripts\python.exe .\scripts\inspect_db.py --table orders --limit 10
.\.venv\Scripts\python.exe .\scripts\inspect_db.py --table algorithm_permissions
~~~

Các bảng chính:

- users: tài khoản và nhóm shipper.
- shipper_groups: cấu hình nhóm shipper.
- algorithm_permissions: quyền sử dụng thuật toán.
- orders: dữ liệu đơn hàng.
- shipper_order_assignments: đơn đã được shipper nhận.

## Mở bằng công cụ đồ họa

SQLite GUI là tùy chọn, không bắt buộc. Nếu muốn xem và chỉnh dữ liệu bằng giao diện, có thể mở file fyp.sqlite bằng DB Browser for SQLite hoặc extension SQLite Viewer trong VS Code.

Không nên chỉnh trực tiếp database trong lúc server đang ghi dữ liệu.
