#!/usr/bin/env python3
"""Geotechnical calculator (SI units: kN, m, kN/m2, kN/m3). Standard library only.

Subcommands:
  bearing        Bearing capacity of a shallow footing (Meyerhof/Vesic/Hansen form)
  spt            SPT corrections and correlations for sand
  consolidation  Consolidation settlement of layered clay under a rectangular footing (2:1 method)
  elastic        Immediate settlement of a footing on an elastic layer

Examples:
  python3 geotech.py bearing --B 2 --L 2 --Df 1.5 --phi 30 --c 0 --gamma 18 --gamma-sat 20 --water 1.0
  python3 geotech.py bearing --B 2 --L 2 --Df 1.5 --phi 0 --c 60 --gamma 18
  python3 geotech.py spt --N 18 --depth 4 --gamma 18 --water 2 --gamma-sat 20 --er 60
  python3 geotech.py consolidation --P 1500 --B 2.5 --L 2.5 --Df 1.5 \
      --layer 3,6,18.5,0.30,0.06,0.9 --water 1.5
  python3 geotech.py elastic --q 150 --B 2 --L 2 --Es 25000 --nu 0.3
"""
import argparse
import math

GW = 9.81


def factors(phi_deg, ngamma="vesic"):
    if phi_deg == 0:
        return 5.14, 1.0, 0.0
    p = math.radians(phi_deg)
    nq = math.exp(math.pi * math.tan(p)) * math.tan(math.radians(45 + phi_deg / 2)) ** 2
    nc = (nq - 1) / math.tan(p)
    if ngamma == "meyerhof":
        ng = (nq - 1) * math.tan(1.4 * p)
    elif ngamma == "hansen":
        ng = 1.5 * (nq - 1) * math.tan(p)
    else:
        ng = 2 * (nq + 1) * math.tan(p)
    return nc, nq, ng


def cmd_bearing(a):
    B, L, Df, phi, c = a.B, a.L or a.B * 1e6, a.Df, a.phi, a.c
    strip = a.L is None
    ex, ey = a.ex, a.ey
    Bp, Lp = B - 2 * ex, (L - 2 * ey) if not strip else L
    if Bp <= 0 or Lp <= 0:
        raise SystemExit("Eccentricity too large: effective dimension <= 0")
    if Bp > Lp:
        Bp, Lp = Lp, Bp
    gsat = a.gamma_sat if a.gamma_sat else a.gamma + 2
    gsub = gsat - GW
    Dw = a.water
    # overburden q
    if Dw is None or Dw >= Df:
        q = a.gamma * Df
    else:
        q = a.gamma * Dw + gsub * (Df - Dw)
    # gamma for N-gamma term
    if Dw is None or Dw >= Df + Bp:
        g_eff = a.gamma
    elif Dw <= Df:
        g_eff = gsub
    else:
        d = Dw - Df
        g_eff = gsub + (d / Bp) * (a.gamma - gsub)
    nc, nq, ng = factors(phi, a.ngamma)
    r = 0 if strip else Bp / Lp
    tp = math.tan(math.radians(phi))
    sc = 1 + r * nq / nc
    sq = 1 + r * tp
    sg = max(1 - 0.4 * r, 0.6)
    if phi == 0:
        sc = 1 + 0.2 * r
        sq = 1.0
    k = Df / B if Df / B <= 1 else math.atan(Df / B)
    if a.no_depth:
        dc = dq = 1.0
    elif phi == 0:
        dq = 1.0
        dc = 1 + 0.4 * k
    else:
        dq = 1 + 2 * tp * (1 - math.sin(math.radians(phi))) ** 2 * k
        dc = dq - (1 - dq) / (nc * tp)
    dg = 1.0
    beta = a.incl
    ic = iq = (1 - beta / 90) ** 2
    ig = (1 - beta / phi) ** 2 if phi > 0 and beta < phi else (0.0 if phi > 0 else 1.0)
    t1 = c * nc * sc * dc * ic
    t2 = q * nq * sq * dq * iq
    t3 = 0.5 * g_eff * Bp * ng * sg * dg * ig
    qult = t1 + t2 + t3
    qnet = qult - q
    print(f"Effective B' = {Bp:.3f} m, L' = {'strip' if strip else f'{Lp:.3f} m'}")
    print(f"phi = {phi} deg  Nc = {nc:.2f}  Nq = {nq:.2f}  Ngamma({a.ngamma}) = {ng:.2f}")
    print(f"Shape  sc={sc:.3f} sq={sq:.3f} sg={sg:.3f}")
    print(f"Depth  dc={dc:.3f} dq={dq:.3f} dg={dg:.3f}{'  (ignored)' if a.no_depth else ''}")
    print(f"Incl.  ic={ic:.3f} iq={iq:.3f} ig={ig:.3f}")
    print(f"Overburden q = {q:.2f} kN/m2 ; gamma used in N-gamma term = {g_eff:.2f} kN/m3")
    print(f"Terms: cohesion {t1:.1f} + overburden {t2:.1f} + width {t3:.1f}")
    print(f"q_ult (gross) = {qult:.1f} kN/m2")
    print(f"q_all gross = q_ult/{a.fs} = {qult / a.fs:.1f} kN/m2  ({qult / a.fs / 98.1:.2f} kg/cm2)")
    print(f"q_all net   = (q_ult - q)/{a.fs} = {qnet / a.fs:.1f} kN/m2  ({qnet / a.fs / 98.1:.2f} kg/cm2)")
    if not strip:
        print(f"Allowable column load on effective area ~ {qnet / a.fs * Bp * Lp:.0f} kN (net)")
    print("Check settlement separately; allowable = min(bearing, settlement-controlled).")


