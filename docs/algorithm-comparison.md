# So sánh thuật toán

| Nhóm | Thuật toán | Mục tiêu | Điểm mạnh | Hạn chế | Vai trò trong demo |
| --- | --- | --- | --- | --- | --- |
| Uninformed Search | BFS | Tìm đường có ít cạnh nhất | Dễ giải thích, phù hợp baseline | Không tối ưu theo thời gian hoặc khoảng cách | Minh họa frontier theo từng lớp |
| Uninformed Search | DFS | Tìm một đường hợp lệ | Dễ thấy chiến lược đi sâu | Có thể đi vòng, không đảm bảo tối ưu | So sánh với BFS/UCS |
| Uninformed Search | UCS | Tối ưu tổng thời gian cạnh | Đúng khi chi phí không âm | Có thể mở rộng nhiều node | Baseline tối ưu chi phí |
| Informed Search | Greedy Best-First | Ưu tiên node gần đích theo heuristic | Nhanh khi heuristic tốt | Có thể chọn đường nhìn gần nhưng thực tế chậm | So sánh với A* |
| Informed Search | A* | Cân bằng chi phí đã đi `g` và heuristic `h` | Thường cho route tốt và dễ trình bày | Phụ thuộc chất lượng heuristic | Lựa chọn chính cho tìm đường |
| Local Search | Hill Climbing | Cải thiện thứ tự giao đơn | Nhanh, trace dễ hiểu | Dễ kẹt cực trị cục bộ | Demo cost delta và best route |
| Local Search | Simulated Annealing | Cho phép nhận bước xấu có kiểm soát | Có cơ hội thoát cực trị cục bộ | Cần lịch nhiệt độ hợp lý | Demo temperature và xác suất accept |
| Local Search | Local Beam | Giữ nhiều route ứng viên | Tìm kiếm rộng hơn Hill Climbing | Tốn nhiều lần đánh giá route | Demo beam và candidate count |
| Local Search | Genetic Algorithm | Tối ưu bằng quần thể route | Phù hợp không gian hoán vị lớn | Runtime cao hơn, kết quả phụ thuộc seed | Demo generation và best cost |
| Complex Environment | Belief-State Search | Lập kế hoạch khi chưa biết đầy đủ cạnh bị ảnh hưởng | Thể hiện partial observability rõ | Cần mô hình belief | Demo belief trước/sau observation |
| Complex Environment | Online Replanning | Quan sát rồi lập lại tuyến khi phát hiện sự cố | Gần bài toán giao hàng thực tế | Phụ thuộc sensor radius | Demo route cũ và route mới |
| Complex Environment | Expectimax | Đánh giá rủi ro theo xác suất | Hợp lý khi disruption có xác suất | Cần xác suất đáng tin | Đóng vai trò stochastic evaluator |
| CSP | Backtracking + MRV | Tìm thứ tự pickup/dropoff hợp lệ | Giải thích rõ assignment/domain | Có thể bùng nổ tổ hợp | Demo backtrack và MRV |
| CSP | Forward Checking | Cắt domain sớm khi vi phạm ràng buộc | Phát hiện infeasible nhanh hơn | Tốn thêm bước kiểm tra consistency | Demo domain bị prune |
| Adversarial Search | Minimax | Chọn tuyến tốt trong tình huống xấu nhất | Mô hình hóa disruption có chủ đích | Duyệt nhiều nhánh | Demo MAX chọn route, MIN chọn disruption |
| Adversarial Search | Alpha-Beta | Cùng giá trị với Minimax nhưng duyệt ít hơn | Prune được nhánh không cần xét | Hiệu quả phụ thuộc thứ tự nhánh | Demo alpha, beta và prune |

## Ghi chú trình bày

- Uninformed Search chỉ cần tìm được đường hoặc tối ưu theo tiêu chí đơn giản, không dùng tri thức tọa độ.
- Informed Search dùng tọa độ để tính heuristic, nhưng quyết định vẫn do thuật toán Python của project thực hiện.
- Local Search tối ưu thứ tự nhiều đơn, không phải tìm một đường đơn lẻ.
- Complex Environment mô phỏng shipper chỉ thấy một phần môi trường và phải cập nhật belief khi quan sát.
- CSP tập trung vào ràng buộc hợp lệ: tải trọng, deadline, pickup trước dropoff và cạnh bị chặn.
- Adversarial Search không mô phỏng hai shipper đua nhau; nó mô phỏng worst-case disruption trên tuyến đường.
