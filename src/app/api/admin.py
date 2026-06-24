from __future__ import annotations

from fastapi import APIRouter, Depends

from app.models.schemas import PermissionPatchRequest, PermissionRow, UserGroupPatchRequest, UserPublic
from app.services.auth_service import list_permissions, list_users, require_admin, update_permission, update_user_group


router = APIRouter(prefix="/admin")


@router.get("/permissions", response_model=list[PermissionRow])
def get_permissions(_: UserPublic = Depends(require_admin)) -> list[PermissionRow]:
    return list_permissions()


@router.patch("/permissions", response_model=PermissionRow)
def patch_permission(request: PermissionPatchRequest, _: UserPublic = Depends(require_admin)) -> PermissionRow:
    return update_permission(request.shipperGroup, request.algorithmGroup, request.algorithmName, request.enabled)


@router.get("/users", response_model=list[UserPublic])
def get_users(_: UserPublic = Depends(require_admin)) -> list[UserPublic]:
    return list_users()


@router.patch("/users/{user_id}/group", response_model=UserPublic)
def patch_user_group(user_id: int, request: UserGroupPatchRequest, _: UserPublic = Depends(require_admin)) -> UserPublic:
    return update_user_group(user_id, request.shipperGroup)
