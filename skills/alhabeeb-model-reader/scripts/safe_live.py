#!/usr/bin/env python3
"""Read a SAFE model DIRECTLY (.FDB) through the SAFE API, run it, and design the slab/raft to ECP 203.
No manual export, no printed report. Windows PC with SAFE v20 or later:
    pip install comtypes openpyxl ezdxf matplotlib
    python safe_live.py --fdb "D:\\Projects\\Tower\\Raft.FDB" --q-allow 150 --service-combos SERV --combos U1 -o out
    python safe_live.py --attach --q-allow 150 -o out
Steps: open (or attach) -> run analysis if needed -> find the strip forces, soil pressure, punching and slab
property tables in SAFE's own table list -> out/safe_tables.xlsx -> safe_design.py --auto-resize (strip steel,
soil pressure, punching, thickness proposal, DXF sheet). Extra options are passed to safe_design.py.
"""
import argparse
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import csi_api  # noqa: E402

WANTED = [
    ("Strip forces", [r"strip", r"forces"], [r"definition", r"object"], "combos"),
    ("Soil pressures", [r"soil", r"pressure"], [], "all"),
    ("Punching", [r"punch"], [], "combos"),
    ("Slab properties", [r"slab", r"propert"], [], None),
    ("Point coordinates", [r"point", r"(coordinates|object connectivity)"], [], None),
]


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--fdb", help="path to the SAFE model (.FDB)")
    g.add_argument("--attach", action="store_true")
    p.add_argument("--run", action="store_true")
    p.add_argument("--visible", action="store_true")
    p.add_argument("--no-design", action="store_true")
    p.add_argument("-o", "--out", required=True)
    a, rest = p.parse_known_args()
    os.makedirs(a.out, exist_ok=True)
    api = csi_api.CSI("SAFE", a.fdb, a.attach, a.visible)
    try:
        if a.run or not api.has_results():
            print("Running analysis and design ...")
            api.run()
            try:
                api.m.DesignConcreteSlab.StartSlabDesign()
            except Exception:
                pass
        pats, combos = api.patterns(), api.combos()
        print(f"Load patterns: {', '.join(pats)}\nCombinations: {', '.join(combos)}")
        tables = {}
        for label, rx, avoid, sel in WANTED:
            key = api.find_table(*rx, avoid=avoid)
            if not key:
                print(f"  {label}: not found in SAFE's table list")
                continue
            f, rows = api.table(key, cases=pats if sel == "all" else ([] if sel else None),
                                combos=combos if sel in ("all", "combos") else None)
            if f is None:
                print(f"  {label} ({key}): no data")
                continue
            tables[key] = (f, rows)
            print(f"  {label} <- '{key}': {len(rows)} rows")
        xlsx = os.path.join(a.out, "safe_tables.xlsx")
        csi_api.write_xlsx(tables, xlsx)
        print(f"Tables: {xlsx}")
    finally:
        api.close(save=False)
    if a.no_design:
        return
    cmd = [sys.executable, os.path.join(HERE, "safe_design.py"), "--tables", xlsx, "-o", a.out, "--auto-resize"] + rest
    sys.exit(subprocess.call(cmd))


if __name__ == "__main__":
    main()
