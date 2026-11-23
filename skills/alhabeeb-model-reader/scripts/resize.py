"""Auto-resize: when an element fails an ECP 203 check, enlarge it step by step and redesign with the SAME forces
until every check passes (or the step limit is reached). Each change is recorded as a proposal, because a bigger
member changes stiffness and self-weight: update the model, re-run the analysis, and design again.

Rules (sizes in mm, steps rounded to 50 mm for members, 10/20 mm for slabs):
  column   : enlarge t by 50, then b by 50, alternating, until it passes AND steel <= --max-rho (default 2%)
  beam     : deepen h by 50; after 6 steps also widen b by 50; up to 12 steps
  slab     : thicken t by 10 (self-weight updated); up to 8 steps
  wall     : thicken t by 50; up to 4 steps
  flat slab: thicken h by 20 until punching and flexure pass; up to 8 steps
Footing anchorage failures are solved by the 90-degree end hooks already drawn and scheduled (12 dia legs) and are
reported as such - footing plan size and depth come from the ECP 203 footing design itself.
"""
import sys


def _rho(s):
    import re
    m = re.search(r"([\d.]+)\s*%", s or "")
    return float(m.group(1)) if m else 0.0


def _fails(rep):
    return [c.desc for c in rep.checks if not c.ok]


def auto_resize(res, reports, a, lib):
    sys.path.insert(0, lib)
    from ecp203.column import design_column
    from ecp203.beam import design_beam
    from ecp203.slab import design_two_way_slab
    from ecp203.wall import design_wall
    from ecp203.floor_flat import design_flat_slab_floor
    import slabs_walls as SW
    out = []

    for c in res["columns"]:
        if c["ok"]:
            continue
        b, t = c["b"], c["t"]
        old = f"{b}x{t}"
        for k in range(12):
            if k % 2 == 0:
                t += 50
            else:
                b += 50
            rep = design_column(b, t, a.fcu, a.fy, c["Pu"], c["Mx"], c["My"], c["He"], c["He"], braced=not a.unbraced,
                                title=f"Column {c['label']} - {c['story']} (resized {old} -> {b}x{t})")
            if rep.ok and _rho(rep.results.get("longitudinal", "")) <= getattr(a, "max_rho", 2.0):
                break
        reports.append(("columns", rep))
        r = rep.results
        out.append(("Column", f"{c['label']} @ {c['story']}", old, f"{b}x{t}", "; ".join(c["fail"]), rep.ok))
        c.update(b=b, t=t, long=r.get("longitudinal", ""), ties=r.get("ties", ""), ok=rep.ok, fail=_fails(rep),
                 resized_from=old)

    for bm in res["beams"]:
        if bm["ok"]:
            continue
        b, h = bm["b"], bm["h"]
        old = f"{b}x{h}"
        for k in range(12):
            h += 50
            if k >= 6:
                b += 50
            rep = design_beam(b, h, a.fcu, a.fy, bm["Mu_pos"], bm["Mu_neg"], bm["Qu"],
                              title=f"Beam {bm['label']} - {bm['story']} (resized {old} -> {b}x{h})")
            if rep.ok:
                break
        reports.append(("beams", rep))
        r = rep.results
        out.append(("Beam", f"{bm['label']} @ {bm['story']}", old, f"{b}x{h}", "; ".join(bm["fail"]), rep.ok))
        bm.update(b=b, h=h, bot=r.get("positive.tension_bars", ""), top=r.get("negative.tension_bars", ""),
                  stir=r.get("shear.stirrups", ""), ok=rep.ok, fail=_fails(rep), resized_from=old)

    for q in res["slabs"]["panels"]:
        if q["ok"]:
            continue
        t0 = q["t"]
        t = t0
        Lx, Ly = q["x1"] - q["x0"], q["y1"] - q["y0"]
        for _ in range(8):
            t += 10
            wD = round(q["wD"] + 25 * (t - t0) / 1000, 2)
            rep = design_two_way_slab(round(Lx, 3), round(Ly, 3), wD, round(q["wL"], 2), q["cx"], q["cy"], t=t,
                                      fcu=a.fcu, fy=a.fy_slab,
                                      title=f"Slab {q['story']} ({q['x0']:g},{q['y0']:g}) resized t {t0} -> {t}")
            if rep.ok:
                break
        reports.append(("slabs", rep))
        R = rep.results
        if "bottom_a" in R:
            bs, bl, ts, tl, mode = R["bottom_a"], R.get("bottom_b", ""), R.get("top_a", ""), R.get("top_b", ""), "two-way"
        else:
            bs, bl, ts, tl, mode = R.get("bottom", ""), R.get("distribution", ""), R.get("top", ""), "", "one-way"
        sx = Lx <= Ly
        out.append(("Slab", f"{q['story']} ({q['x0']:g},{q['y0']:g})-({q['x1']:g},{q['y1']:g})", f"t={t0}", f"t={t}",
                    "; ".join(q["fail"]), rep.ok))
        q.update(t=t, wD=wD, mode=mode, bx=bs if sx else bl, by=bl if sx else bs, tx=ts if sx else tl,
                 ty=tl if sx else ts, ok=rep.ok, fail=_fails(rep), resized_from=t0)

    for w in res["walls"]:
        if w["ok"]:
            continue
        t0 = t = w["t"]
        for _ in range(4):
            t += 50
            rep = design_wall(t, w["H"], round(w["L"], 2), a.fcu, a.fy, round(w["Pu_m"], 1), 0.0,
                              braced=not a.unbraced, title=f"Wall {w['pier']} - {w['story']} resized t {t0} -> {t}")
            if rep.ok:
                break
        reports.append(("walls", rep))
        out.append(("Wall", f"{w['pier']} @ {w['story']}", f"t={t0}", f"t={t}", "; ".join(w["fail"]), rep.ok))
        w.update(t=t, vert=rep.results.get("vertical", ""), hor=rep.results.get("horizontal", ""), ok=rep.ok,
                 fail=_fails(rep), resized_from=t0)

    M = res["model"]
    new_flat = []
    for fl in res["slabs"]["flat"]:
        if fl["ok"]:
            new_flat.append(fl)
            continue
        beams, walls, cols, slabs = SW.story_geometry(M, fl["story"])
        loads = SW.area_loads(M, fl["story"])
        h0 = h = fl["h"]
        best = fl
        for _ in range(8):
            h += 20
            tmp_reports, tmp_skip = [], []
            r = SW._flat(M, fl["story"], cols, slabs, loads, a, design_flat_slab_floor, tmp_reports, tmp_skip,
                         h_override=h)
            if not r:
                break
            best = r[0]
            if best["ok"]:
                break
        if best is not fl:
            reports.append(("slabs", tmp_reports[-1][1]))
            best["resized_from"] = h0
        out.append(("Flat slab", fl["story"], f"h={h0}", f"h={best['h']}", "; ".join(fl["fail"][:3]), best["ok"]))
        new_flat.append(best)
    res["slabs"]["flat"] = new_flat

    for f in res["footings"]:
        if not f["ok"] and all("Ld" in x for x in f["fail"]):
            f["note"] = "straight anchorage short: 90° end hooks (12 dia) provided in drawing and BBS"
    return out
