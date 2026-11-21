#!/usr/bin/env python3
"""Read ETABS / SAFE / ADAPT model exports without the programs' printed reports.

Inputs it understands
  *.e2k / *.$et        ETABS text model (File > Export > ETABS .e2k Text File)
  *.f2k / *.s2k / *.$2k  SAFE / SAP2000 text database ("TABLE: ..." with Key=Value records)
  *.xlsx / *.csv       Tables exported from ETABS, SAFE or ADAPT (Show Tables > Export to Excel, etc.)

Subcommands
  summary     model.e2k                      Stories, sections, materials, loads, combos, counts
  review      model.e2k                      Automatic model checks (list of findings)
  fix         model.e2k [-o fixed.e2k]       Repair what can be repaired safely, write a corrected .e2k + log
  quantities  model.e2k [--xlsx out.xlsx]    Concrete volume and formwork by story and element
  tables      file [--list] [--table NAME] [--head N] [--csv DIR]   Read any table export
  footings    --model m.e2k --reactions r.xlsx --q-allow 200 [--fcu 25 --fy 400] -o footings.json [--raft]
  columns     --model m.e2k --forces f.xlsx --combos U1,U2 [--fcu 30 --fy 400] -o columns.json
  beams       --model m.e2k --forces f.xlsx --combos U1,U2 [--fcu 30 --fy 400] -o beams.json

Output units: kN, kN·m, m (model), mm (section sizes for ecp203), N/mm² (fcu, fy).
Standard library only, except openpyxl for .xlsx (pip install openpyxl).
"""
import argparse
import csv
import json
import math
import os
import re
import sys
from collections import OrderedDict, defaultdict

LEN = {"M": 1.0, "MM": 0.001, "CM": 0.01, "FT": 0.3048, "IN": 0.0254, "INCH": 0.0254, "FEET": 0.3048}
FORCE = {"KN": 1.0, "N": 0.001, "TONF": 9.80665, "TON": 9.80665, "KGF": 0.00980665, "KG": 0.00980665,
         "KIP": 4.448222, "LB": 0.004448222, "LBF": 0.004448222}
DEAD_TYPES = {"dead", "superdead", "super dead", "superimposed dead", "wall"}
LIVE_TYPES = {"live", "reducelive", "reducible live", "roof live", "rooflive", "unreducible live"}

IGNORE = {"END", "TITLE1", "TITLE2", "PREFERENCE", "GRIDSYSTEM", "GRID", "DIAPHRAGM", "PIERS", "SPANDRELS",
          "LOADCASE", "FUNCTION", "SPECTRUM"}
TOKEN = re.compile(r'"([^"]*)"|(\S+)')


def toks(line):
    return [m.group(1) if m.group(1) is not None else m.group(2) for m in TOKEN.finditer(line)]


def kv(tokens, start):
    """Turn KEY value KEY value ... into a dict (keys upper-case). Flags without value -> True."""
    d = {}
    i = start
    while i < len(tokens):
        k = tokens[i].upper()
        if i + 1 < len(tokens):
            d[k] = tokens[i + 1]
            i += 2
        else:
            d[k] = True
            i += 1
    return d


def fnum(v, default=None):
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


# ====================================================================== e2k
class Model:
    def __init__(self):
        self.program = ""
        self.lf = 1.0  # length factor to m
        self.ff = 1.0  # force factor to kN
        self.units = ("KN", "M")
        self.stories = []  # top -> bottom: dict(name, height, elev)
        self.points = {}
        self.lines = {}
        self.areas = {}
        self.line_assigns = []
        self.area_assigns = []
        self.point_assigns = []
        self.frame_sections = OrderedDict()
        self.shell_props = OrderedDict()
        self.materials = OrderedDict()
        self.patterns = OrderedDict()
        self.combos = OrderedDict()
        self.area_loads = []
        self.line_loads = []
        self.point_loads = []
        self.unknown_sections = set()

    # ---------- geometry helpers
    def elev(self, story):
        for s in self.stories:
            if s["name"] == story:
                return s["elev"]
        return None

    def story_below(self, story, n=1):
        names = [s["name"] for s in self.stories]
        if story not in names:
            return None
        i = names.index(story) + n
        return names[i] if i < len(names) else None

    def height(self, story):
        b = self.story_below(story)
        if b is None:
            return 0.0
        return self.elev(story) - self.elev(b)

    def pxy(self, p):
        x, y = self.points[p]
        return x, y

    def fc_mpa(self, mat):
        m = self.materials.get(mat, {})
        fc = fnum(m.get("FC"))
        if fc is None:
            return None
        return fc * self.ff / (self.lf ** 2) / 1000.0

    def fy_mpa(self, mat):
        m = self.materials.get(mat, {})
        fy = fnum(m.get("FY"))
        return None if fy is None else fy * self.ff / (self.lf ** 2) / 1000.0


