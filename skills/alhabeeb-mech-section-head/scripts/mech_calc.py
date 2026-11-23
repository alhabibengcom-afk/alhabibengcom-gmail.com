#!/usr/bin/env python3
"""Electromechanical (HVAC / plumbing / fire) quick design checks - physics only (Darcy-Weisbach + Colebrook).
Design limits (friction rate, velocity) are YOUR inputs; the defaults are common design guidance (ASHRAE
Fundamentals ch.21 ducts / ch.22 pipes, in egyptian-codes/references/hvac) - confirm against the project spec.

  python3 mech_calc.py duct --flow 1500 [--unit l/s|m3/h|cfm] [--friction 1.0] [--vmax 8] [--aspect 2]
      Round diameter for the friction rate (Pa/m) and/or max velocity, rounded up to 50 mm; actual velocity and
      friction; equivalent rectangular duct (Huebscher) for the aspect ratio.

  python3 mech_calc.py pipe (--kw 350 --dt 5.5 | --flow 15 [--unit l/s|m3/h|gpm]) [--fluid chw|hw|cw]
                            [--max-friction 400] [--vmax 2.4] [--material steel|ppr|copper]
      Smallest nominal size meeting both limits (Pa/m, m/s), with velocity and friction of that size and the next.

  python3 mech_calc.py pump --flow 15 --size DN100 --length 180 [--fittings 0.5] [--equipment 60,35,20]
                            [--static 0] [--material steel]
      Pump head = straight friction x (1 + fittings allowance) + equipment drops (kPa) + static (m, open systems).

  python3 mech_calc.py batch lines.xlsx -o sized.xlsx   (sheet: Tag | Type duct/pipe | Flow | Unit | ...)
"""
import argparse
import math
import sys

RHO_AIR, NU_AIR = 1.20, 1.5e-5
FLUIDS = {"chw": (1000.0, 1.52e-6, 4.19), "hw": (980.0, 0.47e-6, 4.19), "cw": (998.0, 1.0e-6, 4.19)}  # rho, nu, cp
ROUGH = {"galv": 0.09e-3, "steel": 0.045e-3, "ppr": 0.007e-3, "copper": 0.0015e-3}
# nominal size -> internal diameter mm (steel sch.40; PPR PN20 and copper type L approximate - check catalogue)
SIZES = {
    "steel": [("DN15", 15.8), ("DN20", 20.9), ("DN25", 26.6), ("DN32", 35.1), ("DN40", 40.9), ("DN50", 52.5),
              ("DN65", 62.7), ("DN80", 77.9), ("DN100", 102.3), ("DN125", 128.2), ("DN150", 154.1),
              ("DN200", 202.7), ("DN250", 254.5), ("DN300", 304.8)],
    "ppr": [("20", 13.2), ("25", 16.6), ("32", 21.2), ("40", 26.6), ("50", 33.2), ("63", 42.0), ("75", 50.0),
            ("90", 60.0), ("110", 73.2), ("125", 83.4), ("160", 106.6)],
    "copper": [("15", 13.8), ("22", 20.2), ("28", 26.2), ("35", 32.6), ("42", 39.6), ("54", 51.6), ("67", 64.3),
               ("76", 73.1), ("108", 105.0)],
}


def friction_factor(Re, eps, D):
    if Re < 2300:
        return 64 / max(Re, 1)
    f = 0.02
    for _ in range(50):
        f = (-2 * math.log10(eps / D / 3.7 + 2.51 / (Re * math.sqrt(f)))) ** -2
    return f


def dp_per_m(Q, D, rho, nu, eps):
    A = math.pi * D * D / 4
    v = Q / A
    f = friction_factor(v * D / nu, eps, D)
    return f / D * rho * v * v / 2, v


def to_m3s(flow, unit, kind="air"):
    u = unit.lower()
    return {"l/s": flow / 1000, "m3/h": flow / 3600, "cfm": flow * 0.000471947, "m3/s": flow,
            "gpm": flow * 6.309e-5}[u]


