"""
NOTE: code generated with chatGPT.
I am sorry, I just couldn't be bothered manually implementing complex logic for each OS/toolkit/SDK.

I am welcome to any pull requests to modify this code to make it better,
as chatGPT/LLMs-generated code is never that great.
"""

import os
import platform
import re
import subprocess
import json
import ctypes
from typing import Tuple, Optional

def getScreenInfo(root) -> Tuple[float, Tuple[int, int], float]:
    """
    Single entry point. Return (dpi, (pixelWidth, pixelHeight), backingScale).

    root: a Tk root/toplevel object with methods:
        - winfo_screenwidth()
        - winfo_screenheight()
        - winfo_fpixels('1i')
        - winfo_id() (on Windows for per-monitor DPI)
    """
    system = platform.system()

    if system == "Darwin":
        info = _getMacDisplayPhysicalInfoTk(root)
        if info is not None:
            return info

    if system == "Windows":
        info = _getWindowsScreenInfo(root)
        if info is not None:
            return info

    # Linux-like: attempt Wayland-aware detection first if env suggests Wayland,
    # otherwise try X11 methods.
    info = _getLinuxScreenInfo(root)
    if info is not None:
        return info

    # Last resort: use Tk's logical points (might be 72 on macOS)
    try:
        fallbackDpi = float(root.winfo_fpixels("1i"))
    except (AttributeError, ValueError):
        fallbackDpi = 72.0
    fallbackSize = (root.winfo_screenwidth(), root.winfo_screenheight())
    return fallbackDpi, fallbackSize, 1.0


# macOS implementation
class CGSize(ctypes.Structure):
    _fields_ = [("width", ctypes.c_double), ("height", ctypes.c_double)]

def _getMacDisplayPhysicalInfoTk(root):
    """
    Return (dpi, (pixel_w, pixel_h), backingScale) or None on failure.
    Uses CoreGraphics via ctypes. Does not swallow generic exceptions.
    """
    try:
        core = ctypes.CDLL("/System/Library/Frameworks/CoreGraphics.framework/CoreGraphics")
    except OSError:
        return None

    # CGMainDisplayID() -> CGDirectDisplayID (uint32)
    core.CGMainDisplayID.restype = ctypes.c_uint32

    # CGDisplayPixelsWide/High(CGDirectDisplayID) -> size_t
    core.CGDisplayPixelsWide.argtypes = [ctypes.c_uint32]
    core.CGDisplayPixelsWide.restype = ctypes.c_size_t
    core.CGDisplayPixelsHigh.argtypes = [ctypes.c_uint32]
    core.CGDisplayPixelsHigh.restype = ctypes.c_size_t

    # CGDisplayScreenSize(CGDirectDisplayID) -> CGSize (two doubles)
    core.CGDisplayScreenSize.argtypes = [ctypes.c_uint32]
    core.CGDisplayScreenSize.restype = CGSize

    try:
        mainDpy = core.CGMainDisplayID()
    except (AttributeError, OSError):
        # function not available / unexpected
        return None

    try:
        pixel_w = int(core.CGDisplayPixelsWide(mainDpy))
        pixel_h = int(core.CGDisplayPixelsHigh(mainDpy))
    except (AttributeError, OSError):
        return None

    try:
        mmSize = core.CGDisplayScreenSize(mainDpy)  # CGSize instance
        mm_w = float(mmSize.width)
        mm_h = float(mmSize.height)
    except (AttributeError, OSError):
        # cant get physical size; return nominal 72dpi x backing
        mm_w = mm_h = 0.0

    # Compute DPI only when mm are sensible
    if mm_w > 1e-6 and mm_h > 1e-6:
        dpi_x = pixel_w / (mm_w / 25.4)
        dpi_y = pixel_h / (mm_h / 25.4)
        dpi = (dpi_x + dpi_y) / 2.0
    else:
        # If physical mm unknown, use logical fallback (72 * backing)
        # compute backing vs Tk logical width if possible
        try:
            tk_logical_w = int(root.winfo_screenwidth())
            backing = float(pixel_w) / float(tk_logical_w) if tk_logical_w > 0 else 1.0
        except Exception:
            backing = 1.0
        dpi = 72.0 * backing
        return round(float(dpi), 2), (int(pixel_w), int(pixel_h)), float(backing)

    # compute backing scale vs Tk logical width
    try:
        tk_logical_w = int(root.winfo_screenwidth())
        backing = float(pixel_w) / float(tk_logical_w) if tk_logical_w > 0 else 1.0
    except Exception:
        backing = 1.0

    return round(float(dpi), 2), (int(pixel_w), int(pixel_h)), float(backing)


