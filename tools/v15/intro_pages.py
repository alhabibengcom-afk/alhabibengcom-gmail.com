"""Rewrite the leasing guide's overview pages (24, 25, 27-30) from the current unit data.

Usage: python3 intro_pages.py SITE_DIR PDF LANG FONT_DIR
  LANG = ar (Arabic guide) or en (English guide, run after translate_pdf.py)
The right-hand panels are cleared (text and line art, images kept) and redrawn: example
units, G39 detail, basement legend, per-floor category counts. Plan links are rebuilt
from the unit outlines so each unit on the plan opens its own page.
"""
import io
import json
import re
import sys

import pymupdf
from PIL import Image

SITE, PDF, LANG, FONTS = sys.argv[1:5]
AR = LANG == 'ar'


def load_js(path, name):
    t = open(path, encoding='utf-8').read()
    i = t.index(name) + len(name)
    return json.JSONDecoder().raw_decode(t[i:].lstrip('= '))[0]


UNITS = load_js(SITE + '/site.js', 'const UNITS=')
DRAW = load_js(SITE + '/unit-data.js', 'const UNIT_DRAWINGS')
U = {u['id']: u for u in UNITS}
EN = load_js(SITE + '/i18n-en.js', 'window.HP_EN')

FLOOR_AR = {'b1': 'البدروم', 'g': 'الأرضي', 'f1': 'الأول', 'f2': 'الثاني'}
FLOOR_EN = {'b1': 'Basement', 'g': 'Ground', 'f1': 'First', 'f2': 'Second'}
CAT_EN = {'محل تجاري': 'Retail shop', 'أغذية ومشروبات': 'Food & beverage', 'أزياء': 'Fashion',
          'اتصالات': 'Telecom', 'صيدلية وخدمات طبية': 'Pharmacy & medical', 'معرض': 'Showroom',
          'إكسسوارات': 'Accessories', 'خدمات مالية': 'Financial services', 'تجزئة': 'Retail',
          'لايف ستايل': 'Lifestyle', 'فود كورت': 'Food court', 'ترفيه': 'Entertainment',
          'موبايلات': 'Mobiles', 'منطقة أطفال وحضانة': 'Kids area & nursery', 'هايبر ماركت': 'Hypermarket'}
DIG = str.maketrans('0123456789.,', '٠١٢٣٤٥٦٧٨٩٫٬')


def num(v, dec=2):
    s = f'{v:,.{dec}f}'
    if dec and s.endswith('.00'):
        s = s[:-3]
    return s.translate(DIG) if AR else s


def m2(v, dec=2):
    return (f'{num(v, dec)} م<span class=l>²</span>' if AR else f'{num(v, dec)} m²')


def L(s):
    return f'<span class=l>{s}</span>' if AR else s


def cat(c):
    return c if AR else CAT_EN.get(c, c)


arch = pymupdf.Archive(FONTS)
CSS_AR = ("@font-face{font-family:ar;src:url(NotoSansArabic-Regular.ttf)}"
          "@font-face{font-family:ar;font-weight:bold;src:url(NotoSansArabic-Bold.ttf)}"
          "body{font-family:ar;direction:rtl;margin:0} .l{font-family:sans-serif}")
CSS_EN = "body{font-family:sans-serif;margin:0} .l{font-family:sans-serif}"


def hexc(c):
    return '#%06x' % c if isinstance(c, int) else c


def put(page, rect, html, size, color, bold=False, align=None, lh=1.35):
    align = align or ('right' if AR else 'left')
    if AR:  # MuPDF mirrors left/right inside direction:rtl
        align = {'right': 'left', 'left': 'right'}.get(align, align)
    w = 'bold' if bold else 'normal'
    css = (CSS_AR if AR else CSS_EN) + f"body{{font-size:{size}px;color:{hexc(color)};font-weight:{w};text-align:{align};line-height:{lh}}}"
    r = pymupdf.Rect(rect)
    spare, scale = page.insert_htmlbox(r, html, css=css, archive=arch, scale_low=0.6)
    if spare < 0:
        raise SystemExit(f'text does not fit on page {page.number + 1}: {html[:60]}')


def clear(page, rect, bg):
    page.add_redact_annot(pymupdf.Rect(rect), fill=bg)
    page.apply_redactions(images=pymupdf.PDF_REDACT_IMAGE_NONE)
    for l in list(page.get_links()):
        if pymupdf.Rect(l['from']).intersects(pymupdf.Rect(rect)):
            page.delete_link(l)


def rgb(h):
    return tuple(int(h[i:i + 2], 16) / 255 for i in (1, 3, 5))


