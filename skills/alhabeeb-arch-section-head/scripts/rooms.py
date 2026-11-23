#!/usr/bin/env python3
"""Rooms, finishes schedule and finishes quantities for the architectural section.

  python3 rooms.py from-dxf plan.dxf [--layers "AR-ROOM,ROOM,A-AREA"] [--text-layers "AR-TEXT,ROOM-NAME"]
                   [--level GF] [--units mm] -o rooms.xlsx
      Rooms = closed polylines on the room/area layers; name = the text/MTEXT whose insertion point lies inside.
      Doors/windows (blocks whose name or layer contains DOOR/DR/باب or WIN/WN/شباك) inside or on a room
      boundary are counted per room. Output: one row per room with area, perimeter and blank finish codes.

  python3 rooms.py template -o rooms.xlsx          empty rooms sheet + finishes legend to fill by hand

  python3 rooms.py finishes rooms.xlsx -o finishes_schedule.xlsx
      Reads the "Rooms" sheet (codes filled) and the "Finishes" legend, and writes:
        * Room finish schedule (per room: floor, skirting, walls, ceiling, height, quantities)
        * Quantities by finish code (floor m², skirting m, walls m², ceiling m²) per level and total
        * Checks: missing codes, codes not in the legend, wet rooms without waterproofing code, rooms with no
          ceiling height
      Deductions: skirting = perimeter - door widths; walls = perimeter x (ceiling height) - door and window areas
      (as entered); nothing deducted for columns unless the perimeter already follows them.
"""
import argparse
import math
import os
import re
import sys
from collections import OrderedDict, defaultdict

ROOM_COLS = ["Level", "Room No.", "Room name", "Area m2", "Perimeter m", "Ceiling height m",
             "Floor code", "Skirting code", "Wall code", "Ceiling code", "Wet room (Y/N)",
             "Doors (no.)", "Door widths total m", "Door height m", "Windows area m2", "Remarks"]
FIN_COLS = ["Code", "Type (Floor/Skirting/Wall/Ceiling/Waterproofing)", "Description", "Spec ref / BOQ item",
            "Approved material (MS ref)", "Unit"]
WET = re.compile(r"(wc|toilet|bath|kitchen|pantry|laundry|حمام|مطبخ|دورة|غسيل|بوفيه|تواليت|mosque ablution|وضوء)", re.I)
DOOR = re.compile(r"(door|^dr|-dr|باب)", re.I)
WIN = re.compile(r"(window|win|^wn|-wn|شباك|نافذة)", re.I)


def poly_area_perim(pts):
    a = 0.0
    p = 0.0
    for i in range(len(pts)):
        x1, y1 = pts[i]
        x2, y2 = pts[(i + 1) % len(pts)]
        a += x1 * y2 - x2 * y1
        p += math.hypot(x2 - x1, y2 - y1)
    return abs(a) / 2, p


def inside(pt, poly):
    x, y = pt
    ins = False
    for i in range(len(poly)):
        x1, y1 = poly[i]
        x2, y2 = poly[(i + 1) % len(poly)]
        if (y1 > y) != (y2 > y) and x < x1 + (y - y1) * (x2 - x1) / (y2 - y1):
            ins = not ins
    return ins


def near_edge(pt, poly, tol):
    x, y = pt
    for i in range(len(poly)):
        (x1, y1), (x2, y2) = poly[i], poly[(i + 1) % len(poly)]
        dx, dy = x2 - x1, y2 - y1
        L2 = dx * dx + dy * dy or 1e-9
        t = max(0, min(1, ((x - x1) * dx + (y - y1) * dy) / L2))
        if math.hypot(x - (x1 + t * dx), y - (y1 + t * dy)) <= tol:
            return True
    return False


