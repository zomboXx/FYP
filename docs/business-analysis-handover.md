# Tài liệu BA handover - Find Your Path

Cập nhật: 2026-06-28
Phạm vi: hỗ trợ người mới tham gia dự án hiểu nghiệp vụ, kiến trúc, dữ liệu, luồng người dùng và tiêu chí kiểm tra trước khi làm việc.

## 1. Tóm tắt dự án

Find Your Path là MVP cho đồ án AI cuối khóa, mô phỏng bài toán giao hàng xe máy trong đô thị Việt Nam. Hệ thống cho phép so sánh nhiều nhóm thuật toán AI trên cùng bối cảnh giao hàng có ràng buộc: thời gian, tải trọng, traffic, đường bị chặn, môi trường không quan sát đầy đủ và tình huống bất lợi.

Mục tiêu hiện tại không phải xây dựng một nền tảng giao hàng thương mại hoàn chỉnh. Mục tiêu chính là tạo demo có thể bảo vệ đồ án: có đăng nhập, phân quyền thuật toán theo nhóm shipper, nhận đơn, lập lộ trình, xem bản đồ, và Defense Lab để giải thích thuật toán từng bước.

## Deployment and storage status - 2026-06-24

Trạng thái deploy hiện tại là preview/demo, không phải production. Local demo dùng SQLite tại `src/app/data/fyp.sqlite`. Khi chạy trên Vercel, app dùng SQLite tạm tại `/tmp/fyp.sqlite` để tránh ghi vào filesystem read-only của Vercel Functions.

Điều này phù hợp cho vấn đáp thuật toán AI vì hệ thống tự seed user, permission và đơn hàng demo khi khởi động. Tuy nhiên, `/tmp` không phải storage bền vững: dữ liệu có thể mất khi cold start, redeploy hoặc function instance thay đổi. Nếu phát triển thành sản phẩm rộng hơn, hướng đề xuất là chuyển dữ liệu nghiệp vụ sang Postgres, ưu tiên Neon hoặc Supabase, đồng thời giữ OSM cache là file JSON read-only.

## 2. Giá trị nghiệp vụ

| Giá trị | Ý nghĩa trong dự án |
| --- | --- |
| Mô phỏng vận hành giao hàng đô thị | Người xem thấy được bài toán gần thực tế: shipper, đơn hàng, pickup, dropoff, kho, deadline và traffic. |
| So sánh thuật toán AI | Cùng một scenario có thể chạy BFS, UCS, A*, Local Search, CSP, Complex Environment và Adversarial Search. |
| Giải thích được quyết định thuật toán | API trả `traceSteps`, `metrics`, `debugData` để UI trình bày frontier, visited, cost, heuristic, domain, belief hoặc alpha-beta. |
| Có phân quyền vận hành | Admin có thể bật/tắt thuật toán theo nhóm shipper, giúp demo giống một sản phẩm có policy sử dụng. |
| Demo ổn định offline | App dùng SQLite và OSM cache local, hạn chế phụ thuộc mạng trong lúc bảo vệ. |

## 3. Stakeholder và vai trò

| Vai trò | Mục tiêu | Cần quan tâm |
| --- | --- | --- |
| Sinh viên/nhóm phát triển | Hoàn thiện MVP và bảo vệ đồ án | Luồng demo, thuật toán, test, quy tắc code. |
| Giảng viên/hội đồng | Đánh giá tính đúng đắn và mức độ ứng dụng AI | Vì sao chọn thuật toán, metric, trace, so sánh kết quả. |
| Admin hệ thống | Quản lý quyền dùng thuật toán | Màn Admin Permissions, tài khoản, nhóm shipper. |
| Shipper standard | Nhận đơn on-demand như food/ride | Lọc đơn, nhận đơn, đi từ vị trí hiện tại đến pickup rồi dropoff. |
| Shipper priority | Giao parcel/grocery từ kho | Nhận nhiều đơn, tối ưu thứ tự giao từ depot. |
| Developer mới | Bảo trì hoặc mở rộng dự án | Cấu trúc source, API contract, DB, test, quy tắc không phá thuật toán lõi. |
| Tester/QA | Kiểm tra luồng demo và regression | Acceptance criteria, pre-check, dữ liệu demo. |