def box(page, rect, fill):
    page.draw_rect(pymupdf.Rect(rect), color=None, fill=rgb(fill), overlay=True)


def link(page, rect, pno):
    page.insert_link({'kind': pymupdf.LINK_GOTO, 'from': pymupdf.Rect(rect), 'page': pno})


doc = pymupdf.open(PDF)

# Unit sheet page for each unit: the code printed large at the top of the sheet.
UPAGE = {}
for i in range(37, len(doc)):
    for b in doc[i].get_text('dict')['blocks']:
        for l in b.get('lines', []):
            for s in l['spans']:
                if s['size'] > 40 and s['text'].strip() in U and s['bbox'][1] < 160:
                    UPAGE.setdefault(s['text'].strip(), i)
missing = [u for u in U if u not in UPAGE]
if missing:
    raise SystemExit('no sheet page for ' + ', '.join(missing))

LIGHT, DARK = '#f6f3ed', '#191a1b'
INK, MUTED, BROWN, RULE = '#192e2b', '#475953', '#765a37', '#d9d2c3'
PAGE_PLAN = {'b1': 26, 'g': 27, 'f1': 28, 'f2': 29}
IMG = pymupdf.Rect(55, 100, 670, 708)

# ---------- page 24: example units ----------
p = doc[23]
clear(p, (40, 140, 1400, 745), rgb(DARK))
put(p, (500, 136, 1375, 186),
    'أمثلة من الوحدات المتاحة للإيجار. اختر الكود لفتح صفحة الوحدة ومساحتها ومخططها.' if AR else
    'Examples of units available for lease. Select a code to open the unit page with its area and plan.',
    21, '#e4e5dd')
TABLES = [((745, 1375), ['G39', 'G40', 'G41', 'G06', 'G44', 'G05']),
          ((65, 695), ['F08', 'F12-15', 'F58-61', 'S08', 'S14-18'])]
for (x0, x1), ids in TABLES:
    box(p, (x0, 217, x1, 267), '#33302b')
    w = x1 - x0
    # columns, right to left in Arabic: code | use | floor | area
    cols = [(0.78, 1.0), (0.40, 0.78), (0.24, 0.40), (0.0, 0.24)]
    if not AR:
        cols = [(0.0, 0.22), (0.22, 0.60), (0.60, 0.76), (0.76, 1.0)]
    heads = ['الكود', 'النشاط', 'الدور', 'م<span class=l>²</span> محملة'] if AR else ['Code', 'Use', 'Floor', 'Loaded m²']
    for (a, b), h in zip(cols, heads):
        put(p, (x0 + a * w + 8, 228, x0 + b * w - 8, 262), h, 17, '#dabc86', True, 'center')
    for r, uid in enumerate(ids):
        u = U[uid]
        y = 267 + r * 55
        title = u['title'] if u['title'] != 'مطعم وكافيه على البلازا' else 'مطعم على البلازا'
        if uid in ('G39', 'G40', 'G41'):
            title = 'مطعم على البلازا'
        t_en = {'مطعم على البلازا': 'Plaza restaurant'}.get(title) or CAT_EN.get(u['cat'], u['cat'])
        cells = [(L(uid), 24, '#f9f6ef', True), (title if AR else t_en, 20, '#f9f6ef', True),
                 (FLOOR_AR[u['f']] if AR else FLOOR_EN[u['f']], 19, '#d1cdc4', False),
                 (num(u['area']), 22, '#dabc86', True)]
        for (a, b), (txt, sz, col, bd) in zip(cols, cells):
            put(p, (x0 + a * w + 6, y + 9, x0 + b * w - 6, y + 52), txt, sz, col, bd, 'center')
        box(p, (x0, y + 54, x1, y + 55), '#504c45')
        link(p, (x0, y + 1, x1, y + 53), UPAGE[uid])
put(p, (400, 632, 1375, 680),
    'لمطاعم البلازا تراسات خارجية غير محسوبة في المساحة. المساحات محملة، والإيجار يُحسب عليها.' if AR else
    'Plaza restaurants also have outdoor terraces not counted in the area. Areas are loaded areas, and rent is charged on them.',
    20, '#d1cdc4')
box(p, (65, 687, 330, 736), '#d8bc84')
put(p, (75, 697, 320, 732), ('تفاصيل مطعم ' + L('G39')) if AR else 'G39 restaurant detail', 19, DARK, True, 'center')
link(p, (65, 687, 330, 736), 24)

