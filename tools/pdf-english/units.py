"""Split a PDF page's Arabic text into translation units.

A unit is either a paragraph (a block whose lines are each one run of Arabic text at the
same size) or a single run of adjacent Arabic spans on one line (labels, buttons).
Shared by extract2.py and translate_pdf.py so both see the same units.
"""
import re
import unicodedata

AR = re.compile(r'[؀-ۿﭐ-﷿ﹰ-﻿]')
LETTER = re.compile(r'[ء-يﭐ-﷿ﹰ-﻿]')
NUM = re.compile(r'[0-9٠-٩][0-9٠-٩٫٬.,]*')
GLUE = re.compile(r'[\s0-9٠-٩.,()%/²×·:\-–٫٬]+')


def fix_digits(s):
    def one(m):
        run = m.group(0)
        if re.search(r'[٠-٩]', run):
            run = run[::-1]
        return run.translate(str.maketrans('٠١٢٣٤٥٦٧٨٩٫٬', '0123456789.,'))
    return NUM.sub(one, s)


def norm(s):
    s = unicodedata.normalize('NFKC', s).replace('ـ', '')
    s = fix_digits(s)
    return re.sub(r'\s+', ' ', s).strip()


def template(s):
    nums = []
    def sub(m):
        nums.append(m.group(0))
        return '{%d}' % (len(nums) - 1)
    return NUM.sub(sub, s), nums


def line_runs(line):
    """Runs of adjacent spans that contain Arabic (plus numbers/punctuation glued to them)."""
    runs, cur, last_x = [], [], None
    for s in line['spans']:
        t = s['text']
        is_ar = bool(AR.search(t))
        is_glue = bool(t) and bool(GLUE.fullmatch(t))
        x0, x1 = s['bbox'][0], s['bbox'][2]
        gap_ok = last_x is None or abs(x0 - last_x) < s['size'] * 1.6 or abs(x1 - (cur[-1]['bbox'][0] if cur else x1)) < s['size'] * 1.6
        if (is_ar or (is_glue and cur)) and (not cur or gap_ok):
            cur.append(s)
        else:
            if cur and any(AR.search(c['text']) for c in cur):
                runs.append(cur)
            cur = [s] if is_ar else []
        last_x = x1 if cur else None
    if cur and any(AR.search(c['text']) for c in cur):
        runs.append(cur)
    return runs


def _box(run):
    x0 = min(s['bbox'][0] for s in run)
    y0 = min(s['bbox'][1] for s in run)
    x1 = max(s['bbox'][2] for s in run)
    y1 = max(s['bbox'][3] for s in run)
    return x0, y0, x1, y1


def _cells(page, span):
    """Split a numbers-only span into cells wherever the characters are far apart."""
    key = tuple(round(v, 1) for v in span['bbox'])
    raw = getattr(page, '_hp_raw', None)
    if raw is None:
        raw = {}
        for b in page.get_text('rawdict')['blocks']:
            for l in b.get('lines', []):
                for s in l['spans']:
                    raw[tuple(round(v, 1) for v in s['bbox'])] = s['chars']
        page._hp_raw = raw
    chars = raw.get(key)
    if not chars:
        return [{'text': norm(span['text']), 'spans': [span], 'para': False}]
    groups, cur = [], [chars[0]]
    for a, b in zip(chars, chars[1:]):
        gap = min(abs(b['bbox'][0] - a['bbox'][2]), abs(a['bbox'][0] - b['bbox'][2]))
        if gap > span['size'] * 1.2:
            groups.append(cur)
            cur = []
        cur.append(b)
    groups.append(cur)
    out = []
    for g in groups:
        text = ''.join(c['c'] for c in g)
        x0 = min(c['bbox'][0] for c in g); x1 = max(c['bbox'][2] for c in g)
        sub = dict(span, text=text, bbox=(x0, span['bbox'][1], x1, span['bbox'][3]),
                   origin=(x0, span['origin'][1]))
        out.append({'text': norm(text), 'spans': [sub], 'para': False})
    return out


def page_units(page):
    # Unit cards list one fact per line; only the other pages have wrapped paragraphs.
    merge_lines = 'RETAIL LEASING' not in page.get_text()
    """Runs of Arabic text; runs stacked under each other with the same right edge,
    size and colour are joined into one paragraph (also across PDF blocks)."""
    runs = []
    for b in page.get_text('dict')['blocks']:
        if b['type'] != 0:
            continue
        for l in b['lines']:
            got = line_runs(l)
            if not got:
                # a number-only line that sits inside an Arabic sentence
                sp = [s for s in l['spans'] if s['text'].strip()]
                if sp and all(GLUE.fullmatch(s['text']) for s in sp) and any(re.search(r'[0-9٠-٩]', s['text']) for s in sp):
                    got = [sp]
            for run in got:
                runs.append(run)
    # Pieces of one printed line can arrive as separate PDF lines (numbers break them up).
    # Join pieces on the same baseline that touch, right to left (Arabic reading order).
    runs.sort(key=lambda r: (round(r[0]['origin'][1]), -_box(r)[2]))
    merged = []
    for run in runs:
        if merged:
            prev = merged[-1]
            px0 = _box(prev)[0]
            letters = lambda r: any(LETTER.search(s['text']) for s in r)
            if (abs(prev[0]['origin'][1] - run[0]['origin'][1]) < 2.5
                    and abs(prev[0]['size'] - run[0]['size']) < 1.5
                    and (letters(prev) or letters(run))
                    and -2 <= px0 - _box(run)[2] <= run[0]['size'] * 0.5):
                prev.extend(run)
                continue
        merged.append(list(run))
    runs = merged
    runs.sort(key=lambda r: (_box(r)[1], -_box(r)[2]))
    groups = []
    for run in runs:
        x0, y0, x1, y1 = _box(run)
        size, color = round(run[0]['size']), run[0]['color']
        joined = False
        for g in groups:
            gx0, gy0, gx1, gy1 = g['box']
            last_w = g['last_w']
            wrapped = merge_lines
            if (wrapped and g['size'] == size and g['color'] == color and abs(gx1 - x1) < 4
                    and 0 <= y0 - g['last_y0'] <= size * 2.1 and y0 > g['last_y0'] + size * 0.6):
                g['runs'].append(run)
                g['box'] = (min(gx0, x0), gy0, max(gx1, x1), max(gy1, y1))
                g['last_y0'] = y0
                g['last_w'] = x1 - x0
                joined = True
                break
        if not joined:
            groups.append({'runs': [run], 'box': (x0, y0, x1, y1), 'size': size, 'color': color, 'last_y0': y0, 'last_w': x1 - x0})
    out = []
    for g in groups:
        spans = [s for run in g['runs'] for s in run]
        if not any(LETTER.search(s['text']) for s in spans):
            # numbers only (e.g. table cells such as 20٪ 30٪ 40٪): keep each cell where it is.
            # One PDF span can hold several cells spread out with spacing, so split on gaps.
            for s in spans:
                for cell in _cells(page, s):
                    out.append(cell)
            continue
        text = norm(' '.join(''.join(s['text'] for s in run) for run in g['runs']))
        out.append({'text': text, 'spans': spans, 'para': len(g['runs']) > 1})
    return out
