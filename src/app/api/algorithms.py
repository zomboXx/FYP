from __future__ import annotations

from fastapi import APIRouter, Depends

from app.models.schemas import (
    AdversarialSearchRequest,
    AlgorithmResponse,
    ComplexSearchRequest,
    ConstraintCheckRequest,
    CspSolveRequest,
    DeliveryOptimizeRequest,
    EventSimulateRequest,
    PathfindingRequest,
    UserPublic,
)
from app.services.auth_service import get_current_user
from app.services.route_service import (
    check_constraints,
    optimize_delivery,
    run_adversarial_search,
    run_complex_search,
    run_pathfinding,
    simulate_dynamic_event,
    solve_csp,
)


router = APIRouter()


@router.post("/pathfinding/run", response_model=AlgorithmResponse)
def post_pathfinding(request: PathfindingRequest, user: UserPublic = Depends(get_current_user)) -> AlgorithmResponse:
    return run_pathfinding(request, user)


@router.post("/delivery/optimize", response_model=AlgorithmResponse)
def post_delivery_optimize(
    request: DeliveryOptimizeRequest,
    user: UserPublic = Depends(get_current_user),
) -> AlgorithmResponse:
    return optimize_delivery(request, user)


@router.post("/constraints/check", response_model=AlgorithmResponse)
def post_constraints_check(
    request: ConstraintCheckRequest,
    user: UserPublic = Depends(get_current_user),
) -> AlgorithmResponse:
    return check_constraints(request, user)


@router.post("/csp/solve", response_model=AlgorithmResponse)
def post_csp_solve(request: CspSolveRequest, user: UserPublic = Depends(get_current_user)) -> AlgorithmResponse:
    return solve_csp(request, user)


@router.post("/events/simulate", response_model=AlgorithmResponse)
def post_events_simulate(
    request: EventSimulateRequest,
    user: UserPublic = Depends(get_current_user),
) -> AlgorithmResponse:
    return simulate_dynamic_event(request, user)


@router.post("/complex/run", response_model=AlgorithmResponse)
def post_complex_run(request: ComplexSearchRequest, user: UserPublic = Depends(get_current_user)) -> AlgorithmResponse:
    return run_complex_search(request, user)


@router.post("/adversarial/run", response_model=AlgorithmResponse)
def post_adversarial_run(
    request: AdversarialSearchRequest,
    user: UserPublic = Depends(get_current_user),
) -> AlgorithmResponse:
    return run_adversarial_search(request, user)
