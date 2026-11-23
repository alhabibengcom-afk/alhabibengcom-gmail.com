#!/usr/bin/env python3
"""Structural section tools (Al-Habeeb technical office).

  python3 struct_tools.py detailing --fcu 30 --fy 400 [--lap-factor 1.0] [-o detailing.xlsx]
      Anchorage / lap table per bar diameter from the office library (Egyptian codes/ecp203:
      footing.development_length, ECP 203 cl. 4-2-5-1 eq. 4-66/4-67, p.130 - marked unverified in params.py),
      plus 12-dia bend legs and weights. Lap = Ld x --lap-factor: confirm the factor with the ECP 203 splice clause.

  python3 struct_tools.py cubes cubes.xlsx --fcu 30 [--outlier 15] [--min-test-ratio R] [--max-fail-pct P]
                                [--mean-margin M] -o cubes_eval.xlsx
      cubes.xlsx: Pour/Element | Date | Batch (truck) | Cube 1 | Cube 2 | Cube 3 | ...  (N/mm2, 28 days)
      Per batch: test result = mean of >= 3 cubes after excluding any cube deviating more than --outlier % from the
      batch mean (ECP 203 ch.8, quality control - the % is garbled in the OCR: confirm it); within-batch range,
      standard deviation and coefficient of variation; overall mean, standard deviation, CoV, characteristic
      estimate (mean - 1.64 s). Acceptance limits are YOUR inputs from ECP 203 ch.8 (PDF page of
      'Ch08-Quality-Control'): --min-test-ratio (no single result below R x fcu), --max-fail-pct, --mean-margin
      (mean of consecutive results >= fcu + M). Without them the tool reports the statistics only.

  python3 struct_tools.py pours pours.xlsx -o pour_summary.xlsx
      Pour register: Element | Level | Volume m3 | Date | Grade | Cubes taken -> totals per level and grade, cube
      sets vs volume (compare with the sampling rule you enter: --m3-per-set).
"""
import argparse
import math
import os
import statistics as stt
import sys
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
DIAS = (8, 10, 12, 14, 16, 18, 20, 22, 25, 28, 32)


def find_lib():
    for base in (os.getcwd(), os.path.join(HERE, "..", "..", ".."), os.path.join(HERE, "..", "..", "..", "..")):
        p = os.path.abspath(os.path.join(base, "Egyptian codes"))
        if os.path.isdir(os.path.join(p, "ecp203")):
            return p
    return None


def detailing(a):
    lib = a.lib or find_lib()
    if not lib:
        sys.exit("Cannot find 'Egyptian codes/ecp203' (pass --lib)")
    sys.path.insert(0, lib)
    from ecp203.footing import development_length
    from ecp203 import params as P
    rows = []
    print(f"fcu {a.fcu} N/mm2, fy {a.fy} N/mm2 - {P.REF_LD.clause} (PDF p.{P.REF_LD.page}"
          f"{', unverified: ' + P.REF_LD.note if not P.REF_LD.verified else ''})")
    print(f"{'Dia':>4}{'Ld mm':>8}{'Lap mm':>8}{'Ld/Ø':>7}{'12Ø leg':>9}{'kg/m':>7}")
    for d in DIAS:
        Ld, fbu = development_length(a.fy, a.fcu, d)
        lap = math.ceil(Ld * a.lap_factor / 10) * 10
        rows.append([d, math.ceil(Ld / 10) * 10, lap, round(Ld / d, 1), 12 * d, round(d * d / 162, 3)])
        print(f"{d:>4}{rows[-1][1]:>8}{lap:>8}{rows[-1][3]:>7}{12 * d:>9}{rows[-1][5]:>7}")
    print(f"fbu = {fbu:.3f} N/mm2. Lap = Ld x {a.lap_factor} (confirm with the ECP 203 splice clause, ch.4-2-5 / ch.7).")
    if a.out:
        import openpyxl
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Detailing"
        ws.append([f"ECP 203 anchorage table - fcu {a.fcu}, fy {a.fy}, lap factor {a.lap_factor}"])
        ws.append(["Dia mm", "Ld mm", "Lap mm", "Ld/dia", "12 dia leg mm", "kg/m"])
        for r in rows:
            ws.append(r)
        ws.append([])
        ws.append([f"Source: {P.REF_LD.clause}, PDF p.{P.REF_LD.page}; minimum Ld {P.REF_LD_MIN.clause}. "
                   "Values marked unverified in params.py - check the code page before issue."])
        wb.save(a.out)
        print(f"-> {a.out}")