def read_e2k(path):
    M = Model()
    sec = ""
    with open(path, encoding="utf-8", errors="replace") as f:
        raw = f.read().splitlines()
    for line in raw:
        s = line.strip()
        if not s:
            continue
        if s.startswith("$"):
            sec = s[1:].strip().upper()
            continue
        t = toks(s)
        if not t:
            continue
        key = t[0].upper()
        try:
            if key == "PROGRAM":
                M.program = " ".join(t[1:])
            elif key == "UNITS" and len(t) >= 3:
                M.units = (t[1].upper(), t[2].upper())
                M.ff = FORCE.get(t[1].upper(), 1.0)
                M.lf = LEN.get(t[2].upper(), 1.0)
            elif key == "STORY":
                d = kv(t, 2)
                M.stories.append({"name": t[1], "height": fnum(d.get("HEIGHT")), "elev": fnum(d.get("ELEV")),
                                  "raw": d})
            elif key == "POINT" and len(t) >= 4:
                M.points[t[1]] = (fnum(t[2]) * M.lf, fnum(t[3]) * M.lf)
            elif key == "LINE" and len(t) >= 5:
                n = int(fnum(t[5], 0)) if len(t) > 5 else 0
                M.lines[t[1]] = {"type": t[2].upper(), "i": t[3], "j": t[4], "n": n}
            elif key == "AREA" and len(t) >= 4:
                npt = int(fnum(t[3], 0))
                pts = t[4:4 + npt]
                offs = [int(fnum(x, 0)) for x in t[4 + npt:4 + 2 * npt]]
                M.areas[t[1]] = {"type": t[2].upper(), "pts": pts, "offs": offs or [0] * npt}
            elif key == "LINEASSIGN" and len(t) >= 3:
                M.line_assigns.append({"label": t[1], "story": t[2], **kv(t, 3)})
            elif key == "AREAASSIGN" and len(t) >= 3:
                M.area_assigns.append({"label": t[1], "story": t[2], **kv(t, 3)})
            elif key == "POINTASSIGN" and len(t) >= 3:
                M.point_assigns.append({"label": t[1], "story": t[2], **kv(t, 3)})
            elif key == "FRAMESECTION":
                M.frame_sections.setdefault(t[1], {}).update(kv(t, 2))
            elif key in ("SHELLPROP", "SLABPROP", "WALLPROP", "DECKPROP"):
                d = M.shell_props.setdefault(t[1], {"KIND": key})
                d.update(kv(t, 2))
            elif key == "MATERIAL":
                M.materials.setdefault(t[1], {}).update(kv(t, 2))
            elif key == "LOADPATTERN":
                M.patterns.setdefault(t[1], {}).update(kv(t, 2))
            elif key == "LOADCASE" and "TYPE" in kv(t, 2):
                pass
            elif key == "COMBO":
                c = M.combos.setdefault(t[1], {"type": "", "items": []})
                d = kv(t, 2)
                if "TYPE" in d and "LOAD" not in d and "CASE" not in d and "COMBO" not in d:
                    c["type"] = d["TYPE"]
                else:
                    case = d.get("LOAD") or d.get("CASE") or d.get("COMBO") or d.get("LOADCASE")
                    if case is not None:
                        c["items"].append((case, fnum(d.get("SF"), 1.0)))
            elif key in ("AREALOAD", "SHELLLOAD"):
                M.area_loads.append({"label": t[1], "story": t[2], **kv(t, 3)})
            elif key in ("LINELOAD", "FRAMELOAD"):
                M.line_loads.append({"label": t[1], "story": t[2], **kv(t, 3)})
            elif key == "POINTLOAD":
                M.point_loads.append({"label": t[1], "story": t[2], **kv(t, 3)})
            elif key not in IGNORE:
                M.unknown_sections.add(sec)
        except (IndexError, ValueError):
            M.unknown_sections.add(sec)
    # story elevations: listed top -> bottom; bottom has ELEV
    if M.stories:
        base = M.stories[-1]
        e = (base["elev"] or 0.0) * M.lf
        base["elev"] = e
        for s in reversed(M.stories[:-1]):
            e += (s["height"] or 0.0) * M.lf
            s["elev"] = e
            s["height"] = (s["height"] or 0.0) * M.lf
    return M


def sec_dims(M, name):
    """Return (shape, depth_m, width_m) for a frame section."""
    s = M.frame_sections.get(name, {})
    shape = str(s.get("SHAPE", "")).lower()
    D = fnum(s.get("D"))
    B = fnum(s.get("B"))
    D = D * M.lf if D is not None else None
    B = B * M.lf if B is not None else None
    return shape, D, B


def shell_t(M, name):
    p = M.shell_props.get(name, {})
    for k, v in p.items():
        if "THICK" in k:
            t = fnum(v)
            if t:
                return t * M.lf
    return None


def shell_kind(M, name, area_type):
    p = M.shell_props.get(name, {})
    k = (str(p.get("PROPTYPE", "")) + " " + p.get("KIND", "")).lower()
    if "wall" in k or area_type == "PANEL":
        return "wall"
    if "deck" in k:
        return "deck"
    return "slab"


def poly_area(pts):
    s = 0.0
    for i in range(len(pts)):
        x1, y1 = pts[i]
        x2, y2 = pts[(i + 1) % len(pts)]
        s += x1 * y2 - x2 * y1
    return abs(s) / 2


def instances(M):
    """Yield every assigned element with geometry: dict(kind, label, story, section, ...)."""
    out = []
    for a in M.line_assigns:
        ln = M.lines.get(a["label"])
        if not ln:
            continue
        secn = a.get("SECTION")
        shape, D, B = sec_dims(M, secn)
        top = M.elev(a["story"])
        if ln["type"] == "COLUMN":
            below = M.story_below(a["story"], max(ln["n"], 1))
            bot = M.elev(below) if below else top
            L = (top - bot) if top is not None and bot is not None else 0.0
            xy = M.points.get(ln["i"], (None, None))
            out.append({"kind": "column", "label": a["label"], "story": a["story"], "section": secn,
                        "shape": shape, "D": D, "B": B, "L": L, "x": xy[0], "y": xy[1], "point": ln["i"],
                        "ang": fnum(a.get("ANG"), 0.0)})
        else:
            if ln["i"] in M.points and ln["j"] in M.points:
                (x1, y1), (x2, y2) = M.points[ln["i"]], M.points[ln["j"]]
                L = math.hypot(x2 - x1, y2 - y1)
            else:
                L = 0.0
            kind = "beam" if ln["type"] == "BEAM" else ln["type"].lower()
            out.append({"kind": kind, "label": a["label"], "story": a["story"], "section": secn,
                        "shape": shape, "D": D, "B": B, "L": L})
    for a in M.area_assigns:
        ar = M.areas.get(a["label"])
        if not ar:
            continue
        secn = a.get("SECTION")
        t = shell_t(M, secn)
        kind = shell_kind(M, secn, ar["type"])
        pts = [M.points[p] for p in ar["pts"] if p in M.points]
        if kind == "wall":
            uniq = []
            for p in pts:
                if p not in uniq:
                    uniq.append(p)
            length = max((math.hypot(p[0] - q[0], p[1] - q[1]) for p in uniq for q in uniq), default=0.0)
            h = M.height(a["story"])
            out.append({"kind": "wall", "label": a["label"], "story": a["story"], "section": secn, "t": t,
                        "length": length, "h": h, "area": length * h})
        else:
            out.append({"kind": kind, "label": a["label"], "story": a["story"], "section": secn, "t": t,
                        "area": poly_area(pts) if len(pts) >= 3 else 0.0})
    return out


