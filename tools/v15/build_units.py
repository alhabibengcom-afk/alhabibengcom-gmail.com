"""Rebuild the guide's unit data from the revised subdivision.

Inputs  : units_public.json (from the shared units sheet, no owner data), auth.json,
          out/{b1,g,f1,f2}.png (new plans cropped to the guide's frame), the current brands/ folder.
Outputs : new site.js / unit-data.js / location-links.js written into brands/, unit crops,
          new plan images, aliases.json (old code -> new code), report.json.
Owner names are never read or written. Owner units whose authorisation is not "موجود"
are shown as not offered, per the sheet's own rule 3.
"""
import json
import math
import re
import sys
from pathlib import Path

from PIL import Image
from shapely.geometry import Polygon, Point
from shapely.ops import unary_union

UPD = Path(sys.argv[1])
B = Path(sys.argv[2])
K = 1983 / 1108  # guide coordinates -> drawing pixels
FLOOR = {'البدروم': 'b1', 'الأرضي': 'g', 'الأول': 'f1', 'التاني': 'f2'}
SHEET = {'b1': 'basement', 'g': 'ground', 'f1': 'first', 'f2': 'second'}
AR_DIG = str.maketrans('0123456789.,', '٠١٢٣٤٥٦٧٨٩٫٬')


def ar(n, dec=2):
    s = f'{n:,.{dec}f}'
    if dec and s.endswith('0' * dec):
        s = s[: -(dec + 1)]
    return s.translate(AR_DIG)


def load_const(path, name):
    t = path.read_text(encoding='utf-8')
    i = t.index(f'const {name}=') + len(f'const {name}=')
    obj, end = json.JSONDecoder().raw_decode(t[i:])
    return t, i, i + end, obj


# ---------------- legend colours sampled from each new sheet ----------------
LEGEND = {  # (panel y in the 1/4-scale legend strip) -> label, per floor
    'b1': [(361, 'Hyper Market'), (405, 'Accessories'), (449, 'Mobiles'), (493, 'Kids')],
    'g': [(98, 'F&B'), (142, 'F&B Outdoor'), (186, 'Fashion'), (230, 'Retail (Lifestyle)'), (274, 'Accessories'),
          (318, 'Banks / Financial'), (362, 'Showroom'), (406, 'Telecom'), (450, 'Pharmacy / Medical'), (493, 'Taken')],
    'f1': [(186, 'F&B'), (230, 'Food Court'), (274, 'Fashion'), (318, 'Retail (Lifestyle)'), (362, 'Accessories'),
           (406, 'Banks / Financial'), (450, 'Showroom'), (493, 'Taken')],
    'f2': [(405, 'F&B'), (449, 'Retail'), (493, 'Entertainment')],
}
CAT_AR = {'Hyper Market': 'هايبر ماركت', 'Accessories': 'إكسسوارات', 'Mobiles': 'موبايلات',
          'Kids': 'منطقة أطفال وحضانة', 'F&B': 'أغذية ومشروبات', 'F&B Outdoor': 'أغذية ومشروبات',
          'Fashion': 'أزياء', 'Retail (Lifestyle)': 'لايف ستايل', 'Retail': 'تجزئة',
          'Banks / Financial': 'خدمات مالية', 'Showroom': 'معرض', 'Telecom': 'اتصالات',
          'Pharmacy / Medical': 'صيدلية وخدمات طبية', 'Food Court': 'فود كورت', 'Entertainment': 'ترفيه',
          'Taken': 'محل تجاري'}


