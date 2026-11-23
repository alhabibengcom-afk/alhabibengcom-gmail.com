"""Happiness Plaza: rebuild the leasing PDF after a change in the shop subdivision (units merged, split or recoded)."""
from pathlib import Path
import argparse
import ctypes
import ctypes.util
import functools
import json
import math
import tempfile
import urllib.parse
import fitz
from PIL import Image, ImageOps
from reportlab.pdfgen import canvas
from reportlab.lib.colors import HexColor
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

# Regenerate from the complete directory extracted from the deployment package.
parser = argparse.ArgumentParser(description='Refresh the leasing PDFs and browser pages from the current unit and photo registrations.')
parser.add_argument('--site-dir', type=Path, default=Path(__file__).resolve().parents[1] / 'brands')
parser.add_argument('--output-dir', type=Path, required=True, help='An empty directory outside the deployed site.')
parser.add_argument('--font-dir', type=Path, default=Path('/usr/share/fonts/truetype/dejavu'))
parser.add_argument('--base-url', default='https://happinessplaza.com/brands/')
options = parser.parse_args()
SRC = options.site_dir.resolve()
DEST = options.output_dir.resolve()
if not (SRC / 'unit-data.js').is_file() or not (SRC / 'location-links.js').is_file():
    parser.error('Choose the complete brands folder with unit-data.js and location-links.js.')
if DEST == SRC or DEST.is_relative_to(SRC) or (DEST.exists() and (not DEST.is_dir() or any(DEST.iterdir()))):
    parser.error('Choose a new or empty output directory outside brands.')
DEST.mkdir(parents=True, exist_ok=True)
work_directory = tempfile.TemporaryDirectory(prefix='hp-pdf-')
ROOT = Path(work_directory.name)
W, H = (1440, 810)
base = urllib.parse.urlsplit(options.base_url)
if base.scheme not in {'http', 'https'} or not base.netloc or base.query or base.fragment:
    parser.error('Use an HTTP(S) directory URL without a query or fragment.')
SITE = options.base_url.rstrip('/') + '/'
FLOORS = {'b1': ('BASEMENT 01', 'البدروم الأول'), 'g': ('GROUND FLOOR', 'الدور الأرضي'), 'f1': ('FIRST FLOOR', 'الدور الأول'), 'f2': ('SECOND FLOOR', 'الدور الثاني')}
PAPER = '#F8F6F0'
DARK = '#173D38'
INK = '#162D2A'
SUB = '#45645B'
DARKT = '#004B43'
OUT = '#CFDAD3'
WHITE = '#FFFFFF'
units = json.JSONDecoder().raw_decode((SRC / 'site.js').read_text().split('const UNITS=', 1)[1])[0]
geometry = json.JSONDecoder().raw_decode((SRC / 'unit-data.js').read_text().split('const UNIT_DRAWINGS=', 1)[1])[0]
by_id = {u['id']: u for u in units}
PANORAMA_ROOT=SRC
register=json.JSONDecoder().raw_decode((PANORAMA_ROOT/'location-links.js').read_text().split('=',1)[1].strip())[0]
photo_manifest=register['photos']
panoramas=register.get('panoramas',{})
photos = {v['id']: v for v in json.JSONDecoder().raw_decode((SRC / 'unit-data.js').read_text().split('const UNIT_GALLERY=', 1)[1])[0]['photos']}
links_manifest = json.JSONDecoder().raw_decode((SRC / 'document-links.js').read_text().split('=', 1)[1])[0]
data_manifest = json.JSONDecoder().raw_decode((SRC / 'document-data.js').read_text().split('=', 1)[1])[0]
pdfmetrics.registerFont(TTFont('Arabic', str(options.font_dir / 'DejaVuSans.ttf')))
pdfmetrics.registerFont(TTFont('ArabicBold', str(options.font_dir / 'DejaVuSans-Bold.ttf')))
fribidi = ctypes.util.find_library('fribidi')
if not fribidi:
    parser.error('Install libfribidi for shaping Arabic PDF text.')
