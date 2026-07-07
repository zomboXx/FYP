# Find Your Path - nội dung thuyết trình gợi ý

Ghi chú: không cần đọc y nguyên. Nên nói tự nhiên theo ý chính, mỗi slide chỉ giữ 3-5 câu.

## Slide 1 - Mở đầu

Em chào cô, nhóm em trình bày đề tài **Find Your Path - Smart Urban Delivery Planner**.

Ý tưởng chính của đề tài là mô phỏng bài toán lập tuyến giao hàng đô thị trên graph, sau đó so sánh cách các nhóm thuật toán AI xử lý bài toán này. Ở đây nhóm không chỉ muốn tìm đường ngắn nhất, mà còn quan tâm tới đơn hàng, điểm nhận - điểm giao, độ ưu tiên, thời hạn, trạng thái đường và khả năng giải thích từng bước chạy.

Sau phần trình bày thuật toán, em sẽ mở webapp để cô xem trực tiếp các role và luồng chạy demo.

## Slide 2 - Nội dung trình bày

Phần trình bày của nhóm đi theo 4 ý chính.

Đầu tiên là bài toán đặt ra: vì sao lập tuyến giao hàng đô thị phức tạp hơn bài toán tìm đường đơn giản. Tiếp theo là cách nhóm mô hình hóa bài toán thành state, action, goal và cost. Sau đó là thiết kế hệ thống, tức UI gọi API, service xử lý nghiệp vụ, rồi thuật toán chạy trên dữ liệu graph. Cuối cùng là các thuật toán đại diện và phần demo webapp.

## Slide 3 - Bài toán đặt ra

Trong bài toán này, đầu vào không chỉ có điểm bắt đầu và điểm kết thúc.

Mỗi đơn hàng có điểm nhận, điểm giao, thời hạn, độ ưu tiên và khối lượng. Môi trường giao thông có thể có traffic, cạnh bị chặn hoặc trạng thái đường thay đổi. Shipper cũng có vị trí hiện tại, nhóm vận hành và quyền dùng thuật toán khác nhau.

Vì vậy mục tiêu của nhóm là tạo ra một route hợp lệ, có chi phí hợp lý, đồng thời có trace để giải thích được vì sao thuật toán chọn đường hoặc chọn thứ tự giao như vậy.

## Slide 4 - Mô hình hóa bài toán

Nhóm mô hình hóa bài toán dưới dạng không gian trạng thái.

**State** gồm vị trí hiện tại, các đơn đã nhận, đơn đang giao và trạng thái các cạnh trên graph. **Initial state** có thể là vị trí hiện tại của shipper hoặc kho W1. **Action** là di chuyển qua một cạnh, nhận đơn hoặc giao đơn. **Goal** là hoàn tất các pickup/dropoff cần thiết.

Hàm cost không chỉ tính thời gian di chuyển, mà còn xét traffic multiplier, deadline penalty và capacity penalty. Nhờ vậy cùng một tuyến đường nhưng trong điều kiện khác nhau có thể cho chi phí khác nhau.

## Slide 5 - Thiết kế hệ thống

Về hệ thống, nhóm tách rõ UI, API, service, thuật toán và dữ liệu.

UI dùng Flet để hiển thị Defense Lab, Admin mode và Shipper mode. FastAPI nhận request từ UI. Service xử lý nghiệp vụ như xác thực, quyền thuật toán, đơn hàng và lập tuyến. Phần thuật toán nằm riêng trong `src/app/algorithms`, còn dữ liệu người dùng, quyền, đơn hàng nằm trong SQLite và graph OSM cache.

Điểm quan trọng là UI không chứa logic thuật toán; UI chỉ gửi yêu cầu và hiển thị kết quả, trace, route.

## Slide 6 - Thuật toán đại diện

Nhóm chọn 6 thuật toán đại diện cho 6 nhóm thuật toán AI.

Tìm kiếm không thông tin dùng **DFS**. Tìm kiếm có thông tin dùng **A\***. Tìm kiếm cục bộ dùng **Simple Hill Climbing**. Môi trường phức tạp dùng **AND-OR Search**. Bài toán thỏa ràng buộc dùng **Forward Checking**. Và tìm kiếm đối kháng dùng **Alpha-Beta Pruning**.

