from __future__ import annotations

from fastapi import APIRouter

from app.data.scenario import load_osm_cached_scenario
from app.models.schemas import ScenarioResponse


router = APIRouter()


@router.get("/scenario/default", response_model=ScenarioResponse)
def get_default_scenario() -> ScenarioResponse:
    return ScenarioResponse(**load_osm_cached_scenario().model_dump())