# Windows implementation
def _getWindowsScreenInfo(root) -> Optional[Tuple[float, Tuple[int, int], float]]:
    """
    Windows: prefer GetDpiForMonitor (Shcore) per-monitor; fallback to GetDeviceCaps.
    Returns None if neither succeeded.
    """
    # Try GetDpiForMonitor via Shcore.dll (available on Windows 8.1+)
    try:
        shcore = ctypes.WinDLL("Shcore")
        user32 = ctypes.WinDLL("user32")
    except OSError:
        shcore = None
        user32 = None

    if shcore is not None and user32 is not None:
        try:
            MonitorFromWindow = user32.MonitorFromWindow
            MonitorFromWindow.argtypes = [ctypes.c_void_p, ctypes.c_uint]
            MonitorFromWindow.restype = ctypes.c_void_p

            hwnd = ctypes.c_void_p(int(root.winfo_id()))
            MONITOR_DEFAULTTONEAREST = 2
            hmonitor = MonitorFromWindow(hwnd, MONITOR_DEFAULTTONEAREST)

            GetDpiForMonitor = shcore.GetDpiForMonitor
            GetDpiForMonitor.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.POINTER(ctypes.c_uint), ctypes.POINTER(ctypes.c_uint)]
            dpiX = ctypes.c_uint()
            dpiY = ctypes.c_uint()
            MDT_EFFECTIVE_DPI = 0
            res = GetDpiForMonitor(hmonitor, MDT_EFFECTIVE_DPI, ctypes.byref(dpiX), ctypes.byref(dpiY))
            if res == 0:
                dpi = float((dpiX.value + dpiY.value) / 2.0)
                pixelW = int(root.winfo_screenwidth())
                pixelH = int(root.winfo_screenheight())
                scale = dpi / 72.0
                return dpi, (pixelW, pixelH), float(scale)
        except (AttributeError, OSError, ValueError):
            # Shcore exists but call failed/unexpected signature; continue to fallback
            pass

    # Fallback: GetDeviceCaps via gdi32
    try:
        user32 = ctypes.WinDLL("user32")
        gdi32 = ctypes.WinDLL("gdi32")
        hdc = user32.GetDC(0)
        LOGPIXELSX = 88
        LOGPIXELSY = 90
        dpiX = gdi32.GetDeviceCaps(hdc, LOGPIXELSX)
        dpiY = gdi32.GetDeviceCaps(hdc, LOGPIXELSY)
        user32.ReleaseDC(0, hdc)
        dpi = float((dpiX + dpiY) / 2.0)
        pixelW = int(root.winfo_screenwidth())
        pixelH = int(root.winfo_screenheight())
        return dpi, (pixelW, pixelH), float(dpi / 72.0)
    except OSError:
        return None
    except (AttributeError, ValueError):
        return None