def sigma_v_eff(z, gamma, gsat, Dw):
    if Dw is None or z <= Dw:
        return gamma * z
    return gamma * Dw + (gsat - GW) * (z - Dw)


def cmd_spt(a):
    cr = 0.75 if a.depth < 4 else 0.85 if a.depth < 6 else 0.95 if a.depth < 10 else 1.0
    if a.rod_length is not None:
        Lr = a.rod_length
        cr = 0.75 if Lr < 4 else 0.85 if Lr < 6 else 0.95 if Lr < 10 else 1.0
    cb = 1.0 if a.diameter <= 115 else 1.05 if a.diameter <= 150 else 1.15
    n60 = a.N * (a.er / 60) * cb * cr
    gsat = a.gamma_sat if a.gamma_sat else a.gamma + 2
    sv = sigma_v_eff(a.depth, a.gamma, gsat, a.water)
    cn = min(math.sqrt(100 / sv), 1.7) if sv > 0 else 1.7
    n160 = cn * n60
    phi_hu = math.sqrt(20 * n160) + 20
    phi_pht = 27.1 + 0.3 * n60 - 0.00054 * n60 ** 2
    dr = min(math.sqrt(max(n160, 0) / 60), 1.0) * 100
    dens = ("very loose" if n160 < 3 else "loose" if n160 < 8 else "medium dense" if n160 < 25
            else "dense" if n160 < 42 else "very dense")
    es = 500 * (n60 + 15)
    print(f"Corrections: ER={a.er}% CB={cb} CR={cr}  -> N60 = {n60:.1f}")
    print(f"sigma'v at {a.depth} m = {sv:.1f} kN/m2 ; CN = {cn:.2f} -> (N1)60 = {n160:.1f}")
    print(f"Density: {dens}, Dr ~ {dr:.0f} %")
    print(f"phi: Hatanaka-Uchida {phi_hu:.1f} deg ; Peck-Hanson-Thornburn {phi_pht:.1f} deg")
    print(f"Es (Bowles, sand) ~ {es / 1000:.1f} MN/m2")
    print(f"If clay: cu ~ {4.4 * n60:.0f}-{6 * n60:.0f} kN/m2 (rough; prefer lab tests)")


def cmd_consolidation(a):
    total = 0.0
    print(f"Footing {a.B} x {a.L} m, Df = {a.Df} m, P = {a.P} kN (net added load)")
    print("top  bot   z_mid  s'0     ds      s'c     Sc(mm)")
    for spec in a.layer:
        vals = [float(v) for v in spec.split(",")]
        if len(vals) == 6:
            top, bot, gsat, cc, cs, e0 = vals
            ocr = 1.0
        elif len(vals) == 7:
            top, bot, gsat, cc, cs, e0, ocr = vals
        else:
            raise SystemExit("--layer top,bot,gamma_sat,Cc,Cs,e0[,OCR]")
        n = max(1, math.ceil((bot - top) / a.sublayer))
        h = (bot - top) / n
        for i in range(n):
            zm = top + h * (i + 0.5)
            s0 = sigma_v_eff(zm, a.gamma, gsat, a.water)
            z = zm - a.Df
            ds = a.P / ((a.B + z) * (a.L + z))
            sc_ = s0 * ocr
            if ocr <= 1.0:
                s = cc * h / (1 + e0) * math.log10((s0 + ds) / s0)
            elif s0 + ds <= sc_:
                s = cs * h / (1 + e0) * math.log10((s0 + ds) / s0)
            else:
                s = (cs * h / (1 + e0) * math.log10(sc_ / s0)
                     + cc * h / (1 + e0) * math.log10((s0 + ds) / sc_))
            total += s
            print(f"{top + h * i:4.1f} {top + h * (i + 1):5.1f} {zm:6.2f} {s0:7.1f} {ds:7.1f} {sc_:7.1f} {s * 1000:8.1f}")
    print(f"Total consolidation settlement = {total * 1000:.1f} mm")


