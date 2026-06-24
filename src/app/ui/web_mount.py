from __future__ import annotations

from fastapi import FastAPI
from flet.fastapi import app as flet_app

from app.ui.flet_app import main as flet_main


def register_web_ui(app: FastAPI) -> None:
    app.mount(
        "/",
        flet_app(
            flet_main,
            app_name="Find Your Path",
            app_short_name="FYP",
            app_description="Smart Urban Delivery Planner",
        ),
    )
