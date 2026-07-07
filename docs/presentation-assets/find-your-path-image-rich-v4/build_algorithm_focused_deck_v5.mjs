import fs from "node:fs/promises";
import path from "node:path";
import { Presentation, PresentationFile } from "@oai/artifact-tool";

const ROOT = "D:/TAI_LIEU_HOC_TAP_DAI_HOC/PersonalPrj/FYP";
const FINAL = `${ROOT}/docs/find-your-path-algorithm-focused-v5-slides.pptx`;
const TMP = "C:/Users/ducph/AppData/Local/Temp/codex-presentations/manual-find-your-path-algorithm-focused-v5/tmp";
const PREVIEW = `${TMP}/preview`;
const LAYOUT = `${TMP}/layout`;
const QA = `${TMP}/qa`;
const ASSET = `${ROOT}/docs/presentation-assets/find-your-path-image-rich-v4`;
const UI_ASSET = `${ROOT}/src/app/ui/assets`;

const W = 1280;
const H = 720;
const C = {
  ink: "#081526",
  panel: "#0F2438",
  cyan: "#00D8FF",
  green: "#14BA5A",
  gold: "#D9C6A3",
  paper: "#F6F2EA",
  violet: "#8B5CF6",
  coral: "#EF4444",
  blue: "#1268B3",
  white: "#FFFFFF",
  muted: "#586777",
};
const F = {
  editorial: "Playfair Display",
  title: "Montserrat",
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

async function addImage(slide, imagePath, x, y, w, h, alt, fit = "cover") {
  slide.images.add({
    blob: await readImageBlob(imagePath),
    contentType: "image/png",
    alt,
    fit,
    position: { left: x, top: y, width: w, height: h },
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

function lightTitle(slide, n, section, title, subtitle = "") {
  rect(slide, 0, 0, W, H, "#FFFDF6C8");
  footer(slide, n, section, false);
  txt(slide, section.toUpperCase(), 72, 44, 260, 22, { size: 13, bold: true, color: C.green, face: F.title });
  txt(slide, title, 72, 84, 840, 70, { size: 45, bold: true, color: C.ink, face: F.title });
  if (subtitle) txt(slide, subtitle, 74, 158, 800, 34, { size: 20, color: C.muted, face: F.body });
  rect(slide, 74, 204, 132, 4, C.green);
}

function darkTitle(slide, n, section, title, subtitle = "") {
  rect(slide, 0, 0, W, H, "#061525AA");
  footer(slide, n, section, true);
  txt(slide, section.toUpperCase(), 72, 44, 260, 22, { size: 13, bold: true, color: C.green, face: F.title });
  txt(slide, title, 72, 86, 880, 64, { size: 44, bold: true, color: C.white, face: F.title });
  if (subtitle) txt(slide, subtitle, 74, 154, 800, 34, { size: 20, color: "#B8C6D4", face: F.body });
  rect(slide, 74, 202, 132, 4, C.cyan);
}

function pin(slide, x, y, color, label = "") {
  ellipse(slide, x - 16, y - 16, 32, 32, `${color}2B`, color, 2);
  ellipse(slide, x - 6, y - 6, 12, 12, color, "none", 0);
  if (label) txt(slide, label, x + 18, y - 10, 110, 20, { size: 13, bold: true, color, face: F.title });
}

function route(slide, pts, color = C.cyan, width = 4) {
  for (let i = 0; i < pts.length - 1; i += 1) line(slide, pts[i][0], pts[i][1], pts[i + 1][0], pts[i + 1][1], color, width);
  pts.forEach((p, i) => pin(slide, p[0], p[1], i === 0 ? C.green : i === pts.length - 1 ? C.coral : color));
}

function infoCard(slide, x, y, w, h, title, body, color, icon = "") {
  round(slide, x, y, w, h, "#FFFFFFE8", "#DDE6E6", 1.1, "rounded-xl");
  rect(slide, x + 22, y + 20, 74, 5, color);
  if (icon) {
    ellipse(slide, x + 24, y + 48, 34, 34, `${color}18`, color, 1.2);
    txt(slide, icon, x + 31, y + 56, 20, 16, { size: 16, bold: true, color, align: "center", face: F.title });
  }
  txt(slide, title, x + (icon ? 84 : 22), y + 42, w - (icon ? 106 : 44), 28, {
    size: 22,
    bold: true,
    color: C.ink,
    face: F.title,
  });
  txt(slide, body, x + 22, y + 82, w - 44, h - 96, { size: 16, color: C.muted, face: F.body });
}

function conceptBlock(slide, x, y, w, h, algo, group, rows, color) {
  round(slide, x, y, w, h, "#061525DD", color, 1.2, "rounded-2xl");
  rect(slide, x + 26, y + 24, 88, 6, color);
  txt(slide, group, x + 26, y + 48, w - 52, 20, { size: 13, bold: true, color, face: F.title });
  txt(slide, algo, x + 26, y + 74, w - 52, 34, { size: 27, bold: true, color: C.white, face: F.title });
  rows.forEach(([label, text], i) => {
    const yy = y + 130 + i * 70;
    ellipse(slide, x + 30, yy + 5, 14, 14, `${color}40`, color, 1);
    txt(slide, label, x + 56, yy - 2, 132, 20, { size: 15, bold: true, color, face: F.title });
    txt(slide, text, x + 56, yy + 24, w - 88, 34, { size: 16, color: "#D8E6F2", face: F.body });
  });
}

function algChip(slide, name, group, x, y, color) {
  round(slide, x, y, 340, 76, "#061525D8", color, 1.1, "rounded-full");
  txt(slide, group, x + 28, y + 14, 130, 16, { size: 12, bold: true, color, face: F.title });
  txt(slide, name, x + 28, y + 36, 240, 22, { size: 20, bold: true, color: C.white, face: F.title });
}

function smallNode(slide, x, y, label, color) {
  ellipse(slide, x - 18, y - 18, 36, 36, `${color}25`, color, 1.4);
  txt(slide, label, x - 18, y - 8, 36, 16, { size: 12, bold: true, color: C.white, align: "center", face: F.mono });
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
    round(s, 74, 544, 132, 38, "#14BA5A18", C.green, 1.3, "rounded-full");
    txt(s, "Nhóm 5", 96, 553, 88, 20, { size: 15, bold: true, color: "#CFFBE1", align: "center", face: F.title });
    round(s, 224, 544, 246, 38, "#00D8FF16", C.cyan, 1.3, "rounded-full");
    txt(s, "AI Route Planning", 250, 553, 194, 20, { size: 15, bold: true, color: "#D8F8FF", align: "center", face: F.title });
    txt(s, "Nguyễn Đức Phát - Nguyễn Văn Thi\nGVHD: TS. Phan Thị Huyền Trang", 76, 614, 480, 40, {
      size: 14,
      color: "#C7D5E1",
      face: F.body,
    });
    footer(s, 1, "Opening", true);
  }

  {
    const s = deck.slides.add();
    await bg(s, "paper");
    lightTitle(s, 2, "Agenda", "Nội dung trình bày");
    const items = [
      ["1", "Bài toán đặt ra", "Problem & motivation", C.green, 250],
      ["2", "Mô hình hóa", "State, action, goal, cost", C.blue, 338],
      ["3", "Thiết kế hệ thống", "UI, API, service, data", C.cyan, 426],
      ["4", "Thuật toán đại diện", "6 nhóm, 6 cách tìm solution", C.violet, 514],
    ];
    line(s, 155, 274, 155, 566, "#B9C7C5", 3);
    items.forEach(([num, title, sub, color, y]) => {
      ellipse(s, 122, y - 24, 66, 66, color === C.blue ? C.ink : color, C.white, 2);
      txt(s, num, 138, y - 2, 36, 22, { size: 20, bold: true, color: C.white, align: "center", face: F.title });
      txt(s, title, 230, y - 12, 320, 28, { size: 22, bold: true, color: C.ink, face: F.title });
      txt(s, sub, 230, y + 18, 460, 22, { size: 15, color: C.muted, face: F.body });
      line(s, 580, y + 2, 816, y + 2, "#CAD8D8", 1.4);
    });
    route(s, [[842, 578], [900, 498], [870, 414], [942, 350], [1030, 266], [1004, 190]], C.green, 4);
    round(s, 836, 424, 236, 86, "#FFFFFFD8", "#D6E4E2", 1, "rounded-xl");
    txt(s, "DFS  A*  Hill Climbing\nAND-OR  Forward Checking\nAlpha-Beta", 862, 446, 184, 44, {
      size: 15,
      bold: true,
      color: C.green,
      align: "center",
      face: F.mono,
    });
  }

  {
    const s = deck.slides.add();
    await bg(s, "paper");
    lightTitle(s, 3, "Problem", "Bài toán đặt ra", "Giao hàng đô thị không chỉ là tìm đường ngắn nhất");
    infoCard(s, 84, 254, 298, 148, "Đơn hàng", "pickup/dropoff, deadline, độ ưu tiên và khối lượng", C.green, "1");
    infoCard(s, 410, 254, 298, 148, "Môi trường", "traffic, cạnh bị chặn, thông tin quan sát chưa đầy đủ", C.cyan, "2");
    infoCard(s, 84, 430, 298, 148, "Shipper", "vị trí hiện tại, nhóm vận hành và quyền dùng thuật toán", C.gold, "3");
    infoCard(s, 410, 430, 298, 148, "Mục tiêu", "route hợp lệ, chi phí hợp lý, trace giải thích được", C.coral, "4");
    round(s, 760, 238, 378, 350, "#081526E8", "#173A54", 1.2, "rounded-2xl");
    await addImage(s, `${UI_ASSET}/map-icons/shipper-bike.png`, 822, 308, 92, 92, "Shipper bike", "contain");
    await addImage(s, `${UI_ASSET}/map-icons/pickup-parcel.png`, 958, 260, 78, 78, "Pickup parcel", "contain");
    await addImage(s, `${UI_ASSET}/map-icons/dropoff-pin.png`, 996, 420, 78, 78, "Dropoff pin", "contain");
    route(s, [[842, 490], [916, 414], [982, 368], [1032, 458]], C.cyan, 4);
    txt(s, "Graph + ràng buộc", 794, 520, 310, 34, { size: 28, bold: true, color: C.white, align: "center", face: F.title });
    txt(s, "node, edge, cost, order state", 800, 556, 300, 22, { size: 16, color: "#BFD2DF", align: "center", face: F.mono });
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
      if (i < nodes.length - 1) line(s, x + 160, 355, x + 238, 355, "#A8BBC4", 4);
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
    txt(s, "Routing do thuật toán Python trong project xử lý trên graph/cache dữ liệu.", 254, 586, 774, 22, {
      size: 15,
      color: "#D6E6F2",
      align: "center",
      face: F.body,
    });
  }

  {
    const s = deck.slides.add();
    await bg(s, "tech");
    darkTitle(s, 5, "System", "Thiết kế hệ thống", "Luồng xử lý từ giao diện tới thuật toán và dữ liệu");
    const steps = [
      ["Flet UI", "Defense Lab\nShipper Mode", 88, C.cyan],
      ["FastAPI", "API routers", 326, C.green],
      ["Services", "auth / route\nmap service", 564, C.gold],
      ["Algorithms", "6 nhóm thuật toán", 802, C.violet],
      ["SQLite + OSM", "orders, users\ngraph cache", 1040, C.coral],
    ];
    steps.forEach(([label, body, x, color], i) => {
      if (i < steps.length - 1) line(s, x + 178, 360, x + 224, 360, "#3A6E8A", 3);
      round(s, x, 280, 178, 160, "#061525D8", "#24506A", 1.2, "rounded-xl");
      rect(s, x + 24, 302, 72, 5, color);
      txt(s, label, x + 20, 330, 138, 28, { size: 22, bold: true, color: C.white, align: "center", face: F.title });
      txt(s, body, x + 18, 374, 142, 44, { size: 15, color: "#B9C9D6", align: "center", face: F.body });
    });
    round(s, 250, 514, 780, 64, "#0D3044E8", "#1F5A78", 1, "rounded-full");
    txt(s, "UI / API / Service / Algorithm / Data", 306, 532, 668, 24, {
      size: 24,
      bold: true,
      color: C.cyan,
      align: "center",
      face: F.title,
    });
  }

  {
    const s = deck.slides.add();
    await addImage(s, `${ASSET}/algorithm-engine-illustration.png`, 0, 0, W, H, "Generated algorithm engine illustration", "cover");
    rect(s, 0, 0, W, H, "#06152558");
    rect(s, 0, 0, W, 176, "#061525BE");
    footer(s, 6, "Algorithms", true);
    txt(s, "Thuật toán đại diện", 72, 54, 700, 58, { size: 46, bold: true, color: C.white, face: F.title });
    txt(s, "Mỗi nhóm chọn một thuật toán để trình bày ý tưởng và cách tìm solution", 74, 124, 760, 28, {
      size: 20,
      color: "#C7D9E7",
      face: F.body,
    });
    algChip(s, "Depth-First Search", "Không thông tin", 72, 226, C.blue);
    algChip(s, "A*", "Có thông tin", 72, 318, C.green);
    algChip(s, "Simple Hill Climbing", "Cục bộ", 72, 410, C.gold);
    algChip(s, "AND-OR Search", "Môi trường phức tạp", 868, 226, C.cyan);
    algChip(s, "Forward Checking", "Thỏa ràng buộc", 868, 318, C.coral);
    algChip(s, "Alpha-Beta Pruning", "Đối kháng", 868, 410, C.violet);
  }

  {
    const s = deck.slides.add();
    await bg(s, "tech");
    darkTitle(s, 7, "Algorithms", "DFS và A*", "Hai cách mở rộng không gian tìm kiếm");
    conceptBlock(
      s,
      74,
      236,
      520,
      354,
      "Depth-First Search",
      "Tìm kiếm không thông tin",
      [
        ["Ý tưởng", "Đi sâu theo một nhánh trước khi quay lui."],
        ["Cách chạy", "Dùng stack hoặc đệ quy; lấy node sâu nhất để mở rộng."],
        ["Solution", "Gặp goal thì dựng lại đường đi qua parent map."],
      ],
      C.blue,
    );
    conceptBlock(
      s,
      686,
      236,
      520,
      354,
      "A* Search",
      "Tìm kiếm có thông tin",
      [
        ["Ý tưởng", "Kết hợp chi phí đã đi g(n) và ước lượng h(n)."],
        ["Cách chạy", "Luôn chọn node có f(n) = g(n) + h(n) nhỏ nhất."],
        ["Solution", "Khi goal được chọn, route hiện tại là lời giải tốt theo heuristic phù hợp."],
      ],
      C.green,
    );
    [170, 248, 326, 404].forEach((x, i) => {
      smallNode(s, x, 620, i === 0 ? "S" : i === 3 ? "G" : String(i), i === 3 ? C.coral : C.blue);
      if (i < 3) line(s, x + 18, 620, x + 60, 620, C.blue, 3);
    });
    [790, 878, 966, 1054].forEach((x, i) => {
      smallNode(s, x, 620, i === 0 ? "S" : i === 3 ? "G" : String(i), i === 3 ? C.coral : C.green);
      if (i < 3) line(s, x + 18, 620, x + 70, 620, C.green, 3);
    });
  }

  {
    const s = deck.slides.add();
    await bg(s, "paper");
    lightTitle(s, 8, "Algorithms", "Hill Climbing và AND-OR Search", "Một thuật toán tối ưu cục bộ và một thuật toán cho môi trường bất định");
    round(s, 74, 244, 520, 360, "#FFFFFFEA", C.gold, 1.4, "rounded-2xl");
    rect(s, 104, 274, 88, 6, C.gold);
    txt(s, "Simple Hill Climbing", 104, 304, 410, 30, { size: 28, bold: true, color: C.ink, face: F.title });
    txt(s, "Cục bộ", 106, 340, 120, 20, { size: 14, bold: true, color: C.gold, face: F.title });
    txt(s, "Ý tưởng", 112, 386, 110, 20, { size: 16, bold: true, color: C.ink, face: F.title });
    txt(s, "Bắt đầu từ một route, thử đổi nhỏ và chỉ nhận bước làm cost tốt hơn.", 232, 386, 300, 38, { size: 17, color: C.muted, face: F.body });
    txt(s, "Cách chạy", 112, 454, 110, 20, { size: 16, bold: true, color: C.ink, face: F.title });
    txt(s, "Sinh hàng xóm bằng swap/thay thứ tự đơn; so cost hiện tại với candidate.", 232, 454, 300, 38, { size: 17, color: C.muted, face: F.body });
    txt(s, "Solution", 112, 522, 110, 20, { size: 16, bold: true, color: C.ink, face: F.title });
    txt(s, "Dừng khi không còn neighbor tốt hơn; trả route tốt nhất tìm được.", 232, 522, 300, 38, { size: 17, color: C.muted, face: F.body });
    round(s, 686, 244, 520, 360, "#081526E8", C.cyan, 1.4, "rounded-2xl");
    rect(s, 716, 274, 88, 6, C.cyan);
    txt(s, "AND-OR Search", 716, 304, 410, 30, { size: 28, bold: true, color: C.white, face: F.title });
    txt(s, "Môi trường phức tạp", 718, 340, 220, 20, { size: 14, bold: true, color: C.cyan, face: F.title });
    txt(s, "Ý tưởng", 724, 386, 110, 20, { size: 16, bold: true, color: C.cyan, face: F.title });
    txt(s, "Agent chọn hành động, môi trường có nhiều outcome cần xử lý hết.", 844, 386, 300, 38, { size: 17, color: "#D8E6F2", face: F.body });
    txt(s, "Cách chạy", 724, 454, 110, 20, { size: 16, bold: true, color: C.cyan, face: F.title });
    txt(s, "OR node là lựa chọn của agent; AND node là các khả năng môi trường.", 844, 454, 300, 38, { size: 17, color: "#D8E6F2", face: F.body });
    txt(s, "Solution", 724, 522, 110, 20, { size: 16, bold: true, color: C.cyan, face: F.title });
    txt(s, "Trả conditional plan: nếu đường thông thì đi nhánh A, nếu disruption thì nhánh B.", 844, 522, 300, 38, { size: 17, color: "#D8E6F2", face: F.body });
  }

  {
    const s = deck.slides.add();
    await bg(s, "tech");
    darkTitle(s, 9, "Algorithms", "Forward Checking và Alpha-Beta", "Một thuật toán ràng buộc và một thuật toán đối kháng");
    conceptBlock(
      s,
      74,
      236,
      520,
      354,
      "Forward Checking",
      "Thỏa ràng buộc",
      [
        ["Ý tưởng", "Gán một biến rồi loại sớm các giá trị làm biến còn lại vi phạm."],
        ["Cách chạy", "Sau mỗi assignment, cập nhật domain theo pickup/dropoff, capacity, deadline."],
        ["Solution", "Nếu mọi biến có giá trị hợp lệ thì có lịch giao hàng thỏa ràng buộc."],
      ],
      C.coral,
    );
    conceptBlock(
      s,
      686,
      236,
      520,
      354,
      "Alpha-Beta Pruning",
      "Tìm kiếm đối kháng",
      [
        ["Ý tưởng", "Tính minimax nhưng bỏ nhánh chắc chắn không ảnh hưởng quyết định."],
        ["Cách chạy", "MAX cập nhật alpha, MIN cập nhật beta; nếu alpha >= beta thì prune."],
        ["Solution", "Chọn route tốt nhất trong worst-case disruption với ít nhánh phải xét hơn."],
      ],
      C.violet,
    );
  }

  for (const [index, slide] of deck.slides.items.entries()) {
    const stem = `slide-${String(index + 1).padStart(2, "0")}`;
    await writeBlob(`${PREVIEW}/${stem}.png`, await deck.export({ slide, format: "png", scale: 1 }));
    await fs.writeFile(`${LAYOUT}/${stem}.layout.json`, await (await slide.export({ format: "layout" })).text());
  }

  await writeBlob(`${QA}/deck-montage.webp`, await deck.export({ format: "webp", montage: true, scale: 1 }));
  await fs.writeFile(`${QA}/inspect.ndjson`, (await deck.inspect({ kind: "slide,textbox,shape,image,notes", maxChars: 18000 })).ndjson);
  const pptx = await PresentationFile.exportPptx(deck);
  await pptx.save(FINAL);
}

buildDeck().catch((error) => {
  process.stderr.write(`${error.stack || error}\n`);
  process.exitCode = 1;
});