def cmd_elastic(a):
    r = a.L / a.B if a.L else 10
    # flexible centre influence factor (approx. interpolation)
    pts = [(1, 1.12), (1.5, 1.36), (2, 1.53), (3, 1.78), (5, 2.10), (10, 2.54)]
    if r >= 10:
        If = 2.54
    else:
        for (r1, f1), (r2, f2) in zip(pts, pts[1:]):
            if r1 <= r <= r2:
                If = f1 + (f2 - f1) * (r - r1) / (r2 - r1)
                break
    se = a.q * a.B * (1 - a.nu ** 2) * If / a.Es
    print(f"L/B = {r:.2f}, If (flexible centre) = {If:.2f}")
    print(f"Se flexible centre = {se * 1000:.1f} mm ; rigid ~ {0.93 * se * 1000:.1f} mm")


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    s = p.add_subparsers(dest="cmd", required=True)

    b = s.add_parser("bearing")
    b.add_argument("--B", type=float, required=True, help="width m")
    b.add_argument("--L", type=float, help="length m (omit for strip)")
    b.add_argument("--Df", type=float, required=True, help="founding depth m")
    b.add_argument("--phi", type=float, required=True)
    b.add_argument("--c", type=float, default=0.0, help="c' or cu kN/m2")
    b.add_argument("--gamma", type=float, required=True, help="moist unit weight above water kN/m3")
    b.add_argument("--gamma-sat", type=float, help="saturated unit weight kN/m3")
    b.add_argument("--water", type=float, help="water table depth below ground m")
    b.add_argument("--ex", type=float, default=0.0, help="eccentricity along B m")
    b.add_argument("--ey", type=float, default=0.0, help="eccentricity along L m")
    b.add_argument("--incl", type=float, default=0.0, help="load inclination deg")
    b.add_argument("--fs", type=float, default=3.0)
    b.add_argument("--ngamma", choices=["vesic", "meyerhof", "hansen"], default="vesic")
    b.add_argument("--no-depth", action="store_true", help="ignore depth factors")
    b.set_defaults(fn=cmd_bearing)

    t = s.add_parser("spt")
    t.add_argument("--N", type=float, required=True)
    t.add_argument("--depth", type=float, required=True)
    t.add_argument("--gamma", type=float, default=18.0)
    t.add_argument("--gamma-sat", type=float)
    t.add_argument("--water", type=float)
    t.add_argument("--er", type=float, default=60.0, help="hammer energy ratio %%")
    t.add_argument("--diameter", type=float, default=100.0, help="borehole diameter mm")
    t.add_argument("--rod-length", type=float)
    t.set_defaults(fn=cmd_spt)

    c = s.add_parser("consolidation")
    c.add_argument("--P", type=float, required=True, help="net load added at founding level kN")
    c.add_argument("--B", type=float, required=True)
    c.add_argument("--L", type=float, required=True)
    c.add_argument("--Df", type=float, required=True)
    c.add_argument("--gamma", type=float, default=18.0, help="unit weight above water")
    c.add_argument("--water", type=float, help="water table depth m")
    c.add_argument("--sublayer", type=float, default=1.0, help="sub-layer thickness m")
    c.add_argument("--layer", action="append", required=True,
                   help="clay layer: top,bot,gamma_sat,Cc,Cs,e0[,OCR] (depths from ground, repeatable). "
                        "Effective stress assumes --gamma above water and this layer's gamma_sat below.")
    c.set_defaults(fn=cmd_consolidation)

    e = s.add_parser("elastic")
    e.add_argument("--q", type=float, required=True, help="net pressure kN/m2")
    e.add_argument("--B", type=float, required=True)
    e.add_argument("--L", type=float, help="omit for strip")
    e.add_argument("--Es", type=float, required=True, help="kN/m2")
    e.add_argument("--nu", type=float, default=0.3)
    e.set_defaults(fn=cmd_elastic)

    a = p.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()
