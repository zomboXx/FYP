from __future__ import annotations

from typing import Any

import flet as ft

from app.ui.theme import CYAN, GREEN, INK, LINE, LINE_LIGHT, PANEL, PANEL_2, TEXT, YELLOW


def text(value: str, size: int = 14, color: str = TEXT, weight: str | None = None, **kwargs: Any) -> ft.Text:
    return ft.Text(value, size=size, color=color, weight=weight, **kwargs)


def pill(label: str, tone: str = "dark") -> ft.Container:
    bg = GREEN if tone == "green" else CYAN if tone == "cyan" else YELLOW if tone == "yellow" else PANEL_2
    color = INK if tone in {"green", "cyan", "yellow"} else GREEN
    border_color = bg if tone in {"green", "cyan", "yellow"} else LINE
    return ft.Container(
        content=text(label, size=11, color=color, weight=ft.FontWeight.W_700),
        bgcolor=bg,
        border=ft.border.all(1, border_color),
        padding=ft.padding.symmetric(horizontal=10, vertical=7),
        border_radius=4,
    )


def panel(content: ft.Control, dark: bool = True, expand: bool | int | None = None, padding: int = 16) -> ft.Container:
    return ft.Container(
        content=content,
        bgcolor=PANEL if dark else "#FFFFFF",
        border=ft.border.all(1, LINE if dark else LINE_LIGHT),
        padding=padding,
        border_radius=4,
        expand=expand,
    )


def primary_button(label: str, on_click: Any = None, icon: str | None = None) -> ft.FilledButton:
    return ft.FilledButton(
        label,
        icon=icon,
        on_click=on_click,
        style=ft.ButtonStyle(
            bgcolor=GREEN,
            color=INK,
            shape=ft.RoundedRectangleBorder(radius=4),
            text_style=ft.TextStyle(weight=ft.FontWeight.W_700),
            padding=ft.padding.symmetric(horizontal=16, vertical=14),
        ),
    )


def outline_button(
    label: str,
    on_click: Any = None,
    icon: str | None = None,
    selected: bool = False,
    disabled: bool = False,
) -> ft.OutlinedButton:
    return ft.OutlinedButton(
        label,
        icon=icon,
        disabled=disabled,
        on_click=None if disabled else on_click,
        style=ft.ButtonStyle(
            bgcolor=GREEN if selected else PANEL if disabled else PANEL_2,
            color=INK if selected else LINE_LIGHT if disabled else TEXT,
            side=ft.BorderSide(1, GREEN if selected else LINE if disabled else LINE_LIGHT),
            shape=ft.RoundedRectangleBorder(radius=4),
            text_style=ft.TextStyle(weight=ft.FontWeight.W_700, size=12),
        ),
    )


def dropdown(label: str, value: str, values: list[tuple[str, str]], on_change: Any) -> ft.Dropdown:
    return ft.Dropdown(
        label=label,
        value=value,
        options=[ft.DropdownOption(key=key, text=display) for key, display in values],
        on_change=on_change,
        border_radius=4,
        border_color=LINE,
        focused_border_color=GREEN,
        bgcolor=PANEL_2,
        color=TEXT,
        text_size=13,
        dense=True,
    )


def metric_value(metrics: dict[str, Any], *keys: str, default: Any = "-") -> Any:
    for key in keys:
        if key in metrics and metrics[key] is not None:
            return metrics[key]
    return default