def duct(a):
    Q = to_m3s(a.flow, a.unit)
    eps = ROUGH["galv"]
    D = 0.05
    while D < 3:
        dp, v = dp_per_m(Q, D, RHO_AIR, NU_AIR, eps)
        if (a.friction is None or dp <= a.friction) and (a.vmax is None or v <= a.vmax):
            break
        D += 0.05
    dp, v = dp_per_m(Q, D, RHO_AIR, NU_AIR, eps)
    print(f"Flow {Q * 1000:.0f} l/s ({Q * 3600:.0f} m3/h): round Ø{D * 1000:.0f} mm, v = {v:.2f} m/s, friction = {dp:.2f} Pa/m")
    # rectangular with the same friction (Huebscher De = 1.30 (ab)^0.625/(a+b)^0.25), b = aspect x h
    h = 0.1
    while True:
        b = a.aspect * h
        De = 1.30 * (b * h) ** 0.625 / (b + h) ** 0.25
        if De >= D - 1e-9:
            break
        h += 0.025
    hh, bb = math.ceil(h * 1000 / 50) * 50, math.ceil(a.aspect * h * 1000 / 50) * 50
    vr = Q / (hh * bb / 1e6)
    print(f"Rectangular (aspect {a.aspect:g}): {bb} x {hh} mm, v = {vr:.2f} m/s (equal-friction equivalent of Ø{D * 1000:.0f})")
    return {"round": D * 1000, "v": v, "dp": dp, "rect": f"{bb}x{hh}"}


def pipe_flow(a):
    rho, nu, cp = FLUIDS[a.fluid]
    if a.kw:
        m = a.kw / (cp * a.dt)  # kg/s
        return m / rho, f"{a.kw:g} kW / ({cp} x {a.dt:g} K) = {m:.2f} kg/s"
    return to_m3s(a.flow, a.unit), f"{a.flow:g} {a.unit}"


def pipe(a):
    rho, nu, cp = FLUIDS[a.fluid]
    Q, basis = pipe_flow(a)
    eps = ROUGH[a.material]
    print(f"Flow: {basis} = {Q * 1000:.2f} l/s ({Q * 3600:.1f} m3/h), fluid {a.fluid}, {a.material}")
    chosen = None
    rows = []
    for nm, di in SIZES[a.material]:
        dp, v = dp_per_m(Q, di / 1000, rho, nu, eps)
        ok = dp <= a.max_friction and v <= a.vmax
        rows.append((nm, di, v, dp, ok))
        if ok and chosen is None:
            chosen = len(rows) - 1
    if chosen is None:
        print("No size in the list meets the limits - split the flow or use a larger material size list.")
        return None
    for nm, di, v, dp, ok in rows[max(chosen - 1, 0):chosen + 2]:
        mark = "<- selected" if (nm, di) == rows[chosen][:2] else ""
        print(f"  {nm:>6} (ID {di:.1f} mm): v = {v:.2f} m/s, friction = {dp:.0f} Pa/m {mark}")
    print(f"Limits used: friction <= {a.max_friction} Pa/m, velocity <= {a.vmax} m/s (design guidance - confirm with spec)")
    return rows[chosen]


def pump(a):
    rho, nu, cp = FLUIDS[a.fluid]
    Q = to_m3s(a.flow, a.unit)
    di = dict(SIZES[a.material]).get(a.size)
    if not di:
        sys.exit(f"Unknown size {a.size}; options: {', '.join(n for n, _ in SIZES[a.material])}")
    dp, v = dp_per_m(Q, di / 1000, rho, nu, ROUGH[a.material])
    pipe_kpa = dp * a.length * (1 + a.fittings) / 1000
    eq = sum(float(x) for x in a.equipment.split(",")) if a.equipment else 0.0
    total_kpa = pipe_kpa + eq + a.static * rho * 9.81 / 1000
    H = total_kpa * 1000 / (rho * 9.81)
    print(f"Index circuit: {a.length:g} m of {a.size}, v = {v:.2f} m/s, {dp:.0f} Pa/m")
    print(f"  pipe + fittings ({a.fittings * 100:.0f}% allowance): {pipe_kpa:.1f} kPa")
    print(f"  equipment (chiller/coil/valves...): {eq:.1f} kPa;  static: {a.static:g} m")
    print(f"Pump head = {total_kpa:.1f} kPa = {H:.1f} m  @ {Q * 1000:.1f} l/s ({Q * 3600:.1f} m3/h); "
          f"add the project's safety margin before selecting the pump.")


