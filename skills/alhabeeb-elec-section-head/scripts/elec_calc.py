#!/usr/bin/env python3
"""Electrical section quick design checks (Al-Habeeb technical office). Physics + your tables:
cable current ratings and derating factors come from the cable manufacturer's catalogue / the Egyptian electrical
code tables (egyptian-codes/references/electrical) that you put in the ampacity CSV - never invented here.

  python3 elec_calc.py panel circuits.xlsx [--demand 0.8] [--pf 0.85] [--v 400] -o panel.xlsx
      circuits.xlsx: Circuit | Description | Load kW (or VA) | Phases (1/3) | PF (opt.)
      Balances single-phase circuits on L1/L2/L3 (largest first to the lightest phase), totals per phase,
      unbalance %, demand load, design current, suggested main breaker (next standard rating).

  python3 elec_calc.py cable --kw 45 --length 85 [--pf 0.85] [--v 400] [--phases 3] [--vd-max 4]
                             --table ampacity.csv [--derate 0.8] [--material cu]
      ampacity.csv columns: size_mm2, rating_A  (your installation method, from the catalogue / code table)
      Picks the smallest size with derated rating >= design current AND voltage drop <= vd-max %.
      Voltage drop: 3-ph  ΔV = √3 I L (R cosφ + X sinφ);  1-ph  ΔV = 2 I L (R cosφ + X sinφ)
      R from resistivity at 70 °C (Cu 0.0225, Al 0.036 Ω·mm²/m), X = 0.08 Ω/km (typical LV cable) unless the CSV
      gives r_ohm_km / x_ohm_km columns. vd-max is YOUR limit from the code/spec (E04 design basis).

  python3 elec_calc.py breaker --amps 73        next standard rating (IEC series)

  python3 elec_calc.py lux --area 120 --lux 500 --lumens 3600 [--uf 0.6] [--mf 0.8]
      Lumen method N = E·A / (Φ·UF·MF); E target from the code/spec (lighting volumes in the electrical code).
"""
import argparse
import csv
import math
import sys

STD = [6, 10, 16, 20, 25, 32, 40, 50, 63, 80, 100, 125, 160, 200, 250, 315, 400, 500, 630, 800, 1000, 1250,
       1600, 2000, 2500, 3200, 4000]
RHO70 = {"cu": 0.0225, "al": 0.036}


def next_std(i):
    return next((s for s in STD if s >= i), None)


def current(kw, v, pf, phases):
    return kw * 1000 / ((math.sqrt(3) * v if phases == 3 else v) * pf)


def panel(a):
    import openpyxl
    ws = openpyxl.load_workbook(a.file, data_only=True).active
    hdr = [str(c.value or "").strip().lower() for c in ws[1]]

    def col(*ks):
        return next((i for i, h in enumerate(hdr) if any(k in h for k in ks)), None)
    ci, cd, ck, cph, cpf = col("circuit"), col("desc"), col("kw", "va", "load"), col("phase"), col("pf")
    va_mode = ck is not None and "va" in hdr[ck] and "kw" not in hdr[ck]
    circ = []
    for r in ws.iter_rows(min_row=2, values_only=True):
        if not r or r[ci] is None:
            continue
        load = float(r[ck] or 0) / (1000 if va_mode else 1)
        pf = float(r[cpf]) if cpf is not None and r[cpf] else a.pf
        circ.append({"c": r[ci], "d": r[cd] if cd is not None else "", "kw": load,
                     "ph": int(r[cph] or 1) if cph is not None else 1, "pf": pf})
    phase = {"L1": 0.0, "L2": 0.0, "L3": 0.0}
    for c in sorted(circ, key=lambda c: -c["kw"]):
        if c["ph"] == 3:
            for k in phase:
                phase[k] += c["kw"] / 3
            c["on"] = "L1-L2-L3"
        else:
            k = min(phase, key=phase.get)
            phase[k] += c["kw"]
            c["on"] = k
    tot = sum(phase.values())
    avg = tot / 3
    unb = (max(phase.values()) - avg) / avg * 100 if avg else 0
    dem = tot * a.demand
    vph = a.v / math.sqrt(3)
    imax = max(phase.values()) * a.demand * 1000 / (vph * a.pf)
    brk = next_std(imax * 1.0)
    print(f"Connected {tot:.2f} kW: L1 {phase['L1']:.2f}  L2 {phase['L2']:.2f}  L3 {phase['L3']:.2f} kW, unbalance {unb:.1f}%")
    print(f"Demand ({a.demand:g}): {dem:.2f} kW; design current (heaviest phase) {imax:.1f} A -> main breaker {brk} A "
          f"(check cable, selectivity and the demand factor from the code/spec)")
    o = openpyxl.Workbook()
    s = o.active
    s.title = "Panel schedule"
    s.append(["Circuit", "Description", "kW", "Phases", "PF", "Phase", "Current A", "Breaker A"])
    for c in circ:
        I = current(c["kw"], a.v if c["ph"] == 3 else vph, c["pf"], c["ph"])
        s.append([c["c"], c["d"], round(c["kw"], 3), c["ph"], c["pf"], c["on"], round(I, 1), next_std(I)])
    s.append([])
    for r in (["L1 kW", round(phase["L1"], 2)], ["L2 kW", round(phase["L2"], 2)], ["L3 kW", round(phase["L3"], 2)],
              ["Unbalance %", round(unb, 1)], ["Demand factor", a.demand], ["Demand kW", round(dem, 2)],
              ["Design current A", round(imax, 1)], ["Main breaker A", brk]):
        s.append(r)
    o.save(a.out)
    print(f"-> {a.out}")


