#!/usr/bin/env python3
"""Read an ETABS model DIRECTLY from the .EDB through the ETABS API - check it, correct it, re-analyse, design, draw.
No manual export and no printed report.

Runs on a Windows PC with ETABS (v18 or later):
    pip install comtypes openpyxl ezdxf matplotlib
    python etabs_live.py --edb "D:\\Projects\\Tower\\Tower.EDB" --fix --q-allow 200 --project Tower -o out
    python etabs_live.py --attach --fix --q-allow 200 -o out      (model already open in ETABS)
or drag the .EDB onto run_etabs.bat.

Steps
  1. Open the .EDB (ETABS hidden) or attach to the running ETABS; units kN-m.
  2. Read the model text (.$et beside the model; one Save creates it) and run the model review.
  3. --fix: apply the safe corrections INSIDE ETABS (missing load patterns, self-weight once, base supports,
     ECP ultimate combination), save as <name>_ALH-fixed.EDB (the original file is never overwritten),
     re-run the analysis. Engineering items (sizes, loads, seismic data) are reported, not changed.
  4. Read Joint Reactions, Element Forces (columns, beams), Pier Forces through the API database tables
     (table names are found in the program's own list, so ETABS versions don't matter) -> out/etabs_tables.xlsx
  5. building_design.py with auto-resize: designs everything to ECP 203, enlarges failing members, draws.
Anything after the known options is passed to building_design.py (--fcu, --fcu-found, --stairs, --client ...).
"""
import argparse
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import csi_api  # noqa: E402
import model_reader as MR  # noqa: E402

WANTED = [  # (label, regex patterns, avoid, selection)
    ("Joint Reactions", [r"joint", r"reaction"], [r"design", r"base"], "patterns"),
    ("Element Forces - Columns", [r"element forces", r"column"], [], "combos"),
    ("Element Forces - Beams", [r"element forces", r"beam"], [], "combos"),
    ("Pier Forces", [r"pier forces"], [r"design"], "combos"),
    ("Base Reactions", [r"base reactions"], [], "patterns"),
    ("Story Drifts", [r"story drifts"], [], "combos"),
    ("Modal Participating Mass Ratios", [r"modal participating mass"], [], None),
]


def text_model(api, edb, allow_save):
    base = os.path.splitext(os.path.abspath(edb or api.filename() or "model"))[0]
    f = csi_api.text_model_file(base, (".$et", ".$ET", ".e2k", ".E2K"))
    if f is None and allow_save:
        try:
            api.m.File.Save()
        except Exception:
            pass
        f = csi_api.text_model_file(base, (".$et", ".$ET", ".e2k", ".E2K"))
    return f


def apply_fixes(api, acts):
    done = []
    for act in acts:
        kind = act[0]
        try:
            if kind == "pattern":
                r = api.add_pattern(act[1], act[2], act[3])
                done.append(f"added load pattern {act[1]} ({act[2]}) - set its loads/parameters" + ("" if r == 0 else f" [ret {r}]"))
            elif kind == "selfweight":
                r = api.set_selfweight(act[1], act[2])
                done.append(f"self-weight multiplier of {act[1]} = {act[2]:g}" + ("" if r == 0 else f" [ret {r}]"))
            elif kind == "support":
                r = api.restrain(act[1], act[2])
                done.append(f"fixed support at point {act[1]} ({act[2]})" + ("" if r == 0 else f" [ret {r}]"))
            elif kind == "combo":
                r = api.add_combo(act[1], act[2])
                done.append(f"combination {act[1]} = " + " + ".join(f"{sf:g}x{c}" for c, sf in act[2])
                            + ("" if r == 0 else f" [ret {r}]"))
        except Exception as e:
            done.append(f"FAILED {act}: {e}")
    return done


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--edb", help="path to the .EDB model")
    g.add_argument("--attach", action="store_true", help="use the model open in a running ETABS")
    p.add_argument("--fix", action="store_true", help="apply safe corrections in ETABS, save a copy, re-analyse")
    p.add_argument("--run", action="store_true", help="always re-run the analysis")
    p.add_argument("--visible", action="store_true")
    p.add_argument("--no-save", action="store_true")
    p.add_argument("--no-design", action="store_true")
    p.add_argument("--combos", help="ultimate combinations for members (default: all combinations)")
    p.add_argument("-o", "--out", required=True)
    a, rest = p.parse_known_args()
    os.makedirs(a.out, exist_ok=True)
    log = []
    api = csi_api.CSI("ETABS", a.edb, a.attach, a.visible)
    try:
        txt = text_model(api, a.edb, not a.no_save)
        if txt:
            M = MR.read_e2k(txt)
            acts = MR.plan_fixes(M)
            print(f"Model: {txt}\nReview: {len(acts)} safe correction(s) found")
            if a.fix and acts:
                log = apply_fixes(api, acts)
                for l in log:
                    print("  fix: " + l)
                src = a.edb or api.filename()
                fixed = os.path.splitext(src)[0] + "_ALH-fixed.EDB"
                api.save_as(fixed)
                print(f"Corrected model saved as {fixed} (original untouched)")
                a.edb = fixed
                txt = text_model(api, fixed, True) or txt
                a.run = True
            elif acts:
                for act in acts:
                    print(f"  would fix: {act}  (use --fix to apply)")
        else:
            print("No .$et/.e2k text beside the model and saving is off - geometry review skipped.")
        if a.run or not api.has_results():
            print("Running analysis ...")
            api.run()
        pats, combos = api.patterns(), api.combos()
        use = a.combos.split(",") if a.combos else combos
        print(f"Load patterns: {', '.join(pats)}\nCombinations: {', '.join(combos)}")
        tables = {}
        for label, pats_re, avoid, sel in WANTED:
            key = api.find_table(*pats_re, avoid=avoid)
            if not key:
                print(f"  {label}: not in this model/version")
                continue
            f, rows = api.table(key, cases=pats if sel == "patterns" else ([] if sel else None),
                                combos=[] if sel == "patterns" else (use if sel else None))
            if f is None:
                print(f"  {label} ({key}): no data")
                continue
            tables[key] = (f, rows)
            print(f"  {label} <- '{key}': {len(rows)} rows")
        xlsx = os.path.join(a.out, "etabs_tables.xlsx")
        csi_api.write_xlsx(tables, xlsx)
        print(f"Tables: {xlsx}")
    finally:
        api.close(save=False)
    if log:
        with open(os.path.join(a.out, "model_corrections.txt"), "w", encoding="utf-8") as f:
            f.write("\n".join(log) + "\n")
    if not txt:
        sys.exit("Need the model text: in ETABS File > Export > ETABS .e2k Text File once (same folder/name).")
    if a.no_design:
        return
    cmd = [sys.executable, os.path.join(HERE, "building_design.py"), "--model", txt, "--reactions", xlsx,
           "--forces", xlsx, "-o", a.out, "--auto-resize"] + (["--combos", ",".join(use)] if use else []) + rest
    print("Designing ...")
    sys.exit(subprocess.call(cmd))


if __name__ == "__main__":
    main()
