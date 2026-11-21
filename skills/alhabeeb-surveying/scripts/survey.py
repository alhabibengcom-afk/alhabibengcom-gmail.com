#!/usr/bin/env python3
"""Site surveying calculator (metric). Standard library only.

Subcommands and CSV formats (header row required, extra columns ignored):

  level     Level book reduction (HI and rise & fall checks, misclosure, adjustment)
            CSV: station,bs,is,fs   (leave blank cells empty; change point = fs and bs on one row)
  traverse  Closed-loop traverse, Bowditch adjustment
            CSV: station,angle,distance   angle = horizontal angle at the station measured
            CLOCKWISE from the previous (back) station to the next (forward) station, as read on
            the total station (decimal degrees or D-M-S like 89-59-30); distance = to the NEXT station.
            Stations listed anticlockwise round the loop -> these are interior angles;
            listed clockwise -> exterior angles. Both are detected from the angle sum.
  inverse   Bearing and distance between two points
  setout    Set-out data (bearing, angle from backsight, distance) from a station to points
            CSV: point,e,n
  area      Polygon area from coordinates (shoelace); CSV: point,e,n  (in order around the boundary)
  grid      Cut/fill volumes, grid method; CSV: row,col,level  (existing ground at grid nodes)
  sections  Volume from cross-section areas; CSV: chainage,cut_area,fill_area

Examples:
  python3 survey.py level --file book.csv --start-rl 25.000 --close-rl 25.000 --km 0.6
  python3 survey.py traverse --file trav.csv --start-e 1000 --start-n 1000 --start-bearing 45-00-00
  python3 survey.py inverse --p1 1000,1000 --p2 1050.25,1080.10
  python3 survey.py setout --station 1000,1000 --backsight 1000,1100 --file pts.csv
  python3 survey.py area --file plot.csv
  python3 survey.py grid --file grid.csv --cell 10 --design 24.50
  python3 survey.py sections --file sec.csv --prismoidal
"""
import argparse
import csv
import math
import sys

FEDDAN = 4200.83
QIRAT = FEDDAN / 24
SAHM = QIRAT / 24


def read_csv(path):
    with open(path, newline="", encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))
    return [{(k or "").strip().lower(): (v or "").strip() for k, v in r.items()} for r in rows]


def num(v):
    return float(v) if v not in ("", None) else None


def parse_angle(s):
    s = str(s).strip()
    if "-" in s[1:] or " " in s:
        parts = [float(x) for x in s.replace(" ", "-").split("-") if x != ""]
        while len(parts) < 3:
            parts.append(0.0)
        d, m, sec = parts
        return d + m / 60 + sec / 3600
    return float(s)


def dms(deg):
    deg = deg % 360
    d = int(deg)
    m_full = (deg - d) * 60
    m = int(m_full)
    s = (m_full - m) * 60
    if round(s, 1) >= 60:
        s = 0
        m += 1
    if m >= 60:
        m = 0
        d += 1
    return f"{d:03d}°{m:02d}'{s:04.1f}\""


def bearing(de, dn):
    return math.degrees(math.atan2(de, dn)) % 360