def batch(a):
    import openpyxl
    ws = openpyxl.load_workbook(a.file, data_only=True).active
    hdr = [str(c.value or "").strip().lower() for c in ws[1]]
    out = openpyxl.Workbook()
    o = out.active
    o.append(["Tag", "Type", "Flow", "Unit", "Result", "Velocity m/s", "Friction Pa/m"])
    for r in ws.iter_rows(min_row=2, values_only=True):
        if not r or r[0] is None:
            continue
        d = dict(zip(hdr, r))
        typ = str(d.get("type", "")).lower()
        ns = argparse.Namespace(flow=float(d.get("flow")), unit=str(d.get("unit") or ("l/s")), friction=a.friction,
                                vmax=a.vmax_duct if typ == "duct" else a.vmax_pipe, aspect=2.0, kw=None, dt=None,
                                fluid=str(d.get("fluid") or "chw"), material=str(d.get("material") or "steel"),
                                max_friction=a.max_friction)
        print(f"--- {r[0]}")
        if typ == "duct":
            res = duct(ns)
            o.append([r[0], "duct", ns.flow, ns.unit, f"Ø{res['round']:.0f} / {res['rect']}", round(res["v"], 2),
                      round(res["dp"], 2)])
        else:
            res = pipe(ns)
            if res:
                o.append([r[0], "pipe", ns.flow, ns.unit, f"{res[0]}", round(res[2], 2), round(res[3])])
    out.save(a.out)
    print(f"-> {a.out}")


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    s = p.add_subparsers(dest="cmd", required=True)
    x = s.add_parser("duct")
    x.add_argument("--flow", type=float, required=True)
    x.add_argument("--unit", default="l/s")
    x.add_argument("--friction", type=float, default=1.0, help="Pa/m (guidance ~0.8-1.2 low-velocity supply)")
    x.add_argument("--vmax", type=float, default=None)
    x.add_argument("--aspect", type=float, default=2.0)
    x.set_defaults(fn=duct)
    x = s.add_parser("pipe")
    x.add_argument("--kw", type=float)
    x.add_argument("--dt", type=float, default=5.5)
    x.add_argument("--flow", type=float)
    x.add_argument("--unit", default="l/s")
    x.add_argument("--fluid", choices=list(FLUIDS), default="chw")
    x.add_argument("--material", choices=list(SIZES), default="steel")
    x.add_argument("--max-friction", type=float, default=400.0, help="Pa/m (guidance 100-400)")
    x.add_argument("--vmax", type=float, default=2.4, help="m/s (guidance; lower near occupied spaces)")
    x.set_defaults(fn=pipe)
    x = s.add_parser("pump")
    x.add_argument("--flow", type=float, required=True)
    x.add_argument("--unit", default="l/s")
    x.add_argument("--size", required=True)
    x.add_argument("--length", type=float, required=True, help="index circuit length, supply + return, m")
    x.add_argument("--fittings", type=float, default=0.5, help="fittings allowance as a fraction of straight friction")
    x.add_argument("--equipment", help="comma list of equipment pressure drops kPa")
    x.add_argument("--static", type=float, default=0.0, help="m (open systems only)")
    x.add_argument("--fluid", choices=list(FLUIDS), default="chw")
    x.add_argument("--material", choices=list(SIZES), default="steel")
    x.set_defaults(fn=pump)
    x = s.add_parser("batch")
    x.add_argument("file")
    x.add_argument("--friction", type=float, default=1.0)
    x.add_argument("--vmax-duct", type=float, default=None)
    x.add_argument("--vmax-pipe", type=float, default=2.4)
    x.add_argument("--max-friction", type=float, default=400.0)
    x.add_argument("-o", "--out", required=True)
    x.set_defaults(fn=batch)
    a = p.parse_args()
    if a.cmd == "pipe" and not a.kw and not a.flow:
        sys.exit("give --kw (and --dt) or --flow")
    a.fn(a)


if __name__ == "__main__":
    main()
