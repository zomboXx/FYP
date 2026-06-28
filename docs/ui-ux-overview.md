# Tổng quan UI/UX

## Mục tiêu giao diện

Giao diện được thiết kế để phục vụ hai nhu cầu cùng lúc:

- Cho shipper thao tác nghiệp vụ: xem đơn, nhận đơn, lập tuyến và xem playback.
- Cho phần bảo vệ đồ án: trình bày thuật toán, trace từng bước, metric và debug data.

Vì đây là demo học thuật, giao diện ưu tiên khả năng giải thích thuật toán hơn là mô phỏng đầy đủ một ứng dụng giao hàng thương mại.

## Các workspace chính

### Shipper Mode

Shipper Mode tập trung vào luồng vận hành:

- lọc đơn theo category và urgency;
- nhận đơn;
- chọn vị trí bắt đầu hoặc chiến lược kho;
- lập tuyến;
- xem route có hướng và playback từng chặng.

Shipper `standard` dùng mô hình on-demand: vị trí hiện tại -> pickup -> dropoff. Shipper `priority` dùng mô hình depot delivery: xuất phát từ kho và tối ưu thứ tự giao.

### Defense Lab

Defense Lab là màn hình trình bày thuật toán. Mỗi nhóm thuật toán có control riêng và bảng debug riêng:

- Uninformed/Informed: frontier, visited, path, cost, heuristic.
- Local Search: candidate route, best route, cost delta, temperature, beam hoặc generation.
- Complex Environment: hidden edges, observed edges, belief state, route sau replan và AND-OR conditional plan với nhánh chính/nhánh dự phòng.
- CSP: assignment, domain, backtrack và forward checking.
- Adversarial: game tree, MAX/MIN, alpha, beta và prune.

### Admin Permissions

Admin Permissions dùng để bật/tắt thuật toán theo nhóm shipper. Phần này giúp demo có yếu tố sản phẩm thực tế: không phải shipper nào cũng được dùng mọi thuật toán.

### Live Map

Live Map dùng Leaflet/OpenStreetMap để hiển thị bản đồ có zoom, pan, marker node và route. Các node có thể được dùng như dữ liệu đầu vào cho thuật toán của project; app không gọi Google Directions hoặc OSRM để tìm đường thay thuật toán.

## Kiến trúc giao diện

Source UI hiện nằm trong:

```text
src/app/ui
```

Các entrypoint chính:

- `src/app/ui/web_mount.py`: mount Flet app vào FastAPI tại `/`.
- `src/app/ui/flet_app.py`: dashboard Flet chính.
- `src/app/ui/map_page.py`: trang bản đồ Leaflet tại `/map`.
- `src/app/ui/theme.py`: màu sắc, nhóm thuật toán và copy workspace.
- `src/app/ui/state.py`: state dataclass cho Flet dashboard.
- `src/app/ui/components.py`: helper UI nhỏ như button, panel, dropdown, pill.

Các file `src/app/flet_ui.py`, `src/app/web_ui.py` và `src/app/map_ui.py` chỉ còn là wrapper tương thích để tránh làm vỡ import cũ.

API backend được tách khỏi entrypoint chính và nằm trong:

```text
src/app/api
```

`src/app/main.py` chỉ còn nhiệm vụ tạo FastAPI app, include router, đăng ký trang bản đồ và mount Flet UI.

## Cách chạy

```powershell
cd D:\TAI_LIEU_HOC_TAP_DAI_HOC\PersonalPrj\FYP
powershell -ExecutionPolicy Bypass -File .\run_app.ps1
```

Sau đó mở URL được in ra trên terminal.

## Nguyên tắc thiết kế

- Ưu tiên thông tin dày nhưng dễ quét, phù hợp dashboard kỹ thuật.
- Không dùng landing page vì app cần mở thẳng vào trải nghiệm làm việc.
- Dùng màu để phân biệt trạng thái thuật toán, route, visited node và disruption.
- Trace và metric luôn đi cùng visualization để dễ thuyết trình.
- Playback trong Shipper Mode giúp tránh nhầm lẫn khi nhiều tuyến chồng lên nhau.