# ---------- page 25: G39 detail ----------
g39 = U['G39']
p = doc[24]
clear(p, (740, 200, 1400, 740), rgb(LIGHT))
if not AR:
    clear(p, (900, 140, 1400, 185), rgb(LIGHT))
    put(p, (900, 142, 1376, 184), 'Ground floor, unit G39', 23, '#4f4d47', align='right')
put(p, (755, 218, 900, 292), L('G39'), 52, '#79613c', True, 'left')
put(p, (905, 236, 1376, 312), m2(g39['area']) + (' للمطعم' if AR else ' restaurant'), 36, DARK, True)
put(p, (905, 312, 1376, 386), m2(g39['extra']) + (' للتراس الخارجي' if AR else ' outdoor terrace'), 32, '#79613c', True)
# crop of the revised ground plan around G39 and its terrace
plan = Image.open(SITE + '/assets/drawings/g.png').convert('RGB')
K = plan.width / 1108
xs = [pt[0] for pt in DRAW['G39']['polygon']]
ys = [pt[1] for pt in DRAW['G39']['polygon']]
cx0, cx1 = (min(xs) - 12) * K, (max(xs) + 95) * K
cy = (min(ys) + max(ys)) / 2 * K
hh = (cx1 - cx0) * 230 / 621 / 2
crop = plan.crop((int(cx0), int(cy - hh), int(cx1), int(cy + hh)))
buf = io.BytesIO()
crop.save(buf, 'JPEG', quality=88)
p.insert_image(pymupdf.Rect(755, 410, 1376, 640), stream=buf.getvalue())
link(p, (755, 410, 1376, 640), UPAGE['G39'])
put(p, (755, 645, 1376, 735),
    ('يظهر التراس الملاصق للمطعم على المسقط بكود ' + L('G39') + ' نفسه، وهو غير محسوب في المساحة المحملة. '
     'تُراجع حدود المساحتين عند المعاينة.') if AR else
    'The terrace next to the restaurant carries the same code, G39, on the plan and is not counted in the loaded area. '
    'Both boundaries are checked at the viewing.', 20, '#4f4d47')


# ---------- plan pages 27-30 ----------
def plan_links(page, floor):
    for uid, u in U.items():
        if u['f'] != floor:
            continue
        poly = DRAW[uid]['polygon']
        x0 = min(q[0] for q in poly); x1 = max(q[0] for q in poly)
        y0 = min(q[1] for q in poly); y1 = max(q[1] for q in poly)
        cx, cy = u['x'], u['y']
        hw, hh = min((x1 - x0) / 2, 30), min((y1 - y0) / 2, 22)
        r = pymupdf.Rect(IMG.x0 + (cx - hw) / 1108 * IMG.width, IMG.y0 + (cy - hh) / 1100 * IMG.height,
                         IMG.x0 + (cx + hw) / 1108 * IMG.width, IMG.y0 + (cy + hh) / 1100 * IMG.height)
        link(page, r, UPAGE[uid])


def floor_page(idx, floor, kicker, heading, para, rows, note, legend=None):
    p = doc[idx]
    for l in list(p.get_links()):
        if pymupdf.Rect(l['from']).intersects(IMG):
            p.delete_link(l)
    clear(p, (690, 30, 1400, 745), rgb(LIGHT))
    put(p, (700, 44, 1374, 100), kicker, 29, BROWN, True)
    put(p, (700, 106, 1374, 190), heading, 38, INK, True)
    put(p, (700, 200, 1374, 300), para, 22, MUTED)
    if legend:
        put(p, (700, 304, 1374, 352), legend[0], 24, INK, True)
        for r, (uid, label, area, sw) in enumerate(legend[1]):
            y = 380 + r * 60
            if AR:
                box(p, (1349, y + 10, 1373, y + 34), sw)
                put(p, (1000, y, 1340, y + 46), label, 22, INK, True)
                put(p, (760, y + 2, 990, y + 46), area, 21, MUTED, False)
                put(p, (700, y + 8, 780, y + 46), L(uid), 21, INK, True, 'left')
            else:
                box(p, (700, y + 10, 724, y + 34), sw)
                put(p, (734, y, 1080, y + 46), label, 22, INK, True)
                put(p, (1090, y + 2, 1290, y + 46), area, 21, MUTED, False)
                put(p, (1295, y + 8, 1374, y + 46), uid, 21, INK, True, 'right')
            box(p, (700, y + 52, 1374, y + 53), RULE)
            link(p, (700, y, 1374, y + 52), UPAGE[uid])
        put(p, (700, 630, 1374, 735), note, 20, MUTED)
    else:
        put(p, (700, 306, 1374, 330), L('SELECT A UNIT ON THE PLAN'), 15, BROWN, True)
        put(p, (700, 338, 1374, 392), 'اضغط على رقم المحل لفتح صفحته' if AR else 'Tap a shop number to open its page', 27, DARK, True)
        n = (len(rows) + 1) // 2
        for k, (c, cnt) in enumerate(rows):
            col, r = divmod(k, n)
            y = 410 + r * 40
            if AR:
                x0, x1 = (1020, 1320) if col == 0 else (700, 1000)
            else:
                x0, x1 = (700, 1000) if col == 0 else (1020, 1320)
            put(p, (x0, y, x1, y + 36), f'{cat(c)}، {num(cnt, 0)}' if AR else f'{cat(c)}, {cnt}', 17, INK, True)
            box(p, (x0, y + 39, x1, y + 40), RULE)
        put(p, (700, 630, 1374, 735), note, 19, MUTED)
    plan_links(p, floor)


