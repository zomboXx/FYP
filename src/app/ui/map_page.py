from __future__ import annotations

import json
from pathlib import Path

from fastapi import FastAPI, Query
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from app.data.scenario import load_osm_cached_scenario
from app.ui.theme import ALGORITHM_GROUPS, ALGORITHM_MAP_STYLES

MAP_ICON_DIR = Path(__file__).resolve().parent / "assets" / "map-icons"


def register_map_ui(app: FastAPI) -> None:
    if MAP_ICON_DIR.exists():
        app.mount("/assets/map-icons", StaticFiles(directory=MAP_ICON_DIR), name="map-icons")

    @app.get("/map", response_class=HTMLResponse)
    def map_view(
        path: str = Query(default="", description="Comma-separated node IDs to highlight."),
        start: str | None = Query(default=None),
        goal: str | None = Query(default=None),
        legs: str = Query(default="", description="JSON route legs for temporary delivery markers."),
        orders: str = Query(default="", description="JSON accepted orders for pickup/dropoff icons."),
        active: int = Query(default=0, ge=0),
        group: str = Query(default="informed", description="Algorithm group used to style this map."),
        algorithm: str | None = Query(default=None),
    ) -> HTMLResponse:
        scenario = load_osm_cached_scenario()
        route = [node_id.strip() for node_id in path.split(",") if node_id.strip()]
        map_group = group if group in ALGORITHM_MAP_STYLES else "informed"
        payload = {
            "scenario": scenario.model_dump(),
            "route": route,
            "start": start,
            "goal": goal,
            "routeLegs": _json_list_param(legs),
            "orders": _json_list_param(orders),
            "activeLeg": active,
            "mapGroup": map_group,
            "algorithm": algorithm,
            "mapStyle": ALGORITHM_MAP_STYLES[map_group],
            "groupLabel": ALGORITHM_GROUPS.get(map_group, {}).get("label", "Shipper Dispatch"),
        }
        return HTMLResponse(_render_map_html(payload))


def _json_list_param(value: str) -> list[dict]:
    if not value:
        return []
    try:
        decoded = json.loads(value)
    except json.JSONDecodeError:
        return []
    return decoded if isinstance(decoded, list) else []


