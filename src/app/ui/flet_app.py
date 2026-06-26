from __future__ import annotations

import json
import math
import asyncio
from typing import Any
from urllib.parse import urlencode

import flet as ft
import flet_map as fmap
from fastapi import HTTPException

from app.data.scenario import load_osm_cached_scenario
from app.models.schemas import (
    AdversarialSearchRequest,
    AlgorithmResponse,
    ComplexSearchRequest,
    CspSolveRequest,
    DeliveryOptimizeRequest,
    MapCreateRequest,
    MapPatchRequest,
    MapSummary,
    PathfindingRequest,
    PermissionRow,
    Scenario,
)
from app.services.auth_service import (
    accept_orders,
    authenticate,
    complete_order,
    list_accepted_orders,
    list_available_orders,
    list_permissions,
    shipper_operation_profile,
    update_permission,
)
from app.services.map_service import create_map, delete_map, default_map_for_group, get_map, list_maps, update_map
from app.services.route_service import (
    optimize_delivery,
    plan_accepted_orders,
    run_adversarial_search,
    run_complex_search,
    run_pathfinding,
    solve_csp,
)
from app.ui.components import dropdown, metric_value, outline_button, panel, pill, primary_button, text
from app.ui.state import ComparisonRow, FletState
from app.ui.theme import (
    ALGORITHM_GROUPS,
    ALGORITHM_MAP_STYLES,
    BG,
    CYAN,
    GREEN,
    GREEN_DARK,
    INK,
    LINE,
    LINE_LIGHT,
    MUTED,
    PANEL,
    PANEL_2,
    PAPER,
    PAPER_2,
    RED,
    TEXT,
    WORKSPACE_COPY,
    YELLOW,
)

MAP_ICON_BASE = "/assets/map-icons"
MAP_ICONS = {
    "shipper_bike": f"{MAP_ICON_BASE}/shipper-bike.png",
    "transport_truck": f"{MAP_ICON_BASE}/transport-truck.png",
    "transport_van": f"{MAP_ICON_BASE}/transport-van.png",
    "pickup_food": f"{MAP_ICON_BASE}/pickup-food.png",
    "pickup_drink": f"{MAP_ICON_BASE}/pickup-drink.png",
    "pickup_cargo": f"{MAP_ICON_BASE}/pickup-cargo.png",
    "pickup_parcel": f"{MAP_ICON_BASE}/pickup-parcel.png",
    "dropoff_pin": f"{MAP_ICON_BASE}/dropoff-pin.png",
}


