#!/usr/bin/env python3
"""Means of escape check per floor - Egyptian fire code ECP 305/1 (2026), chapter 4.

  python3 egress.py template -o egress.xlsx      sheets: Spaces, Exits, Building (fill them)
  python3 egress.py check egress.xlsx -o egress_check.xlsx

Values below are transcribed in egyptian-codes/references/fire/ECP-305-1-KEY-TABLES.md from the page images.
That file states they are NOT yet human-verified: before a submission, check each value on the PDF page cited.
  Table 4-a  occupant load factors (clause 4-1-1, PDF p.3-4)
  Table 4-b  capacity factors: doors 5 mm/person, corridors & stairs down 8, stairs up 13 (clause 4-1-2, PDF p.5)
  Table 4-c  common path / dead end / travel distance limits (clause 4-3-1-2, PDF p.10)
  Table 4-d  minimum number of exits; single exit conditions (clause 4-4-1, PDF p.13)
  4-4-2      minimum clear widths: corridor/stair/ramp 1100 mm, exit door 900 mm (one leaf), leaf 750-1200 mm
Chapter 6 (occupancy-specific rules) can override these - check it for the occupancy.
"""
import argparse
import math
import sys
from collections import defaultdict

REF = "ECP 305/1-2026"
# use key -> (m2 per person, description, source)
LOAD = {
    "assembly_standing": (0.40, "تجمعات - انتظار وقوفاً", "جدول 4-أ ص3"),
    "assembly_open_seating": (0.60, "تجمعات - مدرجات/ساحات عرض", "جدول 4-أ ص3"),
    "assembly_loose_chairs": (0.80, "تجمعات - مقاعد غير مثبتة", "جدول 4-أ ص3"),
    "assembly_tables": (1.00, "تجمعات - مقاعد وطاولات غير مثبتة", "جدول 4-أ ص3"),
    "library_museum": (5.00, "قاعات قراءة/معارض/متاحف", "جدول 4-أ ص3"),
    "gym_equipment": (10.0, "جيمنازيوم بمعدات ثابتة/ورش فنية", "جدول 4-أ ص3"),
    "gym_open": (2.00, "جيمنازيوم بدون معدات", "جدول 4-أ ص3"),
    "restaurant": (1.40, "مطاعم ومقاهي وكافيتريات", "جدول 4-أ ص3"),
    "worship": (1.00, "دور عبادة بدون مقاعد مثبتة", "جدول 4-أ ص3"),
    "office": (10.0, "إداري (عدا مناطق الجمهور)", "جدول 4-أ ص4"),
    "office_public": (5.00, "مهني / مناطق الجمهور بالإداري", "جدول 4-أ ص4"),
    "retail_ground": (3.00, "تجاري - طابق الصرف وما أسفله", "جدول 4-أ ص4"),
    "retail_upper2": (4.50, "تجاري - الطابقين أعلى طابق الصرف", "جدول 4-أ ص4"),
    "retail_other": (6.00, "تجاري - باقي الأدوار", "جدول 4-أ ص4"),
    "retail_storage": (60.0, "تخزين بالتجاري", "جدول 4-أ ص4"),
    "classroom": (1.90, "فصول دراسية", "جدول 4-أ ص4"),
    "lab_edu": (4.60, "معامل تعليمية", "جدول 4-أ ص4"),
    "multipurpose_edu": (1.25, "قاعات متعددة الاستخدام (تعليمي)", "جدول 4-أ ص4"),
    "lecture": (1.40, "قاعات محاضرات بدون مقاعد ثابتة", "جدول 4-أ ص4"),
    "workshop": (10.0, "ورش حرفية", "جدول 4-أ ص4"),
    "workshop_store": (20.0, "مخازن ورش ح-3", "جدول 4-أ ص4"),
}
# per-room counts instead of area (residential): persons per bedroom
PER_ROOM = {"res_bedroom": (2, "سكني ج-1/ج-2: فردين لكل غرفة نوم", "جدول 4-أ ص4"),
            "res_dorm_room": (4, "سكني ج-3: 4 أفراد للغرفة", "جدول 4-أ ص4")}
