from __future__ import annotations

from fastapi import APIRouter, Depends

from app.models.schemas import LoginRequest, RegisterRequest, TokenResponse, UserPublic
from app.services.auth_service import authenticate, create_token, get_current_user, register_user, require_admin


router = APIRouter(prefix="/auth")


@router.post("/login", response_model=TokenResponse)
def login(request: LoginRequest) -> TokenResponse:
    user = authenticate(request.username, request.password)
    return TokenResponse(accessToken=create_token(user), user=user)


@router.get("/me", response_model=UserPublic)
def me(user: UserPublic = Depends(get_current_user)) -> UserPublic:
    return user


@router.post("/register", response_model=UserPublic)
def register(request: RegisterRequest, _: UserPublic = Depends(require_admin)) -> UserPublic:
    return register_user(request.username, request.password, request.role, request.shipperGroup)