Ở mỗi thuật toán, nhóm tập trung vào 3 ý: ý tưởng chính, cách chạy và cách thuật toán tìm ra solution.

## Slide 7 - DFS và A*

DFS là tìm kiếm không thông tin. Thuật toán đi sâu theo một nhánh trước, nếu không tìm được goal thì quay lui. Ưu điểm là đơn giản, dễ cài đặt, nhưng nhược điểm là có thể đi rất sâu và không đảm bảo đường tối ưu nếu graph có nhiều nhánh.

A\* thì có thông tin heuristic. Nó chọn node dựa trên công thức **f(n) = g(n) + h(n)**, trong đó `g(n)` là chi phí đã đi và `h(n)` là ước lượng đến goal. Nhờ heuristic, A\* thường mở rộng ít node hơn DFS và phù hợp hơn với bài toán tìm đường trên bản đồ.

Trong app, A\* được dùng để nối các chặng trên graph, ví dụ từ vị trí hiện tại đến pickup hoặc từ pickup đến dropoff.

## Slide 8 - Hill Climbing và AND-OR Search

Simple Hill Climbing phù hợp khi ta đã có một route ban đầu và muốn cải thiện dần. Thuật toán tạo các route hàng xóm, ví dụ đổi thứ tự đơn, rồi chỉ nhận bước nào làm cost tốt hơn. Khi không còn neighbor tốt hơn, nó dừng và trả về route tốt nhất tìm được.

Nhược điểm là có thể kẹt ở local optimum, nhưng ưu điểm là dễ giải thích và chạy nhanh cho demo.

AND-OR Search dùng cho môi trường có bất định. OR node là lựa chọn của agent, còn AND node là các khả năng môi trường có thể xảy ra. Solution không chỉ là một đường đi cố định, mà là một conditional plan: nếu đường thông thì đi nhánh A, nếu có sự kiện như ngập hoặc chặn đường thì chuyển nhánh B.

## Slide 9 - Forward Checking và Alpha-Beta

Forward Checking thuộc nhóm thỏa ràng buộc. Khi gán một biến, ví dụ chọn đơn hoặc chọn thứ tự giao, thuật toán sẽ cập nhật domain của các biến còn lại và loại sớm các lựa chọn chắc chắn vi phạm ràng buộc như capacity, deadline hoặc thứ tự pickup/dropoff.

Alpha-Beta Pruning thuộc nhóm tìm kiếm đối kháng. Nó dựa trên minimax nhưng cắt bỏ các nhánh không còn ảnh hưởng đến quyết định cuối cùng. Alpha là giá trị tốt nhất phía MAX đang có, beta là giá trị tốt nhất phía MIN đang có; khi alpha lớn hơn hoặc bằng beta thì có thể prune.

Trong bối cảnh giao hàng, nhóm dùng nó để minh họa tư duy chọn phương án trong tình huống có yếu tố bất lợi hoặc disruption, thay vì duyệt hết mọi nhánh.

## Slide 10 - Đăng nhập và phân quyền

Đây là màn hình đăng nhập của webapp.

App có các role card để vào nhanh phần demo. Admin dùng để xem Defense Lab và quản trị quyền. Shipper cuốc lẻ dùng cho đơn riêng, đi từ vị trí hiện tại đến điểm nhận rồi điểm giao. Shipper warehouse dùng cho luồng xuất phát từ kho W1 và tối ưu qua nhiều điểm giao.

Role quyết định màn hình mặc định và quyền thao tác, nên cùng một app nhưng trải nghiệm của admin và shipper sẽ khác nhau.

## Slide 11 - Admin: LAB mode và ADMIN mode

Với role admin, app có hai mode chính.

**LAB mode** là nơi chạy thử thuật toán: chọn nhóm thuật toán, chọn map, chọn thuật toán và xem route/debug timeline. Phần này phục vụ trình bày thuật toán và vấn đáp, vì có thể thấy từng bước mở rộng hoặc quyết định.

**ADMIN mode** dùng để quản lý quyền thuật toán theo nhóm shipper. Ví dụ nhóm warehouse có thể được bật nhiều thuật toán hơn, còn on-demand chỉ dùng một số thuật toán phù hợp. Admin cũng có phần audit summary và map library để quản lý dữ liệu demo.