class FletDashboard:
    def __init__(self, page: ft.Page) -> None:
        self.page = page
        self.state = FletState()
        self.root = ft.Container(expand=True)

    def setup(self) -> None:
        self.page.title = "FYP Delivery"
        self.page.padding = 0
        self.page.spacing = 0
        self.page.bgcolor = BG
        self.page.theme_mode = ft.ThemeMode.DARK
        self.page.on_resized = lambda _: self.render()
        self.state.scenario = load_osm_cached_scenario()
        self.load_map_catalog()
        self.activate_map_for_group(self.state.group)
        self.state.start_id = self.state.scenario.depot_id
        self.state.goal_id = "D1" if any(node.id == "D1" for node in self.state.scenario.nodes) else self.state.scenario.nodes[-1].id
        self.page.add(self.root)
        self.render()

    def render(self) -> None:
        self.root.content = self.login_view() if not self.state.user else self.shell_view()
        self.page.update()

    def notify(self, message: str, danger: bool = False) -> None:
        self.page.open(ft.SnackBar(text(message, color=TEXT), bgcolor=RED if danger else PANEL_2, show_close_icon=True))

    def safe(self, action: Any) -> None:
        try:
            action()
        except HTTPException as exc:
            detail = exc.detail if isinstance(exc.detail, str) else "Request failed."
            self.state.error = detail
            self.notify(detail, True)
            self.render()
        except Exception as exc:  # pragma: no cover - defensive UI guard.
            self.state.error = str(exc)
            self.notify(str(exc), True)
            self.render()

    def load_map_catalog(self) -> None:
        self.state.maps = list_maps()

    def sync_node_selection(self) -> None:
        scenario = self.state.scenario
        if not scenario or not scenario.nodes:
            return
        node_ids = {node.id for node in scenario.nodes}
        if self.state.start_id not in node_ids:
            self.state.start_id = scenario.depot_id if scenario.depot_id in node_ids else scenario.nodes[0].id
        if self.state.goal_id not in node_ids or self.state.goal_id == self.state.start_id:
            self.state.goal_id = next((node.id for node in scenario.nodes if node.id != self.state.start_id), scenario.nodes[0].id)
        if self.state.shipper_start_id and self.state.shipper_start_id not in node_ids:
            self.state.shipper_start_id = ""

    def activate_map_for_group(self, group_key: str) -> None:
        selected_id = self.state.selected_map_ids.get(group_key)
        try:
            detail = get_map(selected_id) if selected_id else default_map_for_group(group_key)
        except HTTPException:
            detail = default_map_for_group(group_key)
        self.state.selected_map_ids[group_key] = detail.id
        self.state.active_map_id = detail.id
        self.state.scenario = detail.scenario
        self.sync_node_selection()

    def selected_map_summary(self) -> MapSummary | None:
        return next((item for item in self.state.maps if item.id == self.state.active_map_id), None)

    def map_options(self) -> list[tuple[str, str]]:
        return [
            (str(item.id), f"{item.name} / {item.algorithmGroup}{' / default' if item.isDefault else ''}")
            for item in self.state.maps
        ]

    def choose_map(self, map_id: int) -> None:
        detail = get_map(map_id)
        group_key = self.current_map_group()
        self.state.selected_map_ids[group_key] = detail.id
        self.state.active_map_id = detail.id
        self.state.scenario = detail.scenario
        self.state.result = None
        self.state.trace_index = 0
        if self.state.workspace == "defense":
            self.state.group_results.pop(self.state.group, None)
            self.state.group_trace_indexes.pop(self.state.group, None)
        self.stop_auto_run()
        self.stop_shipper_playback()
        self.sync_node_selection()
        self.configure_shipper_workspace()
        self.render()

    def algorithm_allowed_for_user(self, algorithm: str) -> bool:
        user = self.state.user
        if user is None or user.role == "admin":
            return True
        if user.shipperGroup is None:
            return False
        if not self.state.permissions:
            self.state.permissions = list_permissions()
        return any(
            permission.shipperGroup == user.shipperGroup
            and permission.algorithmName == algorithm
            and permission.enabled
            for permission in self.state.permissions
        )

    def first_allowed_algorithm(self, group_key: str) -> str:
        algorithms = ALGORITHM_GROUPS[group_key]["algorithms"]
        return next(
            (value for value, _ in algorithms if self.algorithm_allowed_for_user(value)),
            algorithms[0][0],
        )

    def login_view(self) -> ft.Control:
        username = ft.TextField(
            label="Username",
            value="admin",
            border_color=LINE,
            focused_border_color=GREEN,
            color=TEXT,
            bgcolor=PANEL_2,
            border_radius=4,
        )
        password = ft.TextField(
            label="Password",
            value="admin123",
            password=True,
            can_reveal_password=True,
            border_color=LINE,
            focused_border_color=GREEN,
            color=TEXT,
            bgcolor=PANEL_2,
            border_radius=4,
        )

        def fill(user: str, pwd: str) -> None:
            username.value = user
            password.value = pwd
            self.page.update()

        def login(_: Any = None) -> None:
            def do_login() -> None:
                self.state.user = authenticate(username.value or "", password.value or "")
                self.state.workspace = "shipper" if self.state.user.role == "shipper" else "defense"
                self.state.error = ""
                self.state.permissions = list_permissions()
                self.load_map_catalog()
                self.activate_map_for_group("shipper" if self.state.workspace == "shipper" else self.state.group)
                self.configure_shipper_workspace()
                if self.state.user.role != "admin":
                    self.load_orders()
                self.render()

            self.safe(do_login)

        def account_card(
            icon: str,
            title: str,
            subtitle: str,
            color: str,
            user: str,
            pwd: str,
        ) -> ft.Control:
            return ft.Container(
                content=ft.Row(
                    [
                        ft.Icon(icon, color=color, size=22),
                        ft.Column(
                            [
                                text(title, 12, TEXT, ft.FontWeight.W_900),
                                text(subtitle, 10, MUTED),
                            ],
                            spacing=2,
                            expand=True,
                        ),
                    ],
                    spacing=10,
                ),
                bgcolor=PANEL_2,
                border=ft.border.all(1, color),
                border_radius=4,
                padding=12,
                on_click=lambda _: fill(user, pwd),
            )

        demo_cards = ft.Column(
            [
                account_card(ft.Icons.ADMIN_PANEL_SETTINGS, "Admin", "Defense Lab + Admin Panel", YELLOW, "admin", "admin123"),
                account_card(ft.Icons.LOCAL_SHIPPING, "Shipper Standard", "BFS, DFS, A*", GREEN, "shipper_a", "shipper123"),
                account_card(ft.Icons.ROCKET_LAUNCH, "Shipper Priority", "Full algorithm access", CYAN, "shipper_b", "shipper123"),
            ],
            spacing=10,
        )

        hero = ft.Container(
            content=ft.Column(
                [
                    ft.Row(
                        [
                            ft.Icon(ft.Icons.ROUTE, color=GREEN, size=22),
                            text("FYP DELIVERY", 13, GREEN, ft.FontWeight.W_900),
                        ],
                        spacing=10,
                    ),
                    ft.Container(expand=True),
                    ft.Column(
                        [
                            text("AI ROUTE", 74, TEXT, ft.FontWeight.W_900, font_family="Consolas"),
                            text("OPTIMIZER.", 74, GREEN, ft.FontWeight.W_900, font_family="Consolas"),
                            text("LIVE.", 74, TEXT, ft.FontWeight.W_900, font_family="Consolas"),
                        ],
                        spacing=0,
                    ),
                    text(
                        "Mo phong giao hang do thi Viet Nam.\nSo sanh BFS, DFS, A*, Hill Climbing\nva hon the nua - truc tiep tren graph.",
                        18,
                        MUTED,
                        font_family="Consolas",
                    ),
                    ft.Row(
                        [
                            pill("UNINFORMED SEARCH"),
                            pill("INFORMED SEARCH"),
                            pill("LOCAL SEARCH"),
                            pill("CSP"),
                            pill("PARTIAL OBSERVABILITY"),
                            pill("ADVERSARIAL"),
                        ],
                        wrap=True,
                    ),
                    ft.Container(expand=True),
                    ft.Row(
                        [
                            ft.Container(width=44, height=2, bgcolor=GREEN),
                            text("AI DELIVERY CONSOLE v2.0", 11, MUTED, ft.FontWeight.W_700),
                        ],
                        spacing=12,
                    ),
                ],
                expand=True,
                spacing=18,
            ),
            bgcolor=BG,
            border=ft.border.only(right=ft.BorderSide(1, LINE)),
            padding=ft.padding.only(left=58, top=38, right=48, bottom=36),
            expand=2,
        )

        form = ft.Container(
            content=ft.Column(
                [
                    text("SECURE ACCESS", 12, GREEN, ft.FontWeight.W_900, font_family="Consolas"),
                    text("SIGN IN TO CONSOLE", 30, TEXT, ft.FontWeight.W_900, font_family="Consolas"),
                    demo_cards,
                    outline_button("OPEN LIVE MAP", self.open_map, ft.Icons.MAP),
                    username,
                    password,
                    primary_button("ENTER CONSOLE", login, ft.Icons.LOGIN),
                    text(self.state.error, 12, RED) if self.state.error else ft.Container(height=0),
                    ft.Container(expand=True),
                    text("FYP Delivery / AI Delivery Console / Do an AI Cuoi Khoa", 11, MUTED),
                ],
                alignment=ft.MainAxisAlignment.CENTER,
                spacing=16,
            ),
            bgcolor=BG,
            border=ft.border.only(left=ft.BorderSide(1, LINE), right=ft.BorderSide(5, GREEN)),
            padding=36,
            width=440,
        )

        return ft.Column(
            [
                ft.ResponsiveRow(
                    controls=[
                        ft.Container(content=hero, col={"xs": 12, "lg": 8}, height=800),
                        ft.Container(content=form, col={"xs": 12, "lg": 4}, height=800),
                    ],
                    spacing=0,
                    run_spacing=0,
                )
            ],
            spacing=0,
            scroll=ft.ScrollMode.AUTO,
            expand=True,
        )

    def shell_view(self) -> ft.Control:
        compact = bool(self.page.width and self.page.width < 700)
        keys = ["shipper", "defense", "map"]
        if self.state.user and self.state.user.role == "admin":
            keys.append("admin")

        def nav_to(workspace: str) -> None:
            if workspace == "map":
                self.open_map()
                return
            self.stop_auto_run()
            self.stop_shipper_playback()
            if self.state.workspace == "defense":
                self.state.group_trace_indexes[self.state.group] = self.state.trace_index
            self.state.workspace = workspace
            if workspace == "defense":
                self.activate_map_for_group(self.state.group)
                self.state.result = self.state.group_results.get(self.state.group)
                self.state.trace_index = self.state.group_trace_indexes.get(self.state.group, 0)
            else:
                self.state.result = None
                self.state.trace_index = 0
            if self.state.workspace == "admin":
                self.state.permissions = list_permissions()
                self.load_map_catalog()
            if self.state.workspace == "shipper":
                self.activate_map_for_group("shipper")
                self.configure_shipper_workspace()
                self.load_orders()
            self.render()

        def nav_item(workspace: str, icon: str, label: str) -> ft.Control:
            active = self.state.workspace == workspace
            return ft.Container(
                content=ft.Column(
                    [
                        ft.Icon(icon, color=INK if active else MUTED, size=22),
                        text(label, 10, INK if active else MUTED, ft.FontWeight.W_900),
                    ],
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    spacing=4,
                ),
                width=64,
                padding=ft.padding.symmetric(vertical=12),
                bgcolor=GREEN if active else INK,
                border=ft.border.all(1, GREEN if active else "#0E151D"),
                border_radius=4,
                on_click=lambda _: nav_to(workspace),
                tooltip=label,
            )

        nav_controls = [
            nav_item("shipper", ft.Icons.LOCAL_SHIPPING, "SHIP"),
            nav_item("defense", ft.Icons.SCIENCE, "LAB"),
            nav_item("map", ft.Icons.MAP, "MAP"),
        ]
        if "admin" in keys:
            nav_controls.append(nav_item("admin", ft.Icons.ADMIN_PANEL_SETTINGS, "ADMIN"))

        logout_button = ft.IconButton(ft.Icons.LOGOUT, icon_color=MUTED, tooltip="Logout", on_click=lambda _: self.logout())
        if compact:
            rail = ft.Container(
                content=ft.Row([*nav_controls, ft.Container(expand=True), logout_button], spacing=6),
                bgcolor=INK,
                border=ft.border.only(bottom=ft.BorderSide(1, LINE)),
                height=70,
                padding=ft.padding.symmetric(horizontal=8, vertical=3),
            )
        else:
            rail = ft.Container(
                content=ft.Column(
                    [
                        ft.Container(
                            content=text("FYP", 13, GREEN, ft.FontWeight.W_900, text_align=ft.TextAlign.CENTER),
                            width=52,
                            height=52,
                            alignment=ft.alignment.center,
                            border=ft.border.all(2, GREEN),
                            border_radius=4,
                        ),
                        ft.Column(nav_controls, spacing=12),
                        ft.Container(expand=True),
                        ft.Container(
                            content=text((self.state.user.username[:1] if self.state.user else "A").upper(), 14, INK, ft.FontWeight.W_900),
                            width=36,
                            height=36,
                            alignment=ft.alignment.center,
                            bgcolor=GREEN,
                            border_radius=18,
                        ),
                        logout_button,
                    ],
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    spacing=22,
                ),
                bgcolor=INK,
                border=ft.border.only(right=ft.BorderSide(1, LINE)),
                width=82,
                padding=ft.padding.symmetric(horizontal=9, vertical=20),
            )
        content = self.workspace_content()
        workspace = ft.Container(content=content, expand=True, bgcolor=BG, padding=12 if compact else 20)
        if compact:
            return ft.Column([rail, workspace], spacing=0, expand=True)
        return ft.Row([rail, workspace], spacing=0, expand=True)

    def workspace_content(self) -> ft.Control:
        compact = bool(self.page.width and self.page.width < 700)
        title, subtitle = WORKSPACE_COPY[self.state.workspace]
        user = self.state.user
        title_parts = {
            "shipper": ("SHIPPER", "DISPATCH"),
            "defense": ("ALGORITHM", "SIMULATOR"),
            "admin": ("ADMIN", "PERMISSIONS"),
        }[self.state.workspace]
        identity = ft.Column(
            [
                text(user.username if user else "", 13, TEXT, ft.FontWeight.W_700, text_align=ft.TextAlign.RIGHT),
                pill((f"{user.role} / {user.shipperGroup}" if user and user.shipperGroup else f"{user.role} / ALL ACCESS") if user else "GUEST"),
            ],
            horizontal_alignment=ft.CrossAxisAlignment.END,
            spacing=6,
        )
        title_block = ft.Column(
            [
                ft.Row(
                    [
                        ft.Icon(ft.Icons.SCIENCE if self.state.workspace == "defense" else ft.Icons.ROUTE, color=GREEN, size=18),
                        text(title, 12, GREEN, ft.FontWeight.W_900),
                    ],
                    spacing=8,
                ),
                ft.Row(
                    [
                        text(title_parts[0], 30 if compact else 42, TEXT, ft.FontWeight.W_900, font_family="Consolas"),
                        text(title_parts[1], 30 if compact else 42, GREEN, ft.FontWeight.W_900, font_family="Consolas"),
                    ],
                    wrap=True,
                    spacing=8 if compact else 12,
                ),
                text(subtitle, 13, MUTED),
            ],
            expand=not compact,
            spacing=4,
        )
        if compact:
            header = ft.Column([ft.Row([identity], alignment=ft.MainAxisAlignment.END), title_block], spacing=8)
        else:
            header = ft.Row(
                [title_block, identity],
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                vertical_alignment=ft.CrossAxisAlignment.START,
            )
        body = {
            "shipper": self.shipper_view,
            "defense": self.defense_view,
            "admin": self.admin_view,
        }[self.state.workspace]()
        return ft.Column([header, body], expand=True, scroll=ft.ScrollMode.AUTO, spacing=18)

    def logout(self) -> None:
        self.stop_auto_run()
        self.stop_shipper_playback()
        self.state = FletState(scenario=self.state.scenario)
        self.load_map_catalog()
        self.activate_map_for_group(self.state.group)
        if self.state.scenario:
            self.state.start_id = self.state.scenario.depot_id
            self.state.goal_id = "D1" if any(node.id == "D1" for node in self.state.scenario.nodes) else self.state.scenario.nodes[-1].id
        self.render()

    def load_orders(self) -> None:
        if not self.state.user:
            return
        category = None if self.state.category_filter == "all" else self.state.category_filter
        urgency = None if self.state.urgency_filter == "all" else self.state.urgency_filter
        self.state.orders = list_available_orders(category, urgency, self.state.user)
        self.state.accepted_orders = list_accepted_orders(self.state.user)

    def configure_shipper_workspace(self) -> None:
        if not self.state.user or not self.state.scenario:
            return
        profile = shipper_operation_profile(self.state.user)
        if profile == "depot_delivery":
            self.state.shipper_start_id = self.state.scenario.depot_id
        elif not self.state.shipper_start_id or self.state.shipper_start_id == self.state.scenario.depot_id:
            self.state.shipper_start_id = next(
                (
                    node.id
                    for node in self.state.scenario.nodes
                    if node.id != self.state.scenario.depot_id and node.type == "intersection"
                ),
                self.state.scenario.depot_id,
            )

    def shipper_view(self) -> ft.Control:
        profile = shipper_operation_profile(self.state.user) if self.state.user else "on_demand"
        category_options = (
            [("all", "Food + Ride"), ("food", "Food"), ("ride", "Cho nguoi")]
            if profile == "on_demand"
            else [("all", "Parcel + Grocery"), ("parcel", "Hang hoa"), ("grocery", "Di cho")]
        )
        def update_category(event: ft.ControlEvent) -> None:
            self.state.category_filter = event.control.value
            self.state.selected_orders.clear()
            self.load_orders()
            self.render()

        def update_urgency(event: ft.ControlEvent) -> None:
            self.state.urgency_filter = event.control.value
            self.state.selected_orders.clear()
            self.load_orders()
            self.render()

        def toggle_order(order_id: str, checked: bool) -> None:
            if checked:
                self.state.selected_orders.add(order_id)
            else:
                self.state.selected_orders.discard(order_id)

        def accept_selected(_: Any = None) -> None:
            def do_accept() -> None:
                if not self.state.user or not self.state.selected_orders:
                    return
                self.state.accepted_orders = accept_orders(list(self.state.selected_orders), self.state.user)
                self.state.selected_orders.clear()
                self.load_orders()
                self.render()

            self.safe(do_accept)

        def plan_route(_: Any = None) -> None:
            def do_plan() -> None:
                if not self.state.user:
                    return
                response = plan_accepted_orders(
                    DeliveryOptimizeRequest(
                        algorithm="hill_climbing",
                        startId=self.state.shipper_start_id,
                        routingStrategy=self.state.shipper_routing_strategy,
                        scenario=self.state.scenario,
                        debug=True,
                    ),
                    self.state.user,
                )
                self.state.shipper_playback_index = 0
                self.state.arrival_prompted_order_ids.clear()
                self.set_result("shipper-route", "delivery", response)

            self.safe(do_plan)

        order_controls = []
        for order in self.state.orders:
            order_controls.append(
                ft.Container(
                    content=ft.Row(
                        [
                            ft.Checkbox(
                                value=order.id in self.state.selected_orders,
                                active_color=GREEN,
                                on_change=lambda e, oid=order.id: toggle_order(oid, bool(e.control.value)),
                            ),
                            ft.Column(
                                [
                                    text(order.id, 13, TEXT, ft.FontWeight.W_800),
                                    text(
                                        (
                                            f"{order.category}/{order.urgency} | Don tai {order.pickupNodeId} -> Tra tai {order.dropoffNodeId}"
                                            if profile == "on_demand"
                                            else f"{order.category}/{order.urgency} | Kho {self.state.scenario.depot_id} -> Giao {order.dropoffNodeId}"
                                        ),
                                        11,
                                        MUTED,
                                    ),
                                    text(
                                        f"{order.demandKg:.1f} kg | Uu tien {order.priority}/5 | Deadline {order.dueMin} phut",
                                        11,
                                        MUTED,
                                    ),
                                ],
                                spacing=2,
                                expand=True,
                            ),
                            text(f"{order.dueMin}m", 13, RED if order.urgency == "urgent" else GREEN, ft.FontWeight.W_900),
                        ],
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                    bgcolor=PANEL_2,
                    border=ft.border.all(1, LINE),
                    border_radius=4,
                    padding=8,
                )
            )

        accepted_controls = []
        for order in self.state.accepted_orders:
            accepted_controls.append(
                ft.Container(
                    content=ft.Column(
                        [
                            ft.Row(
                                [
                                    text(order.id, 14, TEXT, ft.FontWeight.W_900),
                                    pill(order.category.upper(), "cyan"),
                                    pill(
                                        order.urgency.upper(),
                                        "yellow" if order.urgency == "urgent" else "dark",
                                    ),
                                ],
                                wrap=True,
                                spacing=8,
                            ),
                            text(
                                f"Nhận tại {order.pickupNodeId}  ->  Giao tại {order.dropoffNodeId}",
                                12,
                                GREEN,
                                ft.FontWeight.W_700,
                            ),
                            text(
                                f"Khối lượng: {order.demandKg:.1f} kg | Ưu tiên: {order.priority}/5 | Hạn giao: {order.dueMin} phút",
                                11,
                                MUTED,
                            ),
                        ],
                        spacing=5,
                    ),
                    bgcolor=PANEL_2,
                    border=ft.border.all(1, LINE),
                    border_radius=4,
                    padding=10,
                )
            )

        controls_panel = panel(
            ft.Column(
                [
                    ft.Row([text("ORDERS", 22, TEXT, ft.FontWeight.W_900), pill(f"{len(self.state.orders)} LIVE", "green")]),
                    pill("ON-DEMAND: CURRENT -> PICKUP -> DROPOFF" if profile == "on_demand" else "DEPOT DELIVERY: WAREHOUSE -> STOPS", "cyan"),
                    dropdown(
                        "Live map",
                        str(self.state.active_map_id or ""),
                        self.map_options(),
                        lambda event: self.safe(lambda: self.choose_map(int(event.control.value))),
                    )
                    if self.state.maps
                    else ft.Container(height=0),
                    dropdown(
                        "Category",
                        self.state.category_filter,
                        category_options,
                        update_category,
                    ),
                    dropdown(
                        "Urgency",
                        self.state.urgency_filter,
                        [("all", "Tat ca gap"), ("urgent", "Gap"), ("normal", "Thuong"), ("low", "Thap")],
                        update_urgency,
                    ),
                    ft.Container(
                        content=ft.ListView(order_controls, spacing=8, auto_scroll=False),
                        height=330,
                        bgcolor=INK,
                        padding=8,
                        border_radius=4,
                    ),
                    dropdown(
                        "Vi tri hien tai",
                        self.state.shipper_start_id,
                        [
                            (node.id, f"{node.id} - {node.name}")
                            for node in self.state.scenario.nodes
                            if profile == "on_demand" and node.type in {"intersection", "landmark"}
                        ]
                        or [(self.state.scenario.depot_id, self.state.scenario.depot_id)],
                        lambda event: self.set_field("shipper_start_id", event.control.value),
                    ),
                    dropdown(
                        "Chien luoc giao hang",
                        self.state.shipper_routing_strategy,
                        [
                            ("nearest_neighbor", "Diem gan nhat tiep theo"),
                            ("global_optimization", "Toi uu toan bo tuyen"),
                        ],
                        lambda event: self.set_field("shipper_routing_strategy", event.control.value),
                    )
                    if profile == "depot_delivery"
                    else ft.Container(height=0),
                    ft.Row(
                        [
                            text("ĐƠN ĐANG THỰC HIỆN", 13, TEXT, ft.FontWeight.W_900),
                            pill(str(len(self.state.accepted_orders)), "green"),
                        ],
                        spacing=8,
                    ),
                    ft.Container(
                        content=(
                            ft.ListView(accepted_controls, spacing=8)
                            if accepted_controls
                            else ft.Row(
                                [
                                    ft.Icon(ft.Icons.INBOX_OUTLINED, color=MUTED, size=18),
                                    text("Chưa nhận đơn nào.", 12, MUTED),
                                ]
                            )
                        ),
                        height=190 if accepted_controls else 48,
                        bgcolor=INK,
                        padding=8,
                        border_radius=4,
                    ),
                    ft.Row(
                        [
                            outline_button("Nhan don da chon", accept_selected),
                            primary_button("Lap lo trinh", plan_route, ft.Icons.ROUTE),
                        ],
                        wrap=True,
                    ),
                ],
                spacing=12,
            ),
            expand=False,
        )
        return ft.ResponsiveRow(
            [
                ft.Container(controls_panel, col={"xs": 12, "xl": 3}),
                ft.Container(
                    ft.Column(
                        [
                            self.graph_panel(),
                            self.shipper_playback_panel(),
                            ft.ResponsiveRow([self.metrics_panel(), self.comparison_panel()], spacing=12),
                        ],
                        spacing=12,
                    ),
                    col={"xs": 12, "xl": 9},
                ),
            ],
            spacing=12,
            run_spacing=12,
        )

    def defense_view(self) -> ft.Control:
        selected_group = ALGORITHM_GROUPS[self.state.group]
        group_algorithm_values = [value for value, _ in selected_group["algorithms"]]
        if self.state.algorithm not in group_algorithm_values or not self.algorithm_allowed_for_user(self.state.algorithm):
            self.state.algorithm = self.first_allowed_algorithm(self.state.group)

        def set_group(group_key: str) -> None:
            self.stop_auto_run()
            self.state.group_trace_indexes[self.state.group] = self.state.trace_index
            self.state.group = group_key
            self.activate_map_for_group(group_key)
            self.state.algorithm = self.first_allowed_algorithm(group_key)
            self.state.result = self.state.group_results.get(group_key)
            self.state.trace_index = self.state.group_trace_indexes.get(group_key, 0)
            self.render()

        def set_algorithm(algorithm: str) -> None:
            if not self.algorithm_allowed_for_user(algorithm):
                self.notify(f"Thuat toan {algorithm} dang bi tat cho nhom cua ban.", True)
                return
            self.stop_auto_run()
            self.state.algorithm = algorithm
            self.state.group_results.pop(self.state.group, None)
            self.state.group_trace_indexes.pop(self.state.group, None)
            self.state.result = None
            self.state.trace_index = 0
            self.render()

        def run_debug(_: Any = None) -> None:
            self.safe(self.run_lab)

        group_buttons = [outline_button(meta["label"], lambda _, key=key: set_group(key), selected=key == self.state.group) for key, meta in ALGORITHM_GROUPS.items()]
        algorithm_buttons = [
            outline_button(
                label,
                lambda _, value=value: set_algorithm(value),
                icon=None if self.algorithm_allowed_for_user(value) else ft.Icons.LOCK,
                selected=value == self.state.algorithm,
                disabled=not self.algorithm_allowed_for_user(value),
            )
            for value, label in selected_group["algorithms"]
        ]
        node_options = [(node.id, f"{node.id} - {node.name}") for node in (self.state.scenario.nodes if self.state.scenario else [])]
        controls = [
            ft.Row([text("ALGORITHM GROUP", 11, MUTED, ft.FontWeight.W_900), pill(selected_group["short"], "green")]),
            ft.Column(group_buttons, spacing=8),
            dropdown(
                "Live map",
                str(self.state.active_map_id or ""),
                self.map_options(),
                lambda event: self.safe(lambda: self.choose_map(int(event.control.value))),
            )
            if self.state.maps
            else ft.Container(height=0),
            ft.Container(height=1, bgcolor=LINE),
            text("ALGORITHM", 11, MUTED, ft.FontWeight.W_900),
            ft.Column(algorithm_buttons, spacing=8),
        ]
        mode = selected_group["mode"]
        if mode in {"pathfinding", "complex", "adversarial"}:
            controls.extend(
                [
                    ft.Container(height=1, bgcolor=LINE),
                    text("NODES", 11, MUTED, ft.FontWeight.W_900),
                    dropdown("Start node", self.state.start_id, node_options, lambda e: self.set_field("start_id", e.control.value)),
                    dropdown("Goal node", self.state.goal_id, node_options, lambda e: self.set_field("goal_id", e.control.value)),
                ]
            )
        if mode in {"delivery", "csp"}:
            controls.extend(
                [
                    ft.Container(height=1, bgcolor=LINE),
                    text("DELIVERY ENVIRONMENT", 11, MUTED, ft.FontWeight.W_900),
                    dropdown(
                        "Capacity",
                        str(int(self.state.capacity_kg)),
                        [("12", "12 kg"), ("18", "18 kg"), ("22", "22 kg"), ("30", "30 kg")],
                        lambda e: self.set_field("capacity_kg", float(e.control.value)),
                    ),
                ]
            )
        if mode == "csp":
            controls.append(
                ft.TextField(
                    label="Order IDs",
                    value=self.state.csp_order_ids,
                    hint_text="O4 or O4,O2",
                    on_change=lambda e: self.set_field("csp_order_ids", e.control.value, rerender=False),
                    border_color=LINE,
                    focused_border_color=GREEN,
                    bgcolor=PANEL_2,
                    color=TEXT,
                )
            )
        if mode == "complex":
            controls.extend(
                [
                    dropdown(
                        "Hidden event",
                        self.state.hidden_event,
                        [("accident", "Hidden accident"), ("rain", "Hidden rain"), ("peak_hour", "Hidden peak hour")],
                        lambda e: self.set_field("hidden_event", e.control.value),
                    ),
                    dropdown(
                        "Sensor radius",
                        str(self.state.sensor_radius),
                        [("0", "Current node"), ("1", "1 graph hop"), ("2", "2 graph hops"), ("3", "3 graph hops")],
                        lambda e: self.set_field("sensor_radius", int(e.control.value)),
                    ),
                ]
            )
        if mode == "adversarial":
            controls.extend(
                [
                    dropdown(
                        "Disruption budget",
                        str(self.state.disruption_budget),
                        [("1", "Block up to 1 edge"), ("2", "Block up to 2 edges")],
                        lambda e: self.set_field("disruption_budget", int(e.control.value)),
                    ),
                    text("MAX chon route; MIN chon disruption worst-case.", 11, MUTED),
                ]
            )
        run_button = (
            primary_button(f"RUN {self.state.algorithm.upper()}", run_debug, ft.Icons.PLAY_ARROW)
            if self.algorithm_allowed_for_user(self.state.algorithm)
            else outline_button(f"RUN {self.state.algorithm.upper()}", icon=ft.Icons.LOCK, disabled=True)
        )
        controls.extend([ft.Container(height=1, bgcolor=LINE), text("CONTROLS", 11, MUTED, ft.FontWeight.W_900), run_button])
        lab_controls = panel(ft.Column(controls, spacing=12), padding=14)
        return ft.ResponsiveRow(
            [
                ft.Container(ft.Column([lab_controls, self.metrics_panel()], spacing=12), col={"xs": 12, "xl": 3}),
                ft.Container(
                    ft.Column([self.graph_panel(), self.timeline_panel(), self.comparison_panel()], spacing=12),
                    col={"xs": 12, "xl": 9},
                ),
            ],
            spacing=12,
            run_spacing=12,
        )

    def admin_view(self) -> ft.Control:
        if not self.state.permissions:
            self.state.permissions = list_permissions()
        if not self.state.maps:
            self.load_map_catalog()

        def toggle(permission: PermissionRow) -> None:
            def do_toggle() -> None:
                updated = update_permission(
                    permission.shipperGroup,
                    permission.algorithmGroup,
                    permission.algorithmName,
                    not permission.enabled,
                )
                self.state.permissions = [
                    updated
                    if item.shipperGroup == updated.shipperGroup and item.algorithmName == updated.algorithmName
                    else item
                    for item in self.state.permissions
                ]
                self.render()

            self.safe(do_toggle)

        def reset_map_editor() -> None:
            self.state.map_editor_id = None
            self.state.map_editor_name = ""
            self.state.map_editor_description = ""
            self.state.map_editor_group = self.current_map_group()
            self.state.map_editor_is_default = False
            self.render()

        def edit_map(item: MapSummary) -> None:
            self.state.map_editor_id = item.id
            self.state.map_editor_name = item.name
            self.state.map_editor_description = item.description
            self.state.map_editor_group = item.algorithmGroup
            self.state.map_editor_is_default = item.isDefault
            self.render()

        def save_map(_: Any = None) -> None:
            def do_save() -> None:
                if self.state.map_editor_id is None:
                    create_map(
                        MapCreateRequest(
                            name=self.state.map_editor_name or "New map",
                            description=self.state.map_editor_description,
                            algorithmGroup=self.state.map_editor_group,
                            isDefault=self.state.map_editor_is_default,
                            scenario=self.state.scenario or load_osm_cached_scenario(),
                        )
                    )
                else:
                    update_map(
                        self.state.map_editor_id,
                        MapPatchRequest(
                            name=self.state.map_editor_name or "Untitled map",
                            description=self.state.map_editor_description,
                            algorithmGroup=self.state.map_editor_group,
                            isDefault=self.state.map_editor_is_default,
                        ),
                    )
                self.load_map_catalog()
                self.activate_map_for_group(self.current_map_group())
                self.state.map_editor_id = None
                self.render()

            self.safe(do_save)

        def set_default_map(item: MapSummary) -> None:
            def do_set_default() -> None:
                update_map(item.id, MapPatchRequest(isDefault=True))
                self.load_map_catalog()
                self.activate_map_for_group(self.current_map_group())
                self.render()

            self.safe(do_set_default)

        def remove_map(item: MapSummary) -> None:
            def do_remove() -> None:
                delete_map(item.id)
                self.load_map_catalog()
                if self.state.active_map_id == item.id:
                    self.state.selected_map_ids.pop(self.current_map_group(), None)
                self.activate_map_for_group(self.current_map_group())
                self.render()

            self.safe(do_remove)

        cards = []
        for permission in self.state.permissions:
            cards.append(
                ft.Container(
                    content=ft.Column(
                        [
                            ft.Row(
                                [
                                    ft.Column(
                                        [
                                            text(permission.shipperGroup.upper(), 20, TEXT, ft.FontWeight.W_900),
                                            text(f"{permission.algorithmGroup} / {permission.algorithmName}", 12, MUTED),
                                        ],
                                        expand=True,
                                    ),
                                    ft.Switch(
                                        value=permission.enabled,
                                        active_color=GREEN,
                                        on_change=lambda _, item=permission: toggle(item),
                                    ),
                                ]
                            ),
                            text("Enabled" if permission.enabled else "Disabled", 12, GREEN if permission.enabled else MUTED, ft.FontWeight.W_900),
                        ],
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    ),
                    bgcolor=PANEL_2,
                    border=ft.border.all(1, LINE),
                    border_radius=4,
                    padding=14,
                    col={"xs": 12, "md": 6, "xxl": 4},
                    height=132,
                )
            )
        map_cards = []
        for item in self.state.maps:
            map_cards.append(
                ft.Container(
                    content=ft.Column(
                        [
                            ft.Row(
                                [
                                    ft.Column(
                                        [
                                            text(item.name, 16, TEXT, ft.FontWeight.W_900),
                                            text(f"{item.algorithmGroup} | {item.nodeCount} nodes | {item.edgeCount} edges", 11, MUTED),
                                        ],
                                        expand=True,
                                    ),
                                    ft.Switch(
                                        value=item.isDefault,
                                        active_color=GREEN,
                                        on_change=lambda _, map_item=item: set_default_map(map_item),
                                    ),
                                ],
                                vertical_alignment=ft.CrossAxisAlignment.START,
                            ),
                            text(item.description or "-", 11, MUTED),
                            ft.Row(
                                [
                                    outline_button("Sua", lambda _, map_item=item: edit_map(map_item), ft.Icons.EDIT),
                                    outline_button("Xoa", lambda _, map_item=item: remove_map(map_item), ft.Icons.DELETE),
                                ],
                                wrap=True,
                            ),
                        ],
                        spacing=8,
                    ),
                    bgcolor=PANEL_2,
                    border=ft.border.all(1, GREEN if item.id == self.state.active_map_id else LINE),
                    border_radius=4,
                    padding=12,
                    col={"xs": 12, "md": 6, "xxl": 4},
                    height=160,
                )
            )
        map_group_options = [(key, meta["label"]) for key, meta in ALGORITHM_GROUPS.items()] + [("shipper", "Shipper Dispatch")]
        map_editor = panel(
            ft.Column(
                [
                    ft.Row(
                        [
                            text("Map Library", 20, TEXT, ft.FontWeight.W_900),
                            ft.Icon(ft.Icons.MAP, color=GREEN),
                        ],
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    ),
                    ft.TextField(
                        label="Map name",
                        value=self.state.map_editor_name,
                        on_change=lambda e: self.set_field("map_editor_name", e.control.value, rerender=False),
                        border_color=LINE,
                        focused_border_color=GREEN,
                        bgcolor=PANEL_2,
                        color=TEXT,
                    ),
                    ft.TextField(
                        label="Description",
                        value=self.state.map_editor_description,
                        on_change=lambda e: self.set_field("map_editor_description", e.control.value, rerender=False),
                        border_color=LINE,
                        focused_border_color=GREEN,
                        bgcolor=PANEL_2,
                        color=TEXT,
                    ),
                    dropdown(
                        "Algorithm group",
                        self.state.map_editor_group,
                        map_group_options,
                        lambda event: self.set_field("map_editor_group", event.control.value),
                    ),
                    ft.Switch(
                        label="Default map",
                        value=self.state.map_editor_is_default,
                        active_color=GREEN,
                        on_change=lambda event: self.set_field("map_editor_is_default", bool(event.control.value), rerender=False),
                    ),
                    ft.Row(
                        [
                            primary_button(
                                "Tao map" if self.state.map_editor_id is None else "Luu map",
                                save_map,
                                ft.Icons.SAVE,
                            ),
                            outline_button("Nhap moi", lambda _: reset_map_editor(), ft.Icons.ADD),
                        ],
                        wrap=True,
                    ),
                ],
                spacing=12,
            ),
            dark=True,
        )
        enabled = len([item for item in self.state.permissions if item.enabled])
        summary = panel(
            ft.Column(
                [
                    ft.Row([text("Audit Summary", 20, TEXT, ft.FontWeight.W_900), ft.Icon(ft.Icons.SHIELD, color=GREEN)]),
                    self.dark_stat("Enabled policies", f"{enabled} / {len(self.state.permissions)}"),
                    self.dark_stat("Restricted algorithms", str(len(self.state.permissions) - enabled)),
                    self.dark_stat("Mode", "Defense ready"),
                ],
                spacing=12,
            ),
            dark=True,
        )
        return ft.ResponsiveRow(
            [
                ft.Container(
                    ft.Column(
                        [
                            ft.ResponsiveRow(cards, spacing=12, run_spacing=12),
                            ft.Container(height=1, bgcolor=LINE),
                            ft.Row([text("MAPS", 18, TEXT, ft.FontWeight.W_900), pill(str(len(self.state.maps)), "green")]),
                            ft.ResponsiveRow(map_cards, spacing=12, run_spacing=12),
                        ],
                        spacing=12,
                    ),
                    col={"xs": 12, "xl": 9},
                ),
                ft.Container(ft.Column([summary, map_editor], spacing=12), col={"xs": 12, "xl": 3}),
            ],
            spacing=12,
            run_spacing=12,
        )

    def dark_stat(self, label: str, value: str) -> ft.Control:
        return ft.Container(
            ft.Column([text(label.upper(), 11, MUTED, ft.FontWeight.W_700), text(value, 24, TEXT, ft.FontWeight.W_900)], spacing=4),
            bgcolor=INK,
            border=ft.border.all(1, LINE),
            border_radius=4,
            padding=14,
        )

    def set_field(self, key: str, value: Any, rerender: bool = True) -> None:
        setattr(self.state, key, value)
        if rerender:
            self.render()

    def set_result(self, label: str, mode: str, response: AlgorithmResponse) -> None:
        self.state.result = response
        self.state.trace_index = 0
        if self.state.workspace == "defense":
            self.state.group_results[self.state.group] = response
            self.state.group_trace_indexes[self.state.group] = 0
        self.stop_auto_run()
        self.stop_shipper_playback()
        self.state.comparisons = [ComparisonRow(label, mode, response), *self.state.comparisons][:8]
        self.render()

    def stop_auto_run(self) -> None:
        self.state.auto_run = False
        self.state.auto_run_token += 1

    def choose_trace_step(self, index: int) -> None:
        result = self.state.result
        if not result or not result.traceSteps:
            return
        self.state.trace_index = max(0, min(len(result.traceSteps) - 1, index))
        if self.state.workspace == "defense":
            self.state.group_trace_indexes[self.state.group] = self.state.trace_index
        self.render()

    def step_trace(self, delta: int = 1) -> None:
        result = self.state.result
        if not result or not result.traceSteps:
            return
        next_index = max(0, min(len(result.traceSteps) - 1, self.state.trace_index + delta))
        self.state.trace_index = next_index
        if next_index >= len(result.traceSteps) - 1:
            self.stop_auto_run()
        if self.state.workspace == "defense":
            self.state.group_trace_indexes[self.state.group] = self.state.trace_index
        self.render()

    def start_auto_run(self) -> None:
        result = self.state.result
        if not result or not result.traceSteps:
            return
        if self.state.trace_index >= len(result.traceSteps) - 1:
            self.state.trace_index = 0
        self.state.auto_run = True
        self.state.auto_run_token += 1
        token = self.state.auto_run_token
        self.render()
        self.page.run_task(self.auto_run_trace, token)

    async def auto_run_trace(self, token: int) -> None:
        while self.state.auto_run and token == self.state.auto_run_token:
            result = self.state.result
            if not result or not result.traceSteps or self.state.trace_index >= len(result.traceSteps) - 1:
                self.stop_auto_run()
                self.render()
                return
            await asyncio.sleep(0.8)
            if not self.state.auto_run or token != self.state.auto_run_token:
                return
            self.state.trace_index += 1
            if self.state.workspace == "defense":
                self.state.group_trace_indexes[self.state.group] = self.state.trace_index
            if self.state.trace_index >= len(result.traceSteps) - 1:
                self.stop_auto_run()
            self.render()

    def stop_shipper_playback(self) -> None:
        self.state.shipper_playback_auto = False
        self.state.shipper_playback_token += 1

    def step_shipper_playback(self, delta: int = 1) -> None:
        path = self.state.result.path if self.state.result else []
        if len(path) < 2:
            return
        self.state.shipper_playback_index = max(
            0,
            min(len(path) - 1, self.state.shipper_playback_index + delta),
        )
        if self.state.shipper_playback_index >= len(path) - 1:
            self.stop_shipper_playback()
        self.render()
        self.maybe_prompt_delivery_confirmation()

    def start_shipper_playback(self) -> None:
        path = self.state.result.path if self.state.result else []
        if len(path) < 2:
            return
        if self.state.shipper_playback_index >= len(path) - 1:
            self.state.shipper_playback_index = 0
        self.state.shipper_playback_auto = True
        self.state.shipper_playback_token += 1
        token = self.state.shipper_playback_token
        self.render()
        self.page.run_task(self.auto_run_shipper_route, token)

    async def auto_run_shipper_route(self, token: int) -> None:
        while self.state.shipper_playback_auto and token == self.state.shipper_playback_token:
            path = self.state.result.path if self.state.result else []
            if len(path) < 2 or self.state.shipper_playback_index >= len(path) - 1:
                self.stop_shipper_playback()
                self.render()
                return
            await asyncio.sleep(0.7)
            if not self.state.shipper_playback_auto or token != self.state.shipper_playback_token:
                return
            self.state.shipper_playback_index += 1
            if self.state.shipper_playback_index >= len(path) - 1:
                self.stop_shipper_playback()
            self.render()
            if self.maybe_prompt_delivery_confirmation():
                return

    def delivery_leg_at_playback_index(self, playback_index: int) -> dict[str, Any] | None:
        if not self.state.result:
            return None
        end_index = 0
        for leg in self.state.result.metrics.get("routeLegs", []):
            end_index += max(0, len(leg.get("path", [])) - 1)
            if end_index == playback_index and leg.get("kind") in {"serve_order", "warehouse_delivery"}:
                return leg
        return None

    def route_leg_at_playback_index(self, playback_index: int) -> dict[str, Any] | None:
        if not self.state.result:
            return None
        end_index = 0
        previous_leg = None
        for leg in self.state.result.metrics.get("routeLegs", []):
            segment_count = max(0, len(leg.get("path", [])) - 1)
            start_index = end_index
            end_index += segment_count
            if segment_count and start_index <= playback_index <= end_index:
                return leg
            previous_leg = leg
        return previous_leg

    def order_for_route_leg(self, leg: dict[str, Any] | None):
        if not leg:
            return None
        order_id = str(leg.get("orderId", ""))
        return next((item for item in self.state.accepted_orders if item.id == order_id), None)

    def pickup_icon_src(self, category: str | None) -> str:
        normalized = (category or "").lower()
        if normalized in {"drink", "beverage", "water"}:
            return MAP_ICONS["pickup_drink"]
        if normalized == "food":
            return MAP_ICONS["pickup_food"]
        if normalized == "parcel":
            return MAP_ICONS["pickup_parcel"]
        if normalized == "grocery":
            return MAP_ICONS["pickup_cargo"]
        return MAP_ICONS["pickup_cargo"]

    def vehicle_icon_src(self, leg: dict[str, Any] | None) -> str:
        kind = str((leg or {}).get("kind", ""))
        if kind in {"warehouse_delivery", "transport_to_warehouse"}:
            return MAP_ICONS["transport_truck"]
        return MAP_ICONS["shipper_bike"]

    def maybe_prompt_delivery_confirmation(self) -> bool:
        leg = self.delivery_leg_at_playback_index(self.state.shipper_playback_index)
        if not leg:
            return False
        order_id = str(leg.get("orderId", ""))
        if not order_id or order_id in self.state.arrival_prompted_order_ids:
            return False
        order = next((item for item in self.state.accepted_orders if item.id == order_id), None)
        if order is None:
            return False

        self.stop_shipper_playback()
        self.state.arrival_prompted_order_ids.add(order_id)

        def close_dialog() -> None:
            dialog.open = False
            self.page.close(dialog)

        def postpone(_: Any = None) -> None:
            self.state.arrival_prompted_order_ids.discard(order_id)
            close_dialog()
            self.page.update()

        def confirm(_: Any = None) -> None:
            def do_complete() -> None:
                if not self.state.user:
                    return
                complete_order(order_id, self.state.user)
                close_dialog()
                self.state.accepted_orders = [item for item in self.state.accepted_orders if item.id != order_id]
                self.state.orders = [item for item in self.state.orders if item.id != order_id]
                self.state.selected_orders.discard(order_id)
                self.state.arrival_prompted_order_ids.discard(order_id)
                self.load_orders()
                self.notify(f"Đơn {order_id} đã giao thành công.")
                self.render()

            self.safe(do_complete)

        dialog = ft.AlertDialog(
            modal=True,
            title=text(f"Đã đến điểm giao {order.dropoffNodeId}", 18, TEXT, ft.FontWeight.W_900),
            content=ft.Column(
                [
                    text(f"Đơn {order.id} | {order.category}/{order.urgency}", 13, GREEN, ft.FontWeight.W_800),
                    text(
                        f"Nhận: {order.pickupNodeId}  ->  Giao: {order.dropoffNodeId}",
                        12,
                        TEXT,
                    ),
                    text(
                        f"Khối lượng {order.demandKg:.1f} kg | Hạn giao {order.dueMin} phút",
                        12,
                        MUTED,
                    ),
                    text("Chỉ xác nhận khi khách đã nhận hàng.", 12, YELLOW, ft.FontWeight.W_700),
                ],
                tight=True,
                spacing=8,
            ),
            actions=[
                outline_button("Khách chưa nhận", postpone),
                primary_button("Xác nhận giao thành công", confirm, ft.Icons.CHECK_CIRCLE),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        self.page.open(dialog)
        return True

    def shipper_playback_panel(self) -> ft.Control:
        result = self.state.result
        if not result or len(result.path) < 2:
            return panel(
                ft.Row(
                    [
                        ft.Icon(ft.Icons.PLAY_CIRCLE_OUTLINE, color=GREEN),
                        text("Lap lo trinh de phat lai tung chieu di tren graph.", 12, MUTED),
                    ],
                    spacing=10,
                )
            )
        last_index = len(result.path) - 1
        current_index = min(self.state.shipper_playback_index, last_index)
        current_node = result.path[current_index]
        next_node = result.path[current_index + 1] if current_index < last_index else "DONE"
        progress = current_index / last_index if last_index else 1
        return panel(
            ft.Column(
                [
                    ft.Row(
                        [
                            text("ROUTE PLAYBACK", 16, TEXT, ft.FontWeight.W_900),
                            pill(f"{current_index}/{last_index} EDGES", "green"),
                            text(f"{current_node} -> {next_node}", 12, YELLOW, ft.FontWeight.W_800),
                        ],
                        wrap=True,
                        spacing=10,
                    ),
                    ft.ProgressBar(value=progress, color=GREEN, bgcolor=LINE, height=5),
                    ft.Row(
                        [
                            ft.IconButton(
                                ft.Icons.REPLAY,
                                tooltip="Phat lai tu dau",
                                icon_color=MUTED,
                                on_click=lambda _: self.set_shipper_playback_index(0),
                            ),
                            outline_button("Canh tiep theo", lambda _: self.step_shipper_playback(), ft.Icons.SKIP_NEXT),
                            primary_button(
                                "Dung playback" if self.state.shipper_playback_auto else "Auto playback",
                                lambda _: self.stop_and_render_shipper_playback()
                                if self.state.shipper_playback_auto
                                else self.start_shipper_playback(),
                                ft.Icons.PAUSE if self.state.shipper_playback_auto else ft.Icons.PLAY_ARROW,
                            ),
                        ],
                        wrap=True,
                    ),
                ],
                spacing=10,
            )
        )

    def set_shipper_playback_index(self, index: int) -> None:
        self.stop_shipper_playback()
        self.state.shipper_playback_index = index
        self.render()

    def stop_and_render_shipper_playback(self) -> None:
        self.stop_shipper_playback()
        self.render()

    def current_map_group(self) -> str:
        return "shipper" if self.state.workspace == "shipper" else self.state.group

    def map_url(self) -> str:
        params: dict[str, str] = {"group": self.current_map_group()}
        if self.state.active_map_id:
            params["mapId"] = str(self.state.active_map_id)
        if self.state.algorithm:
            params["algorithm"] = self.state.algorithm
        if self.state.result and self.state.result.path:
            params["path"] = ",".join(self.state.result.path)
            route_legs = self.state.result.metrics.get("routeLegs", [])
            if route_legs:
                params["legs"] = json.dumps(route_legs, ensure_ascii=False, separators=(",", ":"))
                params["active"] = str(self.active_route_leg_index())
                params["orders"] = json.dumps(
                    [
                        {
                            "id": order.id,
                            "category": order.category,
                            "pickupNodeId": order.pickupNodeId,
                            "dropoffNodeId": order.dropoffNodeId,
                        }
                        for order in self.state.accepted_orders
                    ],
                    ensure_ascii=False,
                    separators=(",", ":"),
                )
        if self.state.start_id:
            params["start"] = self.state.start_id
        if self.state.goal_id:
            params["goal"] = self.state.goal_id
        query = urlencode(params)
        return f"/map?{query}" if query else "/map"

    def active_route_leg_index(self) -> int:
        if not self.state.result:
            return 0
        route_legs = self.state.result.metrics.get("routeLegs", [])
        end_index = 0
        for index, leg in enumerate(route_legs):
            end_index += max(0, len(leg.get("path", [])) - 1)
            if self.state.shipper_playback_index <= end_index:
                return index
        return max(0, len(route_legs) - 1)

    def open_map(self, _: Any = None) -> None:
        self.page.launch_url(self.map_url(), web_window_name="_self")

    def run_lab(self) -> None:
        if not self.state.scenario or not self.state.user:
            return
        if not self.algorithm_allowed_for_user(self.state.algorithm):
            raise HTTPException(
                status_code=403,
                detail=f"Thuat toan {self.state.algorithm} dang bi tat cho nhom cua ban.",
            )
        group = ALGORITHM_GROUPS[self.state.group]
        mode = group["mode"]
        if mode == "pathfinding":
            response = run_pathfinding(
                PathfindingRequest(
                    algorithm=self.state.algorithm,
                    startId=self.state.start_id,
                    goalId=self.state.goal_id,
                    scenario=self.state.scenario,
                    debug=True,
                ),
                self.state.user,
            )
        elif mode == "delivery":
            response = optimize_delivery(
                DeliveryOptimizeRequest(
                    algorithm=self.state.algorithm,
                    capacityKg=self.state.capacity_kg,
                    scenario=self.state.scenario,
                    debug=True,
                ),
                self.state.user,
            )
        elif mode == "csp":
            response = solve_csp(
                CspSolveRequest(
                    algorithm=self.state.algorithm,
                    orderIds=[part.strip() for part in self.state.csp_order_ids.split(",") if part.strip()],
                    capacityKg=self.state.capacity_kg,
                    scenario=self.state.scenario,
                    debug=True,
                ),
                self.state.user,
            )
        elif mode == "complex":
            response = run_complex_search(
                ComplexSearchRequest(
                    algorithm=self.state.algorithm,
                    startId=self.state.start_id,
                    goalId=self.state.goal_id,
                    sensorRadius=self.state.sensor_radius,
                    hiddenEvent=self.state.hidden_event,
                    scenario=self.state.scenario,
                    debug=True,
                ),
                self.state.user,
            )
        elif mode == "adversarial":
            response = run_adversarial_search(
                AdversarialSearchRequest(
                    algorithm=self.state.algorithm,
                    startId=self.state.start_id,
                    goalId=self.state.goal_id,
                    disruptionBudget=self.state.disruption_budget,
                    scenario=self.state.scenario,
                    debug=True,
                ),
                self.state.user,
            )
        else:
            return
        self.set_result(self.state.algorithm, mode, response)

    def route_edge_indexes(self, route_edges: list[tuple[str, str]], source: str, target: str) -> list[int]:
        return [
            index
            for index, (route_source, route_target) in enumerate(route_edges)
            if {route_source, route_target} == {source, target}
        ]

    def playback_edge_style(
        self,
        matching_indexes: list[int],
        playback_index: int,
        is_playback: bool,
    ) -> tuple[str, float, float]:
        if not is_playback:
            return (GREEN, 3, 1) if matching_indexes else ("#334152", 1.5, 0.65)

        completed = any(index < playback_index for index in matching_indexes)
        active_edge = playback_index in matching_indexes
        if active_edge:
            return YELLOW, 4, 1
        if completed:
            return GREEN, 3, 1
        if matching_indexes:
            return "#304C43", 2, 0.55
        return "#334152", 1.5, 0.65

    def playback_arrow_offset(self, occurrence: int) -> int:
        if occurrence == 0:
            return 0
        return 7 * ((occurrence + 1) // 2) * (1 if occurrence % 2 else -1)

    def graph_panel(self) -> ft.Control:
        scenario = self.visible_scenario()
        result = self.state.result
        map_group = self.current_map_group()
        map_style = ALGORITHM_MAP_STYLES.get(map_group, ALGORITHM_MAP_STYLES["informed"])
        active_step = self.active_step()
        full_path = result.path if result else []
        is_shipper_playback = self.state.workspace == "shipper" and len(full_path) > 1
        is_debug_trace = bool(active_step and result and result.traceSteps and not is_shipper_playback)
        suppress_highlights = bool(active_step and active_step.debugData.get("suppressHighlights"))
        debug_route_complete = bool(
            is_debug_trace
            and not suppress_highlights
            and full_path
            and (
                active_step.phase == "goal_found"
                or active_step.debugData.get("complete") is True
                or self.state.trace_index >= len(result.traceSteps) - 1
            )
        )
        playback_index = min(self.state.shipper_playback_index, len(full_path) - 1) if is_shipper_playback else 0
        if is_shipper_playback:
            display_path = full_path[: playback_index + 1]
        elif is_debug_trace:
            display_path = full_path if debug_route_complete else []
        else:
            display_path = full_path
        path = set(display_path)
        if is_debug_trace:
            visited = set() if suppress_highlights else set(active_step.visitedNodes)
            frontier = set() if suppress_highlights else set(active_step.frontier)
            current = None if suppress_highlights else active_step.currentNode
        else:
            visited = set(result.visitedNodes if result else [])
            frontier = set()
            current = full_path[playback_index] if is_shipper_playback else None
        active_delivery_leg = self.route_leg_at_playback_index(playback_index) if is_shipper_playback else None
        xs = [node.x for node in scenario.nodes]
        ys = [node.y for node in scenario.nodes]
        min_x, max_x = min(xs), max(xs)
        min_y, max_y = min(ys), max(ys)

        def coordinates(node_id: str) -> fmap.MapLatitudeLongitude:
            node = next(item for item in scenario.nodes if item.id == node_id)
            if node.lat is not None and node.lng is not None:
                return fmap.MapLatitudeLongitude(node.lat, node.lng)
            # Demo nodes are projected into HCM because the legacy graph stores canvas coordinates, not GPS coordinates.
            lng = 106.575 + ((node.x - min_x) / max(1, max_x - min_x)) * (106.845 - 106.575)
            lat = 10.895 - ((node.y - min_y) / max(1, max_y - min_y)) * (10.895 - 10.695)
            return fmap.MapLatitudeLongitude(lat, lng)

        base_lines = []
        for edge in scenario.edges:
            base_lines.append(
                fmap.PolylineMarker(
                    coordinates=[coordinates(edge.source), coordinates(edge.target)],
                    color=RED if edge.blocked else "#607287",
                    stroke_width=4 if edge.blocked else 2,
                )
            )

        route_lines = []
        route_source = display_path
        visible_route_edges = list(zip(route_source, route_source[1:]))
        for index, (source, target) in enumerate(visible_route_edges):
            if is_debug_trace:
                color, width = map_style["route"], 6
            elif is_shipper_playback:
                color = map_style["route"] if index < playback_index else map_style["frontier"] if index == playback_index else "#304C43"
                width = 6 if index <= playback_index else 3
            else:
                color, width = map_style["route"], 6
            route_lines.append(
                fmap.PolylineMarker(
                    coordinates=[coordinates(source), coordinates(target)],
                    color=color,
                    stroke_width=width,
                    border_color="#07110C",
                    border_stroke_width=1,
                )
            )

        preview_path = []
        if is_debug_trace and not suppress_highlights and not debug_route_complete:
            preview_path = active_step.previewPath or active_step.candidatePath
        preview_lines = []
        for source, target in zip(preview_path, preview_path[1:]):
            preview_lines.append(
                fmap.PolylineMarker(
                    coordinates=[coordinates(source), coordinates(target)],
                    color=map_style["preview"],
                    stroke_width=2.5,
                    border_stroke_width=0,
                )
            )

        markers = []

        def image_marker(node_id: str | None, src: str, tooltip: str, size: int = 48) -> None:
            if not node_id or not any(node.id == node_id for node in scenario.nodes):
                return
            markers.append(
                fmap.Marker(
                    coordinates=coordinates(node_id),
                    width=size,
                    height=size,
                    content=ft.Container(
                        content=ft.Image(src=src, fit=ft.ImageFit.CONTAIN),
                        width=size,
                        height=size,
                        tooltip=tooltip,
                    ),
                )
            )

        for node in scenario.nodes:
            active = node.id == current or node.id in frontier or node.id in path or node.id in visited
            color = (
                map_style["current"]
                if node.id == current
                else map_style["frontier"]
                if node.id in frontier
                else map_style["route"]
                if node.id in path
                else map_style["visited"]
                if node.id in visited
                else "#18212B"
            )
            size = 32 if node.id == current else 26
            markers.append(
                fmap.Marker(
                    coordinates=coordinates(node.id),
                    width=size,
                    height=size,
                    content=ft.Container(
                    content=text(node.id, 10, INK if active else MUTED, ft.FontWeight.W_900, text_align=ft.TextAlign.CENTER),
                    width=size,
                    height=size,
                    bgcolor=color,
                    border=ft.border.all(1, color if active else LINE_LIGHT),
                    border_radius=size / 2,
                    alignment=ft.alignment.center,
                    tooltip=node.name,
                    ),
                )
            )

        if active_delivery_leg:
            order = self.order_for_route_leg(active_delivery_leg)
            kind = str(active_delivery_leg.get("kind", ""))
            pickup_node_id = (
                order.pickupNodeId
                if order
                else str(active_delivery_leg.get("from") or active_delivery_leg.get("to") or "")
            )
            dropoff_node_id = (
                order.dropoffNodeId
                if order
                else str(active_delivery_leg.get("to") or "")
            )
            category = order.category if order else ""
            if kind == "approach_pickup":
                image_marker(pickup_node_id or active_delivery_leg.get("to"), self.pickup_icon_src(category), "Diem nhan hang", 44)
            elif kind == "serve_order":
                image_marker(pickup_node_id or active_delivery_leg.get("from"), self.pickup_icon_src(category), "Diem nhan hang", 44)
                image_marker(dropoff_node_id or active_delivery_leg.get("to"), MAP_ICONS["dropoff_pin"], "Diem giao hang", 44)
            elif kind in {"warehouse_delivery", "transport_to_warehouse"}:
                image_marker(dropoff_node_id or active_delivery_leg.get("to"), MAP_ICONS["dropoff_pin"], "Diem giao hang", 44)
            image_marker(current or str(active_delivery_leg.get("from") or ""), self.vehicle_icon_src(active_delivery_leg), "Shipper / xe van chuyen", 58)

        map_layers = []
        if self.state.map_tiles_enabled:
            map_layers.append(fmap.TileLayer(url_template="https://tile.openstreetmap.org/{z}/{x}/{y}.png"))
        map_layers.extend(
            [
                fmap.PolylineLayer(polylines=base_lines),
                fmap.PolylineLayer(polylines=preview_lines),
                fmap.PolylineLayer(polylines=route_lines),
                fmap.MarkerLayer(markers=markers),
            ]
        )
        if self.state.map_tiles_enabled:
            map_layers.append(
                fmap.RichAttribution(
                    attributions=[
                        fmap.TextSourceAttribution(
                            text="OpenStreetMap contributors",
                            on_click=lambda event: event.page.launch_url("https://www.openstreetmap.org/copyright"),
                        )
                    ]
                )
            )

        map_ref = ft.Ref[fmap.Map]()
        map_control = fmap.Map(
            ref=map_ref,
            expand=True,
            bgcolor="#07100F" if not self.state.map_tiles_enabled else None,
            initial_center=fmap.MapLatitudeLongitude(10.7769, 106.7009),
            initial_zoom=11.2,
            min_zoom=3,
            max_zoom=19,
            interaction_configuration=fmap.MapInteractionConfiguration(flags=fmap.MapInteractiveFlag.ALL),
            layers=map_layers,
        )

        def toggle_map_tiles(_: Any) -> None:
            self.state.map_tiles_enabled = not self.state.map_tiles_enabled
            self.render()

        def zoom_in(_: Any) -> None:
            if map_ref.current:
                map_ref.current.zoom_in()

        def zoom_out(_: Any) -> None:
            if map_ref.current:
                map_ref.current.zoom_out()

        def reset_view(_: Any) -> None:
            if map_ref.current:
                map_ref.current.move_to(fmap.MapLatitudeLongitude(10.7769, 106.7009), zoom=11.2)

        map_actions = ft.Container(
            content=ft.Column(
                [
                    ft.IconButton(
                        ft.Icons.MAP if self.state.map_tiles_enabled else ft.Icons.GRID_ON,
                        on_click=toggle_map_tiles,
                        tooltip="Tat nen OSM" if self.state.map_tiles_enabled else "Bat nen OSM",
                        bgcolor=GREEN if self.state.map_tiles_enabled else PANEL,
                        icon_color=INK if self.state.map_tiles_enabled else TEXT,
                    ),
                    ft.IconButton(ft.Icons.ADD, on_click=zoom_in, tooltip="Phong to", bgcolor=PANEL, icon_color=TEXT),
                    ft.IconButton(ft.Icons.REMOVE, on_click=zoom_out, tooltip="Thu nho", bgcolor=PANEL, icon_color=TEXT),
                    ft.IconButton(ft.Icons.CENTER_FOCUS_STRONG, on_click=reset_view, tooltip="Dat lai goc nhin", bgcolor=PANEL, icon_color=TEXT),
                    ft.IconButton(ft.Icons.OPEN_IN_FULL, on_click=self.open_map, tooltip="Mo ban do day du", bgcolor=PANEL, icon_color=TEXT),
                ],
                spacing=6,
            ),
            right=12,
            top=12,
        )
        map_mode_badge = ft.Container(
            content=pill(map_style["badge"] if self.state.map_tiles_enabled else "DEBUG MAP", "green" if self.state.map_tiles_enabled else "yellow"),
            left=12,
            top=12,
        )
        graph = ft.Container(
            content=ft.Stack([map_control, map_mode_badge, map_actions], expand=True),
            bgcolor=PANEL,
            border=ft.border.all(1, LINE),
            border_radius=4,
            clip_behavior=ft.ClipBehavior.HARD_EDGE,
            height=405,
        )
        legend = ft.Row(
            [
                self.legend_item("PATH", map_style["route"]),
                self.legend_item("VISITED", map_style["visited"]),
                self.legend_item("FRONTIER", map_style["frontier"]),
                self.legend_item("CURRENT", map_style["current"]),
            ],
            spacing=12,
            wrap=True,
        )
        group_label = ALGORITHM_GROUPS.get(map_group, {}).get("label", "Shipper Dispatch")
        map_summary = self.selected_map_summary()
        map_title = f"BAN DO / {group_label.upper()}"
        if map_summary:
            map_title = f"{map_title} / {map_summary.name.upper()}"
        return panel(
            ft.Column(
                [
                    ft.Row(
                        [
                            text(map_title, 16, TEXT, ft.FontWeight.W_900),
                            ft.Row(
                                [
                                    legend,
                                    outline_button("Toan man hinh", self.open_map, ft.Icons.MAP),
                                ],
                                spacing=10,
                                wrap=True,
                            ),
                        ],
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        wrap=True,
                    ),
                    graph,
                ],
                spacing=12,
            ),
            dark=True,
        )

    def legend_item(self, label: str, color: str) -> ft.Control:
        return ft.Row(
            [
                ft.Container(width=9, height=9, bgcolor=color, border_radius=9),
                text(label, 10, MUTED, ft.FontWeight.W_900),
            ],
            spacing=6,
            tight=True,
        )

    def graph_stat(self, label: str, value: str) -> ft.Control:
        return ft.Container(
            ft.Column([text(label.upper(), 11, MUTED, ft.FontWeight.W_700), text(value, 12, TEXT, ft.FontWeight.W_700)], spacing=4),
            bgcolor=INK,
            border=ft.border.all(1, LINE),
            padding=10,
            border_radius=4,
            col={"xs": 12, "sm": 6, "lg": 3},
        )

    def metrics_panel(self) -> ft.Control:
        result = self.state.result
        if not result:
            body = ft.Column(
                [
                    ft.Row([text("METRICS", 18, TEXT, ft.FontWeight.W_900), pill("IDLE")]),
                    ft.Container(
                        content=ft.Column(
                            [
                                ft.Icon(ft.Icons.INSIGHTS, color=GREEN, size=28),
                                text("Chay thuat toan de xem metrics.", 12, MUTED, text_align=ft.TextAlign.CENTER),
                            ],
                            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                            spacing=8,
                        ),
                        bgcolor=INK,
                        border=ft.border.all(1, LINE),
                        border_radius=4,
                        padding=18,
                        alignment=ft.alignment.center,
                    ),
                ],
                spacing=10,
            )
            return ft.Container(panel(body), col={"xs": 12, "xl": 6})
        metrics = result.metrics
        cards = ft.ResponsiveRow(
            [
                self.metric_card("Runtime", f"{result.runtimeMs} ms"),
                self.metric_card("Visited", str(len(result.visitedNodes))),
                self.metric_card("Distance", f"{metric_value(metrics, 'distanceKm', default='-')} km"),
                self.metric_card("Minutes", str(metric_value(metrics, "totalMinutes", "travelMinutes", "replannedMinutes", default="-"))),
            ],
            spacing=8,
            run_spacing=8,
        )
        kv_rows = []
        for key, value in list(metrics.items())[:12]:
            if isinstance(value, (dict, list)):
                value_text = str(value)[:90] + ("..." if len(str(value)) > 90 else "")
            else:
                value_text = str(value)
            kv_rows.append(ft.Row([text(key, 12, MUTED, ft.FontWeight.W_700, width=140), text(value_text, 12, TEXT, expand=True)], spacing=8))
        body = ft.Column(
            [
                ft.Row([text("METRICS", 18, TEXT, ft.FontWeight.W_900), pill("READY", "green")]),
                text(result.explanation, 13, MUTED),
                cards,
                ft.Column(kv_rows, spacing=6, scroll=ft.ScrollMode.AUTO, height=220),
            ],
            spacing=10,
        )
        return ft.Container(panel(body), col={"xs": 12, "xl": 6})

    def metric_card(self, label: str, value: str) -> ft.Control:
        return ft.Container(
            ft.Column([text(label.upper(), 10, MUTED, ft.FontWeight.W_700), text(value, 18, TEXT, ft.FontWeight.W_900)], spacing=4),
            bgcolor=INK,
            border=ft.border.all(1, LINE),
            border_radius=4,
            padding=10,
            col={"xs": 6, "md": 3},
        )

    def comparison_panel(self) -> ft.Control:
        rows = []
        for index, item in enumerate(self.state.comparisons, start=1):
            metrics = item.response.metrics
            rows.append(
                ft.DataRow(
                    cells=[
                        ft.DataCell(text(str(index), 11)),
                        ft.DataCell(text(item.label, 11)),
                        ft.DataCell(text(item.mode, 11)),
                        ft.DataCell(text(str(metric_value(metrics, "totalMinutes", "travelMinutes", "replannedMinutes", default="-")), 11)),
                        ft.DataCell(text(str(metric_value(metrics, "distanceKm", default="-")), 11)),
                        ft.DataCell(text(str(item.response.runtimeMs), 11)),
                    ]
                )
            )
        table = ft.DataTable(
            columns=[
                ft.DataColumn(text("#", 11, MUTED, ft.FontWeight.W_700)),
                ft.DataColumn(text("Algorithm", 11, MUTED, ft.FontWeight.W_700)),
                ft.DataColumn(text("Mode", 11, MUTED, ft.FontWeight.W_700)),
                ft.DataColumn(text("Minutes", 11, MUTED, ft.FontWeight.W_700)),
                ft.DataColumn(text("Km", 11, MUTED, ft.FontWeight.W_700)),
                ft.DataColumn(text("RT", 11, MUTED, ft.FontWeight.W_700)),
            ],
            rows=rows,
            column_spacing=18,
            heading_row_color=INK,
            border=ft.border.all(1, LINE),
        )
        body = ft.Column(
            [ft.Row([text("COMPARISON TABLE", 18, TEXT, ft.FontWeight.W_900), pill(f"{len(rows)} RUNS")]), table],
            spacing=10,
            scroll=ft.ScrollMode.AUTO,
        )
        return ft.Container(panel(body), col={"xs": 12, "xl": 6})

    def timeline_panel(self) -> ft.Control:
        result = self.state.result
        if not result or not result.traceSteps:
            return panel(
                ft.Column(
                    [
                        ft.Row([text("DEBUG TIMELINE", 18, TEXT, ft.FontWeight.W_900), pill("IDLE")]),
                        ft.Container(
                            content=ft.Column(
                                [ft.Icon(ft.Icons.PSYCHOLOGY, color=GREEN, size=30), text("Chay mot thuat toan de xem timeline.", 13, MUTED)],
                                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                                alignment=ft.MainAxisAlignment.CENTER,
                            ),
                            bgcolor=INK,
                            border=ft.border.all(1, LINE),
                            border_radius=4,
                            height=150,
                            alignment=ft.alignment.center,
                        ),
                    ],
                    spacing=12,
                ),
                dark=True,
            )

        def compact(items: list[str], limit: int = 8) -> str:
            if not items:
                return "-"
            visible = items[:limit]
            suffix = f" +{len(items) - limit}" if len(items) > limit else ""
            return ", ".join(visible) + suffix

        def debug_row(label: str, value: Any) -> ft.Control:
            value_text = compact(value) if isinstance(value, list) else str(value if value is not None else "-")
            if len(value_text) > 180:
                value_text = value_text[:177] + "..."
            return ft.Container(
                content=ft.Row(
                    [
                        text(label, 11, MUTED, ft.FontWeight.W_900, width=125),
                        text(value_text, 11, TEXT, expand=True),
                    ],
                    spacing=10,
                    vertical_alignment=ft.CrossAxisAlignment.START,
                ),
                bgcolor="#101720",
                border=ft.border.all(1, LINE),
                border_radius=4,
                padding=8,
            )

        def step_title(item: Any) -> str:
            return str(item.debugData.get("result") or item.phase)

        def step_subtitle(item: Any) -> str:
            tried = item.debugData.get("triedValue")
            selected = item.debugData.get("selectedVariable")
            if item.debugData.get("traceType") == "csp":
                return str(tried if tried and tried != "-" else selected or item.currentNode or "-")
            return str(item.currentNode or "-")

        rows = []
        for index, item in enumerate(result.traceSteps):
            active = index == self.state.trace_index
            rows.append(
                ft.Container(
                    content=ft.Row(
                        [
                            ft.Container(
                                text(str(index + 1).zfill(2), 11, INK if active else TEXT, ft.FontWeight.W_900),
                                bgcolor=GREEN if active else "#263241",
                                width=34,
                                height=34,
                                alignment=ft.alignment.center,
                                border_radius=4,
                            ),
                            ft.Column([text(step_title(item), 12, TEXT, ft.FontWeight.W_800), text(step_subtitle(item), 11, MUTED)], spacing=1, expand=True),
                            text(str(item.costSoFar), 11, MUTED),
                        ]
                    ),
                    bgcolor="#16202A" if active else INK,
                    border=ft.border.all(1, GREEN if active else LINE),
                    border_radius=4,
                    padding=8,
                    on_click=lambda _, idx=index: self.choose_trace_step(idx),
                )
            )
        active_step = self.active_step()
        is_csp_trace = bool(active_step and active_step.debugData.get("traceType") == "csp")
        at_first = self.state.trace_index <= 0
        at_last = self.state.trace_index >= len(result.traceSteps) - 1
        if is_csp_trace and active_step:
            csp_data = active_step.debugData
            debug_rows = [
                ft.Container(
                    content=ft.Row(
                        [
                            text("CSP FIELD", 11, MUTED, ft.FontWeight.W_900, width=125),
                            text("VALUE", 11, MUTED, ft.FontWeight.W_900, expand=True),
                        ],
                        spacing=10,
                    ),
                    bgcolor=INK,
                    border=ft.border.all(1, LINE),
                    border_radius=4,
                    padding=8,
                ),
                debug_row("bai toan", csp_data.get("concept")),
                debug_row("bien", csp_data.get("selectedVariable")),
                debug_row("mien", csp_data.get("domainValues", [])),
                debug_row("gia tri thu", csp_data.get("triedValue")),
                debug_row("rang buoc", csp_data.get("constraintCheck", [])),
                debug_row("ket luan", csp_data.get("result")),
                debug_row("gan hien tai", csp_data.get("assignment", [])),
                debug_row("don hang", csp_data.get("remainingOrders", [])),
                debug_row("tai trong", f"{csp_data.get('loadKg', 0)} / {csp_data.get('capacityKg', '-')} kg"),
                debug_row("route tam", active_step.candidatePath),
            ]
        else:
            debug_rows = [
                ft.Container(
                    content=ft.Row(
                        [
                            text("FIELD", 11, MUTED, ft.FontWeight.W_900, width=125),
                            text("VALUE", 11, MUTED, ft.FontWeight.W_900, expand=True),
                        ],
                        spacing=10,
                    ),
                    bgcolor=INK,
                    border=ft.border.all(1, LINE),
                    border_radius=4,
                    padding=8,
                ),
                debug_row("step", f"{self.state.trace_index + 1}/{len(result.traceSteps)}"),
                debug_row("phase", active_step.phase if active_step else "-"),
                debug_row("currentNode", active_step.currentNode if active_step else "-"),
                debug_row("previousNode", active_step.previousNode if active_step else "-"),
                debug_row("frontier", active_step.frontier if active_step else []),
                debug_row("visitedNodes", active_step.visitedNodes if active_step else []),
                debug_row("candidatePath", active_step.candidatePath if active_step else []),
                debug_row("previewPath", active_step.previewPath if active_step else []),
                debug_row("costSoFar", round(active_step.costSoFar, 3) if active_step else "-"),
                debug_row("heuristic", round(active_step.heuristic, 3) if active_step else "-"),
            ]
        if active_step and not is_csp_trace:
            debug_rows.extend(debug_row(key, value) for key, value in list(active_step.debugData.items())[:10])
        debug_table = ft.Column(debug_rows, spacing=6)
        def debug_stat(label: str, value: str) -> ft.Control:
            return ft.Container(
                content=ft.Column(
                    [text(label.upper(), 10, MUTED, ft.FontWeight.W_700), text(value, 15, TEXT, ft.FontWeight.W_900)],
                    spacing=4,
                ),
                bgcolor=INK,
                border=ft.border.all(1, LINE),
                border_radius=4,
                padding=10,
                width=160,
            )

        controls_row = ft.Row(
            [
                ft.IconButton(
                    ft.Icons.RESTART_ALT,
                    icon_color=TEXT,
                    tooltip="Reset trace",
                    disabled=at_first,
                    on_click=lambda _: self.choose_trace_step(0),
                ),
                ft.IconButton(
                    ft.Icons.SKIP_PREVIOUS,
                    icon_color=TEXT,
                    tooltip="Previous step",
                    disabled=at_first,
                    on_click=lambda _: self.step_trace(-1),
                ),
                outline_button("Run next step", lambda _: self.step_trace(1), ft.Icons.SKIP_NEXT, selected=False),
                primary_button(
                    "Stop auto" if self.state.auto_run else "Auto run",
                    lambda _: (self.stop_auto_run(), self.render()) if self.state.auto_run else self.start_auto_run(),
                    ft.Icons.PAUSE if self.state.auto_run else ft.Icons.PLAY_ARROW,
                ),
            ],
            spacing=8,
            wrap=True,
        )
        steps_panel = ft.Container(
            content=ft.ListView(rows, spacing=8, auto_scroll=False),
            bgcolor=INK,
            border=ft.border.all(1, LINE),
            border_radius=4,
            padding=8,
            height=306,
            expand=True,
        )
        table_panel = ft.Container(
            content=ft.Column(
                [
                    ft.Row([ft.Icon(ft.Icons.BACKUP_TABLE, color=GREEN, size=18), text("DEBUG TABLE", 14, TEXT, ft.FontWeight.W_900)], spacing=8),
                    debug_table,
                ],
                spacing=8,
            ),
            bgcolor=INK,
            border=ft.border.all(1, LINE),
            border_radius=4,
            padding=10,
            expand=True,
        )
        return panel(
            ft.Column(
                [
                    ft.Row(
                        [
                            text("DEBUG TIMELINE", 18, TEXT, ft.FontWeight.W_900),
                            pill(f"{len(result.traceSteps)} STEPS", "green"),
                            pill("AUTO RUN" if self.state.auto_run else "MANUAL"),
                        ],
                        wrap=True,
                    ),
                    controls_row,
                    ft.Row(
                        [
                            debug_stat("Current step", f"{self.state.trace_index + 1}/{len(result.traceSteps)}"),
                            debug_stat(
                                "Variable" if is_csp_trace else "Current node",
                                str(active_step.debugData.get("selectedVariable", "-") if is_csp_trace and active_step else active_step.currentNode if active_step and active_step.currentNode else "-"),
                            ),
                            debug_stat("Domain" if is_csp_trace else "Frontier", str(len(active_step.frontier) if active_step else 0)),
                            debug_stat(
                                "Load" if is_csp_trace else "Visited",
                                f"{active_step.debugData.get('loadKg', 0)} kg" if is_csp_trace and active_step else str(len(active_step.visitedNodes) if active_step else 0),
                            ),
                        ],
                        spacing=8,
                        wrap=True,
                    ),
                    ft.Row([steps_panel, table_panel], spacing=12, vertical_alignment=ft.CrossAxisAlignment.START),
                    ft.Container(
                        content=text(
                            f"Step {self.state.trace_index + 1}/{len(result.traceSteps)}: {active_step.decisionReason if active_step else ''}",
                            12,
                            TEXT,
                        ),
                        bgcolor=INK,
                        border=ft.border.all(1, LINE),
                        border_radius=4,
                        padding=10,
                    ),
                ],
                spacing=12,
            ),
            dark=True,
        )

    def active_step(self):
        result = self.state.result
        if not result or not result.traceSteps:
            return None
        index = max(0, min(self.state.trace_index, len(result.traceSteps) - 1))
        return result.traceSteps[index]

    def visible_scenario(self) -> Scenario:
        result = self.state.result
        if result:
            updated = result.metrics.get("updatedScenario")
            if isinstance(updated, dict):
                return Scenario(**updated)
        return self.state.scenario or load_osm_cached_scenario()


async def main(page: ft.Page) -> None:
    dashboard = FletDashboard(page)
    dashboard.setup()