def legend_colors(f):
    im = Image.open(UPD / f'{SHEET[f]}.jpg').convert('RGB')
    out = []
    for y, label in LEGEND[f]:
        X, Y = 232, 1100 + y * 4
        px = [im.getpixel((X + dx, Y + dy)) for dx in range(-12, 13, 4) for dy in range(-12, 13, 4)]
        px.sort()
        out.append((px[len(px) // 2], label))
    return out


def nearest(c, pal):
    return min(pal, key=lambda p: sum((a - b) ** 2 for a, b in zip(c, p[0])))


def sample(im, x, y):
    px = []
    for dx in range(-10, 11, 5):
        for dy in range(-10, 11, 5):
            try:
                px.append(im.getpixel((int(x + dx), int(y + dy))))
            except IndexError:
                pass
    px.sort(key=lambda p: sum(p))
    return px[len(px) // 2]


# ---------------- current guide data ----------------
site_t, s0, s1, old_units = load_const(B / 'site.js', 'UNITS')
ud_t, d0, d1, drawings = load_const(B / 'unit-data.js', 'UNIT_DRAWINGS')
_, g0, g1, gallery = load_const(B / 'unit-data.js', 'UNIT_GALLERY')
ll_t = (B / 'location-links.js').read_text(encoding='utf-8')
ll_i = ll_t.index('=') + 1
links, ll_end = json.JSONDecoder().raw_decode(ll_t[ll_i:].lstrip())
old_by = {u['id']: u for u in old_units}

units = json.load(open(UPD / 'units_public.json', encoding='utf-8'))
auth = json.load(open(UPD / 'auth.json', encoding='utf-8'))
OUTDOOR = {'G06': 111.71, 'G08': 65.36, 'G09': 66.22, 'G11': 68.21, 'G39': 108.08, 'G40': 126.56, 'G41': 82.72}
SELF = {'B01': 'هايبر ماركت الحبيب', 'G16-21': 'الحبيب ستور', 'F16-20': 'الحبيب ستور', 'G46': 'صيدلية الحبيب'}

# metres per guide unit, per floor, from old single units with a plan_scale width
ratio = {}
for f in SHEET:
    rs = []
    for uid, g in drawings.items():
        d = g.get('dimensions') or {}
        if old_by.get(uid, {}).get('f') == f and d.get('width'):
            xs = [p[0] for p in g['polygon']]
            w = max(xs) - min(xs)
            if w > 20:
                rs.append(d['width'] / w)
    rs.sort()
    ratio[f] = rs[len(rs) // 2] if rs else 0.0876

maps = {f: Image.open(UPD / 'out' / f'{f}.png').convert('RGB') for f in SHEET}
pal = {f: legend_colors(f) for f in SHEET}

# Units whose outline is not one old unit: the revised plan split old G42 in two, and the four
# second-floor units that the old guide showed by area only now have printed codes.
OLD_CODE = {'S04': 'F2-A', 'S40': 'F2-B', 'S41': 'F2-C', 'S25': 'F2-D'}
_g42 = drawings['G42']['polygon']  # [[118,422],[231,422],[231,509],[118,509]]
OVERRIDE = {
    'G42': [[118.0, 422.0], [231.0, 422.0], [231.0, 465.5], [118.0, 465.5]],
    'G42-1': [[118.0, 465.5], [231.0, 465.5], [231.0, 509.0], [118.0, 509.0]],
}
for new_id, old_id in OLD_CODE.items():
    OVERRIDE[new_id] = drawings[old_id]['polygon']

new_units, new_draw, aliases, report = [], {}, {}, {'no_geometry': [], 'categories': {}}
shapes = {}
for u in units:
    uid = u['id']
    f = FLOOR[u['floor']]
    parts = [p.strip() for p in re.split(r'\+', u['parts'] or uid) if p.strip()]
    geos = [drawings[p] for p in parts if p in drawings] or ([drawings[uid]] if uid in drawings else [])
    if uid in OVERRIDE:
        geos = [{'polygon': OVERRIDE[uid]}]
    if uid in OLD_CODE:
        aliases[OLD_CODE[uid]] = uid
    if not geos:
        report['no_geometry'].append(uid)
        continue
    poly = unary_union([Polygon(g['polygon']).buffer(0.6) for g in geos]).buffer(-0.6)
    if poly.geom_type != 'Polygon':
        poly = poly.convex_hull
    poly = poly.simplify(0.5)
    shapes[uid] = (f, poly)
    for p in parts:
        if p != uid:
            aliases[p] = uid
    rp = poly.representative_point()
    col = sample(maps[f], rp.x * K, rp.y * K)
    label = nearest(col, pal[f])[1]
    cat = CAT_AR[label]
    report['categories'][uid] = label
    title = cat
    if uid in SELF:
        title = SELF[uid]
        cat = {'B01': 'هايبر ماركت', 'G46': 'صيدلية وخدمات طبية'}.get(uid, 'تجزئة')
    elif uid in OUTDOOR:
        title = 'مطعم وكافيه على البلازا'
        cat = 'أغذية ومشروبات'
    ch = u['channel']
    if ch.startswith('تشغيل ذاتي'):
        held, status = True, 'يشغّلها الحبيب مباشرة'
    elif ch.startswith('إيجار - المالك') and auth.get(uid) != 'موجود':
        held, status = True, 'غير معروضة للتأجير حاليًا'
    else:
        held, status = False, 'متاحة للإيجار'
    note = []
    if len(parts) > 1:
        note.append('وحدة مضمومة من ' + ' و'.join(parts) + ' تُعرض كوحدة واحدة.')
    note.append(f'المساحة المحملة {ar(u["loaded"])} م² والصافي داخل حدود الوحدة {ar(u["net"])} م². '
                'الإيجار يُحسب على المساحة المحملة.')
    if uid in OUTDOOR:
        note.append(f'لها تراس خارجي على البلازا مساحته {ar(OUTDOOR[uid])} م² غير محسوب في المساحة المحملة.')
    # crop image of the unit on the new plan
    x0, y0, x1, y1 = poly.bounds
    m = 45
    box = (max(0, int((x0 - m) * K)), max(0, int((y0 - m) * K)), min(1983, int((x1 + m) * K)), min(1968, int((y1 + m) * K)))
    crop = maps[f].crop(box)
    crop.thumbnail((640, 420))
    cpath = f'assets/units-v15/{uid}.webp'
    (B / 'assets' / 'units-v15').mkdir(parents=True, exist_ok=True)
    crop.save(B / cpath, quality=82)
    new_units.append({'id': uid, 'name': uid, 'pending': False, 'f': f, 'cat': cat, 'title': title,
                      'area': round(u['loaded'], 2), 'extra': OUTDOOR.get(uid), 'elab': 'تراس خارجي على البلازا',
                      'x': round(rp.x), 'y': round(rp.y), 'held': held, 'status': status,
                      'note': ' '.join(note), 'crop': cpath, 'net': round(u['net'], 2),
                      'parts': parts if len(parts) > 1 else None})

# geometry: neighbours, nearby, dimensions
for uid, (f, poly) in shapes.items():
    same = [(o, p) for o, (ff, p) in shapes.items() if ff == f and o != uid]
    neigh = []
    for o, p in same:
        if poly.distance(p) < 2.5:
            c, d = poly.centroid, p.centroid
            dx, dy = d.x - c.x, d.y - c.y
            side = ('right' if dx > 0 else 'left') if abs(dx) > abs(dy) else ('bottom' if dy > 0 else 'top')
            neigh.append({'id': o, 'side': side})
    near = sorted(same, key=lambda op: poly.centroid.distance(op[1].centroid))
    nearby = [o for o, _ in near if o not in {n['id'] for n in neigh}][:4]
    old = drawings.get(uid)
    single = old is not None and not next(x for x in new_units if x['id'] == uid)['parts']
    if single and old.get('dimensions'):
        dims = old['dimensions']
    else:
        x0, y0, x1, y1 = poly.bounds
        r = ratio[f]
        dims = {'width': round((x1 - x0) * r, 1), 'depth': round((y1 - y0) * r, 1), 'method': 'plan_scale'}
    entry = {'polygon': [[round(x, 1), round(y, 1)] for x, y in list(poly.exterior.coords)[:-1]],
             'neighbors': neigh, 'nearby': nearby, 'dimensions': dims}
    if single and old.get('cadInterior'):
        entry['cadInterior'] = old['cadInterior']
    new_draw[uid] = entry


def remap(d):
    out = {}
    for k, v in d.items():
        nk = aliases.get(k, k)
        if nk not in shapes:
            continue
        if isinstance(v, list):
            out.setdefault(nk, []).extend(v)
        elif nk not in out:
            out[nk] = v
    return out


def merge_marks(d, key):
    # A combined unit gets one marker per photo or scene, at the middle of its parts.
    out = {}
    for uid, marks in d.items():
        groups = {}
        for m in marks:
            groups.setdefault(m[key], []).append(m)
        res = []
        for g in groups.values():
            xs = [m['x'] for m in g]
            if len(g) > 1 and max(xs) - min(xs) < 0.35:
                m = dict(g[0])
                m['x'] = round(sum(xs) / len(g), 4)
                m['y'] = round(sum(m2['y'] for m2 in g) / len(g), 4)
                res.append(m)
            else:
                res.extend(g)
        out[uid] = res
    return out


links['photos'] = merge_marks(remap(links.get('photos', {})), 'photo')
if 'tours' in links:
    links['tours'] = remap(links['tours'])
if 'panoramas' in links:
    links['panoramas'] = merge_marks(remap(links['panoramas']), 'scene')
gallery['zones'] = remap(gallery.get('zones', {}))
gallery['units'] = remap(gallery.get('units', {}))

# write files back
site_new = site_t[:s0] + json.dumps(new_units, ensure_ascii=False, separators=(',', ':')) + site_t[s1:]
(B / 'site.js').write_text(site_new, encoding='utf-8')
ud = ud_t[:d0] + json.dumps(new_draw, ensure_ascii=False, separators=(',', ':')) + ud_t[d1:]
gi = ud.index('const UNIT_GALLERY=') + len('const UNIT_GALLERY=')
_, gend = json.JSONDecoder().raw_decode(ud[gi:])
ud = ud[:gi] + json.dumps(gallery, ensure_ascii=False, separators=(',', ':')) + ud[gi + gend:]
(B / 'unit-data.js').write_text(ud, encoding='utf-8')
lead = ll_t[:ll_i]
rest = ll_t[ll_i:]
pad = len(rest) - len(rest.lstrip())
(B / 'location-links.js').write_text(lead + ' ' + json.dumps(links, ensure_ascii=False, indent=2) + rest[pad + ll_end:],
                                     encoding='utf-8')
json.dump(aliases, open(UPD / 'aliases.json', 'w', encoding='utf-8'), ensure_ascii=False)
report['units'] = len(new_units)
report['held'] = sum(u['held'] for u in new_units)
report['offered'] = sum(not u['held'] for u in new_units)
json.dump(report, open(UPD / 'report.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print(json.dumps({k: v for k, v in report.items() if k != 'categories'}, ensure_ascii=False))
