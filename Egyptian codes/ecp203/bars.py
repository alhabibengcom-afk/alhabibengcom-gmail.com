"""أدوات اختيار الأسياخ."""
import math

STANDARD_DIAMETERS = (8, 10, 12, 14, 16, 18, 20, 22, 25, 28, 32)


def bar_area(dia: float) -> float:
    return math.pi * dia ** 2 / 4.0


def choose_bars(as_req: float, b: float, cover: float = 25.0, stirrup: float = 8.0,
                min_dia: int = 12, max_dia: int = 25, min_n: int = 2,
                max_layers: int = 2, clear_min: float = 25.0):
    """أقل عدد أسياخ يحقق المساحة ويدخل في عرض القطاع.

    بيرجع (عدد، قطر، مساحة، عدد الصفوف) أو None.
    """
    best = None
    for d in STANDARD_DIAMETERS:
        if d < min_dia or d > max_dia:
            continue
        n = max(min_n, math.ceil(as_req / bar_area(d) - 1e-9))
        clear = max(clear_min, d)
        per_layer = int((b - 2 * cover - 2 * stirrup + clear) // (d + clear))
        if per_layer < 2:
            continue
        layers = math.ceil(n / per_layer)
        if layers > max_layers:
            continue
        cand = (layers, n * bar_area(d), n, d)
        if best is None or cand < best:
            best = cand
    if best is None:
        return None
    layers, area, n, d = best
    return n, d, area, layers


def fmt(n: int, d: float) -> str:
    return f"{n}Ø{int(d)}"
