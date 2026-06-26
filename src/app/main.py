from __future__ import annotations

from fastapi import FastAPI

from app.api import api_router
from app.services.auth_service import init_db
from app.ui.map_page import register_map_ui
from app.ui.web_mount import register_web_ui


def create_app() -> FastAPI:
    init_db()
    app = FastAPI(title="FYP Delivery API", version="0.1.0")
    app.include_router(api_router)
    register_map_ui(app)
    register_web_ui(app)
    return app


app = create_app()
