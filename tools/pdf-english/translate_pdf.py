"""Make an English copy of an Arabic PDF in place: same pages, images, drawings and links.

Each Arabic label or paragraph is removed and its English translation is written in the
same box, anchored to the same right edge, in Inter. Links to the brand guide get ?lang=en.

Usage: python3 -I translate_pdf.py IN.pdf OUT.pdf DICT.json [DICT2.json ...]
Writes OUT.pdf and OUT.missing.json (units with no translation, left in Arabic).
"""
import json
import re
import sys
import urllib.parse
from pathlib import Path

import pymupdf

sys.path.insert(0, str(Path(__file__).resolve().parent))
from units import page_units, template  # noqa: E402

FONT_DIR = Path('/usr/share/fonts/opentype/inter')
REG = FONT_DIR / 'Inter-Regular.otf'
BOLD = FONT_DIR / 'Inter-SemiBold.otf'
GUIDE_HOST = 'happinessplaza.com'
ARABIC = re.compile(r'[؀-ۿﭐ-﷿ﹰ-﻿]')


def fill(en, nums):
    def sub(m):
        i = int(m.group(1))
        return nums[i] if i < len(nums) else ''
    out = re.sub(r'\{(\d+)\}', sub, en)
    # a superscript "2" of m² glued to the front of an area in the source text
    out = re.sub(r'\b2(107|206) m\b(?!²)', r'\1 m²', out)
    return re.sub(r'\b2(107|206) m²', r'\1 m²', out)


def rgb(c):
    return ((c >> 16) & 255) / 255, ((c >> 8) & 255) / 255, (c & 255) / 255


def english_url(uri):
    p = urllib.parse.urlsplit(uri)
    if p.netloc.endswith(GUIDE_HOST) and p.path.startswith('/brands'):
        q = urllib.parse.parse_qsl(p.query, keep_blank_values=True)
        q = [(k, v) for k, v in q if k != 'lang'] + [('lang', 'en')]
        return urllib.parse.urlunsplit((p.scheme, p.netloc, p.path, urllib.parse.urlencode(q), p.fragment))
    return uri


def left_limit(rect, obstacles):
    """Leftmost x the text may reach: stay inside the button that holds it, and do not run
    over a picture or panel to its left on the same line."""
    limit = 20
    cx, cy = (rect.x0 + rect.x1) / 2, (rect.y0 + rect.y1) / 2
    for kind, r in obstacles:
        if kind == 'box' and r.x0 <= cx <= r.x1 and r.y0 <= cy <= r.y1 and r.width < 700:
            limit = max(limit, r.x0 + 12)
        elif r.x1 <= rect.x0 + 2 and r.y0 < rect.y1 and r.y1 > rect.y0:
            limit = max(limit, r.x1 + 10)
    return limit


def write_fit(page, rect, text, size, color, bold, para, pw, baseline=None, obstacles=()):
    """Write text right-aligned in rect, shrinking or widening leftwards until it fits.
    Single-line labels sit on the original baseline so buttons and captions stay in place."""
    font = 'hpb' if bold else 'hpr'
    fontfile = str(BOLD if bold else REG)
    f = pymupdf.Font(fontfile=fontfile)
    s = size * (0.92 if not para else 0.9)
    min_s = max(6.0, size * 0.55)
    if not para and baseline is not None:
        room = max(rect.width * 1.35, rect.width + 30)
        room = min(room, rect.x1 - left_limit(rect, obstacles))
        while s > min_s and f.text_length(text, fontsize=s) > room:
            s -= 0.25
        if f.text_length(text, fontsize=s) <= room:
            x = rect.x1 - f.text_length(text, fontsize=s)
            page.insert_text((x, baseline), text, fontname=font, fontfile=fontfile, fontsize=s, color=color)
            return True
    while s >= min_s:
        width = f.text_length(text, fontsize=s)
        if para:
            extra = s * (0.6 if s > size * 0.75 else 2.6)
            r = pymupdf.Rect(rect.x0, rect.y0 - 1, rect.x1, max(rect.y1, rect.y0 + s * 1.35) + extra)
        else:
            need = width + 2
            x0 = min(rect.x0, rect.x1 - need)
            x0 = max(x0, 20 if rect.x1 > pw * 0.5 else rect.x0 - (rect.width * 0.8))
            h = max(rect.height, s * 1.3)
            cy = (rect.y0 + rect.y1) / 2
            r = pymupdf.Rect(x0, cy - h / 2, rect.x1 + 1, cy + h / 2 + s * 0.35)
        rc = page.insert_textbox(r, text, fontname=font, fontfile=fontfile, fontsize=s,
                                 color=color, align=pymupdf.TEXT_ALIGN_RIGHT)
        if rc >= 0:
            return True
        s -= max(0.5, size * 0.04)
    if not para and baseline is not None:
        # last resort: original size on the original baseline, ignoring the limits
        s = size * 0.92
        x = max(10, rect.x1 - f.text_length(text, fontsize=s))
        page.insert_text((x, baseline), text, fontname=font, fontfile=fontfile, fontsize=s, color=color)
        return True
    return False