fb = ctypes.CDLL(fribidi)
U = ctypes.c_uint32
I = ctypes.c_int

@functools.lru_cache(None)
def shape(value):
    a = (U * len(value))(*map(ord, value))
    out = (U * len(value))()
    base = U(273)
    fb.fribidi_log2vis(a, I(len(value)), ctypes.byref(base), out, None, None, None)
    return ''.join((chr(n) for n in out if n not in (65279, 8206, 8207)))

def ar_num(x):
    return str(x).translate(str.maketrans('0123456789.,', '٠١٢٣٤٥٦٧٨٩٫٬'))

def fmt(x):
    return f'{x:,.3f}'.rstrip('0').rstrip('.')

def ar(c, text, x, y, sz=17, b=False, color=INK, maxw=None):
    face = 'ArabicBold' if b else 'Arabic'
    visual = shape(text)
    if maxw:
        width = pdfmetrics.stringWidth(visual, face, sz)
        if width > maxw:
            sz *= maxw / width
    c.setFillColor(HexColor(color))
    c.setFont(face, sz)
    c.drawRightString(x, H - y, visual)

def en(c, text, x, y, sz=16, b=False, color=INK, align='left'):
    c.setFillColor(HexColor(color))
    c.setFont('Helvetica-Bold' if b else 'Helvetica', sz)
    {'left': c.drawString, 'center': c.drawCentredString, 'right': c.drawRightString}[align](x, H - y, text)

def rect(c, x, y, w, h, fill=None, stroke=None, lw=1):
    if fill:
        c.setFillColor(HexColor(fill))
    if stroke:
        c.setStrokeColor(HexColor(stroke))
    c.setLineWidth(lw)
    c.rect(x, H - y - h, w, h, fill=bool(fill), stroke=bool(stroke))

def line(c, x, y, x2, y2, color, lw=1):
    c.setStrokeColor(HexColor(color))
    c.setLineWidth(lw)
    c.line(x, H - y, x2, H - y2)

def point(c, x, y, r, fill, stroke=None, lw=1):
    c.setFillColor(HexColor(fill))
    if stroke:
        c.setStrokeColor(HexColor(stroke))
    c.setLineWidth(lw)
    c.circle(x, H - y, r, fill=1, stroke=bool(stroke))

def area_label(c, x, y, s):
    en(c, s, x, y, 14, True, SUB)

def box(c, txt, lbl, x0, y, w, h, primary=False):
    rect(c, x0, y, w, h, DARK if primary else WHITE, None if primary else OUT)
    ar(c, txt, x0 + w - 18, y + 27, 17, True, WHITE if primary else INK, maxw=w - 61)
    en(c, lbl, x0 + 14, y + 25, 12, True, '#DCE9E0' if primary else SUB)
    return (x0, y, x0 + w, y + h)

def outline(c, pts, color, fill=None, width=2, alpha=1):
    if not pts:
        return
    c.saveState()
    c.setLineJoin(1)
    c.setStrokeColor(HexColor(color))
    c.setLineWidth(width)
    if fill:
        c.setFillColor(HexColor(fill))
        c.setFillAlpha(alpha)
    path = c.beginPath()
    path.moveTo(pts[0][0], H - pts[0][1])
    for x, y in pts[1:]:
        path.lineTo(x, H - y)
    path.close()
    c.drawPath(path, stroke=1, fill=int(bool(fill)))
    c.restoreState()

def in_poly(x, y, points):
    inside = False
    for (x0, y0), (x1, y1) in zip(points, points[1:] + points[:1]):
        if (y0 > y) != (y1 > y) and x < (x1 - x0) * (y - y0) / (y1 - y0) + x0:
            inside = not inside
    return inside

def anchor(u, poly):
    """Choose a marker inside the actual outline, including for irregular units."""
    if in_poly(u['x'], u['y'], poly):
        return (u['x'], u['y'])
    x0 = min((i[0] for i in poly))
    x1 = max((i[0] for i in poly))
    y0 = min((i[1] for i in poly))
    y1 = max((i[1] for i in poly))
    points = [(x0 + (x1 - x0) * i / 24, y0 + (y1 - y0) * j / 24) for i in range(1, 24) for j in range(1, 24)]
    return min((pt for pt in points if in_poly(*pt, poly)), key=lambda pt: math.dist(pt, (u['x'], u['y'])))

