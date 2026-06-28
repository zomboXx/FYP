from __future__ import annotations

from app.algorithms.adversarial import adversarial_search
from app.algorithms.complex import complex_search
from app.algorithms.constraints import check_route_constraints
from app.algorithms.constraints import solve_delivery_csp
from app.algorithms.delivery import evaluate_delivery_order, local_beam_search, selected_orders
from app.algorithms.delivery import hill_climbing
from app.algorithms.events import replan_after_event
from app.algorithms.graph import edge_time, find_edge
from app.algorithms.search import astar, bfs, dfs, ucs
from app.data.scenario import default_scenario, load_osm_cached_scenario


def test_cost_function_uses_traffic_multiplier():
    scenario = default_scenario()
    edge = find_edge(scenario, "A", "B")
    assert edge is not None
    assert edge.traffic == "heavy"
    assert edge_time(edge) == 8


def test_bfs_dfs_ucs_return_valid_paths_on_small_graph():
    scenario = default_scenario()
    for algorithm in (bfs, dfs, ucs):
        result = algorithm(scenario, "D0", "E")
        assert result.path[0] == "D0"
        assert result.path[-1] == "E"
        assert "E" in result.visited_nodes


def test_astar_returns_low_cost_path():
    scenario = default_scenario()
    result = astar(scenario, "D0", "E")
    assert result.path == ["D0", "C", "D", "E"]
    assert result.total_minutes <= 15.8


def test_search_groups_expose_distinct_objectives_and_informed_debug_values():
    scenario = default_scenario()
    bfs_result = bfs(scenario, "D0", "E", debug=True)
    dfs_result = dfs(scenario, "D0", "E", debug=True)
    ucs_result = ucs(scenario, "D0", "E", debug=True)
    astar_result = astar(scenario, "D0", "E", debug=True)
    assert len(bfs_result.path) <= len(dfs_result.path)
    assert ucs_result.total_minutes < bfs_result.total_minutes
    assert astar_result.trace_steps[0].debugData["evaluation"] == "astar"
    assert astar_result.trace_steps[0].debugData["f"] == (
        astar_result.trace_steps[0].debugData["g"] + astar_result.trace_steps[0].debugData["h"]
    )


def test_bfs_debug_trace_keeps_parent_and_step_preview_path():
    scenario = default_scenario()
    result = bfs(scenario, "D0", "E", debug=True)
    first = result.trace_steps[0]
    generated = next(step for step in result.trace_steps if step.phase == "push_neighbor")
    generated_node = generated.debugData["generatedNode"]
    generated_pop = next(
        step for step in result.trace_steps if step.phase == "pop_frontier" and step.currentNode == generated_node
    )

    assert first.debugData["suppressHighlights"] is True
    assert first.previewPath == []
    assert generated.currentNode == generated.debugData["generatedFrom"]
    assert generated.debugData["parentMap"][generated_node] == generated.currentNode
    assert generated_pop.previousNode == generated.currentNode
    assert generated_pop.previewPath == generated.debugData["generatedPath"]


def test_constraint_checker_detects_late_capacity_and_blocked_road():
    scenario = default_scenario()
    for edge in scenario.edges:
        if {edge.source, edge.target} == {"C", "D"}:
            edge.blocked = True
    result = check_route_constraints(scenario, ["D0", "C", "D", "E", "G", "H", "I"], capacity_kg=5)
    assert result["valid"] is False
    assert any("Vuot tai" in violation for violation in result["violations"])
    assert any("duong bi chan" in violation for violation in result["violations"])
    assert any("giao tre" in violation for violation in result["violations"])


def test_route_evaluator_computes_delivery_metrics():
    scenario = default_scenario()
    orders = selected_orders(scenario, ["O1", "O2", "O3"])
    result = evaluate_delivery_order(scenario, orders)
    assert result["distanceKm"] > 0
    assert result["totalMinutes"] > 0
    assert result["lateOrders"] >= 0
    assert "penalty" in result
    assert result["initialState"]["position_id"] == scenario.depot_id
    assert result["goalState"]["delivered_order_ids"]