## 4. Persona người dùng

### Admin

Admin dùng hệ thống để:

- đăng nhập vào dashboard;
- xem Defense Lab để chạy và giải thích thuật toán;
- bật/tắt quyền dùng thuật toán theo nhóm shipper;
- xem hoặc chuyển nhóm user;
- trình bày demo bảo vệ đồ án.

Tài khoản demo: `admin` / `admin123`.

### Shipper standard

Shipper standard đại diện cho mô hình on-demand:

- chỉ thấy đơn `food` và `ride`;
- có thể bắt đầu từ vị trí hiện tại;
- lộ trình đi theo dạng `current -> pickup -> dropoff`;
- phù hợp demo giao đồ ăn hoặc chở khách.

Tài khoản demo: `shipper_a` / `shipper123`.

### Shipper priority

Shipper priority đại diện cho mô hình depot delivery:

- chỉ thấy đơn `parcel` và `grocery`;
- đơn có pickup tại depot;
- lộ trình bắt đầu từ kho;
- có thể so sánh `nearest_neighbor` và `global_optimization`.

Tài khoản demo: `shipper_b` / `shipper123`.

## 5. Phạm vi hệ thống

### Trong phạm vi

- Đăng nhập JWT HS256.
- Đăng ký user mới bởi admin.
- Quản lý nhóm shipper.
- Quản lý permission thuật toán theo nhóm shipper.
- Xem danh sách đơn khả dụng theo nhóm vận hành.
- Nhận đơn và tự bổ sung pool đơn demo.
- Lập tuyến cho đơn đã nhận.
- Chạy thuật toán pathfinding, delivery optimization, CSP, complex environment và adversarial search.
- Hiển thị UI Flet tại `/`.
- Hiển thị bản đồ Leaflet tại `/map`.
- Dùng SQLite local để lưu dữ liệu demo/runtime.
- Dùng OSM graph cache local tại `src/app/data/osm_hcm_q1.json`.

### Ngoài phạm vi hiện tại

- Thanh toán, pricing, ví shipper hoặc doanh thu.
- Theo dõi GPS realtime.
- Multi-driver dispatch tối ưu toàn cục.
- Tích hợp Google Directions, OSRM hoặc routing service bên ngoài để thay thuật toán.
- Production-grade auth, phân quyền chi tiết theo tổ chức hoặc audit log đầy đủ.
- Traffic realtime từ provider bên ngoài.

## 6. Quy tắc nghiệp vụ chính

| Mã | Quy tắc |
| --- | --- |
| BR-01 | User phải đăng nhập để gọi các API nghiệp vụ, trừ scenario/default và trang UI public. |
| BR-02 | Admin được phép chạy mọi thuật toán và quản lý permission. |
| BR-03 | Shipper chỉ được chạy thuật toán đã bật cho nhóm của mình. |
| BR-04 | Nhóm `standard` chỉ nhận đơn `food` và `ride`. |
| BR-05 | Nhóm `priority` chỉ nhận đơn `parcel` và `grocery`. |
| BR-06 | Với đơn `parcel` và `grocery`, pickup được chuẩn hóa về depot. |
| BR-07 | Hệ thống duy trì tối thiểu 7 đơn khả dụng cho trải nghiệm demo. |
| BR-08 | Khi shipper nhận đơn, các đơn mới cùng nhóm phù hợp được sinh thêm để pool không cạn. |
| BR-09 | On-demand route đi từ vị trí hiện tại tới pickup rồi dropoff. |
| BR-10 | Depot delivery route luôn xuất phát từ depot, bất kể request gửi start khác. |
| BR-11 | Response thuật toán phải có `path`, `visitedNodes`, `metrics`, `runtimeMs`, `explanation`. |
| BR-12 | Khi `debug=true`, response nên có `traceSteps` để UI giải thích từng bước. |
| BR-13 | Không dùng dịch vụ routing bên ngoài để thay kết quả thuật toán của project. |
| BR-14 | Nếu thêm custom node/edge bền vững, ưu tiên thiết kế bảng DB riêng thay vì ghi đè OSM cache. |

## 7. Luồng nghiệp vụ

### 7.1 Đăng nhập