def main():
    src, dst = sys.argv[1], sys.argv[2]
    dic = {}
    for p in sys.argv[3:]:
        dic.update(json.load(open(p, encoding='utf-8')))
    doc = pymupdf.open(src)
    missing, overflow = {}, []
    for page in doc:
        pw = page.rect.width
        units = page_units(page)
        all_spans = [s for b in page.get_text('dict')['blocks'] if b['type'] == 0
                     for l in b['lines'] for s in l['spans']]
        links = page.get_links()
        jobs = []
        for u in units:
            key, nums = template(u['text'])
            en = dic.get(key)
            if en is None and not re.search(r'[ء-يﭐ-﷿ﹰ-﻿]', key):
                en = key.replace('٪', '%').replace('،', ',').replace('؛', ';')  # numbers and signs only
            if en is None:
                missing[key] = missing.get(key, 0) + 1
                continue
            rect = pymupdf.Rect(u['spans'][0]['bbox'])
            for s in u['spans'][1:]:
                rect |= pymupdf.Rect(s['bbox'])
            first = u['spans'][0]
            jobs.append((rect, fill(en, nums).strip(), first['size'], rgb(first['color']),
                         'Bold' in first['font'] or 'bold' in first['font'].lower(), u['para'],
                         first['origin'][1]))
            extra = []
            if not u['para']:
                # a play arrow printed beside an Arabic button label: drop it, end the English with →
                for b in all_spans:
                    t = b['text'].strip()
                    br = pymupdf.Rect(b['bbox'])
                    if t and set(t) <= set('◀▶◄►←→') and abs(b['origin'][1] - first['origin'][1]) < 4 \
                            and (rect.x0 - 45 <= br.x1 <= rect.x0 + 4 or rect.x1 - 4 <= br.x0 <= rect.x1 + 45):
                        extra.append(b)
                if extra:
                    jobs[-1] = jobs[-1][:1] + (jobs[-1][1] + ' →',) + jobs[-1][2:]
            if u['para']:
                # Latin words or brackets printed inside the Arabic paragraph
                own = {id(s) for s in u['spans']}
                box = rect + (-2, -2, 2, 2)
                for b in all_spans:
                    if id(b) not in own and box.contains(pymupdf.Rect(b['bbox'])):
                        extra.append(b)
            for s in u['spans'] + extra:
                r = pymupdf.Rect(s['bbox'])
                h = r.height
                page.add_redact_annot(pymupdf.Rect(r.x0 + 0.3, r.y0 + h * 0.28, r.x1 - 0.3, r.y1 - h * 0.22), fill=False)
        if jobs:
            page.apply_redactions(images=pymupdf.PDF_REDACT_IMAGE_NONE,
                                  graphics=pymupdf.PDF_REDACT_LINE_ART_NONE,
                                  text=pymupdf.PDF_REDACT_TEXT_REMOVE)
            # second pass: stray Arabic marks (vowel signs) left outside the span boxes
            stray = []
            for tr in page.get_texttrace():
                for c in tr['chars']:
                    if ARABIC.match(chr(c[0])):
                        x0, y0, x1, y1 = c[3]
                        stray.append(pymupdf.Rect(x0 - 1.5, y0, max(x1, x0) + 1.5, y1))
            for r in stray:
                page.add_redact_annot(r, fill=False)
            if stray:
                page.apply_redactions(images=pymupdf.PDF_REDACT_IMAGE_NONE,
                                      graphics=pymupdf.PDF_REDACT_LINE_ART_NONE,
                                      text=pymupdf.PDF_REDACT_TEXT_REMOVE)
        obstacles = [('img', pymupdf.Rect(i['bbox'])) for i in page.get_image_info()]
        for dr in page.get_drawings():
            if dr.get('fill') is not None and dr['rect'].width > 40 and dr['rect'].height > 18:
                obstacles.append(('box', dr['rect']))
        for rect, text, size, color, bold, para, base in jobs:
            if not write_fit(page, rect, text, size, color, bold, para, pw, base, obstacles):
                overflow.append((page.number + 1, text[:60]))
        # links: restore any the redaction dropped, and point the guide at English
        for l in page.get_links():
            page.delete_link(l)
        for l in links:
            l = dict(l)
            l.pop('xref', None)
            l.pop('id', None)
            if l.get('kind') == pymupdf.LINK_URI and l.get('uri'):
                l['uri'] = english_url(l['uri'])
            page.insert_link(l)
    doc.subset_fonts()
    doc.save(dst, garbage=3, deflate=True)
    json.dump({'missing': missing, 'overflow': overflow},
              open(re.sub(r'\.pdf$', '', dst) + '.missing.json', 'w', encoding='utf-8'),
              ensure_ascii=False, indent=1)
    print('pages', len(doc), 'missing', len(missing), 'overflow', len(overflow))


if __name__ == '__main__':
    main()
