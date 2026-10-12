"""Theme constants and window helpers shared by the app's windows."""
import os
import tkinter as tk

import sv_ttk

APP_TITLE = "Prompt Analyzer"
# Tuned for sv-ttk's dark theme.
BG = "#1c1c1c"
FG = "#fafafa"
MUTED_FG = "#9a9a9a"
ERROR_FG = "#ff6b6b"
LINK_FG = "#57c8ff"
CODE_BG = "#2b2b2b"
ACCENT = "Accent.TButton"  # sv-ttk's highlighted button style for primary actions


def apply_theme(root: tk.Tk) -> None:
    sv_ttk.set_theme("dark")
    # sv-ttk sets backgrounds/palette from a <<ThemeChanged>> binding, which Tk 9
    # doesn't deliver; run that step directly (harmless if it already ran).
    root.tk.call("configure_colors")


def enable_dpi_awareness() -> None:
    """Render crisply on scaled displays (125%/150%) instead of being bitmap-stretched."""
    if os.name != "nt":
        return
    try:
        import ctypes
        ctypes.windll.shcore.SetProcessDpiAwareness(1)  # system DPI aware
    except (AttributeError, OSError):
        pass


def scaled(widget: tk.Misc, px: int) -> int:
    """Convert a size designed at 100% (96 DPI) to the current display scaling."""
    return int(px * widget.winfo_fpixels("1i") / 96)


def center(win: tk.Toplevel) -> None:
    win.update_idletasks()
    w, h = win.winfo_reqwidth(), win.winfo_reqheight()
    x = (win.winfo_screenwidth() - w) // 2
    y = (win.winfo_screenheight() - h) // 2
    win.geometry(f"+{x}+{y}")


def dark_title_bar(win: tk.Misc) -> None:
    """Ask Windows 10 (20H1+) / 11 to draw a dark title bar so it matches the theme."""
    if os.name != "nt":
        return
    try:
        import ctypes
        win.update_idletasks()
        hwnd = ctypes.windll.user32.GetParent(win.winfo_id())
        value = ctypes.c_int(1)
        DWMWA_USE_IMMERSIVE_DARK_MODE = 20
        ctypes.windll.dwmapi.DwmSetWindowAttribute(
            hwnd, DWMWA_USE_IMMERSIVE_DARK_MODE, ctypes.byref(value), ctypes.sizeof(value))
    except (AttributeError, OSError):
        pass  # older Windows: keep the default title bar