def clip(c, x, y, w, h):
    path = c.beginPath()
    path.rect(x, H - y - h, w, h)
    c.clipPath(path, stroke=0, fill=0)

def prepare_plan(f):
    path = ROOT / (f + '-desaturated.jpg')
    with Image.open(SRC / 'assets/drawings' / f'{f}.png') as im:
        im = ImageOps.colorize(ImageOps.grayscale(im), black='#435852', white='#ffffff').convert('RGB')
        im.save(path, quality=85, optimize=True, subsampling=0)
    return str(path)
images = {f: prepare_plan(f) for f in FLOORS}

def map_view(c, u, frame, close):
    """Render the source plan and its geometry through the same coordinate transform."""
    x, y, w, h = frame
    geo = geometry[u['id']]
    poly = geo['polygon']
    mx, my = anchor(u, poly)
    if close:
        xs, ys = zip(*poly)
        l, r, t, b = (min(xs), max(xs), min(ys), max(ys))
        world_w = max(130, (r - l) * 1.55)
        world_h = max(105, (b - t) * 1.5)
        scale = min(w / world_w, h / world_h)
        world_w, world_h = (w / scale, h / scale)
        xc = min(max((l + r) / 2, world_w / 2), 1108 - world_w / 2) if world_w < 1108 else (l + r) / 2
        yc = min(max((t + b) / 2, world_h / 2), 1100 - world_h / 2) if world_h < 1100 else (t + b) / 2
    else:
        scale = min(w / 1108, h / 1100)
        xc, yc = (554, 550)
    dx, dy = (x + w * 0.5 - scale * xc, y + h * 0.5 - scale * yc)
    project = lambda v: (dx + scale * v[0], dy + scale * v[1])
    c.saveState()
    clip(c, *frame)
    c.drawImage(images[u['f']], dx, H - dy - 1100 * scale, width=1108 * scale, height=1100 * scale)
    if close:
        for nb in geo['neighbors']:
            n = geometry[nb['id']]
            outline(c, list(map(project, n['polygon'])), '#87836A', '#BDAC79', 0.9, 0.11)
    shp = list(map(project, poly))
    outline(c, shp, WHITE, width=4 if close else 3.4)
    outline(c, shp, DARKT, '#219688', 3 if close else 1.8, 0.42 if close else 0.53)
    center_x, center_y = project((mx, my))
    if close:
        if max((pt[0] for pt in shp)) - min((pt[0] for pt in shp)) > 70:
            point(c, center_x, center_y, 4, WHITE, DARKT, 1.8)
    else:
        badge_w = 18 + pdfmetrics.stringWidth(u['id'], 'Helvetica-Bold', 16)
        badge_h = 25
        bx = center_x + 30 if center_x < x + w * 0.64 else center_x - 30 - badge_w
        bx = max(x + 3, min(bx, x + w - badge_w - 3))
        by = max(y + 3, min(center_y - 37, y + h - badge_h - 3))
        ax = min(bx + badge_w, max(bx, center_x))
        ay = by + badge_h / 2
        line(c, center_x, center_y, ax, ay, WHITE, 4)
        line(c, center_x, center_y, ax, ay, DARKT, 1.6)
        rect(c, bx, by, badge_w, badge_h, DARKT, WHITE, 1)
        en(c, u['id'], bx + badge_w / 2, by + 18, 16, True, WHITE, 'center')
        point(c, center_x, center_y, 3.6, DARKT, WHITE, 1.5)
    c.restoreState()

@functools.lru_cache(None)
def original_photo(pid):
    photo = photos[pid]
    path = SRC / (photo.get('original') or photo['src'])
    with Image.open(path) as im:
        im = im.convert('RGB')
        w, h = im.size
        im.thumbnail((1650, 1650))
        out = ROOT / ('photo-' + pid + '.jpg')
        im.save(out, quality=87, subsampling=0, optimize=True)
    return (str(out), w, h)

