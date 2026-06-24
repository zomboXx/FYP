# FYP: Find Your Path

**Smart Urban Delivery Planner**  
**Tro ly toi uu giao hang xe may do thi**

Find Your Path la MVP cho do an AI cuoi khoa: mo phong giao hang xe may trong do thi Viet Nam va so sanh 6 nhom thuat toan AI trong cung mot bai toan giao hang co rang buoc.

Ban hien tai tap trung vao demo bao ve do an: dang nhap, admin bat/tat thuat toan theo nhom shipper, shipper nhan don va lap lo trinh, ban do, va Defense Lab de debug tung buoc thuat toan.

## Deployed demo

Preview URL: https://find-your-path-2oy6kklc9-ducphat1509-beeps-projects.vercel.app

Trang preview hien dang nam sau Vercel Deployment Protection, nen nguoi mo can co quyen Vercel/team. Khi can link public cho hoi dong hoac coworker, hay tat protection cho project preview hoac tao production deployment public.

Ghi chu: ban deploy gan nhat chi dung SQLite tam thoi cho demo/van dap AI. Du lieu tren Vercel co the reset khi cold start, redeploy hoac function instance thay doi.

## Kien truc

- Backend: Python 3.11+, FastAPI, Pydantic, pytest
- UI: Python Flet single-page UI mounted vao FastAPI tai `/`
- Map: Leaflet/Flet map, OpenStreetMap tile, route do thuat toan Python cua project tinh
- AI core: Uninformed, Informed, Local Search, Complex Environment, CSP, Adversarial Search
- Auth/database: JWT HS256, PBKDF2 password hash, SQLite demo/runtime
- Source: `src/app`; tests: `tests`; scripts: `scripts`; docs: `docs`
- OSM cache: `src/app/data/osm_hcm_q1.json`

Project khong can Node/npm de chay local demo. Browser nhan Flet web client, UI state duoc cap nhat tu Python qua WebSocket.

## Cai dat va chay local

```powershell
cd D:\TAI_LIEU_HOC_TAP_DAI_HOC\PersonalPrj\FYP
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
$env:PYTHONPATH = ".\src"
uvicorn app.main:app --reload
```

Mo app tai `http://127.0.0.1:8000`. API nam duoi prefix `/api`.

## Chay on dinh tren Windows

Nen dung script nay khi demo de tranh sai Python, thieu dependency, hoac port 8000 dang ban:

```powershell
cd D:\TAI_LIEU_HOC_TAP_DAI_HOC\PersonalPrj\FYP
powershell -ExecutionPolicy Bypass -File .\run_app.ps1
```

Script se cai dependency neu thieu, tu chuyen port neu 8000 dang ban, va in URL tren terminal.

## Tai khoan demo

| Username | Password | Vai tro |
| --- | --- | --- |
| `admin` | `admin123` | Quan tri Defense/Admin mode |
| `shipper_a` | `shipper123` | On-demand: Food/Ride, current -> pickup -> dropoff |
| `shipper_b` | `shipper123` | Depot delivery: Parcel/Grocery, xuat phat tu kho |

## Kiem thu

Chay hook bat buoc truoc demo, commit hoac deploy:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\pre_check.ps1
```

Hook compile source, chay pytest, va scan `src`/`tests` de tranh `TODO`, `FIXME`, debug `print`, `console.log`, hoac code bi comment-out.

## Deploy Vercel preview

Vercel deploy hien tai duoc xem la preview demo, khong phai production storage.

Bien moi truong can co tren Vercel:

```text
FYP_JWT_SECRET=<chuoi-bi-mat-dai-ngau-nhien>
PYTHONPATH=src
```

Tuy chon:

```text
FYP_DB_PATH=/tmp/fyp.sqlite
```

Neu khong set `FYP_DB_PATH`, app tu dung:

- Local: `src/app/data/fyp.sqlite`
- Vercel: `/tmp/fyp.sqlite`

Domain rieng chua can cho giai doan van dap. Sau nay co the them domain trong Vercel Project Settings -> Domains.

## Storage roadmap

SQLite hien tai phu hop cho demo thuat toan vi app tu seed user, permission va don hang. Tren Vercel, SQLite chi nen dung tam thoi vi filesystem function la read-only ngoai `/tmp`, va `/tmp` khong phai storage ben vung.

Huong mo rong san pham:

1. Tach lop data-access cho users, permissions, orders va assignments.
2. Chuyen storage ben vung sang Postgres, uu tien Neon hoac Supabase.
3. Giu OSM cache la JSON read-only.
4. Neu them custom node/edge ben vung, tao bang DB rieng thay vi ghi de `osm_hcm_q1.json`.

## API chinh

- `POST /api/auth/login`
- `GET /api/auth/me`
- `GET /api/admin/permissions`
- `PATCH /api/admin/permissions`
- `GET /api/orders/available`
- `POST /api/shipper/orders/accept`
- `POST /api/shipper/orders/complete`
- `POST /api/shipper/routes/plan`
- `GET /api/scenario/default`
- `POST /api/pathfinding/run`
- `POST /api/delivery/optimize`
- `POST /api/constraints/check`
- `POST /api/csp/solve`
- `POST /api/complex/run`
- `POST /api/events/simulate`
- `POST /api/adversarial/run`
- `GET /api/health`

Moi response thuat toan gom `path`, `visitedNodes`, `metrics`, `runtimeMs`, va `explanation`. Khi gui `debug=true`, response co them `traceSteps` va `debugData` de UI trinh bay frontier/visited, g-h-f, belief state, CSP domain/assignment hoac alpha-beta.

## Tai lieu

- `docs/business-analysis-handover.md`: nghiep vu, scope, stakeholder, flow, acceptance criteria.
- `docs/database-guide.md`: cach xem SQLite local va ghi chu storage Vercel.
- `docs/demo-script.md`: kich ban demo 5-7 phut.
- `docs/algorithm-comparison.md`: vai tro, diem manh va han che cua tung thuat toan.
- `docs/ui-ux-overview.md`: tong quan UI/UX.
- `docs/report-outline.md`: de cuong bao cao hoc thuat.

## Tai tao OSM cache

Chi can chay khi muon lay lai du lieu tu OpenStreetMap/Overpass:

```powershell
python -m pip install osmnx
python scripts/import_osm_graph.py
```

Luc demo, app dung cache local de tranh loi mang.
