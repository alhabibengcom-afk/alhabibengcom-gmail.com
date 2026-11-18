"""python -m ecp203 input.json [-o report.md]

ملف المدخلات JSON فيه "type" = beam | column | footing وباقي المفاتيح هي
مدخلات الدالة المناظرة (راجع examples/).
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from .beam import design_beam
from .column import design_column
from .footing import design_isolated_footing
from .foundation import design_combined_footing, design_raft
from .ribbed import design_hollow_block_one_way, design_hollow_block_two_way
from .slab import check_flat_slab_punching, design_one_way_slab, design_slab_strip, design_two_way_slab
from .stair import design_stair
from .wall import design_wall

FUNCS = {"beam": design_beam, "column": design_column, "footing": design_isolated_footing,
         "slab_one_way": design_one_way_slab, "slab_two_way": design_two_way_slab,
         "slab_strip": design_slab_strip, "flat_slab_punching": check_flat_slab_punching,
         "wall": design_wall, "stair": design_stair, "hollow_block": design_hollow_block_one_way,
         "hollow_block_two_way": design_hollow_block_two_way, "combined_footing": design_combined_footing,
         "raft": design_raft}


def _aci():
    from aci318 import check_pt_punching, check_pt_section  # noqa: WPS433
    return {"pt_section": check_pt_section, "pt_punching": check_pt_punching}


def run(data: dict):
    data = dict(data)
    kind = data.pop("type")
    data.pop("_comment", None)
    funcs = FUNCS if kind in FUNCS else _aci()
    return funcs[kind](**data)


def main(argv=None):
    ap = argparse.ArgumentParser(prog="ecp203")
    ap.add_argument("input", help="ملف JSON (عنصر واحد أو قائمة عناصر)")
    ap.add_argument("-o", "--out", help="ملف التقرير Markdown")
    args = ap.parse_args(argv)
    data = json.loads(Path(args.input).read_text(encoding="utf-8"))
    items = data if isinstance(data, list) else [data]
    reports = [run(d) for d in items]
    md = "\n\n".join(r.to_markdown() for r in reports)
    if args.out:
        Path(args.out).write_text(md, encoding="utf-8")
        print(f"اتكتب التقرير: {args.out}")
    else:
        print(md)
    return 0 if all(r.ok for r in reports) else 1


if __name__ == "__main__":
    sys.exit(main())