CAP = {"door": 5, "corridor": 8, "stair_down": 8, "stair_up": 13, "ramp": 8}  # mm/person, table 4-b p.5
LIMITS = {  # occupancy: (common path unspr, spr, dead end unspr, spr, travel unspr, spr)  table 4-c p.10
    "A": (6, 15, 6, 6, 45, 75), "B": (23, 30, 6, 15, 45, 60), "C": (30, 45, 10, 15, 45, 75),
    "D": (23, 30, 6, 15, 60, 75), "E": (23, 30, 6, 15, 45, 60), "G": (23, 30, 6, 15, 45, 75),
    "H2": (15, 25, 6, 9, 30, 60), "H3": (15, 25, 6, 9, 40, 70)}
MIN_W = {"corridor": 1100, "stair_down": 1100, "stair_up": 1100, "ramp": 1100, "door": 900}  # 4-4-2


def template(a):
    import openpyxl
    from openpyxl.styles import Font
    wb = openpyxl.Workbook()
    b = wb.active
    b.title = "Building"
    for r in (["Occupancy group (A,B,C,D,E,G,H2,H3)", "D"], ["Sprinklered (Y/N)", "N"],
              ["Top floor level above ground m", 15.0], ["Project", ""]):
        b.append(r)
    s = wb.create_sheet("Spaces")
    s.append(["Floor", "Space", "Use key", "Area m2", "Fixed seats / known occupants / bedrooms", "Remarks"])
    s.append(["GF", "Open office", "office", 420, None, ""])
    s.append(["GF", "Reception", "office_public", 60, None, ""])
    e = wb.create_sheet("Exits")
    e.append(["Floor", "Exit", "Type (door/corridor/stair_down/stair_up/ramp)", "Clear width mm",
              "Max travel distance m (measured)", "Max common path m", "Max dead end m"])
    e.append(["GF", "Stair 1 door", "door", 1000, 38, 12, 0])
    e.append(["GF", "Stair 1", "stair_down", 1200, None, None, None])
    k = wb.create_sheet("Use keys")
    k.append(["Use key", "m2/person or persons/room", "Description", "Source (" + REF + ")"])
    for key, (f, d, src) in LOAD.items():
        k.append([key, f, d, src])
    for key, (n, d, src) in PER_ROOM.items():
        k.append([key, f"{n}/room", d, src])
    for w in wb.worksheets:
        for c in w[1]:
            c.font = Font(bold=True)
        for col in w.columns:
            w.column_dimensions[col[0].column_letter].width = 26
    wb.save(a.out)
    print(f"Template: {a.out}")