def counts(floor):
    c = {}
    for u in UNITS:
        if u['f'] == floor:
            c[u['cat']] = c.get(u['cat'], 0) + 1
    return sorted(c.items(), key=lambda kv: -kv[1])


def tot(floor):
    us = [u for u in UNITS if u['f'] == floor]
    return len(us), sum(u['area'] for u in us), sum(not u['held'] for u in us)


NOTE = ('البني: غير معروضة للتأجير حاليًا. المساحات محملة، والإيجار يُحسب عليها. '
        'يُراجع التوافر الحالي عند المعاينة.') if AR else \
       'Brown: not currently offered for lease. Areas are loaded areas, and rent is charged on them. Availability is confirmed at the viewing.'

b = [U[k] for k in ('B01', 'B02', 'B03', 'B04')]
floor_page(26, 'b1', 'البدروم الأول' if AR else 'Basement 1',
           'الإكسسوارات والموبايلات ومنطقة الأطفال' if AR else 'Accessories, mobiles and kids area',
           'تواجه الوحدات الثلاث هايبر ماركت الحبيب. يوضّح كل لون موقع النشاط ومساحته المحملة على مخطط الدور.' if AR else
           'The three units face Al Habeeb Hypermarket. Each colour shows the use and its loaded area on the floor plan.',
           None,
           ('تبلغ مساحة الجراج ' + m2(3644, 0) + '. المساحات محملة، والإيجار يُحسب عليها. يشغّل الحبيب الهايبر ماركت مباشرة.') if AR else
           'The garage covers 3,644 m². Areas are loaded areas, and rent is charged on them. Al Habeeb operates the hypermarket directly.',
           ('اضغط على رقم الوحدة أو اسمها لفتح التفاصيل' if AR else 'Select a unit code or name to open its details',
            [(u['id'], u['title'] if AR else EN.get(u['title'], u['title']), m2(u['area']), sw)
             for u, sw in zip(b, ['#d6e6ef', '#f05a28', '#7e57c2', '#f7c7a6'])]))

n, a, o = tot('g')
terr = [U[k]['extra'] for k in U if U[k]['f'] == 'g' and U[k].get('extra')]
floor_page(27, 'g', 'الدور الأرضي' if AR else 'Ground floor',
           'مطاعم البلازا وواجهات التجزئة' if AR else 'Plaza restaurants and retail frontages',
           (f'{num(n, 0)} وحدة بمساحة محملة {m2(a, 0)}، منها {num(o, 0)} متاحة للإيجار. '
            f'لمطاعم البلازا تراسات خارجية من {num(min(terr), 0)} إلى {m2(max(terr), 0)} غير محسوبة في المساحة.') if AR else
           (f'{n} units with {num(a, 0)} m² of loaded area, {o} of them available for lease. '
            f'Plaza restaurants have outdoor terraces of {num(min(terr), 0)} to {num(max(terr), 0)} m², not counted in the area.'),
           counts('g'), NOTE)

n, a, o = tot('f1')
fc = sum(1 for u in UNITS if u['f'] == 'f1' and u['cat'] == 'فود كورت')
floor_page(28, 'f1', 'الدور الأول' if AR else 'First floor',
           'الفود كورت والمعارض والتجزئة' if AR else 'Food court, showrooms and retail',
           (f'{num(n, 0)} وحدة بمساحة محملة {m2(a, 0)}، منها {num(fc, 0)} وحدات فود كورت، '
            f'ووحدة الخدمات المالية {L("F08")} بمساحة {m2(U["F08"]["area"])}.') if AR else
           (f'{n} units with {num(a, 0)} m² of loaded area, including {fc} food-court units '
            f'and the F08 financial-services unit of {num(U["F08"]["area"])} m².'),
           counts('f1'), NOTE)