def from_dxf(a):
    try:
        import ezdxf
    except ImportError:
        sys.exit("pip install ezdxf")
    doc = ezdxf.readfile(a.dxf)
    msp = doc.modelspace()
    f = {"mm": 0.001, "cm": 0.01, "m": 1.0}[a.units]
    room_layers = [x.strip().upper() for x in a.layers.split(",")]
    text_layers = [x.strip().upper() for x in a.text_layers.split(",")] if a.text_layers else None

    def on(layer, wanted):
        L = layer.upper()
        return any(w == L or w in L for w in wanted)

    polys = []
    for e in msp.query("LWPOLYLINE POLYLINE"):
        if not on(e.dxf.layer, room_layers):
            continue
        closed = e.closed if e.dxftype() == "LWPOLYLINE" else e.is_closed
        pts = [(p[0], p[1]) for p in (e.get_points("xy") if e.dxftype() == "LWPOLYLINE" else
                                      [v.dxf.location for v in e.vertices])]
        if len(pts) >= 3 and (closed or math.hypot(pts[0][0] - pts[-1][0], pts[0][1] - pts[-1][1]) < 1):
            polys.append(pts)
    texts = []
    for e in msp.query("TEXT MTEXT"):
        if text_layers and not on(e.dxf.layer, text_layers):
            continue
        s = e.plain_text() if e.dxftype() == "MTEXT" else e.dxf.text
        texts.append(((e.dxf.insert[0], e.dxf.insert[1]), s.strip().replace("\n", " ")))
    blocks = []
    for e in msp.query("INSERT"):
        nm, ly = e.dxf.name, e.dxf.layer
        kind = "door" if (DOOR.search(nm) or DOOR.search(ly)) else ("window" if (WIN.search(nm) or WIN.search(ly)) else None)
        if kind:
            blocks.append(((e.dxf.insert[0], e.dxf.insert[1]), kind, nm))
    tol = 400 if a.units == "mm" else (40 if a.units == "cm" else 0.4)
    rows = []
    for k, pts in enumerate(sorted(polys, key=lambda p: (-max(q[1] for q in p), min(q[0] for q in p))), 1):
        A, P = poly_area_perim(pts)
        names = [t for (pt, t) in texts if inside(pt, pts)]
        num = next((t for t in names if re.fullmatch(r"[A-Z]{0,3}[-.]?\d{1,4}[A-Z]?", t.strip(), re.I)), "")
        name = next((t for t in names if t != num), "")
        doors = sum(1 for (pt, kd, _) in blocks if kd == "door" and (inside(pt, pts) or near_edge(pt, pts, tol)))
        wins = sum(1 for (pt, kd, _) in blocks if kd == "window" and (inside(pt, pts) or near_edge(pt, pts, tol)))
        rows.append([a.level, num or f"R{k:03d}", name, round(A * f * f, 2), round(P * f, 2), None,
                     None, None, None, None, "Y" if WET.search(name or "") else "N", doors, None, None, None,
                     f"{wins} window block(s) found" if wins else None])
    write_rooms(a.out, rows)
    print(f"{len(polys)} room polylines, {len(texts)} texts, {len(blocks)} door/window blocks -> {a.out}")
    if not polys:
        layers = sorted({e.dxf.layer for e in msp.query('LWPOLYLINE POLYLINE')})
        print("No closed polylines on the room layers. Polyline layers in the file: " + ", ".join(layers[:40]))


def write_rooms(path, rows):
    import openpyxl
    from openpyxl.styles import Font, PatternFill
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Rooms"
    ws.append(ROOM_COLS)
    for r in rows:
        ws.append(r)
    lg = wb.create_sheet("Finishes")
    lg.append(FIN_COLS)
    for r in (["F01", "Floor", "e.g. porcelain 60x60 on screed", "", "", "m2"],
              ["SK01", "Skirting", "e.g. porcelain skirting h=10 cm", "", "", "m"],
              ["W01", "Wall", "e.g. plaster + 3 coats emulsion paint", "", "", "m2"],
              ["W02", "Wall", "e.g. ceramic tiles to ceiling (wet rooms)", "", "", "m2"],
              ["C01", "Ceiling", "e.g. gypsum board false ceiling, painted", "", "", "m2"],
              ["WP01", "Waterproofing", "e.g. cementitious waterproofing, turned up 30 cm", "", "", "m2"]):
        lg.append(r)
    for w in (ws, lg):
        for c in w[1]:
            c.font = Font(bold=True, color="FFFFFF")
            c.fill = PatternFill("solid", fgColor="1F3864")
        for col in w.columns:
            w.column_dimensions[col[0].column_letter].width = max(12, min(45, len(str(col[0].value)) + 4))
    wb.save(path)


def template(a):
    write_rooms(a.out, [])
    print(f"Template written: {a.out} (fill 'Rooms' and the 'Finishes' legend)")


def num(v, d=0.0):
    try:
        return float(v)
    except (TypeError, ValueError):
        return d


