from __future__ import annotations

import random
from typing import Any

from app.algorithms.graph import BLOCKED_COST, find_edge, path_time
from app.algorithms.search import astar
from app.models.schemas import Order, Scenario, TraceStep

DEBUG_TRACE_LIMIT = 300
DEFAULT_CSP_ORDER_IDS = ("O4", "O6", "O8")
DEFAULT_CSP_DEMO_DUE_MIN = 75
ALGORITHM_RULES = {
    "backtracking": "Backtracking thu tung gia tri trong domain va quay lui khi vi pham rang buoc.",
    "forward_checking": "Forward Checking xoa gia tri khong con hop le khoi domain cua bien lien quan.",
    "ac3": "AC-3 duy tri nhat quan cung: moi gia tri cua Xi phai co gia tri ho tro o bien ke tiep.",
    "min_conflicts": "Min-Conflicts bat dau bang assignment day du, roi sua bien dang xung dot.",
}


def csp_default_order_ids(scenario: Scenario) -> list[str]:
    available = {order.id for order in scenario.orders}
    selected = [order_id for order_id in DEFAULT_CSP_ORDER_IDS if order_id in available]
    return selected or [order.id for order in scenario.orders[:3]]


def csp_demo_scenario(scenario: Scenario) -> Scenario:
    demo = scenario.model_copy(deep=True)
    selected = set(csp_default_order_ids(demo))
    for order in demo.orders:
        if order.id in selected:
            order.due_min = max(order.due_min, DEFAULT_CSP_DEMO_DUE_MIN)
    return demo


def csp_order_summaries(scenario: Scenario, order_ids: list[str] | None = None) -> list[dict[str, Any]]:
    selected_ids = order_ids or csp_default_order_ids(scenario)
    order_by_id = {order.id: order for order in scenario.orders}
    node_by_id = {node.id: node for node in scenario.nodes}
    summaries: list[dict[str, Any]] = []
    for order_id in selected_ids:
        order = order_by_id.get(order_id)
        if order is None:
            continue
        pickup_id = order.pickup_node_id or scenario.depot_id
        dropoff_id = order.dropoff_node_id or order.node_id
        pickup = node_by_id.get(pickup_id)
        dropoff = node_by_id.get(dropoff_id)
        summaries.append(
            {
                "id": order.id,
                "category": order.category,
                "pickupId": pickup_id,
                "pickupName": pickup.name if pickup else pickup_id,
                "dropoffId": dropoff_id,
                "dropoffName": dropoff.name if dropoff else dropoff_id,
                "demandKg": order.demand_kg,
                "dueMin": order.due_min,
                "priority": order.priority,
            }
        )
    return summaries