## Slide 12 - Hai role shipper

SHIP mode có cùng bố cục vận hành nhưng logic khác nhau theo role.

Với **shipper cuốc lẻ**, điểm bắt đầu là vị trí hiện tại. App ưu tiên tìm pickup gần, sau đó giao đến dropoff. Nếu có nhiều đơn cùng điểm nhận và phù hợp, app có thể gom lại để giảm thao tác.

Với **shipper warehouse**, điểm bắt đầu là kho W1. Shipper nhận các đơn dạng parcel/grocery rồi app lập tuyến qua nhiều điểm giao. Ở role này có thể chọn chiến lược như nearest neighbor hoặc global route optimization.

## Slide 13 - Workflow SHIP mode

Luồng SHIP mode gồm 4 bước.

Đầu tiên shipper lọc và nhận đơn. Sau đó chọn vị trí hoặc chiến lược giao hàng để lập lộ trình. Khi route được tạo, app hiển thị map, playback, thống kê và bảng so sánh. Cuối cùng shipper xác nhận hoàn tất đơn, trạng thái đơn được cập nhật lại.

Ngoài luồng chính, app còn có các chức năng phụ như nhắc uống nước, phát hiện ngập, phát hiện tắc đường và hiển thị phương pháp đang dùng. Về mặt thuật toán, profile sẽ quyết định cách xếp thứ tự stop, còn A\* được dùng để nối từng chặng trên graph.

Sau slide này em có thể chuyển sang app để demo trực tiếp.

## Kịch bản demo app gợi ý

1. Vào bằng role **Admin**.
2. Mở **LAB mode**, chọn một thuật toán dễ giải thích như A\*, chạy và chỉ vào map/trace để nói: "Đây là route và đây là các bước thuật toán mở rộng node."
3. Chuyển qua **ADMIN mode**, chỉ phần permission: "Admin có thể bật/tắt thuật toán theo nhóm shipper."
4. Logout, vào **shipper_on_demand**, nhận vài đơn, lập route và nhấn playback nếu cần.
5. Nếu cô hỏi thêm, vào **shipper_warehouse** để cho thấy luồng W1 -> các điểm giao và chiến lược giao hàng.

## Câu trả lời nhanh khi vấn đáp

**Vì sao không dùng Google Directions hoặc OSRM để thay thuật toán?**  
Vì mục tiêu môn học là tự mô hình hóa và chạy thuật toán AI trên graph của project. Dịch vụ ngoài nếu có chỉ nên là tham khảo, không thay phần thuật toán chính.

**DFS khác A\* ở điểm nào?**  
DFS không dùng heuristic, đi sâu theo nhánh nên đơn giản nhưng không tối ưu. A\* dùng `g(n) + h(n)`, nên chọn node có triển vọng hơn và phù hợp với tìm đường.

**Hill Climbing có chắc tối ưu không?**  
Không chắc tối ưu toàn cục, vì có thể kẹt ở local optimum. Nhưng nó dễ chạy, dễ giải thích và phù hợp khi cần cải thiện một route ban đầu.

**Forward Checking giúp gì?**  
Nó loại sớm các lựa chọn vi phạm ràng buộc sau mỗi bước gán, nên giảm số trường hợp phải thử.

**SHIP mode dùng thuật toán thế nào?**  
Role shipper quyết định profile vận hành. On-demand ưu tiên pickup gần và có thể gom đơn cùng điểm nhận. Warehouse dùng chiến lược như nearest neighbor/global optimization để xếp thứ tự giao. Sau đó A\* nối từng chặng trên graph.

**Nếu có ngập hoặc tắc đường thì sao?**  
App có thể cập nhật trạng thái cạnh hoặc chi phí cạnh, sau đó re-plan route. Khi cost thay đổi, thuật toán sẽ chọn tuyến khác nếu tuyến đó hợp lý hơn.

**Tại sao cần phân quyền thuật toán?**  
Vì không phải nhóm shipper nào cũng nên dùng mọi thuật toán. Admin mode giúp bật/tắt thuật toán theo nhóm, vừa phục vụ demo vừa phản ánh quyền vận hành thực tế.
