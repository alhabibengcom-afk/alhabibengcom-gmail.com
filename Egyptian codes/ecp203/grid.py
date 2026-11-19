"""تعريف سقف على شبكة محاور منتظمة وتقسيمه لإطارات مكافئة في الاتجاهين."""
from __future__ import annotations

from dataclasses import dataclass, field
from itertools import product

from .efm import Frame, Support


@dataclass
class Grid:
    x: list[float]                 # إحداثيات المحاور في اتجاه X (m)
    y: list[float]                 # إحداثيات المحاور في اتجاه Y (m)
    h: float                       # سمك البلاطة (mm)
    col: tuple = (500, 500)        # (cx, cy) mm — cx في اتجاه X
    col_override: dict = field(default_factory=dict)   # {"i,j": [cx, cy]} — i و j رقم المحور من 1
    H_below: float | None = 3.2    # ارتفاع الدور تحت السقف (m)
    H_above: float | None = 3.2    # ارتفاع الدور فوق السقف (m) — None للسقف الأخير

    def col_size(self, i, j):
        v = self.col_override.get(f"{i + 1},{j + 1}")
        return tuple(v) if v else tuple(self.col)

    def location(self, i, j):
        ex = i in (0, len(self.x) - 1)
        ey = j in (0, len(self.y) - 1)
        return "corner" if ex and ey else "edge" if (ex or ey) else "interior"

    def columns(self):
        return list(product(range(len(self.x)), range(len(self.y))))

    def frames(self, direction):
        """بيرجع [(اسم الإطار، index الخط، Frame)] — direction = 'x' أو 'y'."""
        along, across = (self.x, self.y) if direction == "x" else (self.y, self.x)
        out = []
        spans = [b - a for a, b in zip(along, along[1:])]
        for k, _ in enumerate(across):
            left = across[k] - across[k - 1] if k > 0 else 0.0
            right = across[k + 1] - across[k] if k < len(across) - 1 else 0.0
            l2 = left / 2 + right / 2
            sups = []
            for m in range(len(along)):
                i, j = (m, k) if direction == "x" else (k, m)
                cx, cy = self.col_size(i, j)
                c1, c2 = (cx, cy) if direction == "x" else (cy, cx)
                sups.append(Support(c1=c1 / 1000, c2=c2 / 1000, H_below=self.H_below, H_above=self.H_above,
                                    l2_sides=tuple(s for s in (left, right) if s > 0),
                                    edge=m in (0, len(along) - 1)))
            name = f"{'X' if direction == 'x' else 'Y'}-{k + 1}"
            out.append((name, k, Frame(spans, l2, self.h / 1000, sups).solve()))
        return out

    def tributary(self, i, j):
        """مساحة التحميل للعمود (m²)."""
        def half(arr, k):
            a = (arr[k] - arr[k - 1]) / 2 if k > 0 else 0.0
            b = (arr[k + 1] - arr[k]) / 2 if k < len(arr) - 1 else 0.0
            return a + b
        return half(self.x, i) * half(self.y, j)
