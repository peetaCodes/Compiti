"""
NOTE: code generated with chatGPT.
I am sorry, I just couldn't be bothered manually implementing complex logic for each OS/toolkit/SDK.

I am welcome to any pull requests to modify this code to make it better,
as chatGPT/LLMs-generated code is never that great.
"""

from typing import Tuple, Dict, Any, Literal
import tkinter.font as tkFont

from src.system_utils.assets import FONTS
from src.system_utils.assets.font_loader import loadAppFonts

def pointsToPixels(points: float, dpi: float) -> int:
    """
    Convert font size in points to pixels using physical DPI.
    Round and ensure >= 1.
    """
    if dpi is None or dpi <= 0:
        dpi = 72.0
    px = int(round(points * (dpi / 72.0)))
    return max(1, px)

def createScaledFont(root, family: str, points: float, dpi: float, weight: Literal["normal", "bold"] = "normal") -> tkFont.Font:
    """
    Create and return a tkinter.font.Font sized in pixels (negative size) computed from points & dpi.

    - family: font family name (e.g. "Futura", "Segoe UI")
    - points: desired point size in the design spec (e.g. 15, 28)
    - dpi: physical DPI obtained from your platform probe (e.g. getScreenInfo)
    - weight: "normal" or "bold" (optional)

    Returns a tkFont.Font instance you can pass to ttk.Style.configure(..., font=thatFont).
    """
    # compute pixel size (Tk: negative size means pixels)
    px = pointsToPixels(points, dpi)
    # create a named Font (explicitly pass root so fonts are tied to the right Tk instance)
    # use negative px to force pixel-size mode
    try:
        fontObj = tkFont.Font(root=root, family=family, size=-px, weight=weight)
    except (RuntimeError, TypeError):
        # fallback: if family not available, let tk pick system default

        fontObj = tkFont.Font(root=root, size=-px, weight=weight)
    return fontObj

def createFontsForStyle(root, dpi: float, fontSpecs: Dict[str, Tuple[str, float | int, Literal["normal", "bold"], str]]) -> Dict[str, tkFont.Font]:
    """
    Convenience: create a dict of fonts from a font specification dict:
      fontSpecs = { logicalName: (family, points), ... }
    Returns { logicalName: tkFont.Font, ... }
    """
    loadAppFonts(FONTS) # load every locally saved font

    created = {}
    for name, spec in fontSpecs.items():
        family = spec[0]
        points = float(spec[1])
        weight = spec[2] if len(spec) >= 3 else "normal"
        created[name] = createScaledFont(root, family, points, dpi, weight)
    return created

def applyFontsToStyles(style, mapping: Dict[str, tkFont.Font]):
    """
    Apply fonts to ttk/ttkbootstrap styles.

    mapping key: style name (e.g. 'task.danger.TButton')
    mapping value: tkFont.Font instance (not a tuple)
    """
    for styleName, fontObj in mapping.items():
        style.configure(styleName, font=fontObj)

def applyOptionsToStyles(style, mapping: Dict[str, Dict[Any, Any]]):
    """
    Apply fonts to ttk/ttkbootstrap styles.

    mapping key: style name (e.g. 'task.danger.TButton')
    mapping value: tkFont.Font instance (not a tuple)
    """
    for styleName, options in mapping.items():
        style.configure(styleName, **options)