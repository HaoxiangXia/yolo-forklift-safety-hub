"""Path helpers for the FastAPI backend."""

from __future__ import annotations

import os
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
STATIC_DIR = ROOT_DIR / "static"
IMAGES_DIR = ROOT_DIR / "images"
ALARMS_IMAGE_DIR = IMAGES_DIR / "alarms"


def resolve_frontend_dist() -> Path:
    candidates = [
        ROOT_DIR / "frontend" / "dist",
        ROOT_DIR / "vue-app" / "dist",
    ]
    for candidate in candidates:
        if (candidate / "index.html").is_file():
            return candidate
    return candidates[0]


FRONTEND_DIST_DIR = resolve_frontend_dist()
FRONTEND_ASSETS_DIR = FRONTEND_DIST_DIR / "assets"
FRONTEND_PUBLIC_DIR = ROOT_DIR / "frontend" / "public"