def test_local_beam_search_returns_stateful_delivery_plan():
    scenario = default_scenario()
    orders = selected_orders(scenario, ["O1", "O2", "O3"])
    result = local_beam_search(scenario, orders, debug=True)
    assert result["path"][0] == scenario.depot_id
    assert result["iterations"] > 0
    assert result["traceSteps"]


def test_hill_climbing_does_not_worsen_seeded_initial_route():
    scenario = default_scenario()
    orders = selected_orders(scenario, ["O1", "O2", "O3"])
    baseline = evaluate_delivery_order(scenario, orders)["totalCost"]
    result = hill_climbing(scenario, orders, debug=True)
    assert result["totalCost"] <= baseline
    assert any("bestCost" in step.debugData for step in result["traceSteps"])


def test_dynamic_event_replan_reports_before_and_after_paths():
    scenario = default_scenario()
    result = replan_after_event(scenario, "accident", ("C", "D"))
    assert result["originalPath"]
    assert result["replannedPath"]
    assert result["updatedScenario"].edges


def test_partial_observation_reveals_hidden_edge_and_replans():
    scenario = load_osm_cached_scenario()
    result = complex_search(scenario, "online_replan", "W1", "D1", 1, "accident", debug=True)
    assert result["path"][0] == "W1"
    assert result["path"][-1] == "D1"
    assert result["initialPath"] != result["finalPath"]
    assert result["observedEdges"]
    assert result["replans"] > 1
    assert any(step.debugData.get("observation") for step in result["traceSteps"])


def test_and_or_search_returns_complete_conditional_plan():
    scenario = load_osm_cached_scenario()
    result = complex_search(scenario, "and_or", "W1", "D1", 1, "accident", debug=True)
    plan = result["conditionalPlan"]
    assert result["path"][0] == "W1"
    assert result["path"][-1] == "D1"
    assert plan["complete"] is True
    assert plan["ifOpen"]
    assert plan["ifDisrupted"]
    assert plan["ifOpen"] != plan["ifDisrupted"]
    assert any(step.phase == "OR_CHOOSE_ACTION" for step in result["traceSteps"])
    assert any(step.phase == "AND_ENV_OUTCOME" for step in result["traceSteps"])


def test_csp_solver_handles_valid_and_infeasible_order_sets():
    scenario = load_osm_cached_scenario()
    valid = solve_delivery_csp(scenario, "forward_checking", ["O4"], 22, debug=True)
    infeasible = solve_delivery_csp(scenario, "forward_checking", ["O4", "O2"], 22, debug=True)
    ac3 = solve_delivery_csp(scenario, "ac3", ["O4"], 22, debug=True)
    min_conflicts = solve_delivery_csp(scenario, "min_conflicts", ["O4"], 22, debug=True)
    assert valid["valid"] is True
    assert valid["assignment"]
    assert valid["traceSteps"][0].debugData["traceType"] == "csp"
    assert valid["traceSteps"][0].debugData["selectedVariable"].startswith("X1")
    assert valid["traceSteps"][0].debugData["domainValues"]
    assert any(step.phase == "try_value" for step in valid["traceSteps"])
    first_try = next(step for step in valid["traceSteps"] if step.phase == "try_value")
    first_move = next(step for step in valid["traceSteps"] if step.phase == "move_edge")
    assert first_try.candidatePath == [scenario.depot_id]
    assert len(first_move.previewPath) == 2
    assert infeasible["valid"] is False
    assert any(step.phase == "forward_prune" for step in infeasible["traceSteps"])
    assert ac3["valid"] is True
    assert any(step.phase.startswith("ac3_") for step in ac3["traceSteps"])
    assert min_conflicts["valid"] is True
    assert min_conflicts["traceSteps"][0].phase == "min_conflicts_init"


def test_alpha_beta_matches_minimax_and_expands_no_more_nodes():
    scenario = default_scenario()
    minimax = adversarial_search(scenario, "minimax", "D0", "G", 1, debug=True)
    alpha_beta = adversarial_search(scenario, "alpha_beta", "D0", "G", 1, debug=True)
    assert alpha_beta["gameValue"] == minimax["gameValue"]
    assert alpha_beta["path"] == minimax["path"]
    assert alpha_beta["expandedNodes"] <= minimax["expandedNodes"]
    assert alpha_beta["prunedBranches"] > 0