# Linux (Wayland / X11) implementation
def _getLinuxScreenInfo(root) -> Optional[Tuple[float, Tuple[int, int], float]]:
    """
    Attempt Wayland-aware detection, then X11 detection. Returns None if detection fails.
    Detection order:
      - GDK (PyGObject) on Wayland/X11
      - sway (swaymsg get_outputs)
      - wayland-info parsing
      - environment variables (GDK/Qt)
      - xrandr parsing
      - xdpyinfo
    """
    # Determine session type and environment
    xdgType = os.environ.get("XDG_SESSION_TYPE", "").lower()
    waylandDisplay = os.environ.get("WAYLAND_DISPLAY")
    isWayland = bool(waylandDisplay) or xdgType == "wayland"

    # 1) Try GDK (PyGObject) - works on Wayland and X11 when available
    try:
        from gi.repository import Gdk  # type: ignore
    except ImportError:
        Gdk = None

    if Gdk is not None:
        info = _getWaylandInfoViaGdk(Gdk, root)
        if info is not None:
            return info

    # 2) If Wayland Env, try compositor helpers (sway, wayland-info)
    if isWayland:
        info = _getSwayOutputs()
        if info is not None:
            return info

        info = _getWaylandInfoFromTool()
        if info is not None:
            return info

        # Check environment variables (GDK_SCALE, GDK_DPI_SCALE, QT_SCALE_FACTOR) as deliberate last-resort step
        info = _getInfoFromEnvVars(root)
        if info is not None:
            return info

        # If none of the above work and we are on Wayland, do not jump to X11 heuristics automatically.
        # Fall through to try xrandr/xdpyinfo only if the display server is actually X11 or if xrandr is present
        # (some Wayland compositors provide XWayland/xrandr compatibility)
        # Continue intentionally — attempt xrandr if available
        pass

    # 3) Try xrandr (works when X server or XWayland present)
    xrInfo = _getXrandrInfo()
    if xrInfo is not None:
        return xrInfo

    # 4) Try xdpyinfo (X11)
    xdInfo = _getXdpyinfo()
    if xdInfo is not None:
        return xdInfo

    return None

def _getWaylandInfoViaGdk(GdkModule, root) -> Optional[Tuple[float, Tuple[int, int], float]]:
    """
    Use Gdk (PyGObject) to obtain monitor geometry, scale and (when available) physical size.
    Returns None if Gdk reports nothing usable.
    """
    try:
        display = GdkModule.Display.get_default()
    except AttributeError:
        # Older/newer API differences may exist; try fallback
        try:
            display = GdkModule.Display.get_default()  # repeated to satisfy static analyzers
        except AttributeError:
            return None
    if display is None:
        return None

    # Try monitor-based API (GTK4) then fallback to screen (GTK3)
    monitor = None
    try:
        # GTK4: Display.get_n_monitors / Display.get_monitor
        nMonitors = display.get_n_monitors()
        if nMonitors <= 0:
            return None
        monitor = display.get_monitor(0)
    except AttributeError:
        try:
            screen = GdkModule.Screen.get_default()
            if screen is None:
                return None
            nMonitors = screen.get_n_monitors()
            if nMonitors <= 0:
                return None
            monitor = screen.get_monitor(0)
        except AttributeError:
            return None

    if monitor is None:
        return None

    # Determine scale
    scale = 1.0
    try:
        scale = float(monitor.get_scale())
    except (AttributeError, TypeError, ValueError):
        try:
            scale = float(monitor.get_scale_factor())
        except (AttributeError, TypeError, ValueError):
            scale = 1.0

    # Geometry: application pixels (logical) for GTK; multiply by scale to get device pixels
    try:
        geom = monitor.get_geometry()
        appW = int(geom.width)
        appH = int(geom.height)
        pixelW = int(appW * scale)
        pixelH = int(appH * scale)
    except (AttributeError, TypeError):
        # fallback to Tk logical pixels times scale
        try:
            pixelW = int(root.winfo_screenwidth() * scale)
            pixelH = int(root.winfo_screenheight() * scale)
        except (AttributeError, ValueError):
            return None

    # Try physical size (mm) if API available
    dpi = None
    try:
        mmW = float(monitor.get_physical_width())
        mmH = float(monitor.get_physical_height())
        if mmW > 0 and mmH > 0:
            dpiX = pixelW / (mmW / 25.4)
            dpiY = pixelH / (mmH / 25.4)
            dpi = (dpiX + dpiY) / 2.0
    except (AttributeError, TypeError, ValueError):
        # physical size not available; use 72 * scale as reasonable base
        dpi = 72.0 * scale

    return float(dpi), (pixelW, pixelH), float(scale)