# ====================================================================== text tables (f2k / s2k)
def read_text_tables(path):
    tables = OrderedDict()
    cur = None
    buf = ""
    with open(path, encoding="utf-8", errors="replace") as f:
        lines = f.read().splitlines()
    for line in lines:
        s = line.rstrip()
        if s.strip().upper().startswith("TABLE:"):
            name = s.split(":", 1)[1].strip().strip('"')
            cur = tables.setdefault(name, [])
            buf = ""
            continue
        if cur is None or not s.strip() or s.strip().startswith(("$", "END TABLE")):
            continue
        if s.endswith(" _"):
            buf += s[:-2] + " "
            continue
        s = buf + s
        buf = ""
        rec = OrderedDict()
        for m in re.finditer(r'(\w[\w\-/]*)\s*=\s*("([^"]*)"|\S+)', s):
            rec[m.group(1)] = m.group(3) if m.group(3) is not None else m.group(2)
        if rec:
            cur.append(rec)
    return tables


# ====================================================================== spreadsheet tables
def _is_header(row):
    vals = [str(v).strip() for v in row if v not in (None, "")]
    if len(vals) < 2:
        return False
    texty = sum(1 for v in vals if fnum(v) is None)
    return texty >= max(2, int(0.7 * len(vals)))


UNIT_WORDS = {"kn", "kn-m", "kn·m", "m", "mm", "rad", "sec", "kn/m", "kn/m2", "kn/m²", "n", "n-mm", "tonf", "tonf-m",
              "kgf", "kip", "kip-ft", "ft", "in", "unitless", "%", "degrees", "deg", "cm", "kn-m/m", "t", "t.m"}


