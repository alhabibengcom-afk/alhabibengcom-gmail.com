#!/usr/bin/env python3
"""Design slabs / rafts from SAFE results with the office ECP 203 library, and draw the reinforcement sheet.

Input: SAFE tables (from safe_live.py, or Display > Show Tables > Export to Excel by hand):
  * strip forces  (design strip moments)          -> ecp203 design_slab_strip per strip (top and bottom)
  * soil pressures (rafts)                         -> max bearing pressure vs --q-allow, uplift check
  * punching shear design                          -> ratios, failing columns listed
  * point coordinates (optional)                   -> plan with punching ratios
Columns are matched by NAME (fuzzy), because SAFE versions label fields differently. The script prints which
field it used for the moment and the strip width - check them on the first run with a new SAFE version.

    python safe_design.py --tables safe_tables.xlsx --t 600 --q-allow 150 --fcu 30 -o out --project Raft
    --auto-resize : thicken the slab by 50 mm steps until every strip and punching ratio passes
"""
import argparse
import math
import os
import re
import sys
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import model_reader as MR  # noqa: E402


def col(rec, *names, contains=None):
    nk = {MR.norm(k): k for k in rec}
    for n in names:
        if MR.norm(n) in nk:
            return nk[MR.norm(n)]
    if contains:
        for k in rec:
            if all(c in MR.norm(k) for c in contains):
                return k
    return None


def find(T, *words, avoid=()):
    for name, t in T.items():
        n = name.lower()
        if all(w in n for w in words) and not any(x in n for x in avoid) and t["records"]:
            return name, t
    return None, None


def strip_envelopes(recs, combos, width_default, log):
    r0 = recs[0]
    k_strip = col(r0, "Strip", "StripName", "Label", contains=["strip"])
    k_case = col(r0, "OutputCase", "Output Case", "LoadCase", "Combo", "Case")
    k_station = col(r0, "Station", "Distance", contains=["station"])
    moment_cols = [k for k in r0 if re.fullmatch(r"m\d?|moment.*", MR.norm(k))]
    if not moment_cols:
        sys.exit(f"No moment field in the strip table. Fields: {list(r0)}")
    # the bending moment of a strip is the moment field with the largest magnitudes
    k_m = max(moment_cols, key=lambda k: max(abs(MR.fnum(r[k], 0) or 0) for r in recs))
    k_wl = col(r0, contains=["width", "left"])
    k_wr = col(r0, contains=["width", "right"])
    k_w = col(r0, "Width", "StripWidth", "GlobalWidth")
    log.append(f"strip table: strip='{k_strip}', moment='{k_m}' (of {moment_cols}), "
               f"width={'left+right' if k_wl and k_wr else (k_w or f'--strip-width {width_default}')}")
    env = {}
    for r in recs:
        case = str(r.get(k_case, "")) if k_case else ""
        if combos and case not in combos:
            continue
        s = str(r.get(k_strip, "?"))
        m = MR.fnum(r.get(k_m), 0.0) or 0.0
        if k_wl and k_wr:
            w = (MR.fnum(r.get(k_wl), 0) or 0) + (MR.fnum(r.get(k_wr), 0) or 0)
        elif k_w:
            w = MR.fnum(r.get(k_w), 0) or 0
        else:
            w = width_default
        w = w or width_default
        e = env.setdefault(s, {"Mpos": 0.0, "Mneg": 0.0, "w": w, "stations": set()})
        e["w"] = max(e["w"], w) if e["w"] else w
        e["Mpos"] = max(e["Mpos"], m / w)
        e["Mneg"] = max(e["Mneg"], -m / w)
        if k_station:
            e["stations"].add(MR.fnum(r.get(k_station), 0))
    return env


