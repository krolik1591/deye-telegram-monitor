"""Constants + lazy font accessors for the image stats renderer.

Fonts are loaded on first access (NOT at import time) so that importing this
module on a system without the usual TTFs — e.g. macOS dev boxes or very
slim Linux containers — doesn't take down the whole bot. If no path we
probe exists, we fall back to Pillow's built-in bitmap default.
"""

import os
import platform
from typing import Literal

from PIL import ImageColor, ImageFont

BaseColor = Literal[
    "white", "black", "red", "green", "blue", "yellow", "cyan", "magenta"
]


def get_color(color: BaseColor):
    return ImageColor.getrgb(color)


# ---------- layout / colors ----------

BLOCK_WIDTH = 20
BLOCK_HEIGHT = 20
BLOCK_SPACING = 5

COLOR_BG = (18, 18, 18)
COLOR_TEXT = (255, 255, 255)

COLOR_ON = (255, 255, 255)
COLOR_OFF = (80, 80, 80)
COLOR_MIXED = (160, 160, 160)

ICON_SIZE = 22
PADDING = 10
ROW_HEIGHT = 32
ICON = "o"


# ---------- fonts (lazy) ----------

def get_font_path():
    system = platform.system()

    if system == "Windows":
        candidates = [
            "C:/Windows/Fonts/DejaVuSans.ttf",
            "C:/Windows/Fonts/segoeui.ttf",
        ]
    elif system == "Linux":
        candidates = [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
            "/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf",
            "/usr/share/fonts/truetype/ubuntu/Ubuntu-Regular.ttf",
        ]
    elif system == "Darwin":  # macOS
        candidates = [
            "/Library/Fonts/Arial.ttf",
            "/System/Library/Fonts/Helvetica.ttc",
            "/System/Library/Fonts/Supplemental/Arial.ttf",
        ]
    else:
        return None

    for path in candidates:
        if os.path.exists(path):
            return path
    return None


_font_cache: dict[int, ImageFont.FreeTypeFont | ImageFont.ImageFont] = {}


def _get_font(size: int):
    cached = _font_cache.get(size)
    if cached is not None:
        return cached

    path = get_font_path()
    try:
        font = ImageFont.truetype(path, size=size) if path else ImageFont.load_default()
    except Exception:
        font = ImageFont.load_default()

    _font_cache[size] = font
    return font


def __getattr__(name: str):
    """Module-level lazy attributes: FONT / FONT_BOLD / FONT_SMALL."""
    sizes = {"FONT": 14, "FONT_BOLD": 16, "FONT_SMALL": 10}
    if name in sizes:
        return _get_font(sizes[name])
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