def _getSwayOutputs() -> Optional[Tuple[float, Tuple[int, int], float]]:
    """
    Query sway via `swaymsg -t get_outputs -r` and parse JSON. Returns None if swaymsg is not available
    or output doesn't produce a usable monitor entry.
    """
    try:
        out = _runSubprocess(["swaymsg", "-t", "get_outputs", "-r"])
    except subprocess.CalledProcessError:
        return None
    try:
        outputs = json.loads(out)
    except (json.JSONDecodeError, TypeError, ValueError):
        return None

    for o in outputs:
        try:
            if not o.get("active", True):
                continue
            scale = float(o.get("scale", 1.0))
            # determine pixel resolution
            pixelW = None
            pixelH = None
            if "current_mode" in o and isinstance(o["current_mode"], dict):
                pixelW = int(o["current_mode"].get("width", 0))
                pixelH = int(o["current_mode"].get("height", 0))
            elif "rect" in o and isinstance(o["rect"], dict):
                pixelW = int(o["rect"].get("width", 0))
                pixelH = int(o["rect"].get("height", 0))
            elif "modes" in o and isinstance(o["modes"], list) and o["modes"]:
                # pick first mode as fallback
                try:
                    pixelW = int(o["modes"][0].get("width", 0))
                    pixelH = int(o["modes"][0].get("height", 0))
                except (TypeError, ValueError):
                    pixelW = None
                    pixelH = None

            if pixelW is None or pixelH is None:
                continue

            # attempt to compute DPI if mm info present
            dpi = None
            mmW = o.get("width_mm")
            mmH = o.get("height_mm")
            if mmW is not None and mmH is not None:
                try:
                    mmWf = float(mmW)
                    mmHf = float(mmH)
                    if mmWf > 0 and mmHf > 0:
                        dpi = (pixelW / (mmWf / 25.4) + pixelH / (mmHf / 25.4)) / 2.0
                except (TypeError, ValueError):
                    dpi = None
            if dpi is None:
                dpi = 72.0 * scale

            return float(dpi), (int(pixelW), int(pixelH)), float(scale)
        except (KeyError, TypeError, ValueError):
            continue
    return None

def _getWaylandInfoFromTool() -> Optional[Tuple[float, Tuple[int, int], float]]:
    """
    Try parsing `wayland-info` output if available. `wayland-info` output formats vary,
    but many include "physical size", "current mode" and "scale" attributes.
    """
    try:
        raw = _runSubprocess(["wayland-info"])
    except subprocess.CalledProcessError:
        return None

    parsed = _parseWaylandInfoOutput(raw)
    if parsed is None:
        return None
    dpi, (pw, ph), scale = parsed
    return float(dpi), (int(pw), int(ph)), float(scale)

