#!/bin/bash
# Rebuild the v15 site copy from the v14 site, the new plans and the units sheet.
set -euo pipefail
S=/tmp/claude-0/-home-user-alhabibengcom-gmail-com/79d5094b-c810-5d5e-a226-4b227d4db456/scratchpad
rm -rf "$S/site15" "$S/pdfout"
cp -r "$S/site" "$S/site15"
B="$S/site15/brands"
python3 -I "$S/upd/build_units.py" "$S/upd" "$B"
python3 -I - "$S" "$B" <<'EOF'
import json, re, sys
from PIL import Image
S, B = sys.argv[1], sys.argv[2]
names = {f: f'assets/plan-v15-{f}.webp' for f in ['b1', 'g', 'f1', 'f2']}
for f, n in names.items():
    im = Image.open(f'{S}/upd/out/{f}.png').convert('RGB')
    im.save(f'{B}/{n}', quality=86)
    im.save(f'{B}/assets/drawings/{f}.png', optimize=True)
t = open(f'{B}/site.js', encoding='utf-8').read()
t = re.sub(r'MAPS=\{[^}]*\}', 'MAPS=' + json.dumps(names, separators=(',', ':')), t, count=1)
open(f'{B}/site.js', 'w', encoding='utf-8').write(t)
EOF
cp "$S/upd/aliases.json" "$S/site15/tools/aliases.json"
cp "$S/site15/tools/rebuild_leasing_pdf.py" /dev/null 2>&1 || true
EOF_TOOL="$S/upd/rebuild_leasing_pdf.py"
cp "$EOF_TOOL" "$S/site15/tools/rebuild_leasing_pdf.py"
cd "$S/site15"
python3 -W ignore tools/rebuild_leasing_pdf.py --site-dir brands --output-dir "$S/pdfout"
cp -r "$S/pdfout/." "$B/"
echo pipeline-done
