# Phân tích học thuật

## Bài toán

Find Your Path mô phỏng bài toán lập lộ trình giao hàng xe máy trong đô thị. Shipper có thể bắt đầu từ kho hoặc từ vị trí hiện tại, nhận đơn có điểm lấy hàng và điểm trả hàng, sau đó cần tìm tuyến phù hợp trong điều kiện traffic, deadline, tải trọng và sự cố đường.

Ứng dụng dùng graph cache lấy từ OpenStreetMap để bản đồ gần thực tế hơn, nhưng không gọi Overpass hoặc dịch vụ routing bên ngoài khi demo. Toàn bộ quyết định tìm đường, tối ưu route và debug trace đều do thuật toán Python trong project thực hiện.

## 6 nhóm AI được cài đặt

1. **Uninformed Search:** BFS, DFS, UCS trên môi trường deterministic và fully observable.
2. **Informed Search:** Greedy Best-First Search và A* dùng heuristic theo tọa độ.
3. **Local Search:** Hill Climbing, Simulated Annealing, Local Beam và Genetic Algorithm để tối ưu thứ tự nhiều đơn hàng.
4. **Complex Environment / Partial Observability:** Belief-State Search, Online Replanning, AND-OR Search và Expectimax khi một phần cạnh bị ẩn hoặc hành động có nhiều kết quả môi trường.
5. **CSP:** Backtracking + MRV và Forward Checking cho ràng buộc pickup/dropoff, tải trọng, deadline và blocked edge.
6. **Adversarial Search:** Minimax và Alpha-Beta cho worst-case route planning, trong đó MIN chọn disruption bất lợi.

Q-Learning không nằm trong 6 nhóm chính. Endpoint legacy vẫn được giữ để không phá tương thích, nhưng không xuất hiện trong Defense Lab.

## Hàm chi phí

Chi phí cạnh dựa trên thời gian cơ bản và hệ số traffic:

- `light`: 0.8
- `normal`: 1.0
- `heavy`: 1.6
- `blocked`: xem như không khả thi

Route evaluator cộng thêm penalty cho giao trễ và vượt tải. Vì vậy bài toán không chỉ là “đường ngắn nhất”, mà là lập tuyến giao hàng có ràng buộc.

## Mô hình dữ liệu

- Graph gồm node và edge.
- Node có tọa độ nội bộ để vẽ graph và có thể có latitude/longitude khi lấy từ OSM cache.
- Edge có distance, base time, traffic và blocked flag.
- Order có pickup, dropoff, category, urgency, demand, priority và deadline.
- User và permission được lưu trong SQLite để demo phân quyền thuật toán theo nhóm shipper.

## Tiêu chí thành công

- Chạy được app local bằng FastAPI + Flet.
- API trả về metric, explanation và trace step.
- Defense Lab minh họa được frontier, visited nodes, current node và lý do chọn bước tiếp theo.
- Admin bật/tắt thuật toán theo nhóm shipper.
- Shipper nhận đơn, lập lộ trình và xem playback hướng đi.
- Test backend bao phủ các hành vi cốt lõi.

## Đánh giá nhóm Complex Environment

Trong bài toán giao hàng, state đầy đủ không chỉ là vị trí shipper mà còn gồm tình trạng thật của các cạnh: traffic, blocked edge và sự kiện ẩn. Agent biết vị trí hiện tại và goal nghiệp vụ, nhưng chưa chắc biết toàn bộ trạng thái môi trường.

- **Online Replanning:** agent đi theo bản đồ đang tin tưởng, quan sát sự kiện khi vào sensor radius, cập nhật belief rồi gọi A* lại từ node hiện tại tới goal. Thuật toán phù hợp khi hệ thống phản ứng sau khi có percept mới.
- **AND-OR Search:** agent lập kế hoạch có điều kiện trước khi biết outcome của cạnh bất định. OR node là lựa chọn hành động của agent; AND node là các kết quả môi trường như cạnh thông hoặc bị disrupted. Kết quả không chỉ là một path, mà là conditional plan gồm nhánh chính và nhánh dự phòng.

Về bốn tính chất đánh giá thuật toán:

- Online Replanning hoàn thiện nếu mỗi lần quan sát xong, planner con tìm được path trên graph hữu hạn và số lần cập nhật môi trường hữu hạn. Nó không đảm bảo tối ưu toàn cục vì quyết định phụ thuộc percept đến muộn.
- AND-OR Search hoàn thiện trên state space hữu hạn nếu transition model liệt kê đủ outcome, có kiểm tra chu trình và mỗi nhánh AND đều được giải. Nếu mô hình thiếu outcome hoặc graph vô hạn không kiểm soát, tính hoàn thiện không còn được đảm bảo.
- Cả hai dùng A* như planner cấp thấp trên một world cụ thể; phần "complex" nằm ở cách agent xử lý thiếu thông tin và kết quả môi trường bất định.
