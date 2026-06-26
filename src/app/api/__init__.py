from __future__ import annotations

from fastapi import APIRouter

from app.api.admin import router as admin_router
from app.api.algorithms import router as algorithms_router
from app.api.auth import router as auth_router
from app.api.maps import router as maps_router
from app.api.scenario import router as scenario_router
from app.api.shipper import router as shipper_router
from app.api.system import router as system_router


api_router = APIRouter(prefix="/api")
api_router.include_router(scenario_router)
api_router.include_router(auth_router)
api_router.include_router(maps_router)
api_router.include_router(admin_router)
api_router.include_router(algorithms_router)
api_router.include_router(shipper_router)
api_router.include_router(system_router)