def field_photo(c, u, field):
    """Place the registered pin in the original image, accounting for the printed crop."""
    pid = field['photo']
    img, sw, sh = original_photo(pid)
    x, y, w, h = (612, 240, 363, 167)
    scale = max(w / sw, h / sh)
    iw, ih = (sw * scale, sh * scale)
    # Crop only within image bounds and retain the register mark in frame.
    left = max(0, min(iw - w, field['x'] * iw - w / 2))
    top = max(0, min(ih - h, field['y'] * ih - h * 0.61))
    px, py = (x - left, y - top)
    c.saveState()
    clip(c, x, y, w, h)
    c.drawImage(img, px, H - py - ih, width=iw, height=ih)
    c.restoreState()
    mx, my = (px + iw * field['x'], py + ih * field['y'])
    uid = u['id']
    bw = pdfmetrics.stringWidth(uid, 'Helvetica-Bold', 13) + 15
    bx = mx + 11 if mx < x + w * 0.62 else mx - bw - 12
    bx = max(x + 2, min(bx, x + w - bw - 2))
    by = max(y + 2, my - 31)
    tx = min(bx + bw, max(bx, mx))
    ty = by + 17
    line(c, mx, my, tx, ty, WHITE, 3)
    line(c, mx, my, tx, ty, DARKT, 1.3)
    rect(c, bx, by, bw, 19, DARKT, WHITE, 0.65)
    en(c, uid, bx + bw / 2, by + 14, 13, True, WHITE, 'center')
    point(c, mx, my, 4.4, DARKT, WHITE, 1.8)
    caption = 'موضع مسقط على امتداد الواجهة' if field.get('basis') == 'facade-projection' else 'موقع الوحدة في صورة المبنى'
    ar(c, caption, 974, 432, 14, color=SUB)
    return (x, y, x + w, y + h)

def panorama_panel(c, u, mark):
    """Print a perspective view aimed at the calibrated point on the original sphere."""
    import numpy as np
    scene_id=str(mark['scene'])
    if not scene_id.isdigit():
        raise ValueError('Unknown panorama scene '+scene_id)
    with Image.open(PANORAMA_ROOT / 'assets/panoramas' / (scene_id+'.webp')) as frame:
        sphere=np.asarray(frame.convert('RGB'))
    sh,sw=sphere.shape[:2]
    w,h=726,334
    yy,xx=np.mgrid[0:h,0:w]
    focal=w / (2*math.tan(math.radians(82)/2))
    yaw=(mark['x']-.5)*math.tau
    pitch=(.5-mark['y'])*math.pi
    nx=(xx+.5-w/2)/focal
    ny=(h/2-yy-.5)/focal
    z=math.cos(pitch)-ny*math.sin(pitch)
    vy=ny*math.cos(pitch)+math.sin(pitch)
    # Wrap longitude across the zero meridian and clamp latitude at the poles.
    sx=((.5+(np.arctan2(nx,z)+yaw)/math.tau)*sw-.5) % sw
    sy=np.clip((.5-np.arctan2(vy,np.sqrt(nx*nx+z*z))/math.pi)*sh-.5,0,sh-1)
    x0=np.floor(sx).astype(int)
    y0=np.floor(sy).astype(int)
    x1=(x0+1)%sw
    y1=np.minimum(y0+1,sh-1)
    fx=(sx-x0)[...,None]
    fy=(sy-y0)[...,None]
    rgb=(sphere[y0,x0]*(1-fx)+sphere[y0,x1]*fx)*(1-fy)+(sphere[y1,x0]*(1-fx)+sphere[y1,x1]*fx)*fy
    image=ROOT / ('panorama-'+u['id']+'.jpg')
    Image.fromarray(rgb.round().astype('uint8')).save(image,quality=91,subsampling=0)
    x,y,rw,rh=612,240,363,167
    c.drawImage(str(image),x,H-y-rh,width=rw,height=rh)
    cx,cy=x+rw/2,y+rh/2
    uid=u['id']
    badge=pdfmetrics.stringWidth(uid,'Helvetica-Bold',13)+15
    line(c,cx,cy,cx+11,cy-16,WHITE,3)
    line(c,cx,cy,cx+11,cy-16,DARKT,1.3)
    rect(c,cx+10,cy-32,badge,19,DARKT,WHITE,.65)
    en(c,uid,cx+10+badge/2,cy-18,13,True,WHITE,'center')
    point(c,cx,cy,4.4,DARKT,WHITE,1.8)
    ar(c,'موضع الوحدة في التصور المعماري للممر',974,432,14,color=SUB)
    return (x,y,x+rw,y+rh)

