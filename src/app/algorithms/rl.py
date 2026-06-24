from __future__ import annotations

import random

from app.algorithms.graph import build_adjacency, edge_time
from app.models.schemas import Scenario, TraceStep


def q_learning_demo(
    scenario: Scenario,
    episodes: int,
    alpha: float,
    gamma: float,
    epsilon: float,
    debug: bool = False,
) -> dict:
    rng = random.Random(19)
    adjacency = build_adjacency(scenario)
    start = scenario.depot_id
    goal = scenario.orders[-1].node_id
    q: dict[tuple[str, str], float] = {}
    rewards: list[float] = []
    trace_steps: list[TraceStep] = []

    for _ in range(episodes):
        state = start
        total_reward = 0.0
        for _step in range(30):
            actions = [neighbor for neighbor, edge in adjacency[state] if edge_time(edge) < 999999]
            if not actions:
                break
            if rng.random() < epsilon:
                action = rng.choice(actions)
            else:
                action = max(actions, key=lambda candidate: q.get((state, candidate), 0.0))
            edge = next(edge for neighbor, edge in adjacency[state] if neighbor == action)
            reward = 100 if action == goal else -edge_time(edge)
            next_actions = [neighbor for neighbor, _ in adjacency[action]]
            best_next = max((q.get((action, next_action), 0.0) for next_action in next_actions), default=0.0)
            old_value = q.get((state, action), 0.0)
            q[(state, action)] = old_value + alpha * (reward + gamma * best_next - old_value)
            if debug and len(trace_steps) < 80:
                trace_steps.append(
                    TraceStep(
                        stepIndex=len(trace_steps),
                        phase="q_update",
                        currentNode=state,
                        frontier=actions,
                        visitedNodes=[state, action],
                        candidatePath=[state, action],
                        costSoFar=round(total_reward + reward, 2),
                        heuristic=round(q[(state, action)], 2),
                        decisionReason=f"Action {action}, reward {reward:.2f}, Q cu {old_value:.2f}, Q moi {q[(state, action)]:.2f}.",
                    )
                )
            total_reward += reward
            state = action
            if state == goal:
                break
        rewards.append(round(total_reward, 2))

    policy_path = [start]
    visited = [start]
    state = start
    for _ in range(12):
        actions = [neighbor for neighbor, edge in adjacency[state] if edge_time(edge) < 999999]
        if not actions:
            break
        action = max(actions, key=lambda candidate: q.get((state, candidate), -999999))
        policy_path.append(action)
        visited.append(action)
        state = action
        if state == goal or policy_path.count(state) > 1:
            break

    q_table = [
        {"state": state, "action": action, "value": round(value, 2)}
        for (state, action), value in sorted(q.items(), key=lambda item: (item[0][0], item[0][1]))
    ]
    return {
        "path": policy_path,
        "visited": visited,
        "averageReward": round(sum(rewards[-10:]) / min(10, len(rewards)), 2),
        "episodes": episodes,
        "qTable": q_table[:40],
        "rewardHistory": rewards,
        "traceSteps": trace_steps,
    }