# ---------------- level ----------------
def cmd_level(a):
    rows = read_csv(a.file)
    rl = a.start_rl
    hi = None
    out = []
    sbs = sfs = srise = sfall = 0.0
    prev = None
    setup = 0
    for r in rows:
        bs, is_, fs = num(r.get("bs")), num(r.get("is")), num(r.get("fs"))
        st = r.get("station", "")
        rise = fall = None
        if hi is None:  # first row
            if bs is None:
                sys.exit("First row must have a backsight")
            hi = rl + bs
            sbs += bs
            setup = 1
            out.append([st, bs, None, None, None, None, rl, setup])
            prev = bs
            continue
        reading = fs if fs is not None else is_
        if reading is None:
            sys.exit(f"Row {st}: no IS or FS")
        diff = prev - reading
        if diff >= 0:
            rise = diff
            srise += diff
        else:
            fall = -diff
            sfall += -diff
        rl = hi - reading
        out.append([st, bs, is_, fs, rise, fall, rl, setup])
        if fs is not None:
            sfs += fs
        if bs is not None:
            sbs += bs
            hi = rl + bs
            prev = bs
            setup += 1
        else:
            prev = reading
    n_setups = setup
    first, last = a.start_rl, out[-1][6]
    print(f"{'Station':<10}{'BS':>8}{'IS':>8}{'FS':>8}{'Rise':>8}{'Fall':>8}{'RL':>10}{'Adj RL':>10}")
    e = None
    if a.close_rl is not None:
        e = last - a.close_rl
    for row in out:
        st, bs, is_, fs, rise, fall, r_l, su = row
        # correction proportional to set-up number at which the point was observed
        corr = -e * su / n_setups if e is not None else 0.0
        if row is out[0]:
            corr = 0.0
        f = lambda v: f"{v:8.3f}" if v is not None else " " * 8
        print(f"{st:<10}{f(bs)}{f(is_)}{f(fs)}{f(rise)}{f(fall)}{r_l:10.3f}{r_l + corr:10.3f}")
    print()
    print(f"Sum BS = {sbs:.3f}  Sum FS = {sfs:.3f}  BS-FS = {sbs - sfs:+.3f}")
    print(f"Sum Rise = {srise:.3f}  Sum Fall = {sfall:.3f}  Rise-Fall = {srise - sfall:+.3f}")
    print(f"Last RL - First RL = {last - first:+.3f}  -> arithmetic check "
          f"{'OK' if abs((sbs - sfs) - (last - first)) < 5e-4 and abs((srise - sfall) - (last - first)) < 5e-4 else 'FAILED'}")
    print(f"Set-ups: {n_setups}")
    if e is not None:
        print(f"Misclosure = {e * 1000:+.1f} mm (observed {last:.3f} vs known {a.close_rl:.3f})")
        if a.km:
            allow = a.k * math.sqrt(a.km)
            print(f"Allowable = ±{a.k}√K = ±{allow:.1f} mm (K = {a.km} km) -> "
                  f"{'WITHIN tolerance: adjusted RL column applies' if abs(e * 1000) <= allow else 'EXCEEDS tolerance: re-level, do not adjust'}")
        else:
            print("Give --km to compare with ±k√K allowable.")
    else:
        print("No --close-rl given: misclosure not checked (Adj RL = RL).")


# ---------------- traverse ----------------
def cmd_traverse(a):
    rows = read_csv(a.file)
    n = len(rows)
    angles = [parse_angle(r["angle"]) for r in rows]
    dists = [float(r["distance"]) for r in rows]
    names = [r["station"] for r in rows]
    s = sum(angles)
    interior = (n - 2) * 180
    exterior = (n + 2) * 180
    target = interior if abs(s - interior) < abs(s - exterior) else exterior
    mis = s - target
    print(f"Sum of angles = {dms(s) if s < 360 else f'{s:.5f}°'} ({s:.5f}°), should be {target}° -> misclosure {mis * 3600:+.1f}\"")
    if a.k:
        allow = a.k * math.sqrt(n)
        print(f"Allowable ±{a.k}\"√n = ±{allow:.1f}\" -> {'OK' if abs(mis * 3600) <= allow else 'EXCEEDS: re-observe angles'}")
    corr = -mis / n
    adj = [x + corr for x in angles]
    # b_next = b_prev + 180 + clockwise angle (back -> forward) at the next station
    b = [parse_angle(a.start_bearing)]
    for i in range(1, n):
        b.append((b[-1] + 180 + adj[i]) % 360 if not a.anticlockwise else (b[-1] + 180 - adj[i]) % 360)
    de = [d * math.sin(math.radians(x)) for d, x in zip(dists, b)]
    dn = [d * math.cos(math.radians(x)) for d, x in zip(dists, b)]
    fe, fn = sum(de), sum(dn)
    per = sum(dists)
    f = math.hypot(fe, fn)
    print(f"Linear misclosure: fE = {fe:+.4f} m, fN = {fn:+.4f} m, f = {f:.4f} m, perimeter = {per:.3f} m")
    print(f"Relative precision = 1 : {per / f:,.0f}" if f > 0 else "Perfect closure")
    E, N = a.start_e, a.start_n
    print(f"\n{'From':<8}{'To':<8}{'Bearing':>14}{'Dist':>10}{'dE':>10}{'dN':>10}{'cE':>8}{'cN':>8}{'E':>13}{'N':>13}")
    print(f"{'':<16}{'':>14}{'':>10}{'':>10}{'':>10}{'':>8}{'':>8}{E:13.3f}{N:13.3f}  {names[0]}")
    for i in range(n):
        ce, cn = -fe * dists[i] / per, -fn * dists[i] / per
        E += de[i] + ce
        N += dn[i] + cn
        to = names[(i + 1) % n]
        print(f"{names[i]:<8}{to:<8}{dms(b[i]):>14}{dists[i]:10.3f}{de[i]:10.3f}{dn[i]:10.3f}{ce:8.4f}{cn:8.4f}{E:13.3f}{N:13.3f}")
    print("(Last line should return to the start coordinates.)")