def design(a, T, lib, t, reports):
    sys.path.insert(0, lib)
    from ecp203.slab import design_slab_strip
    log, out = [], {"strips": [], "soil": None, "punch": [], "t": t}
    name, tb = find(T, "strip", avoid=("design", "definition", "connect", "object"))
    if not tb:
        name, tb = find(T, "strip")
    if tb:
        combos = set(a.combos.split(",")) if a.combos else None
        env = strip_envelopes(tb["records"], combos, a.strip_width, log)
        for s, e in sorted(env.items()):
            rep = design_slab_strip(t, a.fcu, a.fy, round(e["Mpos"], 1), round(e["Mneg"], 1), title=f"Strip {s} (t={t})")
            reports.append(rep)
            R = rep.results
            out["strips"].append({"strip": s, "w": e["w"], "Mpos": e["Mpos"], "Mneg": e["Mneg"], "bot": R.get("bottom") or "",
                                  "top": R.get("top") or "", "ok": rep.ok,
                                  "fail": [c.desc for c in rep.checks if not c.ok]})
    else:
        log.append("no strip forces table found")
    name, sp = find(T, "soil", "pressure")
    if sp:
        r0 = sp["records"][0]
        k_p = col(r0, "Pressure", "SoilPressure", contains=["pressure"])
        k_case = col(r0, "OutputCase", "Output Case", "LoadCase", "Combo", "Case")
        svc = set(a.service_combos.split(",")) if a.service_combos else None
        vals = [MR.fnum(r.get(k_p)) for r in sp["records"]
                if MR.fnum(r.get(k_p)) is not None and (not svc or str(r.get(k_case, "")) in svc)]
        if vals:
            if min(vals) < 0:  # SAFE convention: compression negative
                comp, uplift = -min(vals), max(vals) > 0
            else:  # table already gives compression as positive
                comp, uplift = max(vals), False
            out["soil"] = {"max": comp, "q_allow": a.q_allow, "ok": a.q_allow is None or comp <= a.q_allow,
                           "uplift": uplift, "cases": "service: " + (",".join(sorted(svc)) if svc else "all cases")}
            log.append(f"soil pressure field '{k_p}'")
    name, pu = find(T, "punch")
    if pu:
        r0 = pu["records"][0]
        k_r = col(r0, "Ratio", "DCRatio", "ShearRatio", contains=["ratio"])
        k_pt = col(r0, "Point", "Label", "UniqueName", "Joint")
        k_x, k_y = col(r0, "GlobalX", "X"), col(r0, "GlobalY", "Y")
        best = {}
        for r in pu["records"]:
            ratio = MR.fnum(r.get(k_r)) if k_r else None
            if ratio is None:
                continue
            p = str(r.get(k_pt, "?"))
            if p not in best or ratio > best[p]["ratio"]:
                best[p] = {"point": p, "ratio": ratio, "x": MR.fnum(r.get(k_x)) if k_x else None,
                           "y": MR.fnum(r.get(k_y)) if k_y else None}
        out["punch"] = sorted(best.values(), key=lambda d: -d["ratio"])
        log.append(f"punching ratio field '{k_r}'")
    out["ok"] = all(s["ok"] for s in out["strips"]) and all(p["ratio"] <= 1.0 for p in out["punch"]) and \
        (out["soil"] is None or out["soil"]["ok"])
    return out, log


