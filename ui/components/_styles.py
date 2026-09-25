"""Centralised, token-driven stylesheet builders for design-system components.

Every value comes from :mod:`ui.theme`; components call these helpers so there
is no per-widget hardcoded colour, spacing or radius. Reusing these keeps all
cards, buttons, progress bars and dividers visually consistent.
"""
from __future__ import annotations

from ui import theme


def dialog_qss(name: str) -> str:
    return f"QDialog#{name} {{ background: {theme.SURFACE}; }}"


def card_qss(name: str) -> str:
    return (
        f"QFrame#{name} {{ background: {theme.SURFACE}; "
        f"border: 1px solid {theme.LINE}; "
        f"border-radius: {theme.RADIUS_MD}px; }}"
    )


def accent_card_qss(name: str) -> str:
    return (
        f"QFrame#{name} {{ background: {theme.ACCENT_SOFT}; "
        f"border: 1px solid {theme.ACCENT}; "
        f"border-radius: {theme.RADIUS_MD}px; }}"
    )


def progressbar_qss(name: str) -> str:
    return (
        f"QProgressBar#{name} {{ background: {theme.SURFACE_ALT}; border: none; "
        f"border-radius: {theme.RADIUS_SM}px; }} "
        f"QProgressBar#{name}::chunk {{ background: {theme.ACCENT}; "
        f"border-radius: {theme.RADIUS_SM}px; }}"
    )


def primary_button_qss(name: str) -> str:
    return (
        f"QPushButton#{name} {{ background: {theme.ACCENT}; color: #ffffff; "
        f"border: none; border-radius: {theme.RADIUS_MD}px; "
        f"padding: {theme.SPACE_2}px {theme.SPACE_4}px; }} "
        f"QPushButton#{name}:hover {{ background: {theme.ACCENT_DARK}; }}"
    )


def secondary_button_qss(name: str) -> str:
    return (
        f"QPushButton#{name} {{ background: {theme.SURFACE}; color: {theme.INK}; "
        f"border: 1px solid {theme.LINE_STRONG}; border-radius: {theme.RADIUS_MD}px; "
        f"padding: {theme.SPACE_2}px {theme.SPACE_4}px; }} "
        f"QPushButton#{name}:hover {{ background: {theme.SURFACE_ALT}; }}"
    )


def divider_qss(name: str) -> str:
    return f"QFrame#{name} {{ background: {theme.LINE}; border: none; }}"


def label_color_qss(color: str) -> str:
    return f"color: {color};"