def cable(a):
    rows = []
    with open(a.table, newline="", encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            rows.append({k.strip().lower(): v for k, v in r.items()})
    I = current(a.kw, a.v, a.pf, a.phases) if a.kw else a.amps
    sinp = math.sqrt(1 - a.pf ** 2)
    print(f"Design current {I:.1f} A ({a.kw} kW, {a.phases}-ph, {a.v} V, pf {a.pf}), length {a.length} m, "
          f"derating {a.derate}, VD limit {a.vd_max}%")
    pick = None
    for r in sorted(rows, key=lambda r: float(r["size_mm2"])):
        S = float(r["size_mm2"])
        Iz = float(r["rating_a"]) * a.derate
        R = float(r.get("r_ohm_km") or 0) or RHO70[a.material] / S * 1000
        X = float(r.get("x_ohm_km") or 0) or 0.08
        k = math.sqrt(3) if a.phases == 3 else 2
        dv = k * I * a.length / 1000 * (R * a.pf + X * sinp)
        vd = dv / a.v * 100 if a.phases == 3 else dv / (a.v / math.sqrt(3) if a.v > 300 else a.v) * 100
        ok = Iz >= I and vd <= a.vd_max
        print(f"  {S:>6g} mm2: Iz {Iz:6.1f} A {'OK ' if Iz >= I else 'LOW'}  VD {vd:5.2f}% {'OK' if vd <= a.vd_max else 'HIGH'}"
              + ("  <- selected" if ok and pick is None else ""))
        if ok and pick is None:
            pick = (S, Iz, vd)
    if pick:
        print(f"Selected {pick[0]:g} mm2; protective device In between {I:.0f} A and {pick[1]:.0f} A -> "
              f"{max(s for s in STD if s <= pick[1]) if any(s <= pick[1] for s in STD) else '-'} A max (Ib <= In <= Iz)")
    else:
        print("No size in the table satisfies both - add larger sizes or parallel cables.")


def breaker(a):
    print(f"{a.amps} A -> next standard rating {next_std(a.amps)} A")


def lux(a):
    n = a.lux * a.area / (a.lumens * a.uf * a.mf)
    print(f"N = {a.lux} x {a.area} / ({a.lumens} x {a.uf} x {a.mf}) = {n:.1f} -> {math.ceil(n)} luminaires; "
          f"achieved ≈ {math.ceil(n) * a.lumens * a.uf * a.mf / a.area:.0f} lux (UF from the photometric data)")


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    s = p.add_subparsers(dest="cmd", required=True)
    x = s.add_parser("panel")
    x.add_argument("file")
    x.add_argument("--demand", type=float, default=0.8, help="demand factor (from code/spec)")
    x.add_argument("--pf", type=float, default=0.85)
    x.add_argument("--v", type=float, default=400)
    x.add_argument("-o", "--out", required=True)
    x.set_defaults(fn=panel)
    x = s.add_parser("cable")
    x.add_argument("--kw", type=float)
    x.add_argument("--amps", type=float)
    x.add_argument("--length", type=float, required=True)
    x.add_argument("--pf", type=float, default=0.85)
    x.add_argument("--v", type=float, default=400)
    x.add_argument("--phases", type=int, choices=(1, 3), default=3)
    x.add_argument("--vd-max", type=float, required=True, help="%% limit from the code/spec")
    x.add_argument("--table", required=True)
    x.add_argument("--derate", type=float, default=1.0)
    x.add_argument("--material", choices=list(RHO70), default="cu")
    x.set_defaults(fn=cable)
    x = s.add_parser("breaker")
    x.add_argument("--amps", type=float, required=True)
    x.set_defaults(fn=breaker)
    x = s.add_parser("lux")
    for k in ("area", "lux", "lumens"):
        x.add_argument(f"--{k}", type=float, required=True)
    x.add_argument("--uf", type=float, default=0.6)
    x.add_argument("--mf", type=float, default=0.8)
    x.set_defaults(fn=lux)
    a = p.parse_args()
    if a.cmd == "cable" and not a.kw and not a.amps:
        sys.exit("give --kw or --amps")
    a.fn(a)


if __name__ == "__main__":
    main()