1. Người dùng nhập username/password.
2. UI gọi `POST /api/auth/login`.
3. Backend xác thực password bằng PBKDF2 hash trong SQLite.
4. Backend trả JWT và thông tin user public.
5. UI dùng token trong header `Authorization: Bearer <token>` cho các request tiếp theo.

Kết quả mong muốn: user vào đúng workspace theo role, hoặc nhận lỗi 401 nếu thông tin sai.

### 7.2 Admin bật/tắt thuật toán

1. Admin đăng nhập.
2. UI gọi `GET /api/admin/permissions`.
3. Admin thay đổi trạng thái một thuật toán cho một nhóm shipper.
4. UI gọi `PATCH /api/admin/permissions`.
5. Khi shipper nhóm đó chạy thuật toán bị tắt, API trả 403.

Kết quả mong muốn: permission ảnh hưởng trực tiếp đến API thuật toán, không chỉ ẩn/hiện trên UI.

### 7.3 Shipper nhận đơn

1. Shipper đăng nhập.
2. UI gọi `GET /api/orders/available`.
3. Backend lọc đơn theo nhóm vận hành.
4. Shipper chọn một hoặc nhiều đơn.
5. UI gọi `POST /api/shipper/orders/accept`.
6. Backend ghi vào `shipper_order_assignments`.
7. Backend sinh thêm đơn để pool còn tối thiểu 7 đơn phù hợp.

Kết quả mong muốn: đơn đã nhận không còn xuất hiện trong danh sách available của shipper đó.

### 7.4 Shipper lập tuyến

1. Shipper đã nhận ít nhất một đơn.
2. UI gọi `POST /api/shipper/routes/plan`.
3. Backend xác định operation profile:
   - `standard`: `on_demand`;
   - `priority`: `depot_delivery`.
4. Backend lập các route leg bằng A* trên scenario local.
5. API trả path phẳng, route leg có ngữ nghĩa, metric và trace.

Kết quả mong muốn: UI có thể vẽ route có hướng và playback từng chặng.

### 7.5 Defense Lab chạy thuật toán

1. Người dùng chọn nhóm thuật toán và tham số.
2. UI gọi endpoint tương ứng, ví dụ `POST /api/pathfinding/run`.
3. Backend kiểm permission.
4. Service chạy thuật toán trong `src/app/algorithms`.
5. API trả kết quả chuẩn `AlgorithmResponse`.
6. UI hiển thị path, metric, trace table và giải thích.

Kết quả mong muốn: người demo có đủ dữ liệu để giải thích vì sao thuật toán chọn node hoặc route đó.

## 8. Nhóm thuật toán trong demo

| Nhóm | Thuật toán active | Endpoint chính | Mục đích demo |
| --- | --- | --- | --- |
| Uninformed Search | `bfs`, `dfs`, `ucs` | `/api/pathfinding/run` | Baseline tìm đường không dùng heuristic. |
| Informed Search | `greedy`, `astar` | `/api/pathfinding/run` | So sánh quyết định dựa trên heuristic và cost. |
| Local Search | `hill_climbing`, `simulated_annealing`, `local_beam`, `genetic` | `/api/delivery/optimize`, `/api/shipper/routes/plan` | Tối ưu thứ tự giao nhiều đơn. |
| Complex Environment | `belief_state`, `online_replan`, `and_or`, `expectimax` | `/api/complex/run`, `/api/events/simulate` | Mô phỏng quan sát không đầy đủ, replan khi có sự cố và conditional plan cho outcome bất định. |
| CSP | `backtracking`, `forward_checking` | `/api/csp/solve`, `/api/constraints/check` | Kiểm ràng buộc pickup/dropoff, capacity, deadline. |
| Adversarial Search | `minimax`, `alpha_beta` | `/api/adversarial/run` | Chọn route robust trước disruption bất lợi. |

Endpoint `/api/rl/train` vẫn tồn tại để tương thích legacy, nhưng không nằm trong 6 nhóm active của Defense Lab.

## 9. Dữ liệu và lưu trữ

### 9.1 SQLite

Database local nằm tại:

```text
src/app/data/fyp.sqlite
```

Các bảng chính:

| Bảng | Ý nghĩa |
| --- | --- |
| `shipper_groups` | Danh sách nhóm shipper như `standard`, `priority`. |
| `users` | Tài khoản, role, password hash và nhóm shipper. |
| `algorithm_permissions` | Nhóm shipper nào được dùng thuật toán nào. |
| `orders` | Đơn hàng demo/runtime. |
| `shipper_order_assignments` | Mapping user đã nhận đơn nào và thời điểm nhận. |

Lưu ý: SQLite hiện là dữ liệu runtime của demo. Không nên commit log, cache test, virtualenv hoặc runtime phát sinh ngoài dữ liệu demo được kiểm soát.

### 9.2 OSM cache

OSM graph cache nằm tại:

```text
src/app/data/osm_hcm_q1.json
```

Ứng dụng dùng cache này để demo ổn định, không cần gọi mạng khi tính route. Script tái tạo cache:

```powershell
python scripts/import_osm_graph.py
```

Nếu cần tham khảo hoặc export OSM thủ công, có thể dùng Overpass Turbo, nhưng runtime demo vẫn nên dùng cache local.

### 9.3 Scenario model

Scenario gồm:

- `depot_id`: kho xuất phát;
- `capacity_kg`: tải trọng;
- `nodes`: điểm depot, order, intersection, landmark;
- `edges`: đường nối node, có distance, base time, traffic, blocked;
- `orders`: đơn có pickup, dropoff, demand, deadline, priority.

## 10. API handover

### Auth

| Method | Endpoint | Mục đích |
| --- | --- | --- |
| POST | `/api/auth/login` | Đăng nhập và lấy token. |
| GET | `/api/auth/me` | Lấy thông tin user hiện tại. |
| POST | `/api/auth/register` | Admin tạo user mới. |

### Admin

| Method | Endpoint | Mục đích |
| --- | --- | --- |
| GET | `/api/admin/permissions` | Xem permission thuật toán. |
| PATCH | `/api/admin/permissions` | Bật/tắt thuật toán theo nhóm. |
| GET | `/api/admin/users` | Xem danh sách user. |
| PATCH | `/api/admin/users/{user_id}/group` | Chuyển nhóm shipper. |

### Shipper

| Method | Endpoint | Mục đích |
| --- | --- | --- |
| GET | `/api/orders/available` | Xem đơn khả dụng, có thể lọc `category`, `urgency`. |
| POST | `/api/shipper/orders/accept` | Nhận đơn. |
| POST | `/api/shipper/routes/plan` | Lập tuyến cho đơn đã nhận. |

### Algorithm and scenario

| Method | Endpoint | Mục đích |
| --- | --- | --- |
| GET | `/api/scenario/default` | Lấy scenario mặc định. |
| POST | `/api/pathfinding/run` | Chạy BFS, DFS, UCS, Greedy, A*. |
| POST | `/api/delivery/optimize` | Tối ưu thứ tự giao bằng Local Search. |
| POST | `/api/constraints/check` | Kiểm tra ràng buộc một route. |
| POST | `/api/csp/solve` | Giải lịch giao bằng CSP. |
| POST | `/api/complex/run` | Chạy belief-state, online replanning, AND-OR Search, expectimax. |
| POST | `/api/events/simulate` | Mô phỏng event động và replan. |
| POST | `/api/adversarial/run` | Chạy minimax hoặc alpha-beta. |
| POST | `/api/rl/train` | Endpoint legacy Q-learning. |

## 11. Cấu trúc source cho người mới

```text
src/app
├── api             # FastAPI routers
├── algorithms      # Thuật toán AI và graph logic
├── data            # Scenario, SQLite, OSM cache
├── models          # Pydantic schemas
├── services        # Auth, permission, route orchestration
├── ui              # Flet UI, Leaflet map, state, theme, components
├── main.py         # Tạo FastAPI app, include routers, mount UI
├── flet_ui.py      # Wrapper tương thích import cũ
├── map_ui.py       # Wrapper tương thích import cũ
└── web_ui.py       # Wrapper tương thích import cũ
```

Quy tắc quan trọng khi code:

- Giữ import theo package `app.*`.
- Không đưa logic thuật toán vào UI.
- Không gọi Google Directions, OSRM hoặc routing service bên ngoài để thay thuật toán.
- Không để debug `print`, code comment-out, `TODO`, `FIXME` trong source.
- Comment chỉ dùng để giải thích lý do thiết kế, không nhắc lại tên hàm hoặc biến.