def check_route_constraints(scenario: Scenario, route: list[str], capacity_kg: float | None = None, debug: bool = False) -> dict:
    capacity = capacity_kg or scenario.capacity_kg
    pickups_by_node: dict[str, list] = {}
    dropoffs_by_node: dict[str, list] = {}
    for order in scenario.orders:
        pickups_by_node.setdefault(order.pickup_node_id or scenario.depot_id, []).append(order)
        dropoffs_by_node.setdefault(order.dropoff_node_id or order.node_id, []).append(order)
    violations: list[str] = []
    load = 0.0
    max_load = 0.0
    current_time = 0.0
    carrying: set[str] = set()
    served: set[str] = set()
    blocked_segments: list[str] = []
    trace_steps: list[TraceStep] = []

    def process_node(node_id: str) -> None:
        nonlocal load, max_load, current_time
        for order in pickups_by_node.get(node_id, []):
            if order.id in served or order.id in carrying:
                continue
            if current_time < order.ready_min:
                current_time = order.ready_min
            carrying.add(order.id)
            load += order.demand_kg
            max_load = max(max_load, load)
            if load > capacity:
                violations.append(f"Vuot tai khi nhan {order.id}: {load:.1f}kg / {capacity:.1f}kg.")
        for order in dropoffs_by_node.get(node_id, []):
            if order.id in served:
                continue
            if order.id not in carrying:
                violations.append(f"Don {order.id} duoc giao tai {node_id} truoc khi nhan hang.")
                continue
            if current_time > order.due_min:
                violations.append(f"Don {order.id} giao tre: den phut {current_time:.1f}, han {order.due_min}.")
            carrying.remove(order.id)
            load -= order.demand_kg
            served.add(order.id)
            current_time += order.service_min

    if route:
        process_node(route[0])

    for a, b in zip(route, route[1:]):
        edge = find_edge(scenario, a, b)
        if edge is None:
            violations.append(f"Khong co duong noi {a}-{b}.")
            continue
        if edge.blocked:
            blocked_segments.append(f"{a}-{b}")
        current_time += path_time(scenario, [a, b])
        process_node(b)
        if debug:
            trace_steps.append(
                TraceStep(
                    stepIndex=len(trace_steps),
                    phase="constraint_check",
                    currentNode=b,
                    frontier=[],
                    visitedNodes=route[: route.index(b) + 1] if b in route else [a, b],
                    candidatePath=[a, b],
                    costSoFar=round(current_time, 2),
                    heuristic=0,
                    decisionReason=f"Kiem tra canh {a}-{b}: dang mang {len(carrying)} don, tai {load:.1f}/{capacity:.1f}kg, thoi gian {current_time:.1f}, vi pham hien co {len(violations)}.",
                )
            )

    if carrying:
        violations.append("Con don chua giao: " + ", ".join(sorted(carrying)) + ".")
    if blocked_segments:
        violations.append("Di qua duong bi chan: " + ", ".join(blocked_segments) + ".")
    if path_time(scenario, route) >= BLOCKED_COST:
        violations.append("Lo trinh co chi phi khong kha thi do duong chan hoac thieu canh.")

    return {
        "valid": len(violations) == 0,
        "violations": violations,
        "servedOrders": len(served),
        "loadKg": round(max_load, 2),
        "capacityKg": capacity,
        "totalMinutes": round(current_time, 2),
        "traceSteps": trace_steps,
    }