def cubes(a):
    import openpyxl
    wb = openpyxl.load_workbook(a.file, data_only=True)
    ws = wb.active
    hdr = [str(c.value or "").strip() for c in ws[1]]
    cube_cols = [i for i, h in enumerate(hdr) if h.lower().startswith("cube")]
    out = []
    results = []
    for r in ws.iter_rows(min_row=2, values_only=True):
        if not r or r[0] is None:
            continue
        vals = [float(r[i]) for i in cube_cols if i < len(r) and r[i] not in (None, "")]
        if len(vals) < 3:
            out.append([r[0], r[1], r[2], len(vals), None, None, None, None, "excluded: fewer than 3 cubes"])
            continue
        m = stt.mean(vals)
        kept = [v for v in vals if abs(v - m) / m * 100 <= a.outlier]
        note = "" if len(kept) == len(vals) else f"{len(vals) - len(kept)} cube(s) excluded (> {a.outlier}% from mean)"
        if len(kept) < 2:
            kept = vals
            note += "; too many outliers - batch kept, investigate"
        res = stt.mean(kept)
        rng = max(kept) - min(kept)
        sd = stt.stdev(kept) if len(kept) > 1 else 0
        results.append((r[0], r[1], r[2], res))
        out.append([r[0], r[1], r[2], len(vals), round(res, 2), round(rng, 2), round(sd, 2),
                    round(sd / res * 100, 1), note])
    vals = [x[3] for x in results]
    if not vals:
        sys.exit("No batch with 3+ cubes")
    mean = stt.mean(vals)
    sd = stt.stdev(vals) if len(vals) > 1 else 0
    fck_est = mean - 1.64 * sd
    print(f"Batches: {len(vals)}  mean {mean:.2f}  s {sd:.2f}  CoV {sd / mean * 100:.1f}%  mean-1.64s = {fck_est:.2f} "
          f"N/mm2 (fcu {a.fcu})")
    checks = []
    if a.min_test_ratio:
        lim = a.min_test_ratio * a.fcu
        low = [x for x in results if x[3] < lim]
        checks.append((f"No test result below {a.min_test_ratio} x fcu = {lim:.1f}", not low,
                       f"{len(low)} below: " + ", ".join(f"{x[0]}/{x[2]} {x[3]:.1f}" for x in low[:8])))
    if a.max_fail_pct is not None:
        nf = sum(1 for x in results if x[3] < a.fcu)
        pct = nf / len(results) * 100
        checks.append((f"Results below fcu <= {a.max_fail_pct}%", pct <= a.max_fail_pct, f"{nf}/{len(results)} = {pct:.0f}%"))
    if a.mean_margin is not None:
        checks.append((f"Mean >= fcu + {a.mean_margin}", mean >= a.fcu + a.mean_margin, f"mean {mean:.2f}"))
    for c, ok, d in checks:
        print(f"  {'OK  ' if ok else 'FAIL'} {c}: {d}")
    if not checks:
        print("  Acceptance limits not given: enter them from ECP 203 ch.8 (--min-test-ratio, --max-fail-pct, --mean-margin).")
    o = openpyxl.Workbook()
    s1 = o.active
    s1.title = "Batches"
    s1.append(["Pour/Element", "Date", "Batch", "Cubes", "Test result N/mm2", "Range", "s (batch)", "CoV %", "Note"])
    for r in out:
        s1.append(r)
    s2 = o.create_sheet("Summary")
    for r in (["fcu", a.fcu], ["Batches", len(vals)], ["Mean", round(mean, 2)], ["Std deviation", round(sd, 2)],
              ["CoV %", round(sd / mean * 100, 1)], ["Mean - 1.64 s", round(fck_est, 2)], []):
        s2.append(r)
    for c, ok, d in checks:
        s2.append([c, "OK" if ok else "FAIL", d])
    s2.append(["Acceptance rules from ECP 203-2020 ch.8 (Quality control) - the OCR of the percentages is garbled: "
               "values used here are the ones entered by the engineer."])
    o.save(a.out)
    print(f"-> {a.out}")