def check(a):
    import openpyxl
    wb = openpyxl.load_workbook(a.file, data_only=True)
    B = {r[0]: r[1] for r in wb["Building"].iter_rows(values_only=True) if r and r[0]}
    occ = str(B.get("Occupancy group (A,B,C,D,E,G,H2,H3)", "D")).strip().upper()
    spr = str(B.get("Sprinklered (Y/N)", "N")).upper().startswith("Y")
    top = float(B.get("Top floor level above ground m") or 0)
    sp = [r for r in wb["Spaces"].iter_rows(min_row=2, values_only=True) if r and r[0]]
    ex = [r for r in wb["Exits"].iter_rows(min_row=2, values_only=True) if r and r[0]]
    load = defaultdict(float)
    area = defaultdict(float)
    lines = []
    out_rows = []
    for fl, name, key, A, fixed, _ in sp:
        key = str(key or "").strip()
        A = float(A or 0)
        area[fl] += A
        if fixed:
            n = float(fixed) * (PER_ROOM[key][0] if key in PER_ROOM else 1)
            basis = f"{fixed} " + ("rooms x " + str(PER_ROOM[key][0]) if key in PER_ROOM else "known/fixed")
            src = PER_ROOM[key][2] if key in PER_ROOM else "بند 4-1-1 (أ)/(ب)"
        elif key in LOAD:
            n = math.ceil(A / LOAD[key][0])
            basis = f"{A:g} / {LOAD[key][0]}"
            src = LOAD[key][2]
        else:
            lines.append(f"! {fl}/{name}: use key '{key}' unknown - see 'Use keys' sheet")
            continue
        load[fl] += n
        out_rows.append([fl, name, key, A, basis, n, f"{REF} {src}"])
    res = []
    for fl in sorted(load):
        L = load[fl]
        E = [r for r in ex if r[0] == fl]
        nmin = 2
        if occ in ("A", "E"):
            nmin = 4 if L > 1000 else (3 if L > 600 else 2)
        single_ok = occ not in ("A", "H1") and top <= 16 and L <= 60 and area[fl] <= 600
        exits = [r for r in E if str(r[2]).strip() == "door"]
        n_ex = len(exits)
        req = {t: L * CAP[t] for t in CAP}
        prov = defaultdict(float)
        for r in E:
            prov[str(r[2]).strip()] += float(r[3] or 0)
        checks = []
        need = 1 if single_ok else nmin
        checks.append(("Number of exits (doors to exits)", n_ex, f">= {need}" + (" (single exit allowed: 4-4-1-2)" if single_ok else ""),
                       n_ex >= need, "جدول 4-د ص13"))
        for t in ("door", "stair_down", "corridor"):
            if prov[t] or t == "door":
                checks.append((f"Total clear width {t}", f"{prov[t]:.0f} mm", f">= {req[t]:.0f} mm ({L:.0f} x {CAP[t]})",
                               prov[t] >= req[t], "جدول 4-ب ص5"))
        for r in E:
            t = str(r[2]).strip()
            w = float(r[3] or 0)
            if t in MIN_W and w and w < MIN_W[t]:
                checks.append((f"{r[1]} clear width", f"{w:.0f} mm", f">= {MIN_W[t]} mm", False, "بند 4-4-2"))
        lim = LIMITS.get(occ)
        if lim:
            cp, de, tr = (lim[1], lim[3], lim[5]) if spr else (lim[0], lim[2], lim[4])
            for r in E:
                for idx, nm, mx in ((4, "travel distance", tr), (5, "common path", cp), (6, "dead end", de)):
                    if r[idx] not in (None, ""):
                        checks.append((f"{r[1]} {nm}", f"{float(r[idx]):g} m", f"<= {mx} m", float(r[idx]) <= mx,
                                       "جدول 4-ج ص10"))
        res.append((fl, L, area[fl], checks))
    out = openpyxl.Workbook()
    s1 = out.active
    s1.title = "Occupant load"
    s1.append(["Floor", "Space", "Use key", "Area m2", "Basis", "Occupants", "Source"])
    for r in out_rows:
        s1.append(r)
    s2 = out.create_sheet("Checks")
    s2.append(["Floor", "Occupant load", "Check", "Provided", "Required", "OK", "Source (" + REF + ")"])
    nfail = 0
    for fl, L, A, checks in res:
        print(f"Floor {fl}: occupant load {L:.0f} (area {A:g} m2), occupancy {occ}, {'sprinklered' if spr else 'not sprinklered'}")
        for c, pv, rq, ok, src in checks:
            s2.append([fl, L, c, pv, rq, "OK" if ok else "FAIL", src])
            nfail += 0 if ok else 1
            print(f"   {'OK  ' if ok else 'FAIL'} {c}: {pv} vs {rq}  [{src}]")
    s2.append([])
    s2.append(["Values from ECP-305-1-KEY-TABLES.md (transcribed from page images, not yet human-verified): check the "
               "cited PDF pages and chapter 6 for the occupancy before submission."])
    out.save(a.out)
    for l in lines:
        print(l)
    print(f"{nfail} failing check(s) -> {a.out}")


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    s = p.add_subparsers(dest="cmd", required=True)
    x = s.add_parser("template"); x.add_argument("-o", "--out", required=True); x.set_defaults(fn=template)
    x = s.add_parser("check"); x.add_argument("file"); x.add_argument("-o", "--out", required=True); x.set_defaults(fn=check)
    a = p.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()
