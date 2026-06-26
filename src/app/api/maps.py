from __future__ import annotations

from fastapi import APIRouter, Depends, Response

from app.models.schemas import MapCreateRequest, MapDetail, MapPatchRequest, MapSummary, UserPublic
from app.services.auth_service import get_current_user, require_admin
from app.services.map_service import create_map, delete_map, get_map, list_maps, selected_map_for_group, update_map


router = APIRouter(prefix="/maps")


@router.get("", response_model=list[MapSummary])
def get_maps(_: UserPublic = Depends(get_current_user)) -> list[MapSummary]:
    return list_maps()


@router.get("/default/{algorithm_group}", response_model=MapDetail)
def get_default_map(
    algorithm_group: str,
    map_id: int | None = None,
    _: UserPublic = Depends(get_current_user),
) -> MapDetail:
    return selected_map_for_group(algorithm_group, map_id)


@router.get("/{map_id}", response_model=MapDetail)
def get_map_detail(map_id: int, _: UserPublic = Depends(get_current_user)) -> MapDetail:
    return get_map(map_id)


@router.post("", response_model=MapDetail)
def post_map(request: MapCreateRequest, _: UserPublic = Depends(require_admin)) -> MapDetail:
    return create_map(request)


@router.patch("/{map_id}", response_model=MapDetail)
def patch_map(map_id: int, request: MapPatchRequest, _: UserPublic = Depends(require_admin)) -> MapDetail:
    return update_map(map_id, request)


@router.delete("/{map_id}", status_code=204)
def remove_map(map_id: int, _: UserPublic = Depends(require_admin)) -> Response:
    delete_map(map_id)
    return Response(status_code=204)
