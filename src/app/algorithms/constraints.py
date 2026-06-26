from __future__ import annotations

from app.algorithms.graph import BLOCKED_COST, find_edge, path_time
from app.algorithms.search import astar
from app.models.schemas import Order, Scenario, TraceStep

DEBUG_TRACE_LIMIT = 300


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
    trace_steps: list[TraceStep] = []
    skipped_trace_steps = 0
    expanded_states = 0
    backtracks = 0

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
        return f"{verb} {order_id} tai {target}"

    def domain_labels(actions: list[tuple[str, str]]) -> list[str]:
        return [action_label(order_id, action) for order_id, action in actions]

    def remaining_orders(picked: set[str], delivered: set[str]) -> list[str]:
        return [
            f"{order.id}: {'da giao' if order.id in delivered else 'dang mang' if order.id in picked else 'chua nhan'}"
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
                    "courseConcept": "CSP = Variables, Domains, Constraints; Backtracking thu gia tri va quay lui khi vi pham.",
                    "algorithmRule": (
                        "Forward Checking cat nhanh khi mot bien chua gan mat het mien."
                        if algorithm == "forward_checking"
                        else "Backtracking thu tung gia tri trong domain cho den khi tim duoc assignment hop le."
                    ),
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

        actions = available_actions(picked, delivered, load)
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
    }
