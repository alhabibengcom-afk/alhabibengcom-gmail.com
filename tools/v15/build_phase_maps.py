# Phase maps for the PDFs: each floor plan with the phase's units in full colour and the rest faded.
# Available units get a gold outline. Usage: build_phase_maps.py <brands dir> <lease.json>  -> pack-img/map-p{2,3}-{floor}.jpg
import json, re, sys
from PIL import Image, ImageDraw
B, LIST = sys.argv[1:3]
OFFER = set(json.load(open(LIST)))
cfg = json.load(open(B + '/site-config.json', encoding='utf-8'))
P2 = set(cfg['phase2'])
t = open(B + '/unit-data.js', encoding='utf-8').read()
D, _ = json.JSONDecoder().raw_decode(t[re.search(r'UNIT_DRAWINGS\s*=\s*', t).end():])
s = open(B + '/site.js', encoding='utf-8').read()
U, _ = json.JSONDecoder().raw_decode(s[s.index('const UNITS=') + len('const UNITS='):])
fl = {u['id']: u['f'] for u in U}
for f in ['b1', 'g', 'f1', 'f2']:
    base = Image.open(f'{B}/assets/plan-v15-{f}.webp').convert('RGB')
    W, H = base.size; kx, ky = W / 1108, H / 1100
    for ph in (2, 3):
        ids = [k for k in D if fl.get(k) == f and ((k in P2) == (ph == 2))]
        faded = Image.blend(base, Image.new('RGB', base.size, (247, 244, 238)), 0.8)
        mask = Image.new('L', base.size, 0); md = ImageDraw.Draw(mask)
        for k in ids:
            md.polygon([(x * kx, y * ky) for x, y in D[k]['polygon']], fill=255)
        out = Image.composite(base, faded, mask)
        d = ImageDraw.Draw(out)
        for k in ids:
            pts = [(x * kx, y * ky) for x, y in D[k]['polygon']]
            if k in OFFER:
                d.line(pts + [pts[0]], fill=(200, 144, 44), width=6, joint='curve')
        out.save(f'{B}/pack-img/map-p{ph}-{f}.jpg', quality=88, optimize=True)
print('ok')