# ---------------- inverse ----------------
def pt(s):
    e, n = [float(x) for x in s.split(",")[:2]]
    return e, n


def cmd_inverse(a):
    (e1, n1), (e2, n2) = pt(a.p1), pt(a.p2)
    de, dn = e2 - e1, n2 - n1
    print(f"dE = {de:+.3f} m, dN = {dn:+.3f} m")
    print(f"Distance = {math.hypot(de, dn):.3f} m")
    print(f"Bearing = {dms(bearing(de, dn))} ({bearing(de, dn):.5f}°)")


def cmd_setout(a):
    se, sn = pt(a.station)
    be, bn = pt(a.backsight)
    b_bs = bearing(be - se, bn - sn)
    print(f"Backsight bearing = {dms(b_bs)}; set instrument to read 000°00'00\" on backsight")
    print(f"{'Point':<10}{'E':>12}{'N':>12}{'Bearing':>14}{'Angle (cw from BS)':>20}{'Distance':>10}")
    for r in read_csv(a.file):
        e, n = float(r["e"]), float(r["n"])
        b = bearing(e - se, n - sn)
        print(f"{r.get('point', ''):<10}{e:12.3f}{n:12.3f}{dms(b):>14}{dms(b - b_bs):>20}{math.hypot(e - se, n - sn):10.3f}")


