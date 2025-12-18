from platform import system
from typing import Union

from screeninfo import get_monitors

def getResolution() -> tuple[int, int]:
    for m in get_monitors():
        if m.is_primary: return m.width, m.height
    return 1920, 1080

def getDpi(root) -> tuple[Union[float, int], str]:
    """
    Cross-platform DPI detection for Tkinter.
    Returns (dpi_x, dpi_y, method_string).

    - Windows: Uses per-monitor APIs (GetDpiForWindow/GetDpiForMonitor)
    - macOS: Uses CoreGraphics (Quartz) to compute from pixel and mm size
    - Linux/other: Uses Tk-reported screenmmwidth/height
    """
    # --- Windows path ---
    if system() == "Windows":
        try:
            import ctypes
            user32 = ctypes.windll.user32
            gdi32 = ctypes.windll.gdi32
            hwnd = root.winfo_id()

            # Try GetDpiForWindow (Windows 10+)
            try:
                GetDpiForWindow = user32.GetDpiForWindow # noqa
                GetDpiForWindow.restype = ctypes.c_uint
                dpi = GetDpiForWindow(hwnd)
                return round(float(dpi), 3), "GetDpiForWindow"
            except: # noqa
                pass

            # Try GetDpiForMonitor via shcore.dll (Windows 8.1+)
            try:
                shcore = ctypes.windll.shcore
            except: # noqa
                shcore = None
            if shcore is not None:
                try:
                    MONITOR_DEFAULTTONEAREST = 2
                    MonitorFromWindow = user32.MonitorFromWindow # noqa
                    MonitorFromWindow.restype = ctypes.c_void_p
                    hmonitor = MonitorFromWindow(hwnd, MONITOR_DEFAULTTONEAREST)

                    MDT_EFFECTIVE_DPI = 0
                    GetDpiForMonitor = shcore.GetDpiForMonitor # noqa
                    GetDpiForMonitor.argtypes = [ctypes.c_void_p, ctypes.c_int,
                                                 ctypes.POINTER(ctypes.c_uint), ctypes.POINTER(ctypes.c_uint)]
                    dpi_x = ctypes.c_uint()
                    dpi_y = ctypes.c_uint()
                    res = GetDpiForMonitor(hmonitor, MDT_EFFECTIVE_DPI,
                                           ctypes.byref(dpi_x), ctypes.byref(dpi_y))
                    if res == 0:
                        return round(float(dpi_x.value), 3), "GetDpiForMonitor"
                except: # noqa
                    pass

            # Fallback: GetDeviceCaps
            try:
                hdc = user32.GetDC(0) # noqa
                LOGPIXELSX = 88
                LOGPIXELSY = 90
                dpi_x = gdi32.GetDeviceCaps(hdc, LOGPIXELSX) # noqa
                dpi_y = gdi32.GetDeviceCaps(hdc, LOGPIXELSY) # noqa
                user32.ReleaseDC(0, hdc) # noqa
                if dpi_x and dpi_y:
                    return round(float(dpi_x), 3), "GetDeviceCaps"
            except: # noqa
                pass
        except: # noqa
            pass

    # --- macOS path ---
    if system() == "Darwin":
        try:
            import ctypes
            from ctypes import util

            # Load Quartz framework
            quartz = ctypes.cdll.LoadLibrary(util.find_library("Quartz"))

            # Define CoreGraphics types
            quartz.CGMainDisplayID.restype = ctypes.c_uint32
            quartz.CGDisplayScreenSize.argtypes = [ctypes.c_uint32]
            quartz.CGDisplayScreenSize.restype = ctypes.c_double * 2  # this is incorrect, so we handle manually

            # Get display ID
            display_id = quartz.CGMainDisplayID()

            # CGDisplayPixelsWide / CGDisplayPixelsHigh
            quartz.CGDisplayPixelsWide.argtypes = [ctypes.c_uint32]
            quartz.CGDisplayPixelsWide.restype = ctypes.c_size_t
            quartz.CGDisplayPixelsHigh.argtypes = [ctypes.c_uint32]
            quartz.CGDisplayPixelsHigh.restype = ctypes.c_size_t

            width_px = quartz.CGDisplayPixelsWide(display_id)
            height_px = quartz.CGDisplayPixelsHigh(display_id)

            # CGDisplayScreenSize returns CGSize in millimeters
            class CGSize(ctypes.Structure):
                _fields_ = [("width", ctypes.c_double),
                            ("height", ctypes.c_double)]
            quartz.CGDisplayScreenSize.restype = CGSize

            size = quartz.CGDisplayScreenSize(display_id)
            width_mm = size.width
            height_mm = size.height

            if width_mm > 0 and height_mm > 0:
                dpi_x = width_px / (width_mm / 25.4)
                dpi_y = height_px / (height_mm / 25.4)
                return round(float((dpi_x + dpi_y)/2), 3), "Quartz"
        except: # noqa
            return 96, "default"

    # --- Linux or fallback path ---
    try:
        screen_w_px = root.winfo_screenwidth()
        screen_h_px = root.winfo_screenheight()
        screen_w_mm = root.winfo_screenmmwidth()
        screen_h_mm = root.winfo_screenmmheight()
        if screen_w_mm and screen_h_mm:
            dpi_x = screen_w_px / (screen_w_mm / 25.4)
            dpi_y = screen_h_px / (screen_h_mm / 25.4)
            return round(float((dpi_x + dpi_y)/2), 3), "screenmm"
    except: # noqa
        pass

    # --- Last resort ---
    try:
        dpi_px = root.winfo_fpixels('1i')
        if 20 < dpi_px < 1000:
            return 96.0, "default"
    except: # noqa
        pass

    return 96.0, "default"