## 12. Tiêu chí nghiệm thu chức năng

### Auth và role

- Login đúng trả token và user info.
- Login sai trả 401.
- Gọi API protected thiếu token trả 401.
- Shipper gọi API admin trả 403.
- Admin gọi được permission và user management.

### Permission thuật toán

- Admin có thể bật/tắt thuật toán cho từng nhóm.
- Shipper bị chặn nếu thuật toán bị tắt.
- Danh sách permission chỉ hiển thị 6 nhóm active, không hiển thị legacy Q-learning.

### Đơn hàng

- Shipper standard chỉ thấy `food`, `ride`.
- Shipper priority chỉ thấy `parcel`, `grocery`.
- Pool available luôn có ít nhất 7 đơn phù hợp cho trải nghiệm demo.
- Đơn đã nhận không quay lại danh sách available của cùng shipper.

### Lập tuyến

- On-demand route bắt đầu từ start user chọn nếu hợp lệ.
- On-demand route có leg `approach_pickup` và `serve_order`.
- Depot delivery luôn bắt đầu từ depot.
- Depot delivery có leg `warehouse_delivery`.
- `global_optimization` không tệ hơn `nearest_neighbor` trong test hiện có.

### Defense Lab

- A* trả trace có frontier, visited, cost và heuristic.
- Complex online replanning trả observed edges và final path đến goal.
- Complex AND-OR Search trả conditional plan có nhánh `ifOpen`, `ifDisrupted` và cờ `complete`.
- CSP forward checking trả assignment khi hợp lệ và trace prune khi infeasible.
- Adversarial alpha-beta cho cùng game value với minimax và mở rộng số node không nhiều hơn minimax.

### UI

- `/` serve được Flet UI và có `flutter_bootstrap.js`.
- `/map` serve được Leaflet map, có marker, route, drag, save và delete manual node.
- Shipper Mode có thể nhận đơn, lập tuyến và xem playback.
- Admin Permissions thay đổi quyền và ảnh hưởng đến API.

## 13. Quy trình setup và chạy local

```powershell
cd D:\TAI_LIEU_HOC_TAP_DAI_HOC\PersonalPrj\FYP
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
$env:PYTHONPATH = ".\src"
uvicorn app.main:app --reload
```

Cách chạy ổn định trên Windows:

```powershell
powershell -ExecutionPolicy Bypass -File .\run_app.ps1
```

Script sẽ tìm Python phù hợp, cài dependency nếu thiếu, xử lý port 8000 nếu đang bận và in URL trên terminal.

## 14. Kiểm tra trước khi bàn giao