def make_card(c, u, num, total, floor_goto, whats):
    """Draw one sheet and return the PDF action for each interactive region."""
    uid = u['id']
    geo = geometry[uid]
    f = u['f']
    actions = []
    rect(c, 0, 0, W, H, PAPER)
    rect(c, 0, 0, W, 10, DARK)
    en(c, 'HAPPINESS PLAZA', 49, 47, 20, True, DARK)
    en(c, '/    RETAIL LEASING', 246, 46, 14, False, SUB)
    en(c, FLOORS[f][0], 49, 144, 16, True, SUB)
    en(c, uid, 48, 117, 56, True, DARK)
    ar(c, 'موقع الوحدة', 1390, 48, 17, False, SUB)
    ar(c, u['title'], 1390, 113, 42, True, DARK, maxw=700)
    ar(c, FLOORS[f][1] + ('   ·   مرجع على المخطط (الكود المطبوع قيد المراجعة)' if u['pending'] else ''), 1390, 147, 17, color=SUB, maxw=790)
    line(c, 48, 164, 1392, 164, OUT, 1.2)
    # Whole-floor satellite map, close-up and source drawing use exactly the web plan coordinate system.
    rect(c, 48, 188, 534, 480, WHITE, OUT)
    area_label(c, 66, 217, 'FLOOR PLAN')
    ar(c, 'خريطة الدور', 562, 217, 21, True)
    line(c, 66, 231, 563, 231, OUT)
    map_view(c, u, (68, 238, 493, 379), False)
    line(c, 66, 630, 563, 630, OUT)
    rect(c, 548, 645, 13, 12, '#4D9D8E', DARKT, 1)
    ar(c, 'حدود الوحدة المختارة', 539, 657, 15, True, DARK)
    en(c, FLOORS[f][0], 67, 657, 12, True, SUB)
    rect(c, 596, 188, 395, 480, WHITE, OUT)
    registered=photo_manifest.get(uid,[])
    virtual=panoramas.get(uid,[])
    title='الوحدة على الطبيعة' if registered else ('بانوراما تصميمية' if virtual else 'الوحدة ومحيطها')
    eyebrow='ON SITE' if registered else ('360° VIEW' if virtual else 'DETAIL')
    area_label(c,612,217,eyebrow)
    ar(c,title,974,217,20,True)
    line(c,612,231,975,231,OUT)
    if registered:
        image_box=field_photo(c,u,registered[0])
        actions.append((image_box,SITE+'?unit='+uid+'&view=real'))
    elif virtual:
        image_box=panorama_panel(c,u,virtual[0])
        actions.append((image_box,SITE+'?unit='+uid+'&view=tour'))
    else:
        map_view(c,u,(612,241,363,191),True)
    line(c, 612, 446, 975, 446, OUT)
    area_label(c, 612, 474, 'DRAWING')
    ar(c, 'رسم الوحدة', 974, 474, 20, True)
    with Image.open(SRC / u['crop']) as im:
        sw, sh = im.size
    scale = min(359 / sw, 163 / sh)
    iw, ih = (sw * scale, sh * scale)
    c.drawImage(str(SRC / u['crop']), 793.5 - iw / 2, H - (483 + (163 - ih) / 2) - ih, width=iw, height=ih, mask='auto')
    # Right-hand leasing facts and direct links to adjoining units.
    rect(c, 1005, 188, 387, 480, WHITE, OUT)
    ar(c, 'مساحة التأجير', 1371, 225, 17, True, SUB)
    if u['area'] is None:
        ar(c, 'تُراجع مع إدارة التأجير', 1371, 267, 22, True, DARK)
    else:
        en(c, fmt(u['area']), 1024, 267, 40, True, DARK)
        ar(c, 'متر مربع', 1371, 266, 19, color=SUB)
    if u['extra']:
        ar(c, u['elab'] + '  ' + ar_num(fmt(u['extra'])) + ' م²', 1371, 300, 16, color=INK, maxw=343)
    line(c, 1024, 313, 1373, 313, OUT)
    dim = geo['dimensions']
    ar(c, 'الأبعاد الهندسية', 1371, 345, 19, True, DARK)
    description = 'من لوحة الأبعاد' if dim['method'] == 'dimensioned_drawing' else 'تقريبية بحسب مقياس المسقط'
    ar(c, description, 1371, 370, 14, color=SUB)
    dy = 397
    row = []
    if dim.get('width'):
        row += ['عرض ' + ar_num(fmt(dim['width'])) + ' م']
    if dim.get('depth'):
        row += ['عمق ' + ar_num(fmt(dim['depth'])) + ' م']
    if row:
        ar(c, '   ·   '.join(row), 1371, dy, 17, True)
        dy += 25
    for seg in dim.get('segments', []):
        ar(c, seg['label'] + '   ' + ar_num(fmt(seg['value'])) + ' م', 1371, dy, 14, color=INK, maxw=344)
        dy += 21
    line(c, 1024, 484, 1373, 484, OUT)
    ar(c, 'الوحدات ذات الحدود المشتركة', 1371, 515, 16, True, DARK)
    p = 1371
    for nb in geo['neighbors']:
        code = nb['id']
        wid = pdfmetrics.stringWidth(code, 'Helvetica-Bold', 15) + 18
        p -= wid
        rect(c, p, 528, wid, 29, '#E9F0EA', OUT)
        en(c, code, p + wid / 2, 548, 15, True, DARK, 'center')
        actions.append(((p, 528, p + wid, 557), ('neighbor', code)))
        p -= 6
    if not geo['neighbors']:
        ar(c, 'لا يظهر محل ملاصق على الرسم', 1371, 549, 14, color=SUB)
    line(c, 1024, 575, 1373, 575, OUT)
    ar(c, 'حالة التأجير', 1371, 605, 15, True, SUB)
    ar(c, u['status'], 1371, 637, 18, True, DARK, maxw=343)
    # Simple navigation: no external login or network is needed to use the floor index.
    actions.extend([
        (box(c, 'مخطط الدور', 'PLAN', 48, 693, 226, 45), floor_goto),
        (box(c, 'بطاقة الوحدة', 'WEB', 287, 693, 229, 45), SITE + '?unit=' + uid),
        (box(c, 'صور الموقع', 'PHOTO', 529, 693, 221, 45), SITE + '?unit=' + uid + '&view=real'),
        (box(c, 'الجولة البصرية', 'TOUR', 763, 693, 248, 45), SITE + '?unit=' + uid + '&view=tour'),
        (box(c, 'طلب معاينة الوحدة', 'VISIT', 1024, 693, 368, 45, True), whats),
        ((46, 60, 70 + pdfmetrics.stringWidth(uid, 'Helvetica-Bold', 56), 124), SITE + '?unit=' + uid),
    ])
    line(c, 48, 755, 1392, 755, OUT)
    en(c, 'ALHABEEB  /  DEVELOPMENT & INVESTMENT', 49, 783, 13, True, SUB)
    en(c, f'{num}  /  {total}', 1390, 783, 14, False, SUB, 'right')
    c.showPage()
    return actions



