import fs from "node:fs/promises";
import path from "node:path";
import { Presentation, PresentationFile } from "@oai/artifact-tool";

const ROOT = "D:/TAI_LIEU_HOC_TAP_DAI_HOC/PersonalPrj/FYP";
const FINAL = `${ROOT}/docs/find-your-path-image-rich-defense-v4-slides.pptx`;
const TMP = "C:/Users/ducph/AppData/Local/Temp/codex-presentations/manual-find-your-path-image-rich-v4/tmp";
const PREVIEW = `${TMP}/preview`;
const LAYOUT = `${TMP}/layout`;
const QA = `${TMP}/qa`;
const ASSET = `${ROOT}/docs/presentation-assets/find-your-path-image-rich-v4`;
const UI_ASSET = `${ROOT}/src/app/ui/assets`;

const W = 1280;
const H = 720;

const C = {
  ink: "#081526",
  ink2: "#0F1B2D",
  panel: "#0F2438",
  panel2: "#102B42",
  cyan: "#00D8FF",
  green: "#14BA5A",
  gold: "#D9C6A3",
  paper: "#F6F2EA",
  paper2: "#FFF8EC",
  sand: "#E7D8B6",
  violet: "#8B5CF6",
  coral: "#EF4444",
  blue: "#1268B3",
  white: "#FFFFFF",
  muted: "#586777",
  pale: "#EAF1F5",
};

const F = {
  editorial: "Playfair Display",
  title: "Montserrat",
  tech: "Oswald",
  body: "Quicksand",
  mono: "Roboto Mono",
};

async function writeBlob(filePath, blob) {
  await fs.mkdir(path.dirname(filePath), { recursive: true });
  await fs.writeFile(filePath, Buffer.from(await blob.arrayBuffer()));
}

async function readImageBlob(imagePath) {
  const bytes = await fs.readFile(imagePath);
  return bytes.buffer.slice(bytes.byteOffset, bytes.byteOffset + bytes.byteLength);
}

function shape(slide, geometry, x, y, w, h, fill, line = "none", width = 0, extra = {}) {
  return slide.shapes.add({
    geometry,
    position: { left: x, top: y, width: w, height: h },
    fill,
    line: { style: "solid", fill: line, width },
    ...extra,
  });
}

function rect(slide, x, y, w, h, fill, line = "none", width = 0, extra = {}) {
  return shape(slide, extra.geometry ?? "rect", x, y, w, h, fill, line, width, extra);
}

function round(slide, x, y, w, h, fill, line = "none", width = 0, radius = "rounded-xl") {
  return rect(slide, x, y, w, h, fill, line, width, { geometry: "roundRect", borderRadius: radius });
}

function ellipse(slide, x, y, w, h, fill, line = "none", width = 0) {
  return shape(slide, "ellipse", x, y, w, h, fill, line, width);
}

function txt(slide, text, x, y, w, h, o = {}) {
  const s = slide.shapes.add({
    geometry: "textbox",
    position: { left: x, top: y, width: w, height: h },
    fill: "none",
    line: { style: "solid", fill: "none", width: 0 },
  });
  s.text = text;
  s.text.fontSize = o.size ?? 22;
  s.text.bold = Boolean(o.bold);
  s.text.color = o.color ?? C.ink;
  s.text.alignment = o.align ?? "left";
  s.text.typeface = o.face ?? F.body;
  return s;
}

function line(slide, x1, y1, x2, y2, color, width = 2) {
  return rect(slide, x1, y1, x2 - x1, y2 - y1, "none", color, width, { geometry: "line" });
}

function pill(slide, text, x, y, w, color, options = {}) {
  round(slide, x, y, w, options.h ?? 38, options.fill ?? `${color}22`, color, 1.3, "rounded-full");
  txt(slide, text, x + 18, y + 9, w - 36, 20, {
    size: options.size ?? 15,
    bold: true,
    color: options.text ?? color,
    align: "center",
    face: options.face ?? F.title,
  });
}

function pin(slide, x, y, color, label = "") {
  ellipse(slide, x - 17, y - 17, 34, 34, `${color}33`, color, 2);
  ellipse(slide, x - 7, y - 7, 14, 14, color, "none", 0);
  if (label) txt(slide, label, x + 16, y - 10, 100, 24, { size: 13, bold: true, color, face: F.tech });
}

function route(slide, pts, color = C.cyan, width = 4) {
  for (let i = 0; i < pts.length - 1; i += 1) {
    line(slide, pts[i][0], pts[i][1], pts[i + 1][0], pts[i + 1][1], color, width);
  }
  pts.forEach((p, i) => pin(slide, p[0], p[1], i === 0 ? C.green : i === pts.length - 1 ? C.coral : color));
}

function footer(slide, n, section, dark = false) {
  rect(slide, 0, 678, W, 42, dark ? "#04101DEE" : "#071526F2");
  txt(slide, "Find Your Path", 44, 690, 180, 16, { size: 12, bold: true, color: C.white, face: F.title });
  txt(slide, `${String(n).padStart(2, "0")} / ${section}`, 1030, 690, 190, 16, {
    size: 12,
    color: dark ? "#A9C4D7" : "#DDE7EE",
    align: "right",
    face: F.mono,
  });
}

async function addImage(slide, imagePath, x, y, w, h, alt, fit = "cover", extra = {}) {
  slide.images.add({
    blob: await readImageBlob(imagePath),
    contentType: "image/png",
    alt,
    fit,
    position: { left: x, top: y, width: w, height: h },
    ...extra,
  });
}

async function bg(slide, kind) {
  const file =
    kind === "hero"
      ? `${ASSET}/hero-route-bg.png`
      : kind === "paper"
        ? `${ASSET}/paper-map-bg.png`
        : `${ASSET}/technical-lab-bg.png`;
  await addImage(slide, file, 0, 0, W, H, `${kind} generated background`, "cover");
}

function lightTitle(slide, n, section, title, subtitle) {
  rect(slide, 0, 0, W, H, "#FFFDF6C8");
  footer(slide, n, section, false);
  txt(slide, section.toUpperCase(), 72, 44, 240, 22, { size: 13, bold: true, color: C.green, face: F.title });
  txt(slide, title, 72, 84, 760, 70, { size: 45, bold: true, color: C.ink, face: F.title });
  txt(slide, subtitle, 74, 158, 760, 34, { size: 20, color: C.muted, face: F.body });
  rect(slide, 74, 204, 132, 4, C.green);
}

function darkTitle(slide, n, section, title, subtitle) {
  rect(slide, 0, 0, W, H, "#061525AA");
  footer(slide, n, section, true);
  txt(slide, section.toUpperCase(), 72, 44, 260, 22, { size: 13, bold: true, color: C.green, face: F.title });
  txt(slide, title, 72, 86, 800, 64, { size: 44, bold: true, color: C.white, face: F.title });
  txt(slide, subtitle, 74, 154, 720, 34, { size: 20, color: "#B8C6D4", face: F.body });
  rect(slide, 74, 202, 132, 4, C.cyan);
}

function card(slide, x, y, w, h, fill, lineColor, title, body, color, icon = "") {
  round(slide, x, y, w, h, fill, lineColor, 1.2, "rounded-xl");
  rect(slide, x + 22, y + 20, 74, 5, color);
  if (icon) {
    ellipse(slide, x + 24, y + 48, 34, 34, `${color}18`, color, 1.2);
    txt(slide, icon, x + 31, y + 56, 20, 16, { size: 16, bold: true, color, align: "center", face: F.title });
  }
  txt(slide, title, x + (icon ? 84 : 22), y + 42, w - (icon ? 106 : 44), 28, {
    size: 22,
    bold: true,
    color: fill === C.white ? C.ink : C.white,
    face: F.title,
  });
  txt(slide, body, x + 22, y + 82, w - 44, h - 96, {
    size: 16,
    color: fill === C.white ? C.muted : "#C9D8E5",
    face: F.body,
  });
}

function notes(slide, lines) {
  slide.notes = lines.join("\n");
}