Hook bắt buộc trước demo hoặc commit:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\pre_check.ps1
```

Hook thực hiện:

- compile source trong `src`;
- chạy pytest;
- scan source và tests để phát hiện `TODO`, `FIXME`, debug `print`, `console.log`, hoặc code bị comment-out.

Nếu hook fail, cần sửa nguyên nhân trước khi bàn giao.

## 15. Checklist onboarding cho contributor mới

1. Đọc `README.md` để hiểu cách chạy app.
2. Đọc tài liệu này để nắm nghiệp vụ và scope.
3. Đọc `docs/algorithm-comparison.md` để hiểu vai trò từng thuật toán trong demo.
4. Đọc `docs/demo-script.md` để biết luồng thuyết trình.
5. Chạy `run_app.ps1` và đăng nhập cả 3 tài khoản demo.
6. Chạy thử Defense Lab với A*, CSP, Complex và Adversarial.
7. Chạy thử Shipper Mode với `shipper_a` và `shipper_b`.
8. Chạy `scripts/pre_check.ps1` để xác nhận môi trường ổn.
9. Khi sửa code, giữ logic thuật toán trong `src/app/algorithms` hoặc service phù hợp, không đưa vào UI.

## 16. Quy trình làm việc đề xuất

### Khi thêm thuật toán

1. Thêm logic trong `src/app/algorithms`.
2. Thêm schema request nếu cần trong `src/app/models/schemas.py`.
3. Thêm service orchestration trong `src/app/services/route_service.py`.
4. Thêm endpoint trong `src/app/api`.
5. Thêm permission mapping trong `auth_service.py` nếu thuật toán cần phân quyền.
6. Bổ sung test trong `tests`.
7. Cập nhật tài liệu so sánh thuật toán và demo script nếu thuật toán xuất hiện trong UI.

### Khi thêm nghiệp vụ đơn hàng

1. Xác định nhóm shipper nào được thấy loại đơn mới.
2. Cập nhật policy trong service auth/order.
3. Nếu dữ liệu cần lưu bền vững, thêm bảng SQLite hoặc migration thủ công phù hợp.
4. Cập nhật Pydantic schema.
5. Cập nhật API và UI.
6. Kiểm tra lại pool đơn tự bổ sung và route planning.

### Khi sửa UI

1. Giữ UI là lớp trình bày, không đưa thuật toán vào UI.
2. Dùng response API hiện có trước khi thêm state riêng.
3. Đảm bảo layout vẫn hỗ trợ demo Defense Lab, Shipper Mode và Admin Permissions.
4. Nếu thay đổi route visualization, kiểm tra cả path phẳng và `routeLegs`.

## 17. Rủi ro và điểm cần chú ý

| Rủi ro | Ảnh hưởng | Cách kiểm soát |
| --- | --- | --- |
| SQLite runtime thay đổi qua nhiều lần demo | Kết quả đơn hàng có thể khác nhau | Reset DB hoặc kiểm tra seed demo trước khi quay video/bảo vệ. |
| Permission bị admin tắt trong lúc demo | Shipper bị 403 ngoài ý muốn | Trước demo, vào Admin Permissions kiểm tra thuật toán cần dùng. |
| Port 8000 đang bận | App không chạy đúng URL mong đợi | Dùng `run_app.ps1`, script sẽ chọn port kế tiếp. |
| OSM cache bị sửa thủ công | Thuật toán có thể không tìm được path | Không ghi đè cache nếu chưa có quy trình tái tạo rõ ràng. |
| UI phụ thuộc trace field | Thay đổi response thuật toán có thể làm bảng debug trống | Giữ contract `AlgorithmResponse` và thêm test khi sửa. |
| Mã hóa tài liệu cũ hiển thị sai trên terminal | Khó đọc khi dùng PowerShell mặc định | Đọc bằng editor hỗ trợ UTF-8 hoặc dùng Markdown preview. |

## 18. Glossary

| Thuật ngữ | Diễn giải |
| --- | --- |
| Depot | Kho xuất phát của nhóm giao parcel/grocery. |
| Pickup | Điểm nhận hàng hoặc đón khách. |
| Dropoff | Điểm giao hàng hoặc trả khách. |
| On-demand | Mô hình shipper đi từ vị trí hiện tại đến pickup rồi dropoff. |
| Depot delivery | Mô hình giao từ kho qua nhiều điểm dropoff. |
| Scenario | Bộ dữ liệu mô phỏng gồm graph, đơn hàng, depot, capacity. |
| Trace step | Một bước giải thích trong quá trình thuật toán chạy. |
| Frontier | Tập node đang chờ xét trong thuật toán tìm kiếm. |
| Belief state | Trạng thái niềm tin khi môi trường chưa quan sát đầy đủ. |
| AND-OR Search | Tìm kiếm trong môi trường bất định, trả kế hoạch có điều kiện; OR là agent chọn hành động, AND là mọi outcome môi trường cần được xử lý. |
| Forward checking | Kỹ thuật CSP cắt bớt domain sớm khi phát hiện vi phạm. |
| Alpha-beta pruning | Tối ưu minimax bằng cách bỏ qua nhánh không ảnh hưởng kết quả. |

## 19. Tài liệu liên quan

- `README.md`: hướng dẫn chạy, tài khoản demo, API chính.
- `AGENTS.md`: quy tắc làm việc trong repo.
- `docs/report-outline.md`: đề cương báo cáo học thuật.
- `docs/algorithm-comparison.md`: bảng so sánh thuật toán.
- `docs/demo-script.md`: kịch bản demo 5-7 phút.
- `docs/ui-ux-overview.md`: tổng quan UI/UX.
- `tests/test_algorithms.py`: test thuật toán lõi.
- `tests/test_api_auth_shipper.py`: test auth, permission, shipper flow và endpoint demo.