n, a, o = tot('f2')
floor_page(29, 'f2', 'الدور الثاني' if AR else 'Second floor',
           'الترفيه والتجزئة' if AR else 'Entertainment and retail',
           (f'{num(n, 0)} وحدة بمساحة محملة {m2(a, 0)}، منها مساحتان للترفيه: '
            f'{L("S08")} بمساحة {m2(U["S08"]["area"])} و{L("S07")} بمساحة {m2(U["S07"]["area"])}.') if AR else
           (f'{n} units with {num(a, 0)} m² of loaded area, including two entertainment spaces: '
            f'S08 of {num(U["S08"]["area"])} m² and S07 of {num(U["S07"]["area"])} m².'),
           counts('f2'), NOTE)

# ---------- page 15: the owner and developer ----------
p = doc[14]
clear(p, (670, 15, 1400, 592), rgb(LIGHT))
if not AR:
    clear(p, (300, 15, 670, 110), rgb(LIGHT))
put(p, (680, 26, 1374, 104), 'الحبيب للتنمية والاستثمار ش.م.م.' if AR else 'Al-Habeeb for Development & Investment LLC', 36, INK, True)
put(p, (680, 116, 1374, 160), 'المالكة والمطوّرة لهابينس بلازا في قنا الجديدة.' if AR else 'Owner and developer of Happiness Plaza, New Qena.', 22, MUTED)
put(p, (680, 172, 1374, 282),
    'مجموعة من الشركات تعمل في تجارة التجزئة والإنتاج الزراعي والتطوير العقاري والتصميم والمقاولات. '
    'تأسست المجموعة ونمت وتطورت في محافظة قنا.' if AR else
    'A group of companies working in retail, agriculture, real estate development, design and contracting. '
    'The group was founded, grew and developed in Qena Governorate.', 22, INK, True)
LINES15 = [
    ('التجزئة', 'Retail', 'سلسلة الحبيب ماركت منذ ' + num(2008, 0).replace('٬', '') + ': ' + num(4, 0) + ' فروع في قنا والبحر الأحمر، ومنها هايبر ماركت ' + L('B01') + ' داخل المول.',
     'Al Habeeb Market since 2008: 4 branches in Qena and the Red Sea, plus the B01 hypermarket in the mall.'),
    ('الزراعة', 'Agriculture', 'مزارع الحبيب منذ ' + num(2014, 0).replace('٬', '') + ': ' + num(2, 0) + ' مليون طائر و' + num(3000, 0) + ' رأس ماشية سنويًا.',
     'Al Habeeb Farms since 2014: 2 million birds and 3,000 head of livestock a year.'),
    ('التطوير العقاري', 'Real estate', 'منذ ' + num(2021, 0).replace('٬', '') + ' بمشروع هابينس بلازا على أرض ' + m2(20000, 0) + '.',
     'Since 2021 with Happiness Plaza, on a 20,000 m² site.'),
    ('التصميم والمقاولات', 'Design & build', 'الحبيب للهندسة والمقاولات منذ ' + num(2008, 0).replace('٬', '') + '.',
     'Al-Habeeb Engineering & Contracting, since 2008.'),
]
for r, (lab_ar, lab_en, txt_ar, txt_en) in enumerate(LINES15):
    y = 300 + r * 58
    box(p, (680, y, 1374, y + 1), RULE)
    if AR:
        put(p, (1160, y + 10, 1374, y + 52), lab_ar, 20, BROWN, True)
        put(p, (680, y + 12, 1150, y + 52), txt_ar, 18, MUTED)
    else:
        put(p, (680, y + 10, 890, y + 52), lab_en, 20, BROWN, True)
        put(p, (900, y + 12, 1374, y + 52), txt_en, 18, MUTED)
box(p, (680, 532, 1374, 533), RULE)
put(p, (680, 544, 1374, 588),
    ('تتولى ' + L('JKFacilities') + ' إدارة المشروع وتشغيله وتنسيق التأجير.') if AR else
    'JKFacilities manages and operates the project and coordinates leasing.', 18, MUTED)
p.insert_link({'kind': pymupdf.LINK_URI, 'from': pymupdf.Rect(680, 172, 1374, 282), 'uri': 'https://alhabeeb.org/'})

doc.save(PDF + '.tmp', garbage=3, deflate=True)
doc.close()
import os
os.replace(PDF + '.tmp', PDF)
print('overview pages rewritten', LANG)