# ---------------------------------------------------------------------------
# Rebuild for a new subdivision. Keeps the 37 opening pages, replaces every unit sheet,
# swaps the floor-plan pictures, and re-points every link from old unit codes to new ones.
# Aliases (old code -> new code) come from aliases.json next to this script or --aliases.
# ---------------------------------------------------------------------------
INTRO = 37
PLAN_PAGES = {'b1': 27, 'g': 28, 'f1': 29, 'f2': 30}  # 1-based pages holding the floor plan picture
alias_path = Path(__file__).resolve().parent / 'aliases.json'
ALIASES = json.loads(alias_path.read_text(encoding='utf-8')) if alias_path.is_file() else {}


def new_code(code):
    code = ALIASES.get(code, code)
    return code if code in by_id else None


def whats_for(u):
    msg = 'أطلب معاينة ' + FLOORS[u['f']][1] + '، ' + u['id']
    return 'https://wa.me/201227777104?text=' + urllib.parse.quote(msg)


def unit_of_page(page):
    refs = {urllib.parse.parse_qs(urllib.parse.urlsplit(l['uri']).query).get('unit', [''])[0]
            for l in page.get_links() if '?unit=' in l.get('uri', '')}
    return refs.pop() if len(refs) == 1 else None


def rebuild_leasing():
    src = fitz.open(SRC / data_manifest['leasing']['file'])
    old_page_unit = {ix: unit_of_page(src[ix]) for ix in range(INTRO, len(src))}
    floor_goto = {}
    for ix in range(INTRO, len(src)):
        for l in src[ix].get_links():
            if l['kind'] == fitz.LINK_GOTO and l['from'].y0 > 675 and l['from'].x0 < 120:
                old = old_page_unit[ix]
                if old and old in ALIASES or old in by_id:
                    floor_goto.setdefault(by_id[new_code(old)]['f'] if new_code(old) else None, l['page'] + 1)
    order = {'b1': 0, 'g': 1, 'f1': 2, 'f2': 3}
    items = sorted(units, key=lambda u: (order[u['f']], [int(n) if n.isdigit() else n for n in re.split(r'(\d+)', u['id'])]))
    total = INTRO + len(items)
    new_index = {u['id']: INTRO + i for i, u in enumerate(items)}
    sheets_pdf = ROOT / 'leasing-sheets.pdf'
    c = canvas.Canvas(str(sheets_pdf), pagesize=(W, H), pageCompression=1)
    c.setTitle('Happiness Plaza | Unit location')
    rows_all = []
    for u in items:
        rows_all.append(make_card(c, u, new_index[u['id']] + 1, total, floor_goto.get(u['f'], 28), whats_for(u)))
    c.save()
    # opening pages: keep, re-point links, swap the plan pictures
    doc = fitz.open()
    doc.insert_pdf(src, from_page=0, to_page=INTRO - 1)
    doc.insert_pdf(fitz.open(sheets_pdf))
    for ix in range(INTRO):
        page = doc[ix]
        saved = src[ix].get_links()
        for l in page.get_links():
            page.delete_link(l)
        for l in saved:
            l = dict(l); l.pop('xref', None); l.pop('id', None)
            if l['kind'] == fitz.LINK_GOTO and l.get('page', 0) >= INTRO:
                code = new_code(old_page_unit.get(l['page']) or '')
                if not code:
                    continue
                l['page'] = new_index[code]
            elif l['kind'] == fitz.LINK_URI and '?unit=' in l.get('uri', ''):
                q = urllib.parse.parse_qs(urllib.parse.urlsplit(l['uri']).query)
                code = new_code(q.get('unit', [''])[0])
                if not code:
                    continue
                l['uri'] = re.sub(r'unit=[^&]+', 'unit=' + urllib.parse.quote(code), l['uri'])
            page.insert_link(l)
        footer = page.search_for('/ 238')
        for r in footer:
            page.add_redact_annot(r, fill=False)
        if footer:
            page.apply_redactions(images=fitz.PDF_REDACT_IMAGE_NONE, graphics=fitz.PDF_REDACT_LINE_ART_NONE)
            for r in footer:
                page.insert_text((r.x0, r.y1 - 2.5), f'/ {total}', fontname='helv', fontsize=r.height * 0.72, color=(0.27, 0.39, 0.36))
    for f, pno in PLAN_PAGES.items():
        page = doc[pno - 1]
        imgs = page.get_images()
        if imgs:
            xref = imgs[0][0]
            info = next(i for i in page.get_image_info(xrefs=True) if i['xref'] == xref)
            w, h = round(info['bbox'][2] - info['bbox'][0]), round(info['bbox'][3] - info['bbox'][1])
            tmp = ROOT / f'plan-{f}.jpg'
            with Image.open(SRC / 'assets/drawings' / f'{f}.png') as im:
                im.convert('RGB').resize((imgs[0][2], imgs[0][3]), Image.LANCZOS).save(tmp, quality=88)
            page.replace_image(xref, filename=str(tmp))
    for u, rows in zip(items, rows_all):
        page = doc[new_index[u['id']]]
        for xy, target in rows:
            if isinstance(target, tuple):
                other = target[1]
                target = new_index[other] + 1 if other in new_index else SITE + '?unit=' + other
            lr = {'from': fitz.Rect(xy)}
            lr.update({'kind': fitz.LINK_URI, 'uri': target} if isinstance(target, str) else {'kind': fitz.LINK_GOTO, 'to': fitz.Point(0, 0), 'page': target - 1})
            page.insert_link(lr)
    toc = [[1, 'Happiness Plaza | دليل التأجير', 1], [2, 'Brand directory | دليل الوحدات', 24]]
    for f in FLOORS:
        group = [u for u in items if u['f'] == f]
        toc.append([2, FLOORS[f][0] + ' | ' + FLOORS[f][1], PLAN_PAGES[f]])
        toc.extend([3, u['id'] + ' | ' + u['title'], new_index[u['id']] + 1] for u in group)
    doc.set_toc(toc)
    doc.set_metadata({'title': 'Happiness Plaza | Retail Leasing Atlas', 'author': 'Alhabeeb Development & Investment',
                      'subject': 'Unit location and retail leasing plans'})
    fpath = DEST / data_manifest['leasing']['file']
    doc.save(fpath, garbage=4, deflate=True)
    data_manifest['leasing']['pages'] = total
    links_manifest['leasing'] = {}
    xscale = 1250 / W
    out_dir = DEST / 'assets/documents/leasing'
    out_dir.mkdir(parents=True, exist_ok=True)
    with fitz.open(fpath) as verify:
        for pgindex, pg in enumerate(verify):
            feats = []
            for l in pg.get_links():
                if l['kind'] == fitz.LINK_URI:
                    target = l['uri'][len(SITE):] if l['uri'].startswith(SITE) else l['uri']
                elif l['kind'] == fitz.LINK_GOTO:
                    target = l['page'] + 1
                else:
                    continue
                b = l['from']
                feats.append([[round(n, 3) for n in [100 * b.x0 / W, 100 * b.y0 / H, 100 * b.width / W, 100 * b.height / H]], target])
            links_manifest['leasing'][str(pgindex + 1)] = feats
            pix = pg.get_pixmap(matrix=fitz.Matrix(xscale, xscale), alpha=False)
            pix.pil_save(out_dir / ('p-' + str(pgindex + 1).zfill(3) + '.jpg'), format='JPEG', quality=85, optimize=True, subsampling=0)
    print(f'leasing: {len(items)} unit sheets, {total} pages ({fpath.stat().st_size:,} bytes)', flush=True)
    return new_index


if __name__ == '__main__':
    import re
    rebuild_leasing()
    for name, var, data in [('document-data.js', 'SITE_DOCUMENTS', data_manifest), ('document-links.js', 'DOCUMENT_LINKS', links_manifest)]:
        (DEST / name).write_text('const ' + var + '=' + json.dumps(data, ensure_ascii=False, separators=(',', ':')) + ';\n')
    print(f'Copy the contents of {DEST} into brands after checking the result.')
    work_directory.cleanup()
