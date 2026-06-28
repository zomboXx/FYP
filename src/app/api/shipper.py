from __future__ import annotations

from fastapi import APIRouter, Depends

from app.models.schemas import (
    AcceptOrdersRequest,
    AlgorithmResponse,
    AvailableOrder,
    CompleteOrderRequest,
    DeliveryOptimizeRequest,
    ShipperPlanRequest,
    UserPublic,
)
from app.services.auth_service import accept_orders, complete_order, get_current_user, list_available_orders
from app.services.route_service import plan_accepted_orders


router = APIRouter()


@router.get("/orders/available", response_model=list[AvailableOrder])
def get_available_orders(
    category: str | None = None,
    urgency: str | None = None,
    user: UserPublic = Depends(get_current_user),
) -> list[AvailableOrder]:
    return list_available_orders(category, urgency, user)


@router.post("/shipper/orders/accept", response_model=list[AvailableOrder])
def post_accept_orders(request: AcceptOrdersRequest, user: UserPublic = Depends(get_current_user)) -> list[AvailableOrder]:
    return accept_orders(request.orderIds, user)


@router.post("/shipper/orders/complete", response_model=AvailableOrder)
def post_complete_order(request: CompleteOrderRequest, user: UserPublic = Depends(get_current_user)) -> AvailableOrder:
    return complete_order(request.orderId, user)


@router.post("/shipper/routes/plan", response_model=AlgorithmResponse)
def post_shipper_route(request: ShipperPlanRequest, user: UserPublic = Depends(get_current_user)) -> AlgorithmResponse:
    return plan_accepted_orders(
        DeliveryOptimizeRequest(
            algorithm=request.algorithm,
            startId=request.startId,
            goalId=request.goalId,
            routingStrategy=request.routingStrategy,
            debug=request.debug,
        ),
        user,
    )
