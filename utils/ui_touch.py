from PyQt5.QtWidgets import QApplication
from math import sqrt


def _screen_diag_inches() -> float:
    scr = QApplication.primaryScreen()
    if not scr:
        return 0.0
    size_mm = scr.physicalSize()
    if size_mm.width() <= 0 or size_mm.height() <= 0:
        return 0.0
    diag_mm = (size_mm.width() ** 2 + size_mm.height() ** 2) ** 0.5
    return diag_mm / 25.4


def touch_height(base_px: int, small_display_threshold_in: float = 7.5) -> int:
    """Return a touch-friendly height in px based on screen physical size.

    - If the primary screen diagonal is <= small_display_threshold_in (e.g. 7"),
      scale up the base size slightly to make targets finger-friendly.
    - Otherwise return the base size unchanged.

    This keeps sizes reasonable across desktops and small touch displays.
    """
    try:
        diag = _screen_diag_inches()
    except Exception:
        diag = 0.0
    if diag and diag <= small_display_threshold_in:
        # small display: increase target but keep it bounded
        return max(44, int(base_px * 1.15))
    return base_px
