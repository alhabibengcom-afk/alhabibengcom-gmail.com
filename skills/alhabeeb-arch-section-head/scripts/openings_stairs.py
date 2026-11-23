#!/usr/bin/env python3
"""Door/window schedule from DXF blocks, and stair geometry check.

  python3 openings_stairs.py openings plan.dxf [--level GF] [-o openings.xlsx]
      Counts door and window blocks (block or layer name contains DOOR/DR/باب or WIN/WN/شباك/نافذة), grouped by
      block name and by attribute values when the blocks carry attributes (TYPE, TAG, MARK, W, H, WIDTH, HEIGHT,
      FIRE, RATING ...). Output: schedule sheet (type, count, size, fire rating) + list with coordinates.

  python3 openings_stairs.py stair --riser 160 --going 300 --width 1200 --flight-risers 12 --headroom 2200 \
      --floor-height 3200 [--max-riser R --min-going G --min-width W --min-headroom H --max-risers N]
      Geometry: number of risers for the floor height, actual riser, 2R+G comfort (600-650 mm, an architectural
      rule, not code), flight length, landings. Code limits are passed as options: take them from the building
      law / fire code page (egyptian-codes skill) - the OCR text of those clauses is garbled, so the numbers are
      not hard-coded here. Stair width from egress: run egress.py.
"""
import argparse
import math
import re
import sys
from collections import Counter, defaultdict

DOOR = re.compile(r"(door|^dr|-dr|_dr|باب)", re.I)
WIN = re.compile(r"(window|win|^wn|-wn|_wn|شباك|نافذة)", re.I)


def openings(a):
    try:
        import ezdxf
    except ImportError:
        sys.exit("pip install ezdxf")
    doc = ezdxf.readfile(a.dxf)
    rows = []
    for e in doc.modelspace().query("INSERT"):
        nm, ly = e.dxf.name, e.dxf.layer
        kind = "Door" if (DOOR.search(nm) or DOOR.search(ly)) else ("Window" if (WIN.search(nm) or WIN.search(ly)) else None)
        if not kind:
            continue
        att = {}
        try:
            att = {x.dxf.tag.upper(): x.dxf.text for x in e.attribs}
        except Exception:
            pass
        typ = att.get("TYPE") or att.get("MARK") or att.get("TAG") or nm
        w = att.get("W") or att.get("WIDTH")
        h = att.get("H") or att.get("HEIGHT")
        fire = att.get("FIRE") or att.get("RATING") or att.get("FR")
        sx = abs(e.dxf.xscale) if e.dxf.hasattr("xscale") else 1
        rows.append({"kind": kind, "type": typ, "block": nm, "layer": ly, "W": w, "H": h, "fire": fire,
                     "x": round(e.dxf.insert[0]), "y": round(e.dxf.insert[1]), "scale": sx})
    grp = Counter((r["kind"], r["type"], r["W"], r["H"], r["fire"]) for r in rows)
    print(f"{len(rows)} door/window blocks")
    for (k, t, w, h, f), n in sorted(grp.items(), key=lambda x: (x[0][0], str(x[0][1]))):
        print(f"  {k:6} {t:20} x{n}" + (f"  {w}x{h}" if w or h else "") + (f"  fire {f}" if f else ""))
    if a.out:
        import openpyxl
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Schedule"
        ws.append(["Level", "Kind", "Type / mark", "Width", "Height", "Fire rating", "Count", "Ironmongery set",
                   "Material / finish", "Remarks"])
        for (k, t, w, h, f), n in sorted(grp.items(), key=lambda x: (x[0][0], str(x[0][1]))):
            ws.append([a.level, k, t, w, h, f, n, None, None, None])
        ws2 = wb.create_sheet("All blocks")
        ws2.append(["Kind", "Type", "Block", "Layer", "W", "H", "Fire", "X", "Y", "Scale"])
        for r in rows:
            ws2.append([r["kind"], r["type"], r["block"], r["layer"], r["W"], r["H"], r["fire"], r["x"], r["y"], r["scale"]])
        wb.save(a.out)
        print(f"-> {a.out}")
    if any(r["kind"] == "Door" and not r["fire"] for r in rows):
        print("Note: doors without a fire-rating attribute - mark fire doors (stairs, shafts, rooms per ECP 305/1 ch.3).")


def stair(a):
    issues = []
    n = math.ceil(a.floor_height / a.riser) if a.floor_height else None
    R = a.floor_height / n if n else a.riser
    G = a.going
    print(f"Floor height {a.floor_height} mm -> {n} risers of {R:.1f} mm" if n else f"Riser {R} mm")
    c = 2 * R + G
    print(f"2R + G = {c:.0f} mm (comfort range 600-650 mm - architectural rule)")
    if not 600 <= c <= 650:
        issues.append(f"2R+G = {c:.0f} outside 600-650 (comfort)")
    if a.flight_risers and n:
        flights = math.ceil(n / a.flight_risers)
        per = math.ceil(n / flights)
        print(f"Flights: {flights} of up to {per} risers; flight length ~ {(per - 1) * G / 1000:.2f} m (goings = risers - 1)")
        if a.max_risers and per > a.max_risers:
            issues.append(f"{per} risers per flight > {a.max_risers} (limit given)")
    for val, lim, name, op in ((R, a.max_riser, "riser", "<="), (G, a.min_going, "going", ">="),
                               (a.width, a.min_width, "clear width", ">="), (a.headroom, a.min_headroom, "headroom", ">=")):
        if lim and val:
            ok = val <= lim if op == "<=" else val >= lim
            print(f"{'OK  ' if ok else 'FAIL'} {name} {val:.0f} {op} {lim:.0f} mm")
            if not ok:
                issues.append(f"{name} {val:.0f} vs {op} {lim:.0f}")
    if a.riser and n and abs(R - a.riser) > 5:
        issues.append(f"designed riser {a.riser} differs from actual {R:.1f} for this floor height - update the drawing")
    print("Limits not given are not checked: take them from the code page (egyptian-codes) and pass them as options.")
    print(f"{len(issues)} issue(s)" + "".join("\n - " + i for i in issues))


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    s = p.add_subparsers(dest="cmd", required=True)
    x = s.add_parser("openings"); x.add_argument("dxf"); x.add_argument("--level", default="GF"); x.add_argument("-o", "--out")
    x.set_defaults(fn=openings)
    x = s.add_parser("stair")
    for k in ("riser", "going", "width", "headroom", "floor-height", "max-riser", "min-going", "min-width",
              "min-headroom"):
        x.add_argument(f"--{k}", type=float)
    x.add_argument("--flight-risers", type=int)
    x.add_argument("--max-risers", type=int)
    x.set_defaults(fn=stair)
    a = p.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()