def draw(res, a, path, short):
    from building_design import Sheet, find_template, preview
    tpl = a.template or find_template()
    for N in (50, 75, 100, 125, 150, 200):
        S = Sheet(tpl, N)
        S.text(f"SLAB / RAFT REINFORCEMENT FROM SAFE  (t = {res['t']} mm)", 0, S.th(10), 5, "ST-TEXT")
        rows = [[s["strip"], f"{s['w']:.2f}", f"{s['Mpos']:.0f}", f"{s['Mneg']:.0f}", short(s["bot"]) or "-",
                 short(s["top"]) or "-", "OK" if s["ok"] else "CHECK"] for s in res["strips"]]
        yb = S.table(0, 0, ["Strip", "Width m", "M+ kN.m/m", "M- kN.m/m", "Bottom", "Top", "ECP 203"], rows,
                     [S.th(16), S.th(14), S.th(18), S.th(18), S.th(20), S.th(20), S.th(14)], h=2.0)
        x2 = S.th(130)
        prow = [[p["point"], f"{p['ratio']:.2f}", "OK" if p["ratio"] <= 1 else "FAIL"] for p in res["punch"][:40]]
        if prow:
            S.text("PUNCHING (SAFE ratios, worst first)", x2, S.th(4), 3, "ST-TEXT")
            S.table(x2, 0, ["Point", "Ratio", ""], prow, [S.th(16), S.th(14), S.th(12)], h=2.0)
        notes = [f"fcu = {a.fcu} N/mm2, fy = {a.fy} N/mm2. Strip moments from SAFE, per metre = strip moment / strip "
                 "width; steel by ECP 203 (ecp203 design_slab_strip).",
                 "Bottom = sagging (span) steel, Top = hogging (support / column) steel of each design strip; "
                 "minimum steel both ways everywhere."]
        if res["soil"]:
            sp = res["soil"]
            notes.append(f"Max soil pressure {sp['max']:.0f} kN/m2 ({sp['cases']}) vs allowable "
                         f"{sp['q_allow']} -> {'OK' if sp['ok'] else 'EXCEEDS - enlarge raft or improve soil'}"
                         + ("; uplift (tension) present - check" if sp["uplift"] else ""))
        for k, n in enumerate(notes):
            S.text(f"{k + 1}. {n}", 0, yb - S.th(6) - k * S.th(5), 2.5, "ST-TEXT")
        if S.fits():
            break
    S.finish(path, a.title_fields("SLAB/RAFT REINFORCEMENT (SAFE)", "120", N, "ZZ"))
    preview(path, path[:-4] + ".png")
    return N


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--tables", required=True, help="xlsx / csv / .f2k with SAFE tables")
    p.add_argument("--t", type=float, help="slab/raft thickness mm (default: from the slab property table)")
    p.add_argument("--fcu", type=float, default=30)
    p.add_argument("--fy", type=float, default=400)
    p.add_argument("--q-allow", type=float)
    p.add_argument("--combos", help="ultimate combinations for strip design (default all)")
    p.add_argument("--service-combos", help="service combinations for soil pressure (default all)")
    p.add_argument("--strip-width", type=float, default=1.0, help="m, only if the table has no width")
    p.add_argument("--auto-resize", action="store_true")
    p.add_argument("--project", default="PROJECT")
    p.add_argument("--client", default="-")
    p.add_argument("--project-code", default="PRJ")
    p.add_argument("--lib")
    p.add_argument("--template")
    p.add_argument("-o", "--out", required=True)
    a = p.parse_args()
    from building_design import find_lib, short
    lib = a.lib or find_lib(os.path.dirname(os.path.abspath(a.tables)))
    if not lib:
        sys.exit("Cannot find 'Egyptian codes/ecp203'; pass --lib")
    os.makedirs(a.out, exist_ok=True)
    T = MR.read_any_tables(a.tables)
    t = a.t
    if not t:
        _, sp = find(T, "slab", "propert")
        if sp:
            k = col(sp["records"][0], contains=["thick"])
            vals = [MR.fnum(r.get(k)) for r in sp["records"] if k and MR.fnum(r.get(k))]
            if vals:
                t = max(vals) * (1000 if max(vals) < 5 else 1)
    if not t:
        sys.exit("Slab thickness unknown: pass --t (mm)")
    t = round(t)

    def title_fields(title, num, N, loc, level="ZZ"):
        return {"PROJECT": a.project, "CLIENT": a.client, "DWG_TITLE": title, "LEVEL": level,
                "DWG_NO": f"{a.project_code}-ST-{loc}-{num}", "REV": "R00", "SCALE": f"1:{N}", "SHEET_SIZE": "A1",
                "PURPOSE": "للمراجعة", "DRAWN": "Claude (auto)"}
    a.title_fields = title_fields
    reports = []
    res, log = design(a, T, lib, t, reports)
    t0 = t
    while a.auto_resize and not res["ok"] and t < t0 + 400:
        # soil pressure is not solved by thickness; stop if only the soil check fails
        if all(s["ok"] for s in res["strips"]) and all(p["ratio"] <= 1 for p in res["punch"]):
            break
        t += 50
        if res["punch"]:
            # punching capacity grows roughly with d^2 (perimeter and depth): scale SAFE ratios as an estimate
            d0, d1 = t0 - 75, t - 75
            scale = (d0 / d1) * ((d0 + 500) / (d1 + 500))
            T_p = [{**pp, "ratio": pp["ratio"] * scale} for pp in res["punch"]]
        reports = []
        res, log = design(a, T, lib, t, reports)
        if res["punch"]:
            res["punch"] = T_p
            res["ok"] = all(s["ok"] for s in res["strips"]) and all(p["ratio"] <= 1 for p in res["punch"]) and \
                (res["soil"] is None or res["soil"]["ok"])
    for l in log:
        print("  " + l)
    if t != t0:
        print(f"RESIZED: thickness {t0} -> {t} mm to pass ECP 203 (punching ratios estimated - re-run SAFE with t={t}).")
    print(f"Strips: {len(res['strips'])} ({sum(1 for s in res['strips'] if not s['ok'])} failing)")
    for s in res["strips"]:
        print(f"  {s['strip']}: w={s['w']:.2f} m  M+ {s['Mpos']:.0f}  M- {s['Mneg']:.0f} kN.m/m  bottom {short(s['bot'])}"
              f"  top {short(s['top'])}" + ("" if s["ok"] else "  FAIL"))
    if res["soil"]:
        sp = res["soil"]
        print(f"Soil: max {sp['max']:.0f} kN/m2 vs {sp['q_allow']}: {'OK' if sp['ok'] else 'EXCEEDS'}")
    if res["punch"]:
        print(f"Punching: worst {res['punch'][0]['point']} = {res['punch'][0]['ratio']:.2f}; "
              f"{sum(1 for p in res['punch'] if p['ratio'] > 1)} failing")
    with open(os.path.join(a.out, "safe_design.md"), "w", encoding="utf-8") as f:
        f.write("\n\n".join(r.to_markdown() for r in reports))
    import openpyxl
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Strips"
    ws.append(["Strip", "Width m", "M+ kN.m/m", "M- kN.m/m", "t mm", "Bottom", "Top", "OK", "Failing"])
    for s in res["strips"]:
        ws.append([s["strip"], s["w"], round(s["Mpos"], 1), round(s["Mneg"], 1), t, short(s["bot"]), short(s["top"]),
                   "yes" if s["ok"] else "NO", "; ".join(s["fail"])])
    ws = wb.create_sheet("Punching")
    ws.append(["Point", "Ratio", "OK"])
    for pp in res["punch"]:
        ws.append([pp["point"], round(pp["ratio"], 3), "yes" if pp["ratio"] <= 1 else "NO"])
    wb.save(os.path.join(a.out, "safe_design.xlsx"))
    path = os.path.join(a.out, f"{a.project_code}-ST-ZZ-120_R00.dxf")
    N = draw(res, a, path, short)
    print(f"Files: {path} (1:{N}), safe_design.xlsx, safe_design.md")


if __name__ == "__main__":
    main()
