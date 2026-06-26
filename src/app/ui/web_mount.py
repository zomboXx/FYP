from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from flet.fastapi import app as flet_app

from app.ui.flet_app import main as flet_main

APP_ASSETS_DIR = Path(__file__).resolve().parent / "assets"


def register_web_ui(app: FastAPI) -> None:
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