def _parseWaylandInfoOutput(raw: str) -> Optional[Tuple[float, Tuple[int, int], float]]:
    """
    Parse common patterns from `wayland-info` output.
    Example heuristics:
      - look for "current mode: <w> x <h>"
      - look for "physical size: <w> x <h> mm"
      - look for "scale: <n>"
    Returns None if parsing fails.
    """
    if not raw:
        return None

    # Try to find the first output block
    # crude approach: search for "Output" or "output" sections
    outputBlocks = re.split(r"\n(?:Output|output)\b", raw, flags=re.IGNORECASE)
    # first block before the first "Output" is likely header; iterate blocks after it
    for block in outputBlocks[1:]:
        # parse current mode
        modeMatch = re.search(r"current mode[:\s]*([0-9]+)\s*[x×]\s*([0-9]+)", block, flags=re.IGNORECASE)
        if not modeMatch:
            # sometimes "current mode: <w>x<h> @ <refresh>" or "mode: <w> x <h> (preferred)"
            modeMatch = re.search(r"([0-9]+)\s*[x×]\s*([0-9]+)\s*(?:@|\()", block)
        if not modeMatch:
            continue
        try:
            pw = int(modeMatch.group(1))
            ph = int(modeMatch.group(2))
        except (IndexError, ValueError):
            continue

        # physical size mm
        mmMatch = re.search(r"physical size[:\s]*([0-9]+)\s*[x×]\s*([0-9]+)\s*mm", block, flags=re.IGNORECASE)
        mmW = mmH = None
        if mmMatch:
            try:
                mmW = float(mmMatch.group(1))
                mmH = float(mmMatch.group(2))
            except (IndexError, ValueError):
                mmW = mmH = None

        # scale
        scaleMatch = re.search(r"scale[:\s]*([0-9]+(?:\.[0-9]+)?)", block, flags=re.IGNORECASE)
        scale = 1.0
        if scaleMatch:
            try:
                scale = float(scaleMatch.group(1))
            except ValueError:
                scale = 1.0

        # compute DPI if mm available
        dpi = None
        if mmW and mmH:
            if mmW > 0 and mmH > 0:
                dpiX = pw / (mmW / 25.4)
                dpiY = ph / (mmH / 25.4)
                dpi = (dpiX + dpiY) / 2.0
        if dpi is None:
            dpi = 72.0 * scale

        return dpi, (pw, ph), scale

    return None

def _getInfoFromEnvVars(root) -> Optional[Tuple[float, Tuple[int, int], float]]:
    """
    Use commonly set environment variables that indicate scaling:
      - GDK_SCALE (integer scale)
      - GDK_DPI_SCALE (float)
      - QT_SCALE_FACTOR
    Return None if no relevant env vars found.
    """
    gdkScale = os.environ.get("GDK_SCALE")
    gdkDpiScale = os.environ.get("GDK_DPI_SCALE")
    qtScale = os.environ.get("QT_SCALE_FACTOR") or os.environ.get("QT_SCALE")
    if not any([gdkScale, gdkDpiScale, qtScale]):
        return None

    scale = 1.0
    try:
        if gdkScale:
            scale = float(gdkScale)
        elif qtScale:
            scale = float(qtScale)
    except ValueError:
        # invalid value; ignore env-based detection
        return None

    dpi = 72.0 * scale
    try:
        pixelW = int(root.winfo_screenwidth() * scale)
        pixelH = int(root.winfo_screenheight() * scale)
    except (AttributeError, ValueError):
        pixelW = root.winfo_screenwidth()
        pixelH = root.winfo_screenheight()

    # If GDK_DPI_SCALE present, consider it multiplicative for font DPI
    try:
        if gdkDpiScale:
            dpi = dpi * float(gdkDpiScale)
    except ValueError:
        pass

    return float(dpi), (int(pixelW), int(pixelH)), float(scale)

def _getXrandrInfo() -> Optional[Tuple[float, Tuple[int, int], float]]:
    """
    Parse xrandr output to find the connected output and the current mode and physical size.
    Returns None if xrandr is not present or parsing yields nothing usable.
    """
    try:
        out = _runSubprocess(["xrandr", "--verbose"])
    except subprocess.CalledProcessError:
        return None

    parsed = _parseXrandrOutput(out)
    return parsed