# ---------------- area ----------------
def cmd_area(a):
    rows = read_csv(a.file)
    P = [(float(r["e"]), float(r["n"])) for r in rows]
    s = 0.0
    per = 0.0
    for i in range(len(P)):
        e1, n1 = P[i]
        e2, n2 = P[(i + 1) % len(P)]
        s += e1 * n2 - e2 * n1
        per += math.hypot(e2 - e1, n2 - n1)
    A = abs(s) / 2
    f = int(A // FEDDAN)
    rem = A - f * FEDDAN
    q = int(rem // QIRAT)
    sh = (rem - q * QIRAT) / SAHM
    print(f"Points: {len(P)}  Perimeter = {per:.3f} m")
    print(f"Area = {A:,.3f} m2 = {A / 10000:.4f} ha")
    print(f"     = {f} feddan {q} qirat {sh:.1f} sahm  (1 feddan = {FEDDAN} m2)")


# ---------------- grid ----------------
def cmd_grid(a):
    rows = read_csv(a.file)
    lv = {}
    for r in rows:
        lv[(int(r["row"]), int(r["col"]))] = float(r["level"])
    A = a.cell * (a.cell_y or a.cell)
    rows_i = sorted({k[0] for k in lv})
    cols_i = sorted({k[1] for k in lv})
    cut = fill = 0.0
    ncell = 0
    for i, j in [(i, j) for i in rows_i for j in cols_i]:
        corners = [(i, j), (i + 1, j), (i + 1, j + 1), (i, j + 1)]
        if not all(c in lv for c in corners):
            continue
        ncell += 1
        h = [lv[c] - a.design for c in corners]  # + = cut, - = fill
        c_ = sum(x for x in h if x > 0)
        f_ = -sum(x for x in h if x < 0)
        if f_ == 0:
            cut += A * c_ / 4
        elif c_ == 0:
            fill += A * f_ / 4
        else:
            cut += A / 4 * c_ ** 2 / (c_ + f_)
            fill += A / 4 * f_ ** 2 / (c_ + f_)
    print(f"Cells: {ncell} of {a.cell} x {a.cell_y or a.cell} m (area {ncell * A:,.1f} m2), design level {a.design:.3f}")
    print(f"Cut  = {cut:,.1f} m3 (bank)")
    print(f"Fill = {fill:,.1f} m3 (compacted in place)")
    print(f"Net  = {cut - fill:+,.1f} m3 ({'surplus' if cut - fill > 0.05 else 'shortage' if fill - cut > 0.05 else 'balanced'})")
    if a.swell:
        print(f"Cut loose volume (swell {a.swell * 100:.0f} %) = {cut * (1 + a.swell):,.1f} m3")
    print("Mixed cells use the cut²/(cut+fill) approximation.")


# ---------------- sections ----------------
def cmd_sections(a):
    rows = read_csv(a.file)
    ch = [float(r["chainage"]) for r in rows]
    ca = [float(r.get("cut_area") or 0) for r in rows]
    fa = [float(r.get("fill_area") or 0) for r in rows]

    def aea(areas):
        return sum((ch[i + 1] - ch[i]) * (areas[i] + areas[i + 1]) / 2 for i in range(len(ch) - 1))

    def simpson(areas):
        d = [ch[i + 1] - ch[i] for i in range(len(ch) - 1)]
        if len(areas) < 3 or (len(areas) - 1) % 2 or max(d) - min(d) > 1e-6:
            return None
        h = d[0]
        s = areas[0] + areas[-1] + sum((4 if k % 2 else 2) * areas[k] for k in range(1, len(areas) - 1))
        return h / 3 * s

    print(f"{'From':>10}{'To':>10}{'Cut m3':>12}{'Fill m3':>12}")
    for i in range(len(ch) - 1):
        L = ch[i + 1] - ch[i]
        print(f"{ch[i]:10.2f}{ch[i + 1]:10.2f}{L * (ca[i] + ca[i + 1]) / 2:12.1f}{L * (fa[i] + fa[i + 1]) / 2:12.1f}")
    print(f"Average end area: cut = {aea(ca):,.1f} m3, fill = {aea(fa):,.1f} m3")
    if a.prismoidal:
        sc, sf = simpson(ca), simpson(fa)
        if sc is None:
            print("Prismoidal (Simpson) needs equal spacing and an odd number of sections.")
        else:
            print(f"Prismoidal (Simpson): cut = {sc:,.1f} m3, fill = {sf:,.1f} m3")


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    s = p.add_subparsers(dest="cmd", required=True)

    x = s.add_parser("level")
    x.add_argument("--file", required=True)
    x.add_argument("--start-rl", type=float, required=True)
    x.add_argument("--close-rl", type=float, help="known RL of the closing benchmark")
    x.add_argument("--km", type=float, help="length of the levelling line in km")
    x.add_argument("--k", type=float, default=12.0, help="allowable constant mm (default 12 -> ±12√K)")
    x.set_defaults(fn=cmd_level)

    x = s.add_parser("traverse")
    x.add_argument("--file", required=True)
    x.add_argument("--start-e", type=float, required=True)
    x.add_argument("--start-n", type=float, required=True)
    x.add_argument("--start-bearing", required=True, help="bearing of the first leg (station1 -> station2)")
    x.add_argument("--k", type=float, help="angular allowable constant in seconds (±k√n)")
    x.add_argument("--anticlockwise", action="store_true",
                   help="angles were measured anticlockwise from back to forward station")
    x.set_defaults(fn=cmd_traverse)

    x = s.add_parser("inverse")
    x.add_argument("--p1", required=True, help="E,N")
    x.add_argument("--p2", required=True, help="E,N")
    x.set_defaults(fn=cmd_inverse)

    x = s.add_parser("setout")
    x.add_argument("--station", required=True, help="E,N")
    x.add_argument("--backsight", required=True, help="E,N")
    x.add_argument("--file", required=True)
    x.set_defaults(fn=cmd_setout)

    x = s.add_parser("area")
    x.add_argument("--file", required=True)
    x.set_defaults(fn=cmd_area)

    x = s.add_parser("grid")
    x.add_argument("--file", required=True)
    x.add_argument("--cell", type=float, required=True, help="grid spacing m (x)")
    x.add_argument("--cell-y", type=float, help="grid spacing m (y), default = --cell")
    x.add_argument("--design", type=float, required=True, help="design formation level")
    x.add_argument("--swell", type=float, help="swell factor as decimal, e.g. 0.25")
    x.set_defaults(fn=cmd_grid)

    x = s.add_parser("sections")
    x.add_argument("--file", required=True)
    x.add_argument("--prismoidal", action="store_true")
    x.set_defaults(fn=cmd_sections)

    a = p.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()