def _render_map_html(payload: dict) -> str:
    data = json.dumps(payload, ensure_ascii=False)
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Find Your Path Map</title>
  <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
  <style>
    html, body, #map {{
      height: 100%;
      margin: 0;
      background: #05080d;
      font-family: Inter, Arial, sans-serif;
    }}
    #map {{
      width: 100%;
    }}
    body.debug-map #map {{
      background-color: #07100f;
      background-image:
        linear-gradient(rgba(35, 209, 121, 0.12) 1px, transparent 1px),
        linear-gradient(90deg, rgba(35, 209, 121, 0.12) 1px, transparent 1px);
      background-size: 40px 40px;
    }}
    .hud {{
      position: absolute;
      top: 16px;
      left: 16px;
      z-index: 1000;
      width: min(360px, calc(100vw - 32px));
      color: #f7fafc;
      background: rgba(5, 8, 13, 0.9);
      border: 1px solid #23303c;
      border-radius: 8px;
      box-shadow: 0 18px 45px rgba(0, 0, 0, 0.32);
      overflow: hidden;
    }}
    .hud header {{
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 10px;
      padding: 12px 14px;
      border-bottom: 1px solid #23303c;
    }}
    .hud h1 {{
      margin: 0;
      font-size: 14px;
      line-height: 1.2;
      letter-spacing: 0;
    }}
    .hud .body {{
      padding: 12px 14px 14px;
    }}
    .muted {{
      color: #8ea0b7;
      font-size: 12px;
      line-height: 1.5;
      margin: 0 0 10px;
    }}
    .pill {{
      flex: 0 0 auto;
      color: #030507;
      background: #23d179;
      border-radius: 999px;
      padding: 5px 9px;
      font-size: 11px;
      font-weight: 800;
    }}
    .pill.debug {{
      background: #facc15;
    }}
    .actions {{
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      margin-top: 10px;
    }}
    button {{
      appearance: none;
      border: 1px solid #344250;
      background: #101720;
      color: #f7fafc;
      border-radius: 6px;
      padding: 8px 10px;
      font-size: 12px;
      font-weight: 700;
      cursor: pointer;
    }}
    button.primary {{
      background: #23d179;
      border-color: #23d179;
      color: #030507;
    }}
    #manual-list {{
      margin: 10px 0 0;
      max-height: 120px;
      overflow: auto;
      padding: 8px;
      background: #030507;
      border: 1px solid #23303c;
      border-radius: 6px;
      color: #8ea0b7;
      font-size: 12px;
      line-height: 1.55;
      white-space: pre-wrap;
    }}
    .node-label {{
      display: grid;
      place-items: center;
      width: 28px;
      height: 28px;
      border-radius: 999px;
      color: #030507;
      background: #18212b;
      border: 2px solid #344250;
      font-size: 10px;
      font-weight: 900;
      box-shadow: 0 8px 18px rgba(0, 0, 0, 0.36);
    }}
    .node-depot {{ background: #23d179; border-color: #23d179; }}
    .node-order {{ background: #24c8e8; border-color: #24c8e8; }}
    .node-path {{ background: #facc15; border-color: #facc15; }}
    .node-start, .node-goal {{ background: #ff4d57; border-color: #ff4d57; }}
    .manual-node {{
      display: grid;
      place-items: center;
      width: 24px;
      height: 24px;
      border-radius: 999px;
      color: #030507;
      background: #ffffff;
      border: 2px solid #23d179;
      font-size: 10px;
      font-weight: 900;
    }}
    .delivery-playback {{
      display: none;
      gap: 8px;
      margin-top: 10px;
    }}
    .delivery-playback.active {{
      display: grid;
    }}
    .delivery-playback .row {{
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      align-items: center;
    }}
    #leg-status {{
      color: #facc15;
      font-size: 12px;
      font-weight: 800;
      line-height: 1.4;
    }}
    .node-editor {{
      display: grid;
      gap: 8px;
      min-width: 220px;
    }}
    .node-editor label {{
      display: grid;
      gap: 4px;
      color: #8ea0b7;
      font-size: 11px;
      font-weight: 700;
    }}
    .node-editor input {{
      width: 100%;
      box-sizing: border-box;
      color: #f7fafc;
      background: #030507;
      border: 1px solid #344250;
      border-radius: 6px;
      padding: 7px 8px;
      font-size: 12px;
    }}
    .node-editor .row {{
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 8px;
    }}
    .node-editor .actions {{
      margin-top: 0;
    }}
    .node-editor button {{
      padding: 7px 9px;
    }}
    button.danger {{
      color: #ffffff;
      background: #ff4d57;
      border-color: #ff4d57;
    }}
    .leaflet-popup-content-wrapper, .leaflet-popup-tip {{
      background: #0b1016;
      color: #f7fafc;
      border: 1px solid #23303c;
    }}
    @media (max-width: 640px) {{
      .hud {{
        top: 10px;
        left: 10px;
        width: calc(100vw - 20px);
      }}
      .hud header {{
        align-items: flex-start;
      }}
    }}
  </style>
</head>
<body>
  <div id="map"></div>
  <section class="hud">
    <header>
      <h1 id="map-title">Find Your Path / Live Map</h1>
      <span class="pill" id="map-mode">OSM + Leaflet</span>
    </header>
    <div class="body">
      <p class="muted">Click tren ban do de them node thu cong. Keo node de sua vi tri; click vao node de sua toa do, doi ten hoac xoa.</p>
      <div class="actions">
        <button class="primary" id="fit-route">Fit route</button>
        <button id="toggle-tiles">Off OSM</button>
        <button id="copy-coords">Copy coords</button>
        <button id="clear-manual">Clear manual</button>
      </div>
      <div class="delivery-playback" id="delivery-playback">
        <div id="leg-status">Delivery leg: -</div>
        <div class="row">
          <button id="prev-leg">Prev leg</button>
          <button class="primary" id="next-leg">Next leg</button>
          <button id="auto-leg">Auto</button>
        </div>
      </div>
      <div id="manual-list">Manual nodes: chua co</div>
    </div>
  </section>
  <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
  <script>
    const payload = {data};
    const scenario = payload.scenario;
    const route = payload.route || [];
    const routeSet = new Set(route);
    const start = payload.start;
    const goal = payload.goal;
    const mapGroup = payload.mapGroup || "informed";
    const mapStyle = payload.mapStyle || {{}};
    const groupLabel = payload.groupLabel || "Live Map";
    const algorithmLabel = payload.algorithm ? ` / ${{String(payload.algorithm).toUpperCase()}}` : "";
    const routeLegs = payload.routeLegs || [];
    const orderItems = payload.orders || [];
    const orderById = new Map(orderItems.map((order) => [String(order.id), order]));
    let activeLegIndex = Math.max(0, Math.min(routeLegs.length - 1, Number(payload.activeLeg || 0)));
    let legTimer = null;
    const nodes = scenario.nodes || [];
    const edges = scenario.edges || [];
    const byId = new Map(nodes.map((node) => [node.id, node]));
    const xs = nodes.map((node) => Number(node.x)).filter(Number.isFinite);
    const ys = nodes.map((node) => Number(node.y)).filter(Number.isFinite);
    const minX = Math.min(...xs);
    const maxX = Math.max(...xs);
    const minY = Math.min(...ys);
    const maxY = Math.max(...ys);
    const hcm = {{
      minLat: 10.695,
      maxLat: 10.895,
      minLng: 106.575,
      maxLng: 106.845,
    }};
    const iconAssets = {{
      shipperBike: "/assets/map-icons/shipper-bike.png",
      transportTruck: "/assets/map-icons/transport-truck.png",
      transportVan: "/assets/map-icons/transport-van.png",
      pickupFood: "/assets/map-icons/pickup-food.png",
      pickupDrink: "/assets/map-icons/pickup-drink.png",
      pickupCargo: "/assets/map-icons/pickup-cargo.png",
      pickupParcel: "/assets/map-icons/pickup-parcel.png",
      dropoffPin: "/assets/map-icons/dropoff-pin.png",
    }};
    document.getElementById("map-title").textContent = `Find Your Path / ${{groupLabel}}${{algorithmLabel}}`;
    document.getElementById("map-mode").textContent = mapStyle.badge || "OSM + Leaflet";

    function scale(value, fromMin, fromMax, toMin, toMax) {{
      if (!Number.isFinite(value) || fromMax === fromMin) return (toMin + toMax) / 2;
      return toMin + ((value - fromMin) / (fromMax - fromMin)) * (toMax - toMin);
    }}

    function nodeLatLng(node) {{
      if (node.lat !== null && node.lat !== undefined && node.lng !== null && node.lng !== undefined
        && Number.isFinite(Number(node.lat)) && Number.isFinite(Number(node.lng))) {{
        return [Number(node.lat), Number(node.lng)];
      }}
      const lng = scale(Number(node.x), minX, maxX, hcm.minLng, hcm.maxLng);
      const lat = scale(Number(node.y), minY, maxY, hcm.maxLat, hcm.minLat);
      return [lat, lng];
    }}

    function nodeIcon(node) {{
      const classes = ["node-label"];
      if (node.id === start) classes.push("node-start");
      else if (node.id === goal) classes.push("node-goal");
      else if (routeSet.has(node.id)) classes.push("node-path");
      else if (node.type === "depot") classes.push("node-depot");
      else if (node.type === "order") classes.push("node-order");
      const style = nodeBadgeStyle(node);
      return L.divIcon({{
        className: "",
        html: `<span class="${{classes.join(" ")}}" style="${{style}}">${{node.id}}</span>`,
        iconSize: [28, 28],
        iconAnchor: [14, 14],
      }});
    }}

    function nodeBadgeStyle(node) {{
      if (node.id === start || node.id === goal) {{
        return `background:${{mapStyle.current || "#ff4d57"}};border-color:${{mapStyle.current || "#ff4d57"}};`;
      }}
      if (routeSet.has(node.id)) {{
        return `background:${{mapStyle.route || "#23d179"}};border-color:${{mapStyle.route || "#23d179"}};`;
      }}
      return "";
    }}

    const map = L.map("map", {{ zoomControl: true }});
    const tileLayer = L.tileLayer("https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png", {{
      maxZoom: 19,
      attribution: "&copy; OpenStreetMap contributors",
    }});
    tileLayer.addTo(map);
    let tilesEnabled = true;

    const graphLayer = L.layerGroup().addTo(map);
    const routeLayer = L.layerGroup().addTo(map);
    const temporaryDeliveryLayer = L.layerGroup().addTo(map);
    const manualLayer = L.layerGroup().addTo(map);
    const allBounds = [];

    for (const edge of edges) {{
      const source = byId.get(edge.source);
      const target = byId.get(edge.target);
      if (!source || !target) continue;
      const pair = [nodeLatLng(source), nodeLatLng(target)];
      L.polyline(pair, {{
        color: edge.blocked ? "#ff4d57" : "#607287",
        weight: edge.blocked ? 4 : 2,
        opacity: edge.blocked ? 0.9 : 0.46,
      }}).bindTooltip(`${{edge.source}} -> ${{edge.target}} | ${{edge.distance_km}} km | ${{edge.base_minutes}} min`).addTo(graphLayer);
      allBounds.push(...pair);
    }}

    for (const node of nodes) {{
      const latLng = nodeLatLng(node);
      L.marker(latLng, {{ icon: nodeIcon(node), title: node.name }})
        .bindPopup(`<strong>${{node.id}} - ${{node.name}}</strong><br/>type: ${{node.type}}<br/>lat,lng: ${{latLng[0].toFixed(6)}}, ${{latLng[1].toFixed(6)}}`)
        .addTo(graphLayer);
      allBounds.push(latLng);
    }}

    const routeCoords = route.map((nodeId) => byId.get(nodeId)).filter(Boolean).map(nodeLatLng);
    if (routeCoords.length > 1) {{
      L.polyline(routeCoords, {{
        color: mapStyle.route || "#23d179",
        weight: 6,
        opacity: 0.95,
        lineJoin: "round",
      }}).bindTooltip(`Route: ${{route.join(" -> ")}}`).addTo(routeLayer);
    }}

    function imageIcon(src, size = 44) {{
      return L.icon({{
        iconUrl: src,
        iconSize: [size, size],
        iconAnchor: [size / 2, size / 2],
        popupAnchor: [0, -size / 2],
      }});
    }}

    function pickupAsset(category) {{
      const normalized = String(category || "").toLowerCase();
      if (["drink", "beverage", "water"].includes(normalized)) return iconAssets.pickupDrink;
      if (normalized === "food") return iconAssets.pickupFood;
      if (normalized === "parcel") return iconAssets.pickupParcel;
      if (normalized === "grocery") return iconAssets.pickupCargo;
      return iconAssets.pickupCargo;
    }}

    function vehicleAsset(leg) {{
      const kind = String(leg.kind || "");
      if (kind === "warehouse_delivery" || kind === "transport_to_warehouse") return iconAssets.transportTruck;
      if (kind === "approach_pickup") return iconAssets.shipperBike;
      return iconAssets.shipperBike;
    }}

    function addTemporaryMarker(nodeId, src, label, size = 46) {{
      const node = byId.get(nodeId);
      if (!node) return;
      const latLng = nodeLatLng(node);
      L.marker(latLng, {{ icon: imageIcon(src, size), title: label }})
        .bindPopup(`<strong>${{escapeHtml(label)}}</strong><br/>${{escapeHtml(node.id)}} - ${{escapeHtml(node.name)}}`)
        .addTo(temporaryDeliveryLayer);
    }}

    function legNodeIds(leg, order) {{
      const pickup = order.pickupNodeId || order.pickup_node_id || leg.from;
      const dropoff = order.dropoffNodeId || order.dropoff_node_id || leg.to;
      return {{ pickup, dropoff }};
    }}

    function renderActiveLeg() {{
      temporaryDeliveryLayer.clearLayers();
      const playback = document.getElementById("delivery-playback");
      const status = document.getElementById("leg-status");
      if (!routeLegs.length) {{
        playback.classList.remove("active");
        return;
      }}
      playback.classList.add("active");
      activeLegIndex = Math.max(0, Math.min(routeLegs.length - 1, activeLegIndex));
      const leg = routeLegs[activeLegIndex];
      const order = orderById.get(String(leg.orderId || "")) || {{}};
      const {{ pickup, dropoff }} = legNodeIds(leg, order);
      const labelOrder = leg.orderId ? `Don ${{leg.orderId}}` : "Delivery leg";
      status.textContent = `${{activeLegIndex + 1}}/${{routeLegs.length}} - ${{labelOrder}}: ${{leg.from}} -> ${{leg.to}}`;

      if (leg.path && leg.path.length > 1) {{
        const coords = leg.path.map((nodeId) => byId.get(nodeId)).filter(Boolean).map(nodeLatLng);
        L.polyline(coords, {{
          color: mapStyle.frontier || "#facc15",
          weight: 7,
          opacity: 0.9,
          lineJoin: "round",
        }}).addTo(temporaryDeliveryLayer);
      }}

      const kind = String(leg.kind || "");
      addTemporaryMarker(leg.from, vehicleAsset(leg), kind === "warehouse_delivery" ? "Xe van chuyen" : "Shipper", 54);
      if (kind === "approach_pickup") {{
        addTemporaryMarker(pickup || leg.to, pickupAsset(order.category), "Diem nhan hang", 46);
      }} else if (kind === "serve_order") {{
        addTemporaryMarker(pickup, pickupAsset(order.category), "Diem nhan hang", 46);
        addTemporaryMarker(dropoff, iconAssets.dropoffPin, "Diem giao hang", 46);
      }} else if (kind === "warehouse_delivery" || kind === "transport_to_warehouse") {{
        addTemporaryMarker(dropoff || leg.to, iconAssets.dropoffPin, "Diem giao hang", 46);
      }}
    }}

    function fitRoute() {{
      const targetBounds = routeCoords.length > 1 ? routeCoords : allBounds;
      if (targetBounds.length) {{
        map.fitBounds(targetBounds, {{ padding: [60, 60], maxZoom: 15 }});
      }} else {{
        map.setView([10.7769, 106.7009], 12);
      }}
    }}
    fitRoute();
    renderActiveLeg();

    const manualNodes = [];
    let manualLine = null;
    let manualSeq = 1;
    let suppressNextMapClick = false;
    const manualList = document.getElementById("manual-list");

    function escapeHtml(value) {{
      return String(value)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
    }}

    function manualIcon(id) {{
      return L.divIcon({{
        className: "",
        html: `<span class="manual-node">${{escapeHtml(id)}}</span>`,
        iconSize: [24, 24],
        iconAnchor: [12, 12],
      }});
    }}

    function manualNodePayload() {{
      return manualNodes.map((node) => ({{ id: node.id, lat: node.lat, lng: node.lng }}));
    }}

    function manualPopupHtml(node) {{
      const safeId = escapeHtml(node.id);
      return `
        <div class="node-editor" data-node-id="${{safeId}}">
          <strong>${{safeId}}</strong>
          <label>Node ID
            <input class="manual-id" value="${{safeId}}" />
          </label>
          <div class="row">
            <label>Latitude
              <input class="manual-lat" type="number" step="0.000001" value="${{node.lat.toFixed(6)}}" />
            </label>
            <label>Longitude
              <input class="manual-lng" type="number" step="0.000001" value="${{node.lng.toFixed(6)}}" />
            </label>
          </div>
          <div class="actions">
            <button class="primary manual-save" type="button">Save</button>
            <button class="danger manual-delete" type="button">Delete</button>
          </div>
        </div>`;
    }}

    function bindManualPopup(node) {{
      node.marker.bindPopup(manualPopupHtml(node));
      node.marker.off("popupopen");
      node.marker.on("popupopen", () => {{
        const popup = node.marker.getPopup().getElement();
        if (!popup) return;
        L.DomEvent.disableClickPropagation(popup);
        L.DomEvent.disableScrollPropagation(popup);
        const idInput = popup.querySelector(".manual-id");
        const latInput = popup.querySelector(".manual-lat");
        const lngInput = popup.querySelector(".manual-lng");
        popup.querySelector(".manual-save").addEventListener("click", (clickEvent) => {{
          clickEvent.preventDefault();
          clickEvent.stopPropagation();
          suppressNextMapClick = true;
          const nextId = idInput.value.trim() || node.id;
          const nextLat = Number(latInput.value);
          const nextLng = Number(lngInput.value);
          if (!Number.isFinite(nextLat) || !Number.isFinite(nextLng)) {{
            manualList.textContent = "Toa do khong hop le. Hay nhap lat/lng dang so.";
            return;
          }}
          node.id = nextId;
          node.lat = nextLat;
          node.lng = nextLng;
          node.marker.setLatLng([node.lat, node.lng]);
          node.marker.setIcon(manualIcon(node.id));
          bindManualPopup(node);
          renderManual();
          node.marker.closePopup();
          window.setTimeout(() => {{
            suppressNextMapClick = false;
          }}, 300);
        }});
        popup.querySelector(".manual-delete").addEventListener("click", (clickEvent) => {{
          clickEvent.preventDefault();
          clickEvent.stopPropagation();
          suppressNextMapClick = true;
          deleteManualNode(node);
          window.setTimeout(() => {{
            suppressNextMapClick = false;
          }}, 300);
        }});
      }});
    }}

    function addManualNode(lat, lng, id = `M${{manualSeq++}}`) {{
      const node = {{ id, lat, lng, marker: null }};
      node.marker = L.marker([lat, lng], {{
        icon: manualIcon(id),
        draggable: true,
        autoPan: true,
        bubblingMouseEvents: false,
      }}).addTo(manualLayer);
      node.marker.on("click", (event) => {{
        L.DomEvent.stopPropagation(event);
      }});
      node.marker.on("dragstart", () => {{
        suppressNextMapClick = true;
      }});
      node.marker.on("dragend", () => {{
        const point = node.marker.getLatLng();
        node.lat = point.lat;
        node.lng = point.lng;
        bindManualPopup(node);
        renderManual();
        suppressNextMapClick = true;
        window.setTimeout(() => {{
          suppressNextMapClick = false;
        }}, 300);
      }});
      bindManualPopup(node);
      manualNodes.push(node);
      renderManual();
      return node;
    }}

    function deleteManualNode(node) {{
      const index = manualNodes.indexOf(node);
      if (index >= 0) manualNodes.splice(index, 1);
      manualLayer.removeLayer(node.marker);
      renderManual();
    }}

    function renderManual() {{
      if (manualLine) manualLayer.removeLayer(manualLine);
      if (manualNodes.length > 1) {{
        manualLine = L.polyline(manualNodes.map((node) => [node.lat, node.lng]), {{
          color: "#ffffff",
          weight: 4,
          dashArray: "8 8",
        }}).addTo(manualLayer);
      }}
      manualList.textContent = manualNodes.length
        ? manualNodes.map((node) => `${{node.id}}: [${{node.lat.toFixed(6)}}, ${{node.lng.toFixed(6)}}]`).join("\\n")
        : "Manual nodes: chua co";
    }}

    map.on("click", (event) => {{
      const target = event.originalEvent && event.originalEvent.target;
      if (
        suppressNextMapClick ||
        (target instanceof Element &&
          target.closest(".leaflet-marker-icon, .leaflet-popup, .leaflet-control, .hud"))
      ) {{
        suppressNextMapClick = false;
        return;
      }}
      addManualNode(event.latlng.lat, event.latlng.lng).marker.openPopup();
    }});

    document.getElementById("fit-route").addEventListener("click", fitRoute);
    document.getElementById("toggle-tiles").addEventListener("click", () => {{
      tilesEnabled = !tilesEnabled;
      const mode = document.getElementById("map-mode");
      const toggle = document.getElementById("toggle-tiles");
      if (tilesEnabled) {{
        tileLayer.addTo(map);
        document.body.classList.remove("debug-map");
        mode.textContent = mapStyle.badge || "OSM + Leaflet";
        mode.classList.remove("debug");
        toggle.textContent = "Off OSM";
      }} else {{
        map.removeLayer(tileLayer);
        document.body.classList.add("debug-map");
        mode.textContent = "Debug map";
        mode.classList.add("debug");
        toggle.textContent = "On OSM";
      }}
    }});
    document.getElementById("clear-manual").addEventListener("click", () => {{
      manualNodes.length = 0;
      manualLayer.clearLayers();
      manualLine = null;
      manualSeq = 1;
      renderManual();
    }});
    document.getElementById("copy-coords").addEventListener("click", async () => {{
      const text = JSON.stringify(manualNodePayload(), null, 2);
      try {{
        await navigator.clipboard.writeText(text);
        manualList.textContent = manualNodes.length ? `${{manualList.textContent}}\\n\\nCopied.` : "Manual nodes: chua co";
      }} catch {{
        manualList.textContent = text || "[]";
      }}
    }});
    document.getElementById("prev-leg").addEventListener("click", () => {{
      activeLegIndex = Math.max(0, activeLegIndex - 1);
      renderActiveLeg();
    }});
    document.getElementById("next-leg").addEventListener("click", () => {{
      activeLegIndex = routeLegs.length ? (activeLegIndex + 1) % routeLegs.length : 0;
      renderActiveLeg();
    }});
    document.getElementById("auto-leg").addEventListener("click", () => {{
      const button = document.getElementById("auto-leg");
      if (legTimer) {{
        window.clearInterval(legTimer);
        legTimer = null;
        button.textContent = "Auto";
        return;
      }}
      button.textContent = "Stop";
      legTimer = window.setInterval(() => {{
        activeLegIndex = routeLegs.length ? (activeLegIndex + 1) % routeLegs.length : 0;
        renderActiveLeg();
      }}, 1200);
    }});
  </script>
</body>
</html>"""