def _is_units(row):
    vals = [str(v).strip().lower() for v in row if v not in (None, "")]
    return bool(vals) and sum(1 for v in vals if v in UNIT_WORDS) >= max(1, len(vals) // 2)


def rows_to_table(rows):
    """Find header row, optional units row; return (records, units)."""
    hi = None
    title = None
    for i, r in enumerate(rows[:15]):
        if r and str(r[0] or "").upper().startswith("TABLE:"):
            title = str(r[0]).split(":", 1)[1].strip()
            continue
        if _is_header(r):
            hi = i
            break
    if hi is None:
        return title, [], {}
    hdr = [str(h).strip() if h not in (None, "") else f"col{j}" for j, h in enumerate(rows[hi])]
    start = hi + 1
    units = {}
    if start < len(rows) and _is_units(rows[start]):
        units = {h: rows[start][j] for j, h in enumerate(hdr) if j < len(rows[start]) and rows[start][j]}
        start += 1
    recs = []
    for r in rows[start:]:
        if not r or all(v in (None, "") for v in r):
            continue
        recs.append(OrderedDict((hdr[j], r[j] if j < len(r) else None) for j in range(len(hdr))))
    return title, recs, units


def read_any_tables(path):
    """Return OrderedDict name -> dict(records, units)."""
    ext = os.path.splitext(path)[1].lower()
    out = OrderedDict()
    if ext in (".xlsx", ".xlsm"):
        try:
            import openpyxl
        except ImportError:
            sys.exit("openpyxl is needed for .xlsx: pip install openpyxl")
        wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
        for ws in wb.worksheets:
            rows = [list(r) for r in ws.iter_rows(values_only=True)]
            title, recs, units = rows_to_table(rows)
            out[title or ws.title] = {"records": recs, "units": units, "sheet": ws.title}
    elif ext in (".csv", ".txt") and not _looks_like_text_db(path):
        with open(path, newline="", encoding="utf-8-sig", errors="replace") as f:
            sample = f.read(4096)
            f.seek(0)
            try:
                dialect = csv.Sniffer().sniff(sample, delimiters=",;\t")
            except csv.Error:
                dialect = csv.excel
            rows = list(csv.reader(f, dialect))
        title, recs, units = rows_to_table(rows)
        out[title or os.path.basename(path)] = {"records": recs, "units": units}
    else:
        for name, recs in read_text_tables(path).items():
            out[name] = {"records": recs, "units": {}}
    return out


def _looks_like_text_db(path):
    with open(path, encoding="utf-8", errors="replace") as f:
        head = f.read(4000).upper()
    return "TABLE:" in head and "=" in head


def norm(s):
    return re.sub(r"[^a-z0-9]", "", str(s).lower())


def pick(rec, *names):
    nk = {norm(k): k for k in rec}
    for n in names:
        if norm(n) in nk:
            return rec[nk[norm(n)]]
    return None


def find_table(tables, *keywords):
    for name, t in tables.items():
        n = name.lower()
        if all(k in n for k in keywords):
            return name, t
    return None, None


def unit_factor(units, col, kind):
    u = str(units.get(col, "")).strip().upper().replace("·", "-")
    if not u:
        return 1.0
    if kind == "force":
        return FORCE.get(u, 1.0)
    if kind == "moment":
        parts = re.split(r"[-.*]", u)
        if len(parts) == 2:
            return FORCE.get(parts[0], 1.0) * LEN.get(parts[1], 1.0)
    return 1.0


# ====================================================================== commands
def cmd_summary(a):
    M = read_e2k(a.model)
    print(f"Program: {M.program or '?'}   Units in file: {M.units[0]}, {M.units[1]} (converted to kN, m)")
    print(f"\nStories ({len(M.stories)}), top to bottom:")
    for s in M.stories:
        print(f"  {s['name']:<14} elev {s['elev']:8.2f} m   height {M.height(s['name']):5.2f} m")
    print(f"\nMaterials ({len(M.materials)}):")
    for n, m in M.materials.items():
        fc = M.fc_mpa(n)
        fy = M.fy_mpa(n)
        extra = f"f'c = {fc:.1f} MPa (≈ fcu {fc / 0.8:.0f} cube)" if fc else (f"fy = {fy:.0f} MPa" if fy else "")
        print(f"  {n:<16} {m.get('TYPE', ''):<10} {extra}")
    print(f"\nFrame sections ({len(M.frame_sections)}):")
    for n in M.frame_sections:
        shape, D, B = sec_dims(M, n)
        dims = f"{(B or 0) * 1000:.0f} x {(D or 0) * 1000:.0f} mm (B x D)" if D else ""
        print(f"  {n:<16} {M.frame_sections[n].get('MATERIAL', ''):<10} {shape:<26} {dims}")
    print(f"\nShell properties ({len(M.shell_props)}):")
    for n, p in M.shell_props.items():
        t = shell_t(M, n)
        print(f"  {n:<16} {p.get('PROPTYPE', p.get('KIND', '')):<10} {p.get('MATERIAL', ''):<10} t = {(t or 0) * 1000:.0f} mm")
    print(f"\nLoad patterns ({len(M.patterns)}):")
    for n, p in M.patterns.items():
        print(f"  {n:<16} type {p.get('TYPE', '?'):<12} self-weight x{p.get('SELFWEIGHT', 0)}")
    print(f"\nLoad combinations ({len(M.combos)}):")
    for n, c in M.combos.items():
        print(f"  {n:<16} {c['type']:<12} " + " + ".join(f"{sf:g}x{case}" for case, sf in c["items"]))
    inst = instances(M)
    cnt = defaultdict(int)
    for e in inst:
        cnt[e["kind"]] += 1
    print("\nObjects (assigned instances): " + ", ".join(f"{k} {v}" for k, v in sorted(cnt.items())))
    print(f"Area loads {len(M.area_loads)}, line loads {len(M.line_loads)}, point loads {len(M.point_loads)}")
    if M.unknown_sections - {""}:
        print("\nSections read but not interpreted: " + ", ".join(sorted(M.unknown_sections - {""})))


def cmd_review(a):
    M = read_e2k(a.model)
    inst = instances(M)
    F = []  # (severity, message)

    def add(sev, msg):
        F.append((sev, msg))

    # units
    if M.units[1] not in LEN or M.units[0] not in FORCE:
        add(1, f"Unknown units {M.units}: conversions may be wrong.")
    # materials
    for n, m in M.materials.items():
        if str(m.get("TYPE", "")).lower() == "concrete":
            fc = M.fc_mpa(n)
            if fc is None:
                add(2, f"Concrete material {n}: no f'c found.")
            else:
                if fc < 16 or fc > 60:
                    add(1, f"Concrete {n}: f'c = {fc:.1f} MPa looks wrong (unit error?).")
                add(3, f"Concrete {n}: ETABS f'c = {fc:.1f} MPa is a CYLINDER strength. ECP 203 fcu (cube) "
                       f"≈ f'c/0.8 = {fc / 0.8:.0f} N/mm². Confirm the model uses the intended grade.")
            w = fnum(m.get("WEIGHTPERVOLUME"))
            if w is not None:
                wk = w * M.ff / M.lf ** 3
                if not 23 <= wk <= 26:
                    add(2, f"Concrete {n}: unit weight {wk:.2f} kN/m³ (expected ≈ 25 for reinforced concrete).")
    # self weight
    sw = [n for n, p in M.patterns.items() if fnum(p.get("SELFWEIGHT"), 0) > 0]
    if len(sw) == 0:
        add(1, "No load pattern has a self-weight multiplier: self-weight is missing unless added manually.")
    elif len(sw) > 1:
        add(1, f"Self-weight multiplier in more than one pattern ({', '.join(sw)}): self-weight may be counted twice.")
    types = {n: str(p.get("TYPE", "")).lower() for n, p in M.patterns.items()}
    if not any(t in LIVE_TYPES for t in types.values()):
        add(1, "No live-load pattern found.")
    if not any("super" in t for t in types.values()) and not M.area_loads:
        add(2, "No superimposed dead load (finishes/partitions) pattern or area loads found.")
    if not any("quake" in t or "seism" in t for t in types.values()):
        add(2, "No earthquake load pattern: confirm seismic design is not required (ECP 201 zone).")
    if not any("wind" in t for t in types.values()):
        add(3, "No wind load pattern: confirm it is not needed (ECP 201).")
    # combos
    if not M.combos:
        add(1, "No load combinations defined in the model (they may be auto-generated by the design code setting).")
    for n, c in M.combos.items():
        for case, sf in c["items"]:
            if case not in M.patterns and case not in M.combos:
                add(1, f"Combination {n} uses '{case}', which is not a defined pattern or combination.")
        dead_sf = [sf for case, sf in c["items"] if types.get(case) in DEAD_TYPES]
        live_sf = [sf for case, sf in c["items"] if types.get(case) in LIVE_TYPES]
        if dead_sf and live_sf and len(c["items"]) == len(dead_sf) + len(live_sf):
            add(3, f"Combination {n}: dead × {sorted(set(dead_sf))}, live × {sorted(set(live_sf))} — compare with "
                   f"ECP 203-2020 load factors (check with the egyptian-codes skill).")
    # sections
    used = {e["section"] for e in inst}
    for e in inst:
        if e["section"] is None:
            add(1, f"{e['kind']} {e['label']} at {e['story']}: no section assigned.")
        elif e["kind"] in ("column", "beam") and e["section"] not in M.frame_sections:
            add(1, f"{e['kind']} {e['label']} at {e['story']}: section '{e['section']}' not defined.")
    for n in M.frame_sections:
        if n not in used:
            add(3, f"Frame section {n} is defined but not used.")
    seen = set()
    for e in inst:
        if e["kind"] == "column" and e["B"] and e["D"]:
            mn = min(e["B"], e["D"]) * 1000
            if mn < 200 and e["section"] not in seen:
                add(1, f"Column section {e['section']}: smallest side {mn:.0f} mm < 200 mm (check ECP 203 minimum).")
                seen.add(e["section"])
        if e["kind"] in ("slab", "deck") and e.get("t") and e["t"] * 1000 < 100 and e["section"] not in seen:
            add(2, f"Slab property {e['section']}: t = {e['t'] * 1000:.0f} mm — check minimum thickness and deflection.")
            seen.add(e["section"])
    # columns continuity: column size increasing upward
    bypt = defaultdict(list)
    for e in inst:
        if e["kind"] == "column" and e["B"] and e["D"]:
            bypt[e["point"]].append((M.elev(e["story"]) or 0, e["B"] * e["D"], e["section"], e["story"]))
    for p, lst in bypt.items():
        lst.sort()
        for lo, hi in zip(lst, lst[1:]):
            if hi[1] > lo[1] * 1.001:
                add(2, f"Column at point {p}: {hi[2]} at {hi[3]} is larger than {lo[2]} below it.")
    # supports
    base = M.stories[-1]["name"] if M.stories else None
    restrained = {(pa["label"], pa["story"]) for pa in M.point_assigns if pa.get("RESTRAINT")}
    if not restrained:
        add(1, "No point restraints (supports) found.")
    lowest = defaultdict(lambda: None)
    for e in inst:
        if e["kind"] == "column":
            below = M.story_below(e["story"])
            if below == base and (e["point"], base) not in restrained:
                add(1, f"Column {e['label']} at {e['story']} reaches {base} at point {e['point']} with no support.")
    # property modifiers
    mods = [la for la in M.line_assigns if any("MOD" in k or k.startswith("PROP") for k in la)]
    if not mods:
        add(3, "No frame property modifiers found: confirm cracked-section stiffness is applied as required.")
    # loads referencing missing patterns
    for ld in M.area_loads + M.line_loads + M.point_loads:
        lc = ld.get("LC") or ld.get("LOADPAT") or ld.get("PATTERN")
        if lc and lc not in M.patterns:
            add(1, f"Load on {ld['label']} at {ld['story']} uses pattern '{lc}', not defined.")
    # stories
    for s in M.stories[:-1]:
        h = M.height(s["name"])
        if h < 2.4 or h > 6.5:
            add(2, f"Story {s['name']}: height {h:.2f} m is unusual — check.")

    F.sort(key=lambda x: x[0])
    label = {1: "HIGH", 2: "MEDIUM", 3: "CHECK"}
    print(f"Model review: {len(F)} findings ({sum(1 for f in F if f[0] == 1)} high)")
    for sev, msg in F:
        print(f"[{label[sev]}] {msg}")


def quantities(M, deduct_slab=True):
    inst = instances(M)
    slab_t = defaultdict(float)
    for e in inst:
        if e["kind"] in ("slab", "deck") and e.get("t"):
            slab_t[e["story"]] = max(slab_t[e["story"]], e["t"])
    rows = []
    for e in inst:
        st = e["story"]
        ts = slab_t[st] if deduct_slab else 0.0
        if e["kind"] == "column":
            if e["D"] is None:
                continue
            if "circ" in e["shape"]:
                area = math.pi * e["D"] ** 2 / 4
                per = math.pi * e["D"]
                size = f"Ø{e['D'] * 1000:.0f}"
            else:
                area = e["B"] * e["D"]
                per = 2 * (e["B"] + e["D"])
                size = f"{e['B'] * 1000:.0f}x{e['D'] * 1000:.0f}"
            h = e["L"] - ts
            rows.append([st, "Column", e["label"], e["section"], size, round(h, 3), round(area * h, 3),
                         round(per * h, 3)])
        elif e["kind"] == "beam":
            if not e["D"] or not e["B"]:
                continue
            dd = max(e["D"] - ts, 0)
            rows.append([st, "Beam", e["label"], e["section"], f"{e['B'] * 1000:.0f}x{e['D'] * 1000:.0f}",
                         round(e["L"], 3), round(e["B"] * dd * e["L"], 3), round((e["B"] + 2 * dd) * e["L"], 3)])
        elif e["kind"] in ("slab", "deck"):
            t = e.get("t") or 0
            rows.append([st, "Slab", e["label"], e["section"], f"t={t * 1000:.0f}", round(e["area"], 3),
                         round(e["area"] * t, 3), round(e["area"], 3)])
        elif e["kind"] == "wall":
            t = e.get("t") or 0
            h = e["h"] - ts
            rows.append([st, "Wall", e["label"], e["section"], f"t={t * 1000:.0f}", round(e["length"], 3),
                         round(e["length"] * h * t, 3), round(2 * e["length"] * h, 3)])
    return rows


def cmd_quantities(a):
    M = read_e2k(a.model)
    rows = quantities(M, not a.gross)
    hdr = ["Story", "Element", "Label", "Section", "Size (mm)", "Length/Area", "Concrete m3", "Formwork m2"]
    summ = defaultdict(lambda: [0.0, 0.0])
    for r in rows:
        summ[(r[0], r[1])][0] += r[6]
        summ[(r[0], r[1])][1] += r[7]
    order = {s["name"]: i for i, s in enumerate(M.stories)}
    print(f"{'Story':<14}{'Element':<10}{'Concrete m3':>14}{'Formwork m2':>14}")
    tc = tf = 0.0
    for (st, el), (c, fw) in sorted(summ.items(), key=lambda x: (order.get(x[0][0], 0), x[0][1])):
        print(f"{st:<14}{el:<10}{c:14.2f}{fw:14.2f}")
        tc += c
        tf += fw
    print(f"{'TOTAL':<24}{tc:14.2f}{tf:14.2f}")
    print("\nRules: " + ("columns and walls measured to slab soffit, beams below the slab (slab deducted); "
                         if not a.gross else "gross dimensions, no deduction at slab; ")
          + "slab formwork = soffit area; openings not deducted unless modeled as separate areas; "
            "foundations not in the superstructure model.")
    if a.xlsx:
        import openpyxl
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Detail"
        ws.append(hdr)
        for r in rows:
            ws.append(r)
        ws2 = wb.create_sheet("Summary")
        ws2.append(["Story", "Element", "Concrete m3", "Formwork m2"])
        for (st, el), (c, fw) in sorted(summ.items(), key=lambda x: (order.get(x[0][0], 0), x[0][1])):
            ws2.append([st, el, round(c, 3), round(fw, 3)])
        ws2.append(["TOTAL", "", round(tc, 3), round(tf, 3)])
        wb.save(a.xlsx)
        print(f"Saved {a.xlsx}")


def cmd_tables(a):
    T = read_any_tables(a.file)
    if a.list or not a.table:
        for n, t in T.items():
            cols = list(t["records"][0].keys()) if t["records"] else []
            print(f"- {n}: {len(t['records'])} rows; columns: {', '.join(cols[:14])}{' ...' if len(cols) > 14 else ''}")
        if not a.table:
            return
    name = next((n for n in T if a.table.lower() in n.lower()), None)
    if not name:
        sys.exit(f"No table matching '{a.table}'")
    recs = T[name]["records"]
    print(f"Table: {name} ({len(recs)} rows) units: {T[name]['units'] or 'n/a'}")
    for r in recs[:a.head]:
        print("  " + " | ".join(f"{k}={v}" for k, v in r.items() if v not in (None, "")))
    if a.csv:
        os.makedirs(a.csv, exist_ok=True)
        for n, t in T.items():
            if not t["records"]:
                continue
            fn = os.path.join(a.csv, re.sub(r"[^\w\-]+", "_", n)[:60] + ".csv")
            with open(fn, "w", newline="", encoding="utf-8") as f:
                w = csv.DictWriter(f, fieldnames=list(t["records"][0].keys()))
                w.writeheader()
                w.writerows(t["records"])
        print(f"CSV files written to {a.csv}")


def case_groups(M, dead, live):
    types = {n: str(p.get("TYPE", "")).lower() for n, p in M.patterns.items()}
    D = set(dead.split(",")) if dead else {n for n, t in types.items() if t in DEAD_TYPES}
    L = set(live.split(",")) if live else {n for n, t in types.items() if t in LIVE_TYPES}
    return D, L


def base_columns(M):
    """point label -> lowest column instance at that point."""
    best = {}
    for e in instances(M):
        if e["kind"] != "column":
            continue
        el = M.elev(e["story"]) or 0
        if e["point"] not in best or el < best[e["point"]][0]:
            best[e["point"]] = (el, e)
    return {p: v[1] for p, v in best.items()}


def cmd_footings(a):
    M = read_e2k(a.model)
    T = read_any_tables(a.reactions)
    name, t = find_table(T, "reaction")
    if not t:
        name, t = next(iter(T.items()))
    recs, units = t["records"], t["units"]
    Dset, Lset = case_groups(M, a.dead_cases, a.live_cases)
    print(f"Reactions table: {name}; dead cases {sorted(Dset)}; live cases {sorted(Lset)}")
    fz_col = None
    if recs:
        for c in recs[0]:
            if norm(c) in ("fz", "f3"):
                fz_col = c
    ffac = unit_factor(units, fz_col, "force") if fz_col else 1.0
    loads = defaultdict(lambda: {"D": 0.0, "L": 0.0, "x": None, "y": None})
    other = set()
    for r in recs:
        p = pick(r, "Label", "Point", "Joint", "PointLabel", "Point Label")
        uq = pick(r, "UniqueName", "Unique Name")
        case = str(pick(r, "Output Case", "OutputCase", "Load Case/Combo", "LoadCase", "Case", "Load Pattern") or "")
        fz = fnum(pick(r, "FZ", "F3"))
        step = str(pick(r, "Step Type", "StepType") or "")
        if fz is None or step.lower() in ("min",):
            continue
        key = str(p if p is not None else uq)
        if case in Dset:
            loads[key]["D"] += fz * ffac
        elif case in Lset:
            loads[key]["L"] += fz * ffac
        else:
            other.add(case)
    if other:
        print(f"Ignored cases (not dead/live): {', '.join(sorted(other))}")
    cols = base_columns(M)
    items = []
    print(f"{'Point':<8}{'Column':<16}{'D kN':>10}{'L kN':>10}")
    for p, v in loads.items():
        c = cols.get(p)
        if c is None:
            print(f"{p:<8}{'(no column found)':<16}{v['D']:10.1f}{v['L']:10.1f}  -> skipped (wall or unmatched label)")
            continue
        b = round((c["B"] or c["D"]) * 1000)
        d = round(c["D"] * 1000)
        print(f"{p:<8}{c['section']:<16}{v['D']:10.1f}{v['L']:10.1f}")
        if v["D"] < 0:
            print(f"   ! negative reaction at {p}: check sign convention / uplift")
        items.append({"point": p, "x": c["x"], "y": c["y"], "a": b, "b": d, "D": round(v["D"], 1),
                      "L": round(v["L"], 1)})
    if a.raft:
        xs = [i["x"] for i in items]
        ys = [i["y"] for i in items]
        x0, y0 = min(xs) - a.overhang, min(ys) - a.overhang
        out = {"_comment": f"Raft from {os.path.basename(a.model)} / {os.path.basename(a.reactions)}",
               "type": "raft", "Lx": round(max(xs) - min(xs) + 2 * a.overhang, 2),
               "Ly": round(max(ys) - min(ys) + 2 * a.overhang, 2), "q_allow": a.q_allow, "fcu": a.fcu, "fy": a.fy,
               "columns": [{"x": round(i["x"] - x0, 3), "y": round(i["y"] - y0, 3), "c1": i["a"], "c2": i["b"],
                            "D": i["D"], "L": i["L"]} for i in items]}
    else:
        out = [{"_comment": f"Point {i['point']} at ({i['x']:.2f}, {i['y']:.2f}) from {os.path.basename(a.model)}",
                "type": "footing", "col_a": i["a"], "col_b": i["b"], "D": i["D"], "L": i["L"],
                "q_allow": a.q_allow, "fcu": a.fcu, "fy": a.fy, "title": f"قاعدة {i['point']}"} for i in items]
    with open(a.out, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print(f"Wrote {a.out}  (run: python3 -m ecp203 {a.out} -o report.md from the 'Egyptian codes' folder)")


def _forces(a, kind):
    M = read_e2k(a.model)
    T = read_any_tables(a.forces)
    name, t = find_table(T, "column" if kind == "column" else "beam")
    if not t:
        sys.exit(f"No {kind} forces table found. Tables: {', '.join(T)}")
    combos = set(a.combos.split(",")) if a.combos else None
    recs, units = t["records"], t["units"]
    env = {}
    pcol = next((c for c in recs[0] if norm(c) == "p"), None) if recs else None
    mcol = next((c for c in recs[0] if norm(c) in ("m3", "m2")), None) if recs else None
    vcol = next((c for c in recs[0] if norm(c) in ("v2", "v3")), None) if recs else None
    pf = unit_factor(units, pcol, "force") if pcol else 1.0
    mf = unit_factor(units, mcol, "moment") if mcol else 1.0
    vf = unit_factor(units, vcol, "force") if vcol else 1.0
    used = set()
    for r in recs:
        case = str(pick(r, "Output Case", "OutputCase", "Load Case/Combo", "Combo", "Case") or "")
        if combos and case not in combos:
            continue
        used.add(case)
        story = str(pick(r, "Story") or "")
        lab = str(pick(r, kind.capitalize(), "Label", "Frame", "Element") or "")
        key = (story, lab)
        e = env.setdefault(key, {"P": 0.0, "M2": 0.0, "M3": 0.0, "M3pos": 0.0, "M3neg": 0.0, "V2": 0.0})
        P = (fnum(pick(r, "P"), 0.0) or 0.0) * pf
        M2 = (fnum(pick(r, "M2"), 0.0) or 0.0) * mf
        M3 = (fnum(pick(r, "M3"), 0.0) or 0.0) * mf
        V2 = (fnum(pick(r, "V2"), 0.0) or 0.0) * vf
        e["P"] = max(e["P"], -P)  # compression positive
        e["M2"] = max(e["M2"], abs(M2))
        e["M3"] = max(e["M3"], abs(M3))
        e["M3pos"] = max(e["M3pos"], M3)
        e["M3neg"] = max(e["M3neg"], -M3)
        e["V2"] = max(e["V2"], abs(V2))
    print(f"Forces table: {name}; combinations used: {', '.join(sorted(used)) or 'none'}")
    sec = {}
    for i in instances(M):
        if i["kind"] == kind:
            sec[(i["story"], i["label"])] = i
    return M, env, sec


def cmd_columns(a):
    M, env, sec = _forces(a, "column")
    out = []
    groups = {}
    for (st, lab), e in env.items():
        i = sec.get((st, lab))
        if not i or not i["D"]:
            print(f"  skip {lab} @ {st}: no section in model")
            continue
        b = round((i["B"] or i["D"]) * 1000)
        t = round(i["D"] * 1000)
        He = round(M.height(st) * 1000)
        key = (i["section"], st) if a.group else (lab, st)
        g = groups.get(key)
        cand = {"_comment": f"{lab} @ {st} ({i['section']}), envelope of selected combos", "type": "column",
                "b": b, "t": t, "fcu": a.fcu, "fy": a.fy, "Pu": round(e["P"], 1), "Mx": round(e["M3"], 1),
                "My": round(e["M2"], 1), "Hex": He, "Hey": He, "braced": not a.unbraced,
                "location": "interior", "title": f"عمود {lab} — {st}"}
        if g is None or cand["Pu"] > g["Pu"]:
            if g is not None:
                cand["Mx"] = max(cand["Mx"], g["Mx"])
                cand["My"] = max(cand["My"], g["My"])
            groups[key] = cand
        else:
            g["Mx"] = max(g["Mx"], cand["Mx"])
            g["My"] = max(g["My"], cand["My"])
    out = list(groups.values())
    with open(a.out, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print(f"Wrote {len(out)} columns to {a.out}. Envelope = max Pu with max |M| (conservative). "
          f"He = story height: replace with the effective length per ECP 203 if needed.")


def cmd_beams(a):
    M, env, sec = _forces(a, "beam")
    groups = {}
    for (st, lab), e in env.items():
        i = sec.get((st, lab))
        if not i or not i["D"]:
            print(f"  skip {lab} @ {st}: no section in model")
            continue
        key = (i["section"], st) if a.group else (lab, st)
        cand = {"_comment": f"{lab} @ {st} ({i['section']})", "type": "beam", "b": round(i["B"] * 1000),
                "h": round(i["D"] * 1000), "fcu": a.fcu, "fy": a.fy, "Mu_pos": round(e["M3pos"], 1),
                "Mu_neg": round(e["M3neg"], 1), "Qu": round(e["V2"], 1), "title": f"كمرة {lab} — {st}"}
        g = groups.get(key)
        if g is None:
            groups[key] = cand
        else:
            for k in ("Mu_pos", "Mu_neg", "Qu"):
                g[k] = max(g[k], cand[k])
    out = list(groups.values())
    with open(a.out, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print(f"Wrote {len(out)} beams to {a.out}. Sign convention: ETABS M3 positive = sagging. "
          f"Add flange_width/flange_t for T-beams if wanted.")


# ====================================================================== fix
def _load_factors():
    """Read LOAD_D, LOAD_L from Egyptian codes/ecp203/params.py when available."""
    here = os.path.dirname(os.path.abspath(__file__))
    for base in (os.getcwd(), os.path.join(here, "..", "..", ".."), os.path.join(here, "..", "..", "..", "..")):
        f = os.path.join(base, "Egyptian codes", "ecp203", "params.py")
        if os.path.exists(f):
            m = re.search(r"LOAD_D\s*,\s*LOAD_L\s*=\s*([\d.]+)\s*,\s*([\d.]+)", open(f, encoding="utf-8").read())
            if m:
                return float(m.group(1)), float(m.group(2)), f
    return 1.4, 1.6, None


def _guess_type(name):
    n = name.lower()
    if "wind" in n or n.startswith("w"):
        return "Wind"
    if "quake" in n or "seis" in n or n.startswith(("eq", "ex", "ey")):
        return "Seismic"
    if "live" in n or n in ("ll", "l"):
        return "Live"
    return "Super Dead"


def cmd_fix(a):
    M = read_e2k(a.model)
    with open(a.model, encoding="utf-8", errors="replace") as f:
        lines = f.read().splitlines()
    log = []
    inserts = defaultdict(list)  # keyword -> new lines (inserted after last line with that keyword)

    def last_index(keyword):
        idx = None
        for i, ln in enumerate(lines):
            t = ln.strip().split(None, 1)
            if t and t[0].upper() == keyword:
                idx = i
        return idx

    # 1. undefined load patterns referenced by loads or combinations
    refs = set()
    for ld in M.area_loads + M.line_loads + M.point_loads:
        lc = ld.get("LC") or ld.get("LOADPAT") or ld.get("PATTERN")
        if lc:
            refs.add(lc)
    for c in M.combos.values():
        for case, _ in c["items"]:
            if case not in M.combos:
                refs.add(case)
    for r in sorted(refs - set(M.patterns)):
        typ = _guess_type(r)
        inserts["LOADPATTERN"].append(f'  LOADPATTERN "{r}"  TYPE  "{typ}"  SELFWEIGHT  0')
        M.patterns[r] = {"TYPE": typ, "SELFWEIGHT": "0"}
        log.append(f"Added missing load pattern '{r}' as type {typ} (referenced but not defined) - VERIFY its type "
                   f"and, for wind/seismic, define its load parameters in ETABS.")
    # 2. self-weight exactly once
    sw = [n for n, p in M.patterns.items() if fnum(p.get("SELFWEIGHT"), 0) > 0]
    dead = [n for n, p in M.patterns.items() if str(p.get("TYPE", "")).lower() == "dead"]
    if len(sw) > 1:
        keep = dead[0] if dead and dead[0] in sw else sw[0]
        for n in sw:
            if n == keep:
                continue
            for i, ln in enumerate(lines):
                t = toks(ln)
                if len(t) > 1 and t[0].upper() == "LOADPATTERN" and t[1] == n:
                    lines[i] = re.sub(r"SELFWEIGHT\s+\S+", "SELFWEIGHT  0", ln)
            log.append(f"Self-weight removed from '{n}' (kept only in '{keep}') to avoid counting it twice.")
    elif not sw:
        if dead:
            for i, ln in enumerate(lines):
                t = toks(ln)
                if len(t) > 1 and t[0].upper() == "LOADPATTERN" and t[1] == dead[0]:
                    lines[i] = re.sub(r"SELFWEIGHT\s+\S+", "SELFWEIGHT  1", ln) if "SELFWEIGHT" in ln.upper() \
                        else ln + "  SELFWEIGHT  1"
            log.append(f"Self-weight multiplier 1 set on '{dead[0]}' (no pattern carried self-weight).")
        else:
            inserts["LOADPATTERN"].append('  LOADPATTERN "Dead"  TYPE  "Dead"  SELFWEIGHT  1')
            M.patterns["Dead"] = {"TYPE": "Dead", "SELFWEIGHT": "1"}
            log.append("Added load pattern 'Dead' with self-weight (none existed).")
    # 3. supports under base columns
    base = M.stories[-1]["name"] if M.stories else None
    restrained = {(pa["label"], pa["story"]) for pa in M.point_assigns if pa.get("RESTRAINT")}
    added = set()
    for e in instances(M):
        if e["kind"] == "column" and M.story_below(e["story"]) == base and (e["point"], base) not in restrained \
                and e["point"] not in added:
            inserts["POINTASSIGN"].append(f'  POINTASSIGN  "{e["point"]}"  "{base}"  RESTRAINT "UX UY UZ RX RY RZ"')
            added.add(e["point"])
            log.append(f"Added fixed support at point {e['point']} ({base}) under column {e['label']} - change to "
                       f"pinned if the foundation concept requires.")
    # 4. ultimate gravity combination
    LD, LL, src = _load_factors()
    types = {n: str(p.get("TYPE", "")).lower() for n, p in M.patterns.items()}
    dl = [n for n, t in types.items() if t in DEAD_TYPES]
    ll = [n for n, t in types.items() if t in LIVE_TYPES]
    has = False
    for c in M.combos.values():
        cs = {case for case, _ in c["items"]}
        if set(dl) <= cs and set(ll) <= cs and dl:
            has = True
    if not has and dl:
        name = "ECP-U1"
        new = [f'  COMBO "{name}"  TYPE "Linear Add"  DESIGN "Concrete"']
        new += [f'  COMBO "{name}"  LOAD "{n}"  SF {LD:g}' for n in dl]
        new += [f'  COMBO "{name}"  LOAD "{n}"  SF {LL:g}' for n in ll]
        inserts["COMBO"].extend(new)
        log.append(f"Added combination {name} = {LD:g}·(" + " + ".join(dl) + f") + {LL:g}·(" + " + ".join(ll) + ")"
                   + (f" (factors from {os.path.relpath(src)})" if src else " (default factors - verify)"))
    # write
    for kw, new in inserts.items():
        idx = last_index(kw)
        if idx is None:
            hdr = {"LOADPATTERN": "$ LOAD PATTERNS", "POINTASSIGN": "$ POINT ASSIGNS", "COMBO": "$ LOAD COMBINATIONS"}[kw]
            end = next((i for i, ln in enumerate(lines) if ln.strip().upper() == "END"), len(lines))
            lines[end:end] = [hdr] + new + [""]
        else:
            lines[idx + 1:idx + 1] = new
    out = a.out or re.sub(r"(\.[^.]+)$", r"_fixed\1", a.model)
    with open(out, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print(f"Fixes applied: {len(log)}")
    for l in log:
        print(" - " + l)
    print(f"Wrote {out}  (ETABS: File > Import > ETABS .e2k Text File, then re-run the analysis)")
    print("Not changed automatically (engineering decisions): section sizes, columns growing upward, stiffness "
          "modifiers, live-load values, seismic/wind parameters. See 'review'.")


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    s = p.add_subparsers(dest="cmd", required=True)
    x = s.add_parser("summary"); x.add_argument("model"); x.set_defaults(fn=cmd_summary)
    x = s.add_parser("review"); x.add_argument("model"); x.set_defaults(fn=cmd_review)
    x = s.add_parser("fix"); x.add_argument("model"); x.add_argument("-o", "--out"); x.set_defaults(fn=cmd_fix)
    x = s.add_parser("quantities"); x.add_argument("model"); x.add_argument("--xlsx")
    x.add_argument("--gross", action="store_true", help="no deduction at slab level"); x.set_defaults(fn=cmd_quantities)
    x = s.add_parser("tables"); x.add_argument("file"); x.add_argument("--list", action="store_true")
    x.add_argument("--table"); x.add_argument("--head", type=int, default=10); x.add_argument("--csv")
    x.set_defaults(fn=cmd_tables)
    x = s.add_parser("footings"); x.add_argument("--model", required=True); x.add_argument("--reactions", required=True)
    x.add_argument("--q-allow", type=float, required=True); x.add_argument("--fcu", type=float, default=25)
    x.add_argument("--fy", type=float, default=400); x.add_argument("--dead-cases"); x.add_argument("--live-cases")
    x.add_argument("--raft", action="store_true"); x.add_argument("--overhang", type=float, default=0.5)
    x.add_argument("-o", "--out", required=True); x.set_defaults(fn=cmd_footings)
    for nm, fn in (("columns", cmd_columns), ("beams", cmd_beams)):
        x = s.add_parser(nm); x.add_argument("--model", required=True); x.add_argument("--forces", required=True)
        x.add_argument("--combos", help="comma-separated ultimate combinations (default: all)")
        x.add_argument("--fcu", type=float, default=30); x.add_argument("--fy", type=float, default=400)
        x.add_argument("--group", action="store_true", help="one design per section per story")
        if nm == "columns":
            x.add_argument("--unbraced", action="store_true")
        x.add_argument("-o", "--out", required=True); x.set_defaults(fn=fn)
    a = p.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()
