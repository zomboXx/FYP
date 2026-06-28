# Đề cương báo cáo

## 1. Giới thiệu

- Bối cảnh giao hàng xe máy trong đô thị Việt Nam.
- Vấn đề: kẹt xe, hạn giao, tải trọng, đường bị chặn và môi trường không quan sát đầy đủ.
- Mục tiêu: xây dựng hệ thống demo giúp so sánh 6 nhóm thuật toán AI trên cùng một bài toán lập lộ trình.

## 2. Phân tích bài toán

- Mô hình bản đồ dưới dạng graph gồm node và edge.
- Mô hình đơn hàng gồm pickup, dropoff, độ ưu tiên, deadline và khối lượng.
- Mô hình shipper gồm vị trí hiện tại, nhóm vận hành và quyền dùng thuật toán.
- Hàm chi phí dựa trên thời gian di chuyển, traffic, giao trễ và vượt tải.
- Các trạng thái đặc biệt: cạnh bị chặn, traffic nặng, thông tin bị ẩn và disruption bất lợi.

## 3. Thiết kế hệ thống

- Source code chính nằm trong `src/app`.
- API được tách thành router trong `src/app/api`.
- FastAPI cung cấp API và mount giao diện Flet tại `/`.
- Flet là giao diện demo chính, không cần Node/npm.
- SQLite lưu user, nhóm shipper, permission thuật toán, đơn hàng và đơn đã nhận.
- OSM cache nằm tại `src/app/data/osm_hcm_q1.json` để demo ổn định, không phụ thuộc mạng.
- Tests nằm trong `tests`, scripts hỗ trợ nằm trong `scripts`.

## 4. Thiết kế cơ sở dữ liệu

- `shipper_groups`: nhóm shipper và mô tả nhóm.
- `users`: tài khoản, vai trò, mật khẩu đã hash và nhóm shipper.
- `algorithm_permissions`: nhóm shipper nào được dùng thuật toán nào.
- `orders`: đơn hàng, category, urgency, pickup, dropoff, demand, priority, deadline và status.
- `shipper_order_assignments`: shipper đã nhận đơn nào và thời điểm nhận.

## 5. Thuật toán

- Uninformed Search: BFS, DFS, UCS.
- Informed Search: Greedy Best-First Search và A*.
- Local Search: Hill Climbing, Simulated Annealing, Local Beam và Genetic Algorithm.
- Complex Environment: Belief-State Search, Online Replanning, AND-OR Search và Expectimax.
- CSP: Backtracking + MRV và Forward Checking.
- Adversarial Search: Minimax và Alpha-Beta.

## 6. Kết quả thực nghiệm

- Bảng so sánh path, visited nodes, runtime và cost.
- Trace step-by-step để trình bày frontier, visited, `g`, `h`, `f`, belief state, AND-OR conditional plan, CSP domain hoặc alpha-beta.
- Kịch bản shipper: lọc đơn, nhận đơn, lập tuyến và xem playback hướng di chuyển.
- Kịch bản admin: bật/tắt thuật toán theo nhóm shipper để chứng minh phân quyền.

## 7. Kết luận và hướng phát triển

- Kết quả đạt được: hệ thống chạy local, có UI, API, DB, phân quyền và 6 nhóm thuật toán.
- Hạn chế: graph cache còn nhỏ, mô hình traffic và observation vẫn được đơn giản hóa.
- Hướng phát triển: lưu custom node/edge vào DB, route history, bản đồ thực tế lớn hơn, traffic realtime và multi-driver routing.
