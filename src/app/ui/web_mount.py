from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from flet.fastapi import app as flet_app

from app.ui.flet_app import main as flet_main

APP_ASSETS_DIR = Path(__file__).resolve().parent / "assets"
ASSET_HEADERS = {"Cache-Control": "no-store, max-age=0"}


def _asset_response(path: Path, media_type: str) -> FileResponse:
    if not path.is_file():
        raise HTTPException(status_code=404)
    return FileResponse(path, media_type=media_type, headers=ASSET_HEADERS)


def register_web_ui(app: FastAPI) -> None:
    @app.get("/favicon.ico", include_in_schema=False)
    def favicon_ico() -> FileResponse:
        return _asset_response(APP_ASSETS_DIR / "favicon.ico", "image/x-icon")

    @app.get("/favicon.png", include_in_schema=False)
    def favicon_png() -> FileResponse:
        return _asset_response(APP_ASSETS_DIR / "favicon.png", "image/png")

    @app.get("/manifest.json", include_in_schema=False)
    def manifest_json() -> FileResponse:
        return _asset_response(APP_ASSETS_DIR / "manifest.json", "application/manifest+json")

    @app.get("/manifest.webmanifest", include_in_schema=False)
    def manifest_webmanifest() -> FileResponse:
        return _asset_response(APP_ASSETS_DIR / "manifest.webmanifest", "application/manifest+json")

    @app.get("/icons/{asset_path:path}", include_in_schema=False)
    def icon_asset(asset_path: str) -> FileResponse:
        icon_path = (APP_ASSETS_DIR / "icons" / asset_path).resolve()
        icons_dir = (APP_ASSETS_DIR / "icons").resolve()
        if not icon_path.is_relative_to(icons_dir):
            raise HTTPException(status_code=404)
        suffix = icon_path.suffix.lower()
        media_type = "image/x-icon" if suffix == ".ico" else "image/png"
        return _asset_response(icon_path, media_type)

    app.mount(
        "/",
        flet_app(
            flet_main,
            assets_dir=str(APP_ASSETS_DIR),
            app_name="FYP Delivery",
            app_short_name="FYP Delivery",
            app_description="Smart Urban Delivery Planner",
        ),
    )