def finishes(a):
    import openpyxl
    from openpyxl.styles import Font, PatternFill
    wb = openpyxl.load_workbook(a.rooms, data_only=True)
    ws = wb["Rooms"]
    hdr = [c.value for c in ws[1]]
    rooms = [dict(zip(hdr, r)) for r in ws.iter_rows(min_row=2, values_only=True) if any(v is not None for v in r)]
    legend = OrderedDict()
    if "Finishes" in wb.sheetnames:
        lh = [c.value for c in wb["Finishes"][1]]
        for r in wb["Finishes"].iter_rows(min_row=2, values_only=True):
            d = dict(zip(lh, r))
            if d.get("Code"):
                legend[str(d["Code"]).strip()] = d
    qty = defaultdict(lambda: defaultdict(float))  # code -> level -> qty
    issues = []
    sched = []
    for rm in rooms:
        lvl = rm.get("Level") or "-"
        rid = f"{lvl}/{rm.get('Room No.') or '?'} {rm.get('Room name') or ''}".strip()
        A, P, H = num(rm.get("Area m2")), num(rm.get("Perimeter m")), num(rm.get("Ceiling height m"))
        dw, dh = num(rm.get("Door widths total m")), num(rm.get("Door height m"), 2.2)
        win = num(rm.get("Windows area m2"))
        if not H:
            issues.append(f"{rid}: no ceiling height - wall quantities set to 0")
        sk = max(P - dw, 0)
        wall = max(P * H - dw * dh - win, 0) if H else 0
        codes = {k: (str(rm.get(k)).strip() if rm.get(k) else "") for k in
                 ("Floor code", "Skirting code", "Wall code", "Ceiling code")}
        for k, c in codes.items():
            if not c:
                issues.append(f"{rid}: {k} missing")
            elif legend and c not in legend:
                issues.append(f"{rid}: {k} '{c}' not in the Finishes legend")
        wet = str(rm.get("Wet room (Y/N)") or "").upper().startswith("Y")
        wp_codes = [c for c, d in legend.items() if "water" in str(d.get("Type (Floor/Skirting/Wall/Ceiling/Waterproofing)", "")).lower()]
        if wet and not any(c in str(rm.get("Remarks") or "") + codes["Floor code"] for c in wp_codes):
            issues.append(f"{rid}: wet room - add the waterproofing code (e.g. in Remarks) and turn-up detail")
        if codes["Floor code"]:
            qty[codes["Floor code"]][lvl] += A
        if codes["Skirting code"] and codes["Skirting code"] != codes["Wall code"]:
            qty[codes["Skirting code"]][lvl] += sk
        if codes["Wall code"]:
            qty[codes["Wall code"]][lvl] += wall
        if codes["Ceiling code"]:
            qty[codes["Ceiling code"]][lvl] += A
        if wet:
            for c in wp_codes:
                if c in str(rm.get("Remarks") or "") + codes["Floor code"]:
                    qty[c][lvl] += A + P * 0.3  # floor + 30 cm turn-up (adjust to the detail)
        sched.append([lvl, rm.get("Room No."), rm.get("Room name"), round(A, 2), round(P, 2), H or None,
                      codes["Floor code"], codes["Skirting code"], codes["Wall code"], codes["Ceiling code"],
                      round(sk, 2), round(wall, 2), round(A, 2), "Y" if wet else "N"])
    out = openpyxl.Workbook()
    s1 = out.active
    s1.title = "Room finish schedule"
    s1.append(["Level", "Room No.", "Room name", "Area m2", "Perimeter m", "Ceiling h m", "Floor", "Skirting", "Walls",
               "Ceiling", "Skirting m", "Walls m2", "Ceiling m2", "Wet"])
    for r in sched:
        s1.append(r)
    levels = sorted({lvl for d in qty.values() for lvl in d})
    s2 = out.create_sheet("Quantities by finish")
    s2.append(["Code", "Type", "Description", "Unit"] + levels + ["Total"])
    for c in sorted(qty):
        d = legend.get(c, {})
        unit = d.get("Unit") or ("m" if c.upper().startswith("SK") else "m2")
        vals = [round(qty[c].get(l, 0), 2) for l in levels]
        s2.append([c, d.get("Type (Floor/Skirting/Wall/Ceiling/Waterproofing)", ""), d.get("Description", ""), unit]
                  + vals + [round(sum(vals), 2)])
    s3 = out.create_sheet("Checks")
    s3.append(["Issue"])
    for x in issues:
        s3.append([x])
    s4 = out.create_sheet("Notes")
    for n in ["Skirting = perimeter - door widths; walls = perimeter x ceiling height - doors (width x height) - windows.",
              "Waterproofing in wet rooms = floor area + perimeter x 0.30 m turn-up (change to the approved detail).",
              "Quantities are net room quantities from the plan; add wastage per the specification / BOQ rules "
              "(alhabeeb-takeoff-boq). Areas behind fixed furniture and shafts are not deducted."]:
        s4.append([n])
    for w in out.worksheets:
        for c in w[1]:
            c.font = Font(bold=True, color="FFFFFF")
            c.fill = PatternFill("solid", fgColor="1F3864")
        for col in w.columns:
            w.column_dimensions[col[0].column_letter].width = max(10, min(50, max(len(str(c.value or "")) for c in col) + 2))
    out.save(a.out)
    print(f"{len(sched)} rooms, {len(qty)} finish codes, {len(issues)} check(s) -> {a.out}")
    for c in sorted(qty):
        print(f"  {c}: {sum(qty[c].values()):.2f}")
    for x in issues[:15]:
        print("  ! " + x)


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    s = p.add_subparsers(dest="cmd", required=True)
    x = s.add_parser("from-dxf")
    x.add_argument("dxf")
    x.add_argument("--layers", default="AR-ROOM,ROOM,AREA,A-AREA")
    x.add_argument("--text-layers")
    x.add_argument("--level", default="GF")
    x.add_argument("--units", choices=["mm", "cm", "m"], default="mm")
    x.add_argument("-o", "--out", required=True)
    x.set_defaults(fn=from_dxf)
    x = s.add_parser("template")
    x.add_argument("-o", "--out", required=True)
    x.set_defaults(fn=template)
    x = s.add_parser("finishes")
    x.add_argument("rooms")
    x.add_argument("-o", "--out", required=True)
    x.set_defaults(fn=finishes)
    a = p.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()
