# Kịch bản demo

## Chuẩn bị

1. Mở terminal tại thư mục gốc project.
2. Chạy:

```powershell
powershell -ExecutionPolicy Bypass -File .\run_app.ps1
```

3. Mở URL được in ra, thường là `http://127.0.0.1:8000`.
4. Đăng nhập `admin/admin123` để trình bày Defense Lab và Admin Permissions.

URL local mặc định: `http://127.0.0.1:8000`  
URL Vercel: `https://find-your-path-fyp.vercel.app`

Nếu dùng Vercel, SQLite chỉ là dữ liệu demo tạm thời. Nếu dữ liệu đơn hàng thay đổi hoặc reset sau một lần mở lại app, hãy đăng nhập lại và dùng dữ liệu seed mới.

## Luồng trình bày 5-7 phút

1. Giới thiệu mục tiêu: mô phỏng giao hàng đô thị và so sánh 6 nhóm thuật toán AI.
2. Vào **Defense Lab**, chọn Informed Search/A*, chạy từ `D0` đến một điểm giao.
3. Dùng **Run Next Step** để giải thích `frontier`, `visited`, `g`, `h`, `f` và lý do chọn current node.
4. Chuyển sang Uninformed Search/BFS hoặc UCS để so sánh tiêu chí mở rộng node.
5. Chuyển sang Local Search/Hill Climbing để minh họa tối ưu thứ tự nhiều đơn hàng.
6. Chuyển sang Complex/Online Replanning để trình bày observation, belief update và route mới khi phát hiện sự cố.
7. Chuyển sang CSP/Forward Checking để minh họa assignment, domain và ràng buộc pickup-before-dropoff.
8. Chuyển sang Adversarial/Minimax và Alpha-Beta để giải thích MAX route, MIN disruption và nhánh bị prune.
9. Mở **Admin Permissions**, tắt một thuật toán cho nhóm `standard`, sau đó đăng nhập `shipper_a` để chứng minh guard API.
10. Đăng nhập `shipper_b`, vào **Shipper Mode**, nhận đơn parcel/grocery và lập tuyến từ kho.

## Câu kết

“Hệ thống này không chỉ tìm một đường ngắn, mà cho phép so sánh nhiều nhóm AI trong cùng một bài toán giao hàng có ràng buộc, bất định và phân quyền vận hành.”