def solve_delivery_csp(
    scenario: Scenario,
    algorithm: str,
    order_ids: list[str] | None = None,
    capacity_kg: float | None = None,
    debug: bool = False,
) -> dict:
    selected_order_ids = set(order_ids) if order_ids is not None else None
    orders = [order for order in scenario.orders if selected_order_ids is None or order.id in selected_order_ids]
    capacity = capacity_kg or scenario.capacity_kg
    order_by_id = {order.id: order for order in orders}
    node_by_id = {node.id: node for node in scenario.nodes}
    order_summaries = csp_order_summaries(scenario, [order.id for order in orders])
    trace_steps: list[TraceStep] = []
    skipped_trace_steps = 0
    expanded_states = 0
    backtracks = 0
    ac3_revisions = 0
    min_conflict_steps = 0

    def location(order: Order, action: str) -> str:
        return (order.pickup_node_id or scenario.depot_id) if action == "pickup" else (order.dropoff_node_id or order.node_id)

    def travel(current: str, target: str) -> tuple[list[str], float]:
        if current == target:
            return [current], 0.0
        result = astar(scenario, current, target)
        return result.path, result.total_minutes

    def available_actions(picked: set[str], delivered: set[str], load: float) -> list[tuple[str, str]]:
        actions: list[tuple[str, str]] = []
        for order in orders:
            if order.id not in picked and load + order.demand_kg <= capacity:
                actions.append((order.id, "pickup"))
            elif order.id in picked and order.id not in delivered:
                actions.append((order.id, "dropoff"))
        # Dropoffs are tried first because they release capacity and tighten deadline checks early.
        return sorted(
            actions,
            key=lambda item: (
                0 if item[1] == "dropoff" else 1,
                order_by_id[item[0]].due_min,
                -order_by_id[item[0]].priority,
            ),
        )

    def action_label(order_id: str, action: str) -> str:
        order = order_by_id[order_id]
        target = location(order, action)
        verb = "Nhan" if action == "pickup" else "Giao"
        node = node_by_id.get(target)
        suffix = f" ({node.name})" if node else ""
        return f"{verb} {order_id} tai {target}{suffix}"

    def domain_labels(actions: list[tuple[str, str]]) -> list[str]:
        return [action_label(order_id, action) for order_id, action in actions]

    def remaining_orders(picked: set[str], delivered: set[str]) -> list[str]:
        return [
            (
                f"{order.id}: {'da giao' if order.id in delivered else 'dang mang' if order.id in picked else 'chua nhan'} | "
                f"{location(order, 'pickup')} -> {location(order, 'dropoff')} | "
                f"{order.demand_kg:.1f}kg | han {order.due_min}p"
            )
            for order in orders
        ]

    def forward_feasible(current: str, current_time: float, picked: set[str], delivered: set[str]) -> bool:
        for order in orders:
            if order.id in delivered:
                continue
            pickup = order.pickup_node_id or scenario.depot_id
            dropoff = order.dropoff_node_id or order.node_id
            if order.id in picked:
                _, eta = travel(current, dropoff)
            else:
                _, to_pickup = travel(current, pickup)
                _, to_dropoff = travel(pickup, dropoff)
                eta = to_pickup + to_dropoff
            if eta >= BLOCKED_COST or current_time + eta > order.due_min:
                return False
        return True

    def projected_state(
        current: str,
        current_time: float,
        load: float,
        picked: set[str],
        delivered: set[str],
        route: list[str],
        assignment: list[str],
        order_id: str,
        action: str,
    ) -> dict | None:
        order = order_by_id[order_id]
        target = location(order, action)
        segment, travel_minutes = travel(current, target)
        if not segment or travel_minutes >= BLOCKED_COST:
            return None
        next_time = max(current_time + travel_minutes, order.ready_min) if action == "pickup" else current_time + travel_minutes
        if action == "dropoff" and next_time > order.due_min:
            return None
        next_load = load + order.demand_kg if action == "pickup" else load - order.demand_kg
        if next_load > capacity:
            return None
        next_picked = picked | {order_id} if action == "pickup" else set(picked)
        next_delivered = delivered | {order_id} if action == "dropoff" else set(delivered)
        next_route = route + (segment[1:] if route else segment)
        next_assignment = assignment + [f"{action}:{order_id}@{target}"]
        return {
            "target": target,
            "segment": segment,
            "travelMinutes": travel_minutes,
            "time": next_time,
            "load": next_load,
            "picked": next_picked,
            "delivered": next_delivered,
            "route": next_route,
            "assignment": next_assignment,
        }

    def has_arc_support(
        current: str,
        current_time: float,
        load: float,
        picked: set[str],
        delivered: set[str],
        route: list[str],
        assignment: list[str],
        action_value: tuple[str, str],
    ) -> tuple[bool, str]:
        state = projected_state(current, current_time, load, picked, delivered, route, assignment, *action_value)
        label = action_label(*action_value)
        if state is None:
            return False, f"{label}: khong thoa rang buoc don bien."
        if len(state["delivered"]) == len(orders):
            return True, f"{label}: hoan tat assignment nen khong can cung ho tro."
        next_actions = available_actions(state["picked"], state["delivered"], state["load"])
        for next_action in next_actions:
            if projected_state(
                state["target"],
                state["time"],
                state["load"],
                state["picked"],
                state["delivered"],
                state["route"],
                state["assignment"],
                *next_action,
            ) is not None:
                return True, f"{label}: co ho tro tu {action_label(*next_action)}."
        return False, f"{label}: khong co gia tri nao o bien ke tiep lam cung nhat quan."

    def ac3_reduce_actions(
        current: str,
        current_time: float,
        load: float,
        picked: set[str],
        delivered: set[str],
        route: list[str],
        assignment: list[str],
        actions: list[tuple[str, str]],
    ) -> list[tuple[str, str]]:
        nonlocal ac3_revisions
        if algorithm != "ac3":
            return actions
        trace(
            "ac3_queue",
            current,
            route,
            current_time,
            actions,
            assignment,
            "Khoi tao hang doi AC-3 bang cac cung giua bien hien tai va bien tiep theo trong lich pickup/dropoff.",
            load,
            picked,
            delivered,
            result_label="Lap hang doi cung",
            constraint_checks=["Cung (Xi, Xj) nhat quan neu moi gia tri cua Xi co it nhat mot gia tri ho tro o Xj."],
        )
        reduced: list[tuple[str, str]] = []
        removed: list[str] = []
        support_notes: list[str] = []
        for action_value in actions:
            supported, note = has_arc_support(current, current_time, load, picked, delivered, route, assignment, action_value)
            support_notes.append(note)
            if supported:
                reduced.append(action_value)
            else:
                removed.append(note)
        if removed:
            ac3_revisions += 1
            trace(
                "ac3_revise",
                current,
                route,
                current_time,
                reduced,
                assignment,
                "REVISE loai cac gia tri khong co support, sau do lan truyen lai cac cung lien quan.",
                load,
                picked,
                delivered,
                result_label="Cat mien" if reduced else "Domain rong",
                constraint_checks=removed,
            )
        else:
            trace(
                "ac3_consistent",
                current,
                route,
                current_time,
                actions,
                assignment,
                "Tat ca gia tri trong domain hien tai deu co support nen cung dang nhat quan.",
                load,
                picked,
                delivered,
                result_label="Nhat quan",
                constraint_checks=support_notes[:4],
            )
        return reduced

    def impossible_from_start() -> list[str]:
        issues = []
        for order in orders:
            pickup = order.pickup_node_id or scenario.depot_id
            dropoff = order.dropoff_node_id or order.node_id
            if order.demand_kg > capacity:
                issues.append(f"{order.id}: demand {order.demand_kg:.1f}kg vuot suc chua {capacity:.1f}kg.")
                continue
            _, to_pickup = travel(scenario.depot_id, pickup)
            _, to_dropoff = travel(pickup, dropoff)
            earliest_dropoff = max(to_pickup, order.ready_min) + to_dropoff
            if to_pickup >= BLOCKED_COST or to_dropoff >= BLOCKED_COST:
                issues.append(f"{order.id}: khong co duong hop le tu depot qua pickup den dropoff.")
            elif earliest_dropoff > order.due_min:
                issues.append(f"{order.id}: som nhat den phut {earliest_dropoff:.1f}, tre deadline {order.due_min}.")
        return issues

    def trace(
        phase: str,
        current: str,
        route: list[str],
        current_time: float,
        actions: list[tuple[str, str]],
        assignment: list[str],
        reason: str,
        load: float,
        picked: set[str],
        delivered: set[str],
        tried_value: str | None = None,
        result_label: str = "Dang xet",
        constraint_checks: list[str] | None = None,
        preview_path: list[str] | None = None,
    ) -> None:
        nonlocal skipped_trace_steps
        if not debug:
            return
        if len(trace_steps) >= DEBUG_TRACE_LIMIT:
            skipped_trace_steps += 1
            return
        selected_variable = "Hoan tat assignment" if phase == "csp_solution" else f"X{len(assignment) + 1}: hanh dong tiep theo"
        domain = domain_labels(actions)
        trace_steps.append(
            TraceStep(
                stepIndex=len(trace_steps),
                phase=phase,
                currentNode=current,
                frontier=domain,
                visitedNodes=list(dict.fromkeys(route)),
                candidatePath=route[:],
                previewPath=preview_path or [],
                costSoFar=round(current_time, 2),
                heuristic=float(len(domain)),
                decisionReason=reason,
                debugData={
                    "traceType": "csp",
                    "courseConcept": "CSP = Variables, Domains, Constraints; Backtracking, Forward Checking, AC-3, Min-Conflicts.",
                    "algorithmRule": ALGORITHM_RULES.get(algorithm, ALGORITHM_RULES["backtracking"]),
                    "concept": "Bien = vi tri tiep theo trong chuoi pickup/dropoff; mien = cac hanh dong con hop le.",
                    "selectedVariable": selected_variable,
                    "domainValues": domain,
                    "triedValue": tried_value or "-",
                    "constraintCheck": constraint_checks or [
                        "Dung thu tu: phai pickup truoc dropoff.",
                        "Tai trong khong vuot suc chua xe.",
                        "Thoi gian giao khong qua deadline.",
                        "Co duong di hop le giua hai node.",
                    ],
                    "result": result_label,
                    "assignment": assignment[:],
                    "remainingOrders": remaining_orders(picked, delivered),
                    "orderDetails": order_summaries,
                    "loadKg": round(load, 2),
                    "capacityKg": capacity,
                },
            )
        )

    initial_issues = impossible_from_start() if selected_order_ids is None or len(orders) > 4 else []
    if initial_issues:
        trace(
            "initial_infeasible",
            scenario.depot_id,
            [scenario.depot_id],
            0.0,
            available_actions(set(), set(), 0.0),
            [],
            "Kiem tra kha thi ban dau thay co don khong the giao dung han ngay ca khi xu ly rieng le.",
            0.0,
            set(),
            set(),
            result_label="Vo nghiem",
            constraint_checks=initial_issues,
        )
        return {
            "valid": False,
            "path": [],
            "assignment": [],
            "totalMinutes": None,
            "servedOrders": 0,
            "capacityKg": capacity,
            "expandedStates": expanded_states,
            "backtracks": backtracks,
            "algorithm": algorithm,
            "traceSteps": trace_steps,
            "traceTruncated": skipped_trace_steps > 0,
            "skippedTraceSteps": skipped_trace_steps,
            "ac3Revisions": ac3_revisions,
            "minConflictSteps": min_conflict_steps,
            "orderSummaries": order_summaries,
        }

    def backtrack(
        current: str,
        current_time: float,
        load: float,
        picked: set[str],
        delivered: set[str],
        route: list[str],
        assignment: list[str],
    ) -> tuple[list[str], list[str], float] | None:
        nonlocal expanded_states, backtracks
        expanded_states += 1
        if len(delivered) == len(orders):
            trace(
                "csp_solution",
                current,
                route,
                current_time,
                [],
                assignment,
                "Da gan du gia tri cho cac bien X1..Xn va thoa tat ca rang buoc.",
                load,
                picked,
                delivered,
                result_label="Tim thay nghiem",
                constraint_checks=["Tat ca don da pickup va dropoff dung thu tu, dung tai trong, dung deadline."],
            )
            return route, assignment, current_time

        actions = ac3_reduce_actions(
            current,
            current_time,
            load,
            picked,
            delivered,
            route,
            assignment,
            available_actions(picked, delivered, load),
        )
        trace(
            "select_variable",
            current,
            route,
            current_time,
            actions,
            assignment,
            f"Chon bien X{len(assignment) + 1}. Mien hien co {len(actions)} gia tri, sap xep dropoff truoc pickup va don gan deadline truoc.",
            load,
            picked,
            delivered,
            result_label="Chon bien va lap mien",
        )
        for order_id, action in actions:
            order = order_by_id[order_id]
            target = location(order, action)
            segment, travel_minutes = travel(current, target)
            if not segment or travel_minutes >= BLOCKED_COST:
                trace(
                    "reject_value",
                    current,
                    route,
                    current_time,
                    actions,
                    assignment,
                    f"Loai {action_label(order_id, action)} vi khong co duong di hop le tu {current}.",
                    load,
                    picked,
                    delivered,
                    tried_value=action_label(order_id, action),
                    result_label="Loai gia tri",
                    constraint_checks=["Rang buoc duong di: that bai."],
                )
                continue
            next_time = max(current_time + travel_minutes, order.ready_min) if action == "pickup" else current_time + travel_minutes
            next_load = load + order.demand_kg if action == "pickup" else load - order.demand_kg
            if action == "dropoff" and next_time > order.due_min:
                trace(
                    "reject_value",
                    current,
                    route,
                    next_time,
                    actions,
                    assignment,
                    f"Loai {action_label(order_id, action)} vi den phut {next_time:.1f}, tre deadline {order.due_min}.",
                    load,
                    picked,
                    delivered,
                    tried_value=action_label(order_id, action),
                    result_label="Loai gia tri",
                    constraint_checks=[
                        f"Deadline {order_id}: den {next_time:.1f} <= han {order.due_min} la sai.",
                        "Thu tu pickup/dropoff va tai trong khong vi pham tai buoc nay.",
                    ],
                )
                continue
            next_picked = picked | {order_id} if action == "pickup" else set(picked)
            next_delivered = delivered | {order_id} if action == "dropoff" else set(delivered)
            next_route = route + (segment[1:] if route else segment)
            next_assignment = assignment + [f"{action}:{order_id}@{target}"]
            action_text = action_label(order_id, action)
            trace(
                "try_value",
                current,
                route,
                current_time,
                actions,
                assignment,
                f"Thu gan {action_text} cho X{len(assignment) + 1}; dung A* de kiem tra duong toi node muc tieu truoc khi cap nhat assignment.",
                load,
                picked,
                delivered,
                tried_value=action_text,
                result_label="Thu gia tri",
                constraint_checks=[
                    f"A* de xuat duong {' -> '.join(segment)} voi {travel_minutes:.1f} phut.",
                    "Chua cap nhat pickup/dropoff cho den khi di het doan nay.",
                ],
                preview_path=[current],
            )
            for segment_index in range(1, len(segment)):
                travel_prefix = route + segment[1 : segment_index + 1] if route else segment[: segment_index + 1]
                prefix_minutes = path_time(scenario, segment[: segment_index + 1])
                trace(
                    "move_edge",
                    segment[segment_index],
                    travel_prefix,
                    current_time + prefix_minutes,
                    actions,
                    assignment,
                    f"Di chuyen {segment[segment_index - 1]} -> {segment[segment_index]} de thuc hien {action_text}.",
                    load,
                    picked,
                    delivered,
                    tried_value=action_text,
                    result_label="Di chuyen",
                    constraint_checks=[
                        f"Canh {segment[segment_index - 1]}->{segment[segment_index]} nam tren duong A* da chon.",
                        "Assignment va tai trong giu nguyen trong luc di chuyen.",
                    ],
                    preview_path=segment[segment_index - 1 : segment_index + 1],
                )
            trace(
                "commit_value",
                target,
                next_route,
                next_time,
                actions,
                next_assignment,
                f"Hoan tat {action_text} cho X{len(assignment) + 1}; cap nhat route, tai trong va thoi gian.",
                next_load,
                next_picked,
                next_delivered,
                tried_value=action_text,
                result_label="Chap nhan tam thoi",
                constraint_checks=[
                    f"Duong di {current}->{target}: {travel_minutes:.1f} phut.",
                    f"Tai trong sau buoc nay: {next_load:.1f}/{capacity:.1f} kg.",
                    "Thu tu pickup/dropoff hop le.",
                ],
                preview_path=segment[-2:] if len(segment) >= 2 else [target],
            )
            if algorithm == "forward_checking" and not forward_feasible(target, next_time, next_picked, next_delivered):
                trace(
                    "forward_prune",
                    target,
                    next_route,
                    next_time,
                    actions,
                    next_assignment,
                    "Forward checking nhin truoc cac don con lai va thay it nhat mot don khong the giao dung han.",
                    next_load,
                    next_picked,
                    next_delivered,
                    tried_value=action_label(order_id, action),
                    result_label="Cat nhanh",
                    constraint_checks=[
                        "Kiem tra moi don chua giao: tu vi tri moi co kip pickup/dropoff truoc deadline khong.",
                        "Neu mot don khong con mien gia tri kha thi thi nhanh nay bi cat.",
                    ],
                )
                continue
            result = backtrack(target, next_time, next_load, next_picked, next_delivered, next_route, next_assignment)
            if result is not None:
                return result
        backtracks += 1
        trace(
            "backtrack",
            current,
            route,
            current_time,
            actions,
            assignment,
            f"Mien cua X{len(assignment) + 1} da thu het nhung khong dan toi nghiem; quay lui ve bien truoc.",
            load,
            picked,
            delivered,
            result_label="Quay lui",
            constraint_checks=["Khong con gia tri trong mien tao duoc loi giai hoan chinh."],
        )
        return None

    def evaluate_complete_sequence(sequence: list[str]) -> dict:
        route = [scenario.depot_id]
        assignment: list[str] = []
        current = scenario.depot_id
        current_time = 0.0
        load = 0.0
        max_load = 0.0
        picked: set[str] = set()
        delivered: set[str] = set()
        conflicts: dict[str, list[str]] = {}

        def add_conflict(order_id: str, message: str) -> None:
            conflicts.setdefault(order_id, []).append(message)

        for order_id in sequence:
            order = order_by_id[order_id]
            for action in ("pickup", "dropoff"):
                target = location(order, action)
                segment, travel_minutes = travel(current, target)
                if not segment or travel_minutes >= BLOCKED_COST:
                    add_conflict(order_id, f"{action_label(order_id, action)} khong co duong di hop le.")
                    continue
                route.extend(segment[1:])
                current = target
                current_time = max(current_time + travel_minutes, order.ready_min) if action == "pickup" else current_time + travel_minutes
                if action == "pickup":
                    picked.add(order_id)
                    load += order.demand_kg
                    max_load = max(max_load, load)
                    if load > capacity:
                        add_conflict(order_id, f"Tai trong {load:.1f}kg vuot suc chua {capacity:.1f}kg.")
                else:
                    if order_id not in picked:
                        add_conflict(order_id, "Dropoff khong co pickup truoc do.")
                    if current_time > order.due_min:
                        add_conflict(order_id, f"Giao tre: den {current_time:.1f}, han {order.due_min}.")
                    delivered.add(order_id)
                    load -= order.demand_kg
                    current_time += order.service_min
                assignment.append(f"{action}:{order_id}@{target}")

        for order in orders:
            if order.id not in delivered:
                add_conflict(order.id, "Chua giao xong trong assignment day du.")
        score = sum(len(items) for items in conflicts.values())
        return {
            "valid": score == 0,
            "path": route,
            "assignment": assignment,
            "totalMinutes": current_time,
            "conflicts": conflicts,
            "score": score,
            "loadKg": max_load,
        }

    def solve_with_min_conflicts() -> tuple[list[str], list[str], float] | None:
        nonlocal expanded_states, min_conflict_steps
        if not orders:
            return [scenario.depot_id], [], 0.0
        rng = random.Random(13)
        sequence = [order.id for order in sorted(orders, key=lambda item: (item.due_min, -item.priority, item.id))]
        current_eval = evaluate_complete_sequence(sequence)
        expanded_states += 1
        trace(
            "min_conflicts_init",
            scenario.depot_id,
            current_eval["path"],
            current_eval["totalMinutes"],
            [],
            current_eval["assignment"],
            "Khoi tao assignment hoan chinh cho tat ca bien, chap nhan tam thoi ca cac xung dot neu co.",
            current_eval["loadKg"],
            set(sequence),
            set(order.id for order in orders if order.id not in current_eval["conflicts"]),
            result_label="Het xung dot" if current_eval["valid"] else "Con xung dot",
            constraint_checks=[
                f"{order_id}: {'; '.join(messages)}" for order_id, messages in current_eval["conflicts"].items()
            ] or ["Assignment ban dau khong vi pham rang buoc."],
        )
        max_steps = max(20, len(orders) * len(orders) * 4)
        for step in range(max_steps + 1):
            min_conflict_steps = step
            if current_eval["valid"]:
                return current_eval["path"], current_eval["assignment"], current_eval["totalMinutes"]
            conflicted = list(current_eval["conflicts"])
            selected = rng.choice(conflicted)
            candidates: list[tuple[int, float, list[str], dict]] = []
            rest = [order_id for order_id in sequence if order_id != selected]
            for position in range(len(rest) + 1):
                candidate_sequence = rest[:position] + [selected] + rest[position:]
                candidate_eval = evaluate_complete_sequence(candidate_sequence)
                candidates.append((candidate_eval["score"], candidate_eval["totalMinutes"], candidate_sequence, candidate_eval))
            best_score, _, best_sequence, best_eval = min(candidates, key=lambda item: (item[0], item[1]))
            trace(
                "min_conflicts_update",
                scenario.depot_id,
                best_eval["path"],
                best_eval["totalMinutes"],
                [],
                best_eval["assignment"],
                f"Chon bien dang xung dot {selected}, thu cac vi tri khac va giu assignment co so conflict nho nhat.",
                best_eval["loadKg"],
                set(best_sequence),
                set(order.id for order in orders if order.id not in best_eval["conflicts"]),
                tried_value=selected,
                result_label=f"Con {best_score} xung dot",
                constraint_checks=(
                    ["Cac assignment ung vien: " + " | ".join(", ".join(candidate[2]) for candidate in candidates[:6])]
                    + [f"{order_id}: {'; '.join(messages)}" for order_id, messages in best_eval["conflicts"].items()]
                    or ["Khong con xung dot."]
                ),
            )
            sequence = best_sequence
            current_eval = best_eval
            expanded_states += 1
        return None

    if algorithm == "min_conflicts":
        solution = solve_with_min_conflicts()
    else:
        solution = backtrack(scenario.depot_id, 0.0, 0.0, set(), set(), [scenario.depot_id], [])
    return {
        "valid": solution is not None,
        "path": solution[0] if solution else [],
        "assignment": solution[1] if solution else [],
        "totalMinutes": round(solution[2], 2) if solution else None,
        "servedOrders": len(orders) if solution else 0,
        "capacityKg": capacity,
        "expandedStates": expanded_states,
        "backtracks": backtracks,
        "algorithm": algorithm,
        "traceSteps": trace_steps,
        "traceTruncated": skipped_trace_steps > 0,
        "skippedTraceSteps": skipped_trace_steps,
        "ac3Revisions": ac3_revisions,
        "minConflictSteps": min_conflict_steps,
        "orderSummaries": order_summaries,
    }