def _parseXrandrOutput(raw: str) -> Optional[Tuple[float, Tuple[int, int], float]]:
    """
    Parse xrandr --verbose output. Heuristics:
     - find first line with "<name> connected" and pick that output block
     - within block, find "current <w> x <h>" or mode line marked with '*' or "preferred"
     - find "physical size: <w> x <h> mm" or "Physical size" variants
     - find "scale" entry (often shown as "scale x:y" in newer xrandr)
    """
    if not raw:
        return None

    lines = raw.splitlines()
    # Find start indices of connected outputs
    outputIndices = []
    for idx, line in enumerate(lines):
        if re.search(r"\bconnected\b", line):
            outputIndices.append(idx)

    if not outputIndices:
        return None

    # Choose the first connected output block that's not disconnected
    for startIdx in outputIndices:
        # gather block until next output or EOF
        endIdx = len(lines)
        for j in range(startIdx + 1, len(lines)):
            if re.search(r"^[^\s].*\bconnected\b", lines[j]):
                endIdx = j
                break
        block = "\n".join(lines[startIdx:endIdx])

        # Determine pixel resolution: look for "current <w> x <h>"
        curMatch = re.search(r"current\s+([0-9]+)\s*x\s*([0-9]+)", block)
        pw = ph = None
        if curMatch:
            try:
                pw = int(curMatch.group(1))
                ph = int(curMatch.group(2))
            except (IndexError, ValueError):
                pw = ph = None

        # If not found, look for mode marked with '*' (active mode)
        if pw is None:
            modeMatch = re.search(r"^\s*([0-9]+)x([0-9]+)\s+.*\*", block, flags=re.MULTILINE)
            if modeMatch:
                try:
                    pw = int(modeMatch.group(1))
                    ph = int(modeMatch.group(2))
                except (IndexError, ValueError):
                    pw = ph = None

        # physical size
        mmMatch = re.search(r"Physical size:\s*([0-9]+)x([0-9]+)\s*mm", block, flags=re.IGNORECASE)
        mmW = mmH = None
        if mmMatch:
            try:
                mmW = float(mmMatch.group(1))
                mmH = float(mmMatch.group(2))
            except (IndexError, ValueError):
                mmW = mmH = None

        # scale (xrandr may show "scale: 1.00x1.00" or newer "scale" lines)
        scale = 1.0
        scaleMatch = re.search(r"scale[:\s]*([0-9]+(?:\.[0-9]+)?)x([0-9]+(?:\.[0-9]+)?)", block)
        if scaleMatch:
            try:
                sx = float(scaleMatch.group(1))
                sy = float(scaleMatch.group(2))
                # pick sx as representative
                scale = sx
            except ValueError:
                scale = 1.0
        else:
            # sometimes xrandr lacks scale; attempt to infer from DPI if mm present
            pass

        if pw is None:
            continue

        dpi = None
        if mmW and mmH:
            if mmW > 0 and mmH > 0:
                dpi = (pw / (mmW / 25.4) + ph / (mmH / 25.4)) / 2.0
        if dpi is None:
            dpi = 72.0 * scale

        return float(dpi), (int(pw), int(ph)), float(scale)

    return None

def _getXdpyinfo() -> Optional[Tuple[float, Tuple[int, int], float]]:
    """
    Parse xdpyinfo output for resolution. Returns None if xdpyinfo is unavailable or parsing fails.
    """
    try:
        out = _runSubprocess(["xdpyinfo"])
    except subprocess.CalledProcessError:
        return None

    # parse a line like: "  resolution:    96x96 dots per inch"
    m = re.search(r"resolution:\s*([0-9]+)x([0-9]+)\s*dots per inch", out, flags=re.IGNORECASE)
    if m:
        try:
            dpi = float(m.group(1))
            # Tk logical pixel size as fallback for width/height
            # Many X servers report resolution but not pixel dims via xdpyinfo; use Tk for pixel dims
            # Caller should pass a Tk root to get actual pixel width/height if needed.
            # Here, we simply return None for pixel dims because xdpyinfo lacks them reliably.
            return dpi, (0, 0), float(dpi / 72.0)
        except (IndexError, ValueError):
            return None
    return None


# Utilities
def _runSubprocess(args: list) -> str:
    """
    Run a subprocess and return stdout decoded as UTF-8.
    Raises subprocess.CalledProcessError on non-zero exit code.
    Raises FileNotFoundError if binary not found.
    """
    try:
        proc = subprocess.run(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
    except FileNotFoundError:
        raise subprocess.CalledProcessError(returncode=127, cmd=args, output=b"", stderr=b"")
    except subprocess.CalledProcessError:
        raise
    stdout = proc.stdout.decode("utf-8", errors="ignore")
    return stdout