async function buildDeck() {
  await fs.mkdir(PREVIEW, { recursive: true });
  await fs.mkdir(LAYOUT, { recursive: true });
  await fs.mkdir(QA, { recursive: true });

  const deck = Presentation.create({ slideSize: { width: W, height: H } });

  {
    const s = deck.slides.add();
    await bg(s, "hero");
    rect(s, 0, 0, 630, H, "#061525D8");
    rect(s, 610, 0, 160, H, "#06152555");
    await addImage(s, `${UI_ASSET}/app-icon.png`, 68, 66, 118, 118, "Find Your Path app icon", "contain");
    txt(s, "FIND\nYOUR PATH", 70, 222, 540, 160, { size: 68, bold: true, color: C.white, face: F.editorial });
    txt(s, "Smart Urban Delivery Planner", 74, 394, 480, 36, { size: 28, bold: true, color: C.green, face: F.title });
    txt(s, "So sánh 6 nhóm thuật toán AI cho bài toán lập tuyến giao hàng đô thị", 76, 448, 510, 58, {
      size: 20,
      color: "#D9E6F0",
      face: F.body,
    });
    pill(s, "20 phút: trình bày + demo + vấn đáp", 74, 544, 338, C.cyan, { fill: "#00D8FF16", text: "#D8F8FF", size: 13 });
    pill(s, "Nhóm 5", 432, 544, 132, C.green, { fill: "#14BA5A18", text: "#CFFBE1" });
    txt(s, "Nguyễn Đức Phát - Nguyễn Văn Thi\nGVHD: TS. Phan Thị Huyền Trang", 76, 614, 480, 40, {
      size: 14,
      color: "#C7D5E1",
      face: F.body,
    });
    footer(s, 1, "Opening", true);
    notes(s, ["Mở bằng bài toán giao hàng đô thị và mục tiêu so sánh 6 nhóm thuật toán.", "Nhắc có demo app trong phần giữa để kiểm chứng trace/metric."]);
  }

  {
    const s = deck.slides.add();
    await bg(s, "paper");
    lightTitle(s, 2, "Agenda", "Nội dung trình bày", "Đi theo một tuyến: từ bài toán đến demo và vấn đáp");
    const items = [
      ["01", "Bài toán", "Motivation & mô hình hóa", C.green, 238],
      ["02", "Hệ thống", "UI, API, service, dữ liệu", C.blue, 326],
      ["03", "Thuật toán", "6 nhóm AI & trace", C.cyan, 414],
      ["04", "Demo", "Defense Lab + Shipper", C.gold, 502],
      ["05", "Đánh giá", "Kết quả, hạn chế, Q&A", C.violet, 590],
    ];
    line(s, 155, 258, 155, 610, "#B9C7C5", 3);
    items.forEach(([num, title, sub, color, y], i) => {
      ellipse(s, 122, y - 24, 66, 66, i % 2 ? C.ink : color, C.white, 2);
      txt(s, String(i + 1), 138, y - 2, 36, 22, { size: 20, bold: true, color: C.white, align: "center", face: F.title });
      txt(s, title, 220, y - 12, 260, 28, { size: 22, bold: true, color: C.ink, face: F.title });
      txt(s, sub, 220, y + 18, 360, 22, { size: 15, color: C.muted, face: F.body });
      line(s, 500, y + 2, 772, y + 2, "#CAD8D8", 1.4);
    });
    route(s, [[822, 578], [874, 506], [842, 430], [890, 356], [978, 316], [944, 236], [1030, 178]], C.green, 4);
    round(s, 846, 484, 200, 68, "#FFFFFFD8", "#D6E4E2", 1, "rounded-xl");
    txt(s, "Demo app chiếm 5-6 phút", 870, 504, 150, 26, { size: 18, bold: true, color: C.green, align: "center", face: F.title });
    notes(s, ["Không đọc agenda quá lâu; nói đây là route của buổi bảo vệ.", "Nhấn mạnh phần demo nằm ở giữa để cô thấy app vận hành thật."]);
  }

  {
    const s = deck.slides.add();
    await bg(s, "paper");
    lightTitle(s, 3, "Problem", "Bài toán đặt ra", "Giao hàng đô thị không chỉ là tìm đường ngắn nhất");
    card(s, 84, 254, 298, 148, C.white, "#DDE6E6", "Đơn hàng", "pickup/dropoff, deadline, độ ưu tiên và khối lượng", C.green, "1");
    card(s, 410, 254, 298, 148, C.white, "#DDE6E6", "Môi trường", "traffic, cạnh bị chặn, thông tin quan sát chưa đầy đủ", C.cyan, "2");
    card(s, 84, 430, 298, 148, C.white, "#DDE6E6", "Shipper", "vị trí hiện tại, nhóm vận hành và quyền dùng thuật toán", C.gold, "3");
    card(s, 410, 430, 298, 148, C.white, "#DDE6E6", "Mục tiêu", "route hợp lệ, chi phí hợp lý, trace giải thích được", C.coral, "4");
    round(s, 760, 238, 378, 350, "#081526E8", "#173A54", 1.2, "rounded-2xl");
    await addImage(s, `${UI_ASSET}/map-icons/shipper-bike.png`, 822, 308, 92, 92, "Shipper bike", "contain");
    await addImage(s, `${UI_ASSET}/map-icons/pickup-parcel.png`, 958, 260, 78, 78, "Pickup parcel", "contain");
    await addImage(s, `${UI_ASSET}/map-icons/dropoff-pin.png`, 996, 420, 78, 78, "Dropoff pin", "contain");
    route(s, [[842, 490], [916, 414], [982, 368], [1032, 458]], C.cyan, 4);
    txt(s, "Graph + ràng buộc", 794, 520, 310, 34, { size: 28, bold: true, color: C.white, align: "center", face: F.title });
    txt(s, "node, edge, cost, order state", 800, 556, 300, 22, { size: 16, color: "#BFD2DF", align: "center", face: F.mono });
    notes(s, ["Đặt bài toán bằng ngôn ngữ thực tế: giao hàng có deadline, traffic và giới hạn quyền vận hành.", "Dẫn sang mô hình state/goal/cost."]);
  }

  {
    const s = deck.slides.add();
    await bg(s, "paper");
    lightTitle(s, 4, "Model", "Mô hình hóa bài toán", "State, action, goal test và cost function");
    const nodes = [
      ["STATE", "vị trí\nđơn đã nhận\ntrạng thái cạnh", 112, C.green],
      ["INITIAL", "shipper hiện tại\nhoặc kho", 366, C.blue],
      ["ACTION", "đi cạnh kế tiếp\nnhận/giao đơn", 620, C.cyan],
      ["GOAL", "hoàn tất pickup\nvà dropoff", 874, C.coral],
    ];
    nodes.forEach(([label, body, x, color], i) => {
      if (i < nodes.length - 1) line(s, x + 156, 355, x + 238, 355, "#A8BBC4", 4);
      round(s, x, 274, 160, 164, "#FFFFFFEC", color, 2, "rounded-2xl");
      ellipse(s, x + 22, 300, 40, 40, `${color}22`, color, 1.4);
      txt(s, String(i + 1), x + 33, 310, 20, 22, { size: 18, bold: true, color, align: "center", face: F.title });
      txt(s, label, x + 22, 354, 118, 24, { size: 18, bold: true, color: C.ink, face: F.title });
      txt(s, body, x + 22, 386, 118, 54, { size: 12, color: C.muted, face: F.body });
    });
    round(s, 200, 496, 880, 120, "#081526E8", "#173A54", 1.3, "rounded-xl");
    txt(s, "cost = base time × traffic multiplier", 236, 518, 810, 28, {
      size: 23,
      bold: true,
      color: C.cyan,
      align: "center",
      face: F.mono,
    });
    txt(s, "+ deadline / capacity penalty", 236, 548, 810, 28, {
      size: 23,
      bold: true,
      color: C.cyan,
      align: "center",
      face: F.mono,
    });
    txt(s, "OSM cache hiển thị bản đồ; quyết định routing do thuật toán Python trong project thực hiện.", 234, 586, 814, 22, {
      size: 15,
      color: "#D6E6F2",
      align: "center",
      face: F.body,
    });
    notes(s, ["Nếu bị hỏi: state không chỉ là tọa độ, mà còn đơn hàng và trạng thái cạnh.", "Nhấn mạnh không gọi Directions/OSRM để thay thuật toán."]);
  }

  {
    const s = deck.slides.add();
    await bg(s, "tech");
    darkTitle(s, 5, "System", "Thiết kế hệ thống", "Luồng dữ liệu từ UI tới thuật toán và trace trả về");
    const steps = [
      ["Flet UI", "Defense Lab\nShipper Mode", 88, C.cyan],
      ["FastAPI", "API routers", 326, C.green],
      ["Services", "auth / route\nmap service", 564, C.gold],
      ["AI Core", "6 nhóm thuật toán", 802, C.violet],
      ["SQLite + OSM", "user, orders\ngraph cache", 1040, C.coral],
    ];
    steps.forEach(([label, body, x, color], i) => {
      if (i < steps.length - 1) line(s, x + 178, 360, x + 224, 360, "#3A6E8A", 3);
      round(s, x, 280, 178, 160, "#061525D8", "#24506A", 1.2, "rounded-xl");
      rect(s, x + 24, 302, 72, 5, color);
      txt(s, label, x + 22, 330, 134, 28, { size: 23, bold: true, color: C.white, align: "center", face: F.title });
      txt(s, body, x + 18, 374, 142, 44, { size: 15, color: "#B9C9D6", align: "center", face: F.body });
    });
    round(s, 170, 506, 940, 74, "#0D3044E8", "#1F5A78", 1, "rounded-xl");
    txt(s, "Boundary quan trọng: UI không chứa logic thuật toán; routing do package app.algorithms xử lý.", 210, 530, 860, 26, {
      size: 22,
      bold: true,
      color: C.cyan,
      align: "center",
      face: F.title,
    });
    notes(s, ["Slide này trả lời câu hệ thống chạy như thế nào.", "Nói rõ separation: UI gọi API/service, thuật toán nằm trong src/app/algorithms."]);
  }

  {
    const s = deck.slides.add();
    await addImage(s, `${ASSET}/algorithm-engine-illustration.png`, 0, 0, W, H, "Generated algorithm engine illustration", "cover");
    rect(s, 0, 0, W, H, "#06152554");
    rect(s, 0, 0, W, 188, "#061525B8");
    footer(s, 6, "Algorithms", true);
    txt(s, "6 nhóm thuật toán áp dụng", 72, 54, 700, 58, { size: 46, bold: true, color: C.white, face: F.title });
    txt(s, "Mỗi nhóm giải một lát cắt khác nhau của bài toán route planning", 74, 124, 720, 28, {
      size: 20,
      color: "#C7D9E7",
      face: F.body,
    });
    const chips = [
      ["Uninformed", "BFS / DFS / UCS", 72, 238, C.blue],
      ["Informed", "Greedy / A*", 72, 300, C.green],
      ["Local", "Hill / SA / Beam / GA", 72, 362, C.gold],
      ["Complex", "Belief / Replan / AND-OR", 918, 238, C.cyan],
      ["CSP", "MRV / Forward Checking", 918, 300, C.coral],
      ["Adversarial", "Minimax / Alpha-Beta", 918, 362, C.violet],
    ];
    chips.forEach(([a, b, x, y, color]) => {
      round(s, x, y, 300, 48, "#061525D8", color, 1.1, "rounded-full");
      txt(s, a, x + 18, y + 9, 126, 18, { size: 14, bold: true, color, face: F.title });
      txt(s, b, x + 152, y + 9, 130, 18, { size: 11, color: "#D6E5EF", face: F.mono });
    });
    notes(s, ["Không đọc hết tên thuật toán; nói vai trò của từng nhóm.", "Dẫn sang slide A* để cô thấy một trace cụ thể."]);
  }

  {
    const s = deck.slides.add();
    await bg(s, "tech");
    darkTitle(s, 7, "Trace", "Ví dụ A*: trace tìm đường", "A* chọn node có f(n) = g(n) + h(n)");
    round(s, 72, 242, 512, 330, "#061525DD", "#244B66", 1.2, "rounded-2xl");
    txt(s, "MINI MAP", 92, 262, 140, 22, { size: 16, bold: true, color: C.cyan, face: F.title });
    const mapNodes = [
      ["D0", 150, 496], ["A", 208, 408], ["B", 292, 366], ["C", 258, 500],
      ["D", 360, 470], ["E", 456, 412], ["X", 452, 514], ["F", 366, 350],
    ];
    const edges = [["D0", "A"], ["A", "B"], ["B", "E"], ["D0", "C"], ["C", "D"], ["D", "E"], ["D", "X"], ["F", "E"], ["B", "F"]];
    const lookup = Object.fromEntries(mapNodes.map(([id, x, y]) => [id, [x, y]]));
    edges.forEach(([a, b]) => line(s, lookup[a][0], lookup[a][1], lookup[b][0], lookup[b][1], "#2A5873", 2));
    [["D0", "C"], ["C", "D"], ["D", "E"]].forEach(([a, b]) => line(s, lookup[a][0], lookup[a][1], lookup[b][0], lookup[b][1], C.green, 4));
    mapNodes.forEach(([id, x, y]) => {
      const active = ["D0", "C", "D", "E"].includes(id);
      ellipse(s, x - 18, y - 18, 36, 36, active ? "#14BA5A" : "#2C3E50", active ? C.green : "#7C8EA0", 1.5);
      txt(s, id, x - 22, y - 8, 44, 16, { size: id.length > 1 ? 10 : 12, bold: true, color: C.white, align: "center", face: F.mono });
    });
    round(s, 618, 242, 256, 330, "#061525DD", "#244B66", 1.2, "rounded-2xl");
    txt(s, "NODE HIỆN TẠI", 642, 266, 180, 22, { size: 16, bold: true, color: C.green, face: F.title });
    txt(s, "D", 654, 318, 54, 54, { size: 46, bold: true, color: C.green, face: F.title });
    txt(s, "g(n)", 654, 394, 96, 24, { size: 20, bold: true, color: C.green, face: F.mono });
    txt(s, "12.0", 758, 394, 82, 24, { size: 20, bold: true, color: C.white, align: "right", face: F.mono });
    txt(s, "h(n)", 654, 436, 96, 24, { size: 20, bold: true, color: C.cyan, face: F.mono });
    txt(s, "3.6", 758, 436, 82, 24, { size: 20, bold: true, color: C.white, align: "right", face: F.mono });
    txt(s, "f(n)", 654, 478, 96, 24, { size: 20, bold: true, color: C.gold, face: F.mono });
    txt(s, "15.6", 758, 478, 82, 24, { size: 20, bold: true, color: C.white, align: "right", face: F.mono });
    round(s, 902, 242, 296, 330, "#061525DD", "#244B66", 1.2, "rounded-2xl");
    txt(s, "FRONTIER", 928, 266, 160, 22, { size: 16, bold: true, color: C.cyan, face: F.title });
    [["Node", "g", "h", "f"], ["E", "15.6", "0", "15.6"], ["F", "14.0", "4.1", "18.1"], ["X", "15.4", "6.2", "21.6"]].forEach((row, i) => {
      row.forEach((cell, j) => {
        txt(s, cell, 930 + j * 62, 316 + i * 42, 58, 20, {
          size: i === 0 ? 13 : 15,
          bold: i === 0 || (i === 1 && j === 0),
          color: i === 1 ? C.green : i === 0 ? "#8DAEC5" : C.white,
          align: "center",
          face: F.mono,
        });
      });
    });
    round(s, 434, 596, 410, 42, "#0D3044E8", "#1F5A78", 1, "rounded-full");
    txt(s, "Trace giúp vấn đáp: vì sao thuật toán chọn node tiếp theo?", 466, 608, 350, 18, {
      size: 15,
      bold: true,
      color: C.cyan,
      align: "center",
      face: F.title,
    });
    notes(s, ["Giải thích g là cost đã đi, h là heuristic tới đích, f là tổng để ưu tiên frontier.", "Nối với demo Defense Lab: Run Next Step để thấy frontier/visited thay đổi."]);
  }

  {
    const s = deck.slides.add();
    await bg(s, "paper");
    lightTitle(s, 8, "Beyond", "Không chỉ shortest path", "Mỗi nhóm thuật toán trả lời một loại câu hỏi khác nhau");
    const blocks = [
      ["Local Search", "Tối ưu thứ tự nhiều đơn", "Hill / SA / Beam / GA", C.gold, 86, 266],
      ["Complex", "Quan sát thiếu, phải replan", "Belief / Online / AND-OR", C.cyan, 438, 266],
      ["CSP", "Ràng buộc pickup trước dropoff", "MRV / Forward Checking", C.coral, 790, 266],
      ["Adversarial", "Worst-case disruption", "Minimax / Alpha-Beta", C.violet, 438, 430],
    ];
    blocks.forEach(([title, body, methods, color, x, y]) => {
      round(s, x, y, 318, 136, "#FFFFFFE8", color, 1.6, "rounded-2xl");
      rect(s, x + 22, y + 22, 80, 6, color);
      txt(s, title, x + 22, y + 48, 260, 26, { size: 23, bold: true, color: C.ink, face: F.title });
      txt(s, body, x + 22, y + 80, 260, 22, { size: 16, color: C.muted, face: F.body });
      txt(s, methods, x + 22, y + 106, 260, 18, { size: 13, color, face: F.mono });
    });
    round(s, 94, 596, 1036, 52, "#081526E8", "#173A54", 1.1, "rounded-full");
    txt(s, "Ý chính khi vấn đáp", 130, 609, 210, 20, { size: 18, bold: true, color: C.cyan, face: F.title });
    txt(s, "Trả lời theo: vai trò -> state -> rule chọn -> output trace.", 350, 610, 640, 18, {
      size: 17,
      bold: true,
      color: C.white,
      face: F.body,
    });
    notes(s, ["Đây là slide giúp tránh bị hỏi xoáy: mỗi nhóm có vai trò riêng.", "Nhấn mạnh adversarial là worst-case disruption, không phải hai shipper cạnh tranh."]);
  }

  {
    const s = deck.slides.add();
    await bg(s, "tech");
    darkTitle(s, 9, "Demo", "Kịch bản thao tác app", "5-6 phút: chứng minh app chạy và trace giải thích được");
    round(s, 74, 238, 500, 360, "#061525DD", "#244B66", 1.2, "rounded-2xl");
    rect(s, 74, 238, 500, 48, "#0D3044", "#244B66", 1);
    ellipse(s, 96, 256, 10, 10, C.coral);
    ellipse(s, 116, 256, 10, 10, C.gold);
    ellipse(s, 136, 256, 10, 10, C.green);
    txt(s, "Defense Lab", 164, 253, 160, 18, { size: 16, bold: true, color: C.white, face: F.title });
    await addImage(s, `${UI_ASSET}/app-icon-route-arrow.png`, 410, 310, 104, 104, "Route app icon", "contain");
    route(s, [[134, 508], [214, 438], [302, 476], [384, 380], [482, 438]], C.cyan, 4);
    txt(s, "Run Next Step", 122, 326, 170, 22, { size: 20, bold: true, color: C.green, face: F.title });
    txt(s, "frontier / visited / g-h-f", 122, 360, 210, 24, { size: 16, color: "#C8D8E4", face: F.mono });
    const steps = [
      ["01", "Admin", "bật/tắt quyền thuật toán"],
      ["02", "Defense Lab", "chạy A* từng bước"],
      ["03", "Compare", "đổi BFS/UCS/Local"],
      ["04", "Complex/CSP", "show replan, domain prune"],
      ["05", "Shipper", "nhận đơn và lập tuyến"],
    ];
    steps.forEach(([num, title, body], i) => {
      const y = 248 + i * 70;
      ellipse(s, 670, y, 44, 44, i === 1 ? C.green : "#0D3044", i === 1 ? C.green : "#25506D", 1.2);
      txt(s, String(i + 1), 676, y + 10, 32, 18, { size: 16, bold: true, color: C.white, align: "center", face: F.title });
      txt(s, title, 734, y - 1, 180, 24, { size: 22, bold: true, color: C.white, face: F.title });
      txt(s, body, 734, y + 28, 330, 20, { size: 16, color: "#B8C8D5", face: F.body });
      if (i < steps.length - 1) line(s, 692, y + 44, 692, y + 70, "#315B75", 2);
    });
    round(s, 760, 590, 360, 44, "#0D3044E8", "#1F5A78", 1, "rounded-full");
    txt(s, "Câu chuyển: “Em sẽ mở app để kiểm chứng trace vừa trình bày.”", 784, 603, 314, 18, {
      size: 14,
      bold: true,
      color: C.cyan,
      align: "center",
      face: F.body,
    });
    notes(s, ["Đây là slide bridge sang demo app.", "Không demo quá nhiều màn hình; ưu tiên Defense Lab trước, sau đó shipper/admin nếu còn thời gian."]);
  }

  {
    const s = deck.slides.add();
    await bg(s, "paper");
    lightTitle(s, 10, "Results", "Kết quả minh họa từ scenario demo", "Case D0 -> E trong project: đọc cost, visited và trace");
    round(s, 78, 238, 574, 308, "#FFFFFFE8", "#D5E2E2", 1.2, "rounded-2xl");
    txt(s, "Total minutes", 108, 260, 210, 24, { size: 20, bold: true, color: C.ink, face: F.title });
    s.charts.add("bar", {
      position: { left: 104, top: 304, width: 500, height: 206 },
      categories: ["BFS", "DFS", "UCS", "A*"],
      series: [{ name: "minutes", values: [27.4, 27.4, 15.6, 15.6], fill: C.green }],
      hasLegend: false,
      dataLabels: { showValue: true, position: "outEnd" },
      yAxis: { majorGridlines: { style: "solid", fill: "#E2ECEF", width: 1 } },
    });
    round(s, 704, 238, 420, 198, "#081526E8", "#173A54", 1.2, "rounded-2xl");
    txt(s, "Search trace", 736, 264, 180, 24, { size: 20, bold: true, color: C.cyan, face: F.title });
    const rows = [
      ["Alg", "Path", "Visited"],
      ["BFS", "D0-A-B-E", "7"],
      ["DFS", "D0-A-B-E", "9"],
      ["UCS", "D0-C-D-E", "7"],
      ["A*", "D0-C-D-E", "5"],
    ];
    rows.forEach((row, i) => {
      row.forEach((cell, j) => {
        txt(s, cell, 734 + [0, 72, 238][j], 304 + i * 24, [58, 148, 70][j], 18, {
          size: i === 0 ? 12 : 13,
          bold: i === 0 || (i === 4 && j === 0),
          color: i === 0 ? "#83A1B7" : i === 4 ? C.green : C.white,
          face: F.mono,
        });
      });
    });
    round(s, 704, 456, 420, 104, "#FFFFFFE8", "#D5E2E2", 1.2, "rounded-2xl");
    txt(s, "Alpha-Beta pruning", 734, 476, 250, 24, { size: 21, bold: true, color: C.ink, face: F.title });
    txt(s, "Minimax mở 41 node\nAlpha-Beta mở 26 node, prune 15 nhánh\nGame value giữ nguyên: -28.0", 734, 508, 340, 42, {
      size: 15,
      color: C.muted,
      face: F.body,
    });
    txt(s, "Khi thuyết trình: đây là case demo nhỏ để minh họa cách đọc metric, không phải benchmark tổng quát.", 110, 584, 992, 32, {
      size: 20,
      bold: true,
      color: C.green,
      align: "center",
      face: F.title,
    });
    notes(s, ["Số liệu lấy từ scenario demo trong project, không nói là benchmark toàn diện.", "Điểm chính: A* giữ cost tối ưu như UCS trong case này nhưng visited ít hơn."]);
  }

  {
    const s = deck.slides.add();
    await bg(s, "paper");
    lightTitle(s, 11, "Discussion", "Đánh giá & hướng phát triển", "Nêu được điểm mạnh, giới hạn và bước tiếp theo");
    const cols = [
      ["Đạt được", ["UI + API + SQLite", "6 nhóm thuật toán", "Defense Lab có trace", "Admin phân quyền"], C.green, 86],
      ["Hạn chế", ["Graph cache còn nhỏ", "Traffic/observation đơn giản", "Chưa phải production storage", "Benchmark chưa mở rộng"], C.coral, 450],
      ["Phát triển", ["custom node/edge trong DB", "route history", "traffic realtime", "multi-driver routing"], C.cyan, 814],
    ];
    cols.forEach(([title, items, color, x]) => {
      round(s, x, 260, 318, 286, "#FFFFFFE8", color, 1.5, "rounded-2xl");
      rect(s, x + 26, 286, 82, 6, color);
      txt(s, title, x + 26, 314, 250, 30, { size: 25, bold: true, color: C.ink, face: F.title });
      items.forEach((item, i) => {
        ellipse(s, x + 32, 370 + i * 38, 12, 12, color, "none", 0);
        txt(s, item, x + 56, 364 + i * 38, 230, 20, { size: 16, color: C.muted, face: F.body });
      });
    });
    round(s, 176, 580, 928, 54, "#081526E8", "#173A54", 1.1, "rounded-full");
    txt(s, "Kết luận: hệ thống giúp nhìn thấy cách thuật toán ra quyết định trong bài toán giao hàng có ràng buộc.", 214, 596, 852, 22, {
      size: 15,
      bold: true,
      color: C.cyan,
      align: "center",
      face: F.title,
    });
    notes(s, ["Nói thẳng hạn chế để tạo độ tin cậy.", "Hướng phát triển gắn với dữ liệu bền vững và bản đồ lớn hơn."]);
  }

  {
    const s = deck.slides.add();
    await bg(s, "hero");
    rect(s, 0, 0, W, H, "#061525D0");
    footer(s, 12, "Q&A", true);
    txt(s, "Kết luận & vấn đáp", 72, 78, 720, 64, { size: 54, bold: true, color: C.white, face: F.title });
    txt(s, "Find Your Path giúp biến thuật toán thành trace có thể quan sát, so sánh và bảo vệ.", 76, 158, 760, 34, {
      size: 23,
      color: C.green,
      face: F.body,
    });
    round(s, 86, 250, 520, 270, "#061525DD", "#244B66", 1.2, "rounded-2xl");
    txt(s, "3 takeaway", 118, 276, 170, 24, { size: 20, bold: true, color: C.cyan, face: F.title });
    txt(s, "1. Bài toán được mô hình hóa bằng graph có ràng buộc.\n2. 6 nhóm thuật toán giải các tình huống khác nhau.\n3. App cho thấy trace, metric và quyền dùng thuật toán.", 124, 326, 430, 112, {
      size: 23,
      bold: true,
      color: C.white,
      face: F.body,
    });
    round(s, 690, 228, 430, 342, "#061525DD", "#244B66", 1.2, "rounded-2xl");
    txt(s, "Q&A radar", 724, 254, 180, 24, { size: 20, bold: true, color: C.green, face: F.title });
    const qs = [
      "State / goal / cost là gì?",
      "Vì sao dùng A*?",
      "AND-OR khác Online Replanning?",
      "CSP kiểm tra ràng buộc nào?",
      "Vì sao không gọi Google Directions / OSRM?",
      "Hạn chế và hướng phát triển?",
    ];
    qs.forEach((q, i) => {
      ellipse(s, 728, 306 + i * 38, 11, 11, i % 2 ? C.cyan : C.green, "none", 0);
      txt(s, q, 752, 298 + i * 38, 330, 22, { size: 17, color: "#D8E6F2", face: F.body });
    });
    route(s, [[128, 594], [330, 548], [526, 606], [744, 554], [1034, 612]], C.cyan, 4);
    notes(s, ["Nói câu kết chậm rồi dừng để nhận câu hỏi.", "Nếu bị hỏi sâu, dùng framework: state -> goal -> rule chọn -> output trace."]);
  }

  for (const [index, slide] of deck.slides.items.entries()) {
    const stem = `slide-${String(index + 1).padStart(2, "0")}`;
    await writeBlob(`${PREVIEW}/${stem}.png`, await deck.export({ slide, format: "png", scale: 1 }));
    await fs.writeFile(`${LAYOUT}/${stem}.layout.json`, await (await slide.export({ format: "layout" })).text());
  }

  await writeBlob(`${QA}/deck-montage.webp`, await deck.export({ format: "webp", montage: true, scale: 1 }));
  await fs.writeFile(`${QA}/inspect.ndjson`, (await deck.inspect({ kind: "slide,textbox,shape,image,chart,notes", maxChars: 18000 })).ndjson);
  const pptx = await PresentationFile.exportPptx(deck);
  await pptx.save(FINAL);
}

buildDeck().catch((error) => {
  process.stderr.write(`${error.stack || error}\n`);
  process.exitCode = 1;
});
