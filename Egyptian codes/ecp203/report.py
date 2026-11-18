"""سجل خطوات الحساب وتصديره كتقرير Markdown."""
from __future__ import annotations

from dataclasses import dataclass, field

from .params import Ref


def _fmt(v):
    if not isinstance(v, float):
        return v
    if v != 0 and abs(v) < 0.1:
        return f"{v:.5f}"
    return f"{v:,.3f}".rstrip("0").rstrip(".")


@dataclass
class Step:
    desc: str
    formula: str
    subst: str
    value: float | str
    unit: str
    ref: Ref | None


@dataclass
class Check:
    desc: str
    demand: float
    capacity: float
    unit: str
    ok: bool
    ref: Ref | None
    relation: str = "≤"


@dataclass
class Report:
    title: str
    inputs: dict = field(default_factory=dict)
    steps: list[Step] = field(default_factory=list)
    checks: list[Check] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    results: dict = field(default_factory=dict)

    def step(self, desc, formula, subst, value, unit="", ref=None):
        self.steps.append(Step(desc, formula, subst, value, unit, ref))
        return value

    def check(self, desc, demand, capacity, unit="", ref=None, relation="≤"):
        ok = demand <= capacity + 1e-9 if relation == "≤" else demand >= capacity - 1e-9
        self.checks.append(Check(desc, demand, capacity, unit, ok, ref, relation))
        return ok

    def note(self, text):
        if text not in self.notes:
            self.notes.append(text)

    @property
    def ok(self) -> bool:
        return all(c.ok for c in self.checks)

    def unverified_refs(self) -> list[Ref]:
        seen, out = set(), []
        for r in [s.ref for s in self.steps] + [c.ref for c in self.checks]:
            if r is not None and not r.verified and r.clause not in seen:
                seen.add(r.clause)
                out.append(r)
        return out

    def to_markdown(self) -> str:
        L = [f"# {self.title}", ""]
        if self.inputs:
            L += ["## المدخلات", "", "| البند | القيمة |", "|---|---|"]
            L += [f"| {k} | {v} |" for k, v in self.inputs.items()]
            L.append("")
        L += ["## خطوات الحساب", ""]
        i = 0
        for s in self.steps:
            if not s.formula and s.value == "" and s.desc.startswith("—"):
                L += [f"### {s.desc.strip('— ')}", ""]
                continue
            i += 1
            val = _fmt(s.value)
            L.append(f"**{i}. {s.desc}**")
            if s.formula:
                L.append(f"- المعادلة: `{s.formula}`")
            if s.subst:
                L.append(f"- التعويض: `{s.subst}`")
            L.append(f"- النتيجة: **{val} {s.unit}**")
            if s.ref:
                L.append(f"- المرجع: {s.ref}")
            L.append("")
        if self.checks:
            L += ["## التحققات", "", "| التحقق | المطلوب | الحد | النتيجة | المرجع |", "|---|---|---|---|---|"]
            for c in self.checks:
                L.append(f"| {c.desc} | {c.demand:,.2f} {c.unit} | {c.relation} {c.capacity:,.2f} {c.unit} | "
                         f"{'✓' if c.ok else '✗'} | {c.ref or ''} |")
            L.append("")
            L.append(f"**الحكم العام: {'آمن ✓' if self.ok else 'غير آمن ✗ — راجع البنود المعلّمة'}**")
            L.append("")
        if self.results:
            L += ["## النتائج", ""]
            L += [f"- {k}: **{v}**" for k, v in self.results.items()]
            L.append("")
        if self.notes:
            L += ["## ملاحظات", ""] + [f"- {n}" for n in self.notes] + [""]
        unv = self.unverified_refs()
        if unv:
            L += ["## ⚠️ قيم تحتاج تحقق من PDF الكود", "",
                  "القيم دي اتاخدت من المعرفة العامة أو من نص OCR غير واضح:", ""]
            L += [f"- {r.clause} — صفحة {r.page or '؟'}: {r.note}" for r in unv]
            L.append("")
        L += ["---", "_الحسابات للمساعدة والمراجعة فقط. لازم يراجعها ويعتمدها مهندس إنشائي مسؤول قبل التنفيذ._"]
        return "\n".join(L)
