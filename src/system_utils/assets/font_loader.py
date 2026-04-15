"""
NOTE: code generated with chatGPT.
I am sorry, I just couldn't be bothered manually implementing complex logic for each OS/toolkit/SDK.

I am welcome to any pull requests to modify this code to make it better,
as chatGPT/LLMs-generated code is never that great.
"""

from __future__ import annotations

import ctypes
import os
import platform
from pathlib import Path
from typing import Mapping


def _load_windows_font(font_path: Path) -> None:
    # AddFontResourceExW(path, FR_PRIVATE, None)
    # FR_PRIVATE = 0x10
    gdi32 = ctypes.windll.gdi32
    gdi32.AddFontResourceExW.argtypes = [ctypes.c_wchar_p, ctypes.c_uint, ctypes.c_void_p]
    gdi32.AddFontResourceExW.restype = ctypes.c_int

    FR_PRIVATE = 0x10
    added = gdi32.AddFontResourceExW(str(font_path), FR_PRIVATE, None)
    if added <= 0:
        raise OSError(f"Windows could not load font: {font_path}")


def _load_macos_font(font_path: Path) -> None:
    # CoreText: CTFontManagerRegisterFontsForURL(url, kCTFontManagerScopeProcess, error)
    corefoundation = ctypes.CDLL(
        "/System/Library/Frameworks/CoreFoundation.framework/CoreFoundation"
    )
    coretext = ctypes.CDLL(
        "/System/Library/Frameworks/CoreText.framework/CoreText"
    )

    corefoundation.CFURLCreateFromFileSystemRepresentation.argtypes = [
        ctypes.c_void_p,        # allocator
        ctypes.c_char_p,        # buffer
        ctypes.c_long,          # buffer length
        ctypes.c_bool,          # isDirectory
    ]
    corefoundation.CFURLCreateFromFileSystemRepresentation.restype = ctypes.c_void_p

    coretext.CTFontManagerRegisterFontsForURL.argtypes = [
        ctypes.c_void_p,                 # URL
        ctypes.c_uint32,                 # scope
        ctypes.POINTER(ctypes.c_void_p), # error
    ]
    coretext.CTFontManagerRegisterFontsForURL.restype = ctypes.c_bool

    path_bytes = os.fsencode(str(font_path))
    url = corefoundation.CFURLCreateFromFileSystemRepresentation(
        None, path_bytes, len(path_bytes), False
    )
    if not url:
        raise OSError(f"macOS could not create file URL for: {font_path}")

    # kCTFontManagerScopeProcess = 1
    error = ctypes.c_void_p()
    ok = coretext.CTFontManagerRegisterFontsForURL(url, 1, ctypes.byref(error))
    if not ok:
        raise OSError(f"macOS could not load font: {font_path}")


def _load_linux_font(font_path: Path) -> None:
    # fontconfig application font database
    from ctypes.util import find_library

    libname = find_library("fontconfig")
    if not libname:
        raise OSError("fontconfig library not found")

    fc = ctypes.CDLL(libname)
    fc.FcConfigAppFontAddFile.argtypes = [ctypes.c_void_p, ctypes.c_char_p]
    fc.FcConfigAppFontAddFile.restype = ctypes.c_int

    added = fc.FcConfigAppFontAddFile(None, os.fsencode(str(font_path)))
    if added == 0:
        raise OSError(f"Linux/fontconfig could not load font: {font_path}")


def loadAppFonts(font_map: Mapping[str, str]) -> None:
    """
    font_map: {"Family Name": "/absolute/path/to/font.ttf", ...}

    Call this before creating Tk() if possible.
    """
    system = platform.system()

    for family, raw_path in font_map.items():
        font_path = Path(raw_path).expanduser().resolve()
        if not font_path.exists():
            raise FileNotFoundError(f"Missing font for {family!r}: {font_path}")

        if system == "Windows":
            _load_windows_font(font_path)
        elif system == "Darwin":
            _load_macos_font(font_path)
        elif system == "Linux":
            _load_linux_font(font_path)
        else:
            raise RuntimeError(f"Unsupported platform: {system}")