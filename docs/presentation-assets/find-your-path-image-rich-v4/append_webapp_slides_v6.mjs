import fs from "node:fs/promises";
import path from "node:path";
import { FileBlob, PresentationFile } from "@oai/artifact-tool";

const ROOT = "D:/TAI_LIEU_HOC_TAP_DAI_HOC/PersonalPrj/FYP";
const SOURCE =
  "C:/Users/ducph/AppData/Local/Temp/codex-presentations/webapp-addon/tmp/source-repaired.pptx";
const FINAL = `${ROOT}/docs/find-your-path-v5-webapp-addon-slides.pptx`;
const TMP = "C:/Users/ducph/AppData/Local/Temp/codex-presentations/webapp-addon/tmp";
const PREVIEW = `${TMP}/preview`;
const LAYOUT = `${TMP}/layout`;
const QA = `${TMP}/qa`;
const ASSET = `${ROOT}/docs/presentation-assets/find-your-path-image-rich-v4`;
const CAPTURE = "C:/Users/ducph/AppData/Local/Temp/codex-presentations/webapp-captures";

const W = 1280;
const H = 720;
const C = {
  ink: "#081526",
  panel: "#0F2438",
  panel2: "#0B1A2A",
  cyan: "#00D8FF",
  green: "#14BA5A",
  gold: "#D9C6A3",
  paper: "#F6F2EA",
  violet: "#8B5CF6",
  coral: "#EF4444",
  white: "#FFFFFF",
  muted: "#66768A",
  pale: "#E5F2FF",
};
const F = {
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

function line(slide, x1, y1, x2, y2, color, width = 2) {
  return rect(slide, x1, y1, x2 - x1, y2 - y1, "none", color, width, { geometry: "line" });
}

function txt(slide, text, x, y, w, h, o = {}) {
  const s = slide.shapes.add({
    geometry: "textbox",
    position: { left: x, top: y, width: w, height: h },
    fill: "none",
    line: { style: "solid", fill: "none", width: 0 },
  });
  s.text = text;
  s.text.fontSize = o.size ?? 20;
  s.text.bold = Boolean(o.bold);
  s.text.color = o.color ?? C.ink;
  s.text.alignment = o.align ?? "left";
  s.text.typeface = o.face ?? F.body;
  return s;
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
    kind === "paper" ? `${ASSET}/paper-map-bg.png` : kind === "hero" ? `${ASSET}/hero-route-bg.png` : `${ASSET}/technical-lab-bg.png`;
  await addImage(slide, file, 0, 0, W, H, `${kind} background`, "cover");
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

function header(slide, n, eyebrow, title, subtitle, dark = false) {
  if (dark) {
    rect(slide, 0, 0, W, H, "#061525B8");
    footer(slide, n, "Webapp", true);
    txt(slide, eyebrow.toUpperCase(), 72, 44, 310, 20, { size: 13, bold: true, color: C.green, face: F.title });
    txt(slide, title, 72, 80, 920, 56, { size: 40, bold: true, color: C.white, face: F.title });
    txt(slide, subtitle, 74, 138, 800, 28, { size: 18, color: "#C7D5E2", face: F.body });
    rect(slide, 74, 172, 132, 4, C.green);
  } else {
    rect(slide, 0, 0, W, H, "#FFFDF6D8");
    footer(slide, n, "Webapp", false);
    txt(slide, eyebrow.toUpperCase(), 72, 44, 310, 20, { size: 13, bold: true, color: C.green, face: F.title });
    txt(slide, title, 72, 80, 920, 56, { size: 40, bold: true, color: C.ink, face: F.title });
    txt(slide, subtitle, 74, 138, 820, 28, { size: 18, color: C.muted, face: F.body });
    rect(slide, 74, 172, 132, 4, C.green);
  }
}

async function screenFrame(slide, file, x, y, w, h, label, accent, fit = "cover") {
  round(slide, x - 9, y - 9, w + 18, h + 18, "#071526", `${accent}AA`, 1.2, "rounded-lg");
  rect(slide, x - 9, y - 9, w + 18, 30, "#071526F5", `${accent}AA`, 1);
  ellipse(slide, x + 8, y + 2, 8, 8, accent);
  ellipse(slide, x + 24, y + 2, 8, 8, "#94A3B8");
  ellipse(slide, x + 40, y + 2, 8, 8, "#CBD5E1");
  txt(slide, label, x + 62, y - 1, w - 80, 16, { size: 11, bold: true, color: "#DCEBFA", face: F.mono });
  await addImage(slide, file, x, y + 22, w, h - 22, label, fit);
  rect(slide, x, y + 22, w, h - 22, "none", "#FFFFFF35", 1);
}

function chip(slide, text, x, y, w, color, dark = false) {
  round(slide, x, y, w, 28, dark ? "#081526D8" : "#FFFFFFE8", color, 1, "rounded-lg");
  ellipse(slide, x + 12, y + 9, 9, 9, color);
  txt(slide, text, x + 28, y + 6, w - 36, 12, { size: 12, bold: true, color: dark ? C.white : C.ink, face: F.title });
}

function roleCard(slide, x, y, w, h, title, tag, body, color, dark = false) {
  round(slide, x, y, w, h, dark ? "#081526E8" : "#FFFFFFEA", color, 1.2, "rounded-xl");
  rect(slide, x + 18, y + 18, 70, 5, color);
  txt(slide, title, x + 18, y + 32, w - 36, 24, { size: 21, bold: true, color: dark ? C.white : C.ink, face: F.title });
  txt(slide, tag, x + 19, y + 64, w - 38, 16, { size: 12, bold: true, color, face: F.title });
  txt(slide, body, x + 19, y + 86, w - 38, Math.max(24, h - 96), { size: 15, color: dark ? "#CFE0EC" : C.muted, face: F.body });
}

function stepCard(slide, n, x, y, title, body, color) {
  ellipse(slide, x, y + 3, 42, 42, color);
  txt(slide, String(n), x, y + 14, 42, 12, { size: 13, bold: true, color: C.ink, face: F.mono, align: "center" });
  round(slide, x + 58, y, 420, 60, "#081526D8", "#1D3A55", 1, "rounded-lg");
  txt(slide, title, x + 78, y + 11, 170, 18, { size: 17, bold: true, color: C.white, face: F.title });
  txt(slide, body, x + 78, y + 34, 350, 16, { size: 13, color: "#BED1E2", face: F.body });
}

function featurePill(slide, x, y, label, text, color) {
  round(slide, x, y, 268, 42, "#0B1D2DE6", color, 1.1, "rounded-lg");
  ellipse(slide, x + 18, y + 11, 20, 20, color);
  txt(slide, label, x + 44, y + 12, 44, 12, { size: 9, bold: true, color, face: F.mono });
  txt(slide, text, x + 86, y + 12, 158, 14, { size: 13, bold: true, color: C.white, face: F.title });
}

function loginRoleRow(slide, x, y, w, title, tag, body, color) {
  round(slide, x, y, w, 64, "#FFFFFFEA", color, 1.1, "rounded-lg");
  rect(slide, x + 16, y + 15, 6, 34, color);
  txt(slide, title, x + 34, y + 12, 130, 18, { size: 18, bold: true, color: C.ink, face: F.title });
  txt(slide, tag, x + 170, y + 14, 135, 12, { size: 10, bold: true, color, face: F.mono });
  txt(slide, body, x + 34, y + 36, w - 62, 14, { size: 12, color: C.muted, face: F.body });
}

async function addLoginSlide(deck, n) {
  const s = deck.slides.add();
  await bg(s, "paper");
  header(
    s,
    n,
    "Webapp entry",
    "Đăng nhập & phân quyền",
    "Chọn role card trên màn hình login, app tự điền tài khoản mẫu rồi vào console tương ứng.",
  );
  await screenFrame(s, `${CAPTURE}/login.png`, 74, 204, 690, 431, "Login console", C.green, "cover");

  chip(s, "Luồng vào app", 822, 204, 156, C.cyan);
  txt(s, "Chọn role card", 822, 250, 185, 22, { size: 24, bold: true, color: C.ink, face: F.title });
  txt(s, "Admin hoặc một trong hai role shipper. Form login được điền sẵn để vào nhanh phần demo.", 824, 286, 350, 46, {
    size: 17,
    color: C.muted,
    face: F.body,
  });
  line(s, 826, 352, 1154, 352, C.gold, 1.4);
  roleCard(s, 812, 378, 132, 166, "Admin", "LAB + ADMIN", "Xem thuật toán, debug trace, quản lý quyền và map.", C.green);
  roleCard(s, 962, 378, 132, 166, "Cuốc lẻ", "ON DEMAND", "Nhận đơn riêng, có thể gom đơn cùng điểm pickup.", C.cyan);
  roleCard(s, 1112, 378, 132, 166, "Kho W1", "WAREHOUSE", "Xuất phát từ kho, tối ưu tuyến qua nhiều điểm giao.", C.gold);
  round(s, 812, 574, 432, 58, "#081526", C.green, 1.2, "rounded-xl");
  txt(s, "Role quyết định màn hình mặc định và nhóm chức năng được phép dùng.", 838, 594, 382, 18, {
    size: 16,
    bold: true,
    color: C.white,
    face: F.body,
  });
}

async function addAdminSlide(deck, n) {
  const s = deck.slides.add();
  await bg(s, "tech");
  header(s, n, "Admin console", "Admin: LAB mode & ADMIN mode", "Một role, hai góc nhìn: thử thuật toán và quản trị quyền chạy thuật toán.", true);
  await screenFrame(s, `${CAPTURE}/admin-lab.png`, 72, 210, 548, 310, "LAB mode / thuật toán", C.cyan, "cover");
  await screenFrame(s, `${CAPTURE}/admin-mode.png`, 660, 210, 548, 310, "ADMIN mode / quyền & map", C.green, "cover");
  round(s, 72, 552, 548, 84, "#081526E8", C.cyan, 1.1, "rounded-xl");
  txt(s, "LAB mode", 98, 570, 150, 22, { size: 22, bold: true, color: C.cyan, face: F.title });
  txt(s, "Chọn nhóm thuật toán, chọn map, chạy thử và xem route/debug timeline ngay trên graph.", 252, 573, 312, 34, {
    size: 15,
    color: "#D8E6F2",
    face: F.body,
  });
  round(s, 660, 552, 548, 84, "#081526E8", C.green, 1.1, "rounded-xl");
  txt(s, "ADMIN mode", 686, 570, 170, 22, { size: 22, bold: true, color: C.green, face: F.title });
  txt(s, "Bật/tắt permission theo nhóm shipper, xem audit summary và quản lý thư viện map.", 862, 573, 310, 34, {
    size: 15,
    color: "#D8E6F2",
    face: F.body,
  });
}

async function addShipperRolesSlide(deck, n) {
  const s = deck.slides.add();
  await bg(s, "paper");
  header(s, n, "Shipper console", "Hai role shipper trong SHIP mode", "Cùng một màn vận hành, nhưng logic nhận đơn và lập tuyến thay đổi theo role.");
  await screenFrame(s, `${CAPTURE}/shipper-on-demand.png`, 72, 206, 548, 310, "shipper_on_demand", C.cyan, "cover");
  await screenFrame(s, `${CAPTURE}/shipper-warehouse.png`, 660, 206, 548, 310, "shipper_warehouse", C.gold, "cover");
  roleCard(
    s,
    72,
    552,
    548,
    88,
    "Shipper cuốc lẻ",
    "Hiện tại -> nhận -> giao",
    "Phù hợp đơn food/ride. App ưu tiên pickup gần bằng A*, rồi gom các đơn có cùng điểm nhận khi có thể.",
    C.cyan,
  );
  roleCard(
    s,
    660,
    552,
    548,
    88,
    "Shipper warehouse",
    "W1 -> các điểm giao",
    "Phù hợp parcel/grocery. Có thể chọn nearest neighbor hoặc global route optimization cho toàn tuyến.",
    C.gold,
  );
}

async function addWorkflowSlide(deck, n) {
  const s = deck.slides.add();
  await bg(s, "tech");
  header(s, n, "Ship workflow", "SHIP mode: nhận đơn, lập tuyến, xác nhận", "Slide này dùng để dẫn thẳng sang thao tác app khi giảng viên hỏi chi tiết.", true);
  stepCard(s, 1, 76, 214, "Nhận đơn", "Lọc loại đơn, độ gấp; shipper tick các đơn muốn nhận.", C.green);
  line(s, 97, 262, 97, 291, "#31516C", 2);
  stepCard(s, 2, 76, 296, "Lập lộ trình", "Chọn vị trí/chiến lược; app sinh route và các chặng giao.", C.cyan);
  line(s, 97, 344, 97, 373, "#31516C", 2);
  stepCard(s, 3, 76, 378, "Theo dõi route", "Map, playback, thống kê và bảng so sánh xuất hiện sau khi chạy.", C.gold);
  line(s, 97, 426, 97, 455, "#31516C", 2);
  stepCard(s, 4, 76, 460, "Xác nhận hoàn tất", "Đơn chuyển trạng thái completed, danh sách đang thực hiện được cập nhật.", C.violet);

  await screenFrame(s, `${CAPTURE}/shipper-warehouse.png`, 680, 206, 500, 312, "SHIP mode / route planning", C.green, "cover");
  round(s, 680, 548, 500, 72, "#081526E8", C.green, 1.1, "rounded-xl");
  txt(s, "Phương pháp đang dùng", 706, 566, 210, 20, { size: 20, bold: true, color: C.green, face: F.title });
  txt(s, "Profile quyết định thứ tự stop; A* nối từng chặng trên graph. SHIP mode hiển thị chiến lược đang chọn để giải thích khi vấn đáp.", 706, 592, 410, 24, {
    size: 14,
    color: "#D8E6F2",
    face: F.body,
  });

  featurePill(s, 78, 604, "H2O", "Nhắc nhở uống nước", C.cyan);
  featurePill(s, 370, 604, "FLD", "Phát hiện ngập lụt", C.green);
  featurePill(s, 662, 604, "TRF", "Phát hiện tắc đường", C.gold);
  featurePill(s, 954, 604, "ALG", "Xem phương pháp/thuật toán", C.violet);
}

async function addLoginSlideFixed(deck, n) {
  const s = deck.slides.add();
  await bg(s, "paper");
  header(
    s,
    n,
    "Webapp entry",
    "Đăng nhập & phân quyền",
    "Chọn role card trên màn hình login, app tự điền tài khoản mẫu rồi vào console tương ứng.",
  );
  await screenFrame(s, `${CAPTURE}/login.png`, 74, 204, 670, 431, "Login console", C.green, "cover");

  chip(s, "Luồng vào app", 800, 204, 156, C.cyan);
  txt(s, "Chọn role", 800, 250, 220, 24, { size: 26, bold: true, color: C.ink, face: F.title });
  txt(s, "Chọn card tương ứng, kiểm tra username/password đã điền sẵn, sau đó bấm Enter Console.", 802, 290, 388, 44, {
    size: 17,
    color: C.muted,
    face: F.body,
  });
  line(s, 804, 352, 1204, 352, C.gold, 1.4);
  loginRoleRow(s, 800, 374, 408, "Admin", "LAB + ADMIN", "Xem thuật toán, trace, quyền và map.", C.green);
  loginRoleRow(s, 800, 454, 408, "Cuốc lẻ", "ON DEMAND", "Nhận đơn riêng, có thể gom cùng điểm pickup.", C.cyan);
  loginRoleRow(s, 800, 534, 408, "Kho W1", "WAREHOUSE", "Xuất phát từ kho, tối ưu tuyến giao.", C.gold);
  round(s, 800, 616, 408, 42, "#081526", C.green, 1.2, "rounded-lg");
  txt(s, "Role quyết định màn hình và quyền thao tác.", 824, 628, 358, 14, {
    size: 14,
    bold: true,
    color: C.white,
    face: F.body,
  });
}

async function addShipperRolesSlideFixed(deck, n) {
  const s = deck.slides.add();
  await bg(s, "paper");
  header(s, n, "Shipper console", "Hai role shipper trong SHIP mode", "Cùng một màn vận hành, nhưng logic nhận đơn và lập tuyến thay đổi theo role.");
  await screenFrame(s, `${CAPTURE}/shipper-on-demand.png`, 72, 196, 548, 300, "shipper_on_demand", C.cyan, "cover");
  await screenFrame(s, `${CAPTURE}/shipper-warehouse.png`, 660, 196, 548, 300, "shipper_warehouse", C.gold, "cover");
  roleCard(
    s,
    72,
    526,
    548,
    130,
    "Shipper cuốc lẻ",
    "Hiện tại -> nhận -> giao",
    "Phù hợp đơn food/ride. App ưu tiên pickup gần bằng A*, rồi gom các đơn có cùng điểm nhận khi có thể.",
    C.cyan,
  );
  roleCard(
    s,
    660,
    526,
    548,
    130,
    "Shipper warehouse",
    "W1 -> các điểm giao",
    "Phù hợp parcel/grocery. Có thể chọn nearest neighbor hoặc global route optimization cho toàn tuyến.",
    C.gold,
  );
}

async function addWorkflowSlideFixed(deck, n) {
  const s = deck.slides.add();
  await bg(s, "tech");
  header(s, n, "Ship workflow", "SHIP mode: nhận đơn, lập tuyến, xác nhận", "Slide này dùng để dẫn thẳng sang thao tác app khi giảng viên hỏi chi tiết.", true);
  stepCard(s, 1, 76, 214, "Nhận đơn", "Lọc loại đơn, độ gấp; shipper tick các đơn muốn nhận.", C.green);
  line(s, 97, 262, 97, 291, "#31516C", 2);
  stepCard(s, 2, 76, 296, "Lập lộ trình", "Chọn vị trí/chiến lược; app sinh route và các chặng giao.", C.cyan);
  line(s, 97, 344, 97, 373, "#31516C", 2);
  stepCard(s, 3, 76, 378, "Theo dõi route", "Map, playback, thống kê và bảng so sánh xuất hiện sau khi chạy.", C.gold);
  line(s, 97, 426, 97, 455, "#31516C", 2);
  stepCard(s, 4, 76, 460, "Xác nhận hoàn tất", "Đơn chuyển trạng thái completed, danh sách đang thực hiện được cập nhật.", C.violet);

  await screenFrame(s, `${CAPTURE}/shipper-warehouse.png`, 680, 206, 500, 300, "SHIP mode / route planning", C.green, "cover");
  round(s, 680, 532, 500, 74, "#081526E8", C.green, 1.1, "rounded-xl");
  txt(s, "Phương pháp đang dùng", 706, 552, 360, 20, { size: 20, bold: true, color: C.green, face: F.title });
  txt(s, "Profile xếp thứ tự stop; A* nối từng chặng trên graph.", 706, 584, 410, 14, {
    size: 14,
    color: "#D8E6F2",
    face: F.body,
  });

  featurePill(s, 78, 624, "H2O", "Nhắc uống nước", C.cyan);
  featurePill(s, 370, 624, "FLD", "Phát hiện ngập", C.green);
  featurePill(s, 662, 624, "TRF", "Tắc đường", C.gold);
  featurePill(s, 954, 624, "ALG", "Xem phương pháp", C.violet);
}

async function renderNewSlides(deck, firstNewIndex) {
  await fs.mkdir(PREVIEW, { recursive: true });
  await fs.mkdir(LAYOUT, { recursive: true });
  await fs.mkdir(QA, { recursive: true });
  for (let index = firstNewIndex; index < deck.slides.items.length; index += 1) {
    const slide = deck.slides.items[index];
    const stem = `slide-${String(index + 1).padStart(2, "0")}`;
    await writeBlob(`${PREVIEW}/${stem}.png`, await deck.export({ slide, format: "png", scale: 1 }));
    await fs.writeFile(`${LAYOUT}/${stem}.layout.json`, await (await slide.export({ format: "layout" })).text());
  }
  await writeBlob(`${QA}/webapp-addon-montage.webp`, await deck.export({ format: "webp", montage: true, scale: 1 }));
  await fs.writeFile(
    `${QA}/inspect-webapp-addon.ndjson`,
    (await deck.inspect({ kind: "slide,textbox,shape,image,notes", maxChars: 16000 })).ndjson,
  );
}

async function writeAuditFiles(originalCount) {
  await fs.writeFile(
    `${TMP}/template-audit.txt`,
    [
      "Source deck imported from repaired PPTX copy.",
      `Existing slide count: ${originalCount}. Existing slides are preserved and new webapp slides are appended after them.`,
      "Visual system reused: dark technical lab background, warm paper map background, green/cyan/gold accents, Montserrat/Quicksand/Roboto Mono.",
      "New media source: live Playwright captures from the local FYP webapp.",
    ].join("\n"),
  );
  await fs.writeFile(
    `${TMP}/template-frame-map.json`,
    JSON.stringify(
      {
        sourceSlidesPreserved: Array.from({ length: originalCount }, (_, index) => index + 1),
        appendedSlides: [
          { title: "Đăng nhập & phân quyền", sourceStyle: "paper/map" },
          { title: "Admin: LAB mode & ADMIN mode", sourceStyle: "technical lab" },
          { title: "Hai role shipper trong SHIP mode", sourceStyle: "paper/map" },
          { title: "SHIP mode: nhận đơn, lập tuyến, xác nhận", sourceStyle: "technical lab" },
        ],
      },
      null,
      2,
    ),
  );
  await fs.writeFile(
    `${TMP}/deviation-log.txt`,
    [
      "Intentional deviation: appended four webapp appendix slides instead of cloning old algorithm slides.",
      "Reason: user explicitly asked not to edit existing slides and to add basic webapp introduction slides behind the current deck.",
      "No existing slide content was edited by this script.",
    ].join("\n"),
  );
}

async function build() {
  const deck = await PresentationFile.importPptx(await FileBlob.load(SOURCE));
  const originalCount = deck.slides.items.length;

  await addLoginSlideFixed(deck, originalCount + 1);
  await addAdminSlide(deck, originalCount + 2);
  await addShipperRolesSlideFixed(deck, originalCount + 3);
  await addWorkflowSlideFixed(deck, originalCount + 4);

  await writeAuditFiles(originalCount);
  await renderNewSlides(deck, originalCount);

  const pptx = await PresentationFile.exportPptx(deck);
  await pptx.save(FINAL);
  console.log(JSON.stringify({ output: FINAL, originalCount, finalCount: deck.slides.items.length }, null, 2));
}

build().catch((error) => {
  process.stderr.write(`${error.stack || error}\n`);
  process.exitCode = 1;
});