def pours(a):
    import openpyxl
    ws = openpyxl.load_workbook(a.file, data_only=True).active
    hdr = [str(c.value or "").strip().lower() for c in ws[1]]
    ix = {k: next((i for i, h in enumerate(hdr) if k in h), None) for k in ("element", "level", "volume", "grade", "cube")}
    tot = defaultdict(float)
    sets = defaultdict(float)
    rows = []
    for r in ws.iter_rows(min_row=2, values_only=True):
        if not r or r[0] is None:
            continue
        lv = r[ix["level"]] if ix["level"] is not None else "-"
        gr = r[ix["grade"]] if ix["grade"] is not None else "-"
        v = float(r[ix["volume"]] or 0)
        c = float(r[ix["cube"]] or 0) if ix["cube"] is not None else 0
        tot[(lv, gr)] += v
        sets[(lv, gr)] += c
        need = math.ceil(v / a.m3_per_set) if a.m3_per_set else None
        rows.append([r[ix["element"]] if ix["element"] is not None else r[0], lv, gr, v, c, need,
                     "" if need is None or c >= need else "fewer cube sets than the sampling rule"])
    o = openpyxl.Workbook()
    s = o.active
    s.title = "Pours"
    s.append(["Element", "Level", "Grade", "Volume m3", "Cube sets", "Required sets", "Note"])
    for r in rows:
        s.append(r)
    s2 = o.create_sheet("Totals")
    s2.append(["Level", "Grade", "Volume m3", "Cube sets"])
    for (lv, gr), v in sorted(tot.items(), key=lambda x: str(x[0])):
        s2.append([lv, gr, round(v, 2), sets[(lv, gr)]])
        print(f"  {lv} {gr}: {v:.1f} m3, {sets[(lv, gr)]:.0f} cube sets")
    o.save(a.out)
    print(f"-> {a.out}" + ("" if a.m3_per_set else "  (pass --m3-per-set from the ECP 203 ch.8 sampling rule to check sets)"))


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    s = p.add_subparsers(dest="cmd", required=True)
    x = s.add_parser("detailing")
    x.add_argument("--fcu", type=float, required=True)
    x.add_argument("--fy", type=float, default=400)
    x.add_argument("--lap-factor", type=float, default=1.0)
    x.add_argument("--lib")
    x.add_argument("-o", "--out")
    x.set_defaults(fn=detailing)
    x = s.add_parser("cubes")
    x.add_argument("file")
    x.add_argument("--fcu", type=float, required=True)
    x.add_argument("--outlier", type=float, default=15.0, help="%% deviation from batch mean to exclude a cube (verify)")
    x.add_argument("--min-test-ratio", type=float)
    x.add_argument("--max-fail-pct", type=float)
    x.add_argument("--mean-margin", type=float)
    x.add_argument("-o", "--out", required=True)
    x.set_defaults(fn=cubes)
    x = s.add_parser("pours")
    x.add_argument("file")
    x.add_argument("--m3-per-set", type=float)
    x.add_argument("-o", "--out", required=True)
    x.set_defaults(fn=pours)
    a = p.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()
