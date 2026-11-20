"""محرّك تحليل الإطار المكافئ (Equivalent Frame) للبلاطات المسطحة — رياضيات فقط، بدون معاملات كود.

- شريحة البلاطة (slab-beam) بعرض الإطار l2، وجساءة مكبّرة من محور العمود لوشه: I / (1 − c2/l2)².
- العمود المكافئ: زنبرك دوراني Kec = 1 / (1/ΣKc + 1/Kt) عند كل ركيزة، والأطراف البعيدة للأعمدة مثبتة.
- عناصر Euler-Bernoulli محدودة، والركائز ممنوعة من الهبوط.
- الحل بالتراكب: استجابة لحمل 1 kN/m على كل بحر لوحده، وبعدين أي حالة تحميل = مجموع.

الوحدات: m و kN. معاير المرونة E = 1 (بيتلغي لأن الخرسانة واحدة).
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np


@dataclass
class Support:
    c1: float          # بعد العمود في اتجاه الإطار (m)
    c2: float          # البعد العمودي على الإطار (m)
    H_below: float | None = 3.0
    H_above: float | None = 3.0
    l2_sides: tuple = ()  # أطوال البحور العرضية على جانبي الإطار (m) — لعنصر اللي
    edge: bool = False    # ركيزة طرفية في اتجاه الإطار


@dataclass
class Frame:
    spans: list[float]
    l2: float             # عرض الإطار (m)
    h: float              # سمك البلاطة (m)
    supports: list[Support]
    n_el: int = 40
    # نتائج
    x: np.ndarray = field(default=None, repr=False)
    unit_M: np.ndarray = field(default=None, repr=False)   # [span_loaded, node]
    unit_R: np.ndarray = field(default=None, repr=False)   # [span_loaded, support]
    unit_Mc: np.ndarray = field(default=None, repr=False)  # [span_loaded, support] عزم منقول للأعمدة
    Kec: list = field(default_factory=list)

    def kec(self, s: Support) -> float:
        Ic = s.c2 * s.c1 ** 3 / 12
        Kc = sum(4 * Ic / H for H in (s.H_below, s.H_above) if H)
        x, y = sorted((self.h, s.c1))
        C = (1 - 0.63 * x / y) * x ** 3 * y / 3
        Kt = sum(9 * C / (l2 * (1 - s.c2 / l2) ** 3) for l2 in s.l2_sides if l2 > s.c2)
        if Kc == 0:
            return 0.0
        if Kt == 0:
            return Kc
        return 1 / (1 / Kc + 1 / Kt)

    def solve(self):
        I0 = self.l2 * self.h ** 3 / 12
        xs, EI, span_of = [0.0], [], []
        sup_x = np.concatenate([[0], np.cumsum(self.spans)])
        for j, L in enumerate(self.spans):
            cL, cR = self.supports[j].c1 / 2, self.supports[j + 1].c1 / 2
            pts = sorted({0, cL, L / 2, L - cR, L} | {L * k / self.n_el for k in range(1, self.n_el)})
            for a, b in zip(pts, pts[1:]):
                xm = (a + b) / 2
                in_col = xm < cL or xm > L - cR
                c2 = self.supports[j].c2 if xm < L / 2 else self.supports[j + 1].c2
                I = I0 / (1 - c2 / self.l2) ** 2 if in_col else I0
                xs.append(sup_x[j] + b)
                EI.append(I)
                span_of.append(j)
        xs = np.array(xs)
        n_nodes = len(xs)
        ndof = 2 * n_nodes
        K = np.zeros((ndof, ndof))
        for e in range(n_nodes - 1):
            Le = xs[e + 1] - xs[e]
            k = EI[e] / Le ** 3 * np.array([[12, 6 * Le, -12, 6 * Le], [6 * Le, 4 * Le ** 2, -6 * Le, 2 * Le ** 2],
                                            [-12, -6 * Le, 12, -6 * Le], [6 * Le, 2 * Le ** 2, -6 * Le, 4 * Le ** 2]])
            idx = [2 * e, 2 * e + 1, 2 * e + 2, 2 * e + 3]
            K[np.ix_(idx, idx)] += k
        sup_nodes = [int(np.argmin(abs(xs - sx))) for sx in sup_x]
        self.Kec = [self.kec(s) for s in self.supports]
        for nd, kk in zip(sup_nodes, self.Kec):
            K[2 * nd + 1, 2 * nd + 1] += kk
        fixed = [2 * nd for nd in sup_nodes]
        free = [i for i in range(ndof) if i not in fixed]

        nsp = len(self.spans)
        self.x = xs
        self.unit_M = np.zeros((nsp, n_nodes))
        self.unit_R = np.zeros((nsp, len(sup_nodes)))
        self.unit_Mc = np.zeros((nsp, len(sup_nodes)))
        self._sup_nodes, self._sup_x = sup_nodes, sup_x
        for j in range(nsp):
            f = np.zeros(ndof)
            loaded = [e for e in range(n_nodes - 1) if span_of[e] == j]
            for e in loaded:
                Le = xs[e + 1] - xs[e]
                fe = -np.array([Le / 2, Le ** 2 / 12, Le / 2, -Le ** 2 / 12])  # w = 1 kN/m لأسفل
                f[[2 * e, 2 * e + 1, 2 * e + 2, 2 * e + 3]] += fe
            u = np.zeros(ndof)
            u[free] = np.linalg.solve(K[np.ix_(free, free)], f[free])
            # عزوم العقد (sagging موجب) وردود الأفعال
            M = np.zeros(n_nodes)
            cnt = np.zeros(n_nodes)
            R = np.zeros(ndof)
            for e in range(n_nodes - 1):
                Le = xs[e + 1] - xs[e]
                k = EI[e] / Le ** 3 * np.array([[12, 6 * Le, -12, 6 * Le], [6 * Le, 4 * Le ** 2, -6 * Le, 2 * Le ** 2],
                                                [-12, -6 * Le, 12, -6 * Le], [6 * Le, 2 * Le ** 2, -6 * Le, 4 * Le ** 2]])
                idx = [2 * e, 2 * e + 1, 2 * e + 2, 2 * e + 3]
                fe = -np.array([Le / 2, Le ** 2 / 12, Le / 2, -Le ** 2 / 12]) if e in loaded else np.zeros(4)
                F = k @ u[idx] - fe
                R[idx] += F
                M[e] += -F[1]
                M[e + 1] += F[3]
                cnt[e] += 1
                cnt[e + 1] += 1
            # عند الركيزة: العزم بيقفز بقيمة عزم العمود — نخزن متوسط الجانبين، وعزوم الأوجه بنقراها من جوه البحر
            self.unit_M[j] = M / np.maximum(cnt, 1)
            self.unit_R[j] = [R[2 * nd] for nd in sup_nodes]
            self.unit_Mc[j] = [self.Kec[i] * u[2 * nd + 1] for i, nd in enumerate(sup_nodes)]
        return self

    # -------- قراءة النتائج
    def node_at(self, xg):
        return int(np.argmin(abs(self.x - xg)))

    def face_nodes(self, j):
        """عقد وش الركيزة يمين ويسار البحر j، وعقدة المنتصف."""
        x0 = self._sup_x[j]
        L = self.spans[j]
        cL, cR = self.supports[j].c1 / 2, self.supports[j + 1].c1 / 2
        cL, cR = min(cL, 0.175 * L), min(cR, 0.175 * L)
        return self.node_at(x0 + cL), self.node_at(x0 + L - cR)

    def span_nodes(self, j):
        x0, L = self._sup_x[j], self.spans[j]
        return [i for i, xx in enumerate(self.x) if x0 - 1e-9 <= xx <= x0 + L + 1e-9]

    def combine(self, w_per_span):
        """w_per_span: حمل kN/m لكل بحر (لأسفل موجب) → (M[node], R[support], Mc[support])."""
        w = np.asarray(w_per_span, float)
        return w @ self.unit_M, w @ self.unit_R, w @ self.unit_Mc

    def face_moment(self, w, j, side):
        """العزم عند وش الركيزة من ناحية البحر j (side = 'L' أو 'R') — بيتحسب من داخل البحر."""
        M, _, _ = self.combine(w)
        nL, nR = self.face_nodes(j)
        return M[nL] if side == "L" else M[nR]
