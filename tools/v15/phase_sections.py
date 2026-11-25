# Interactive phase-two and phase-three sections shared by build_lite.py and build_full.py.
# Each section: key figures, floor tabs, the floor plan with the phase's units lit (available units clickable),
# and a table of the units available for lease with loaded area and the restaurants' outdoor terraces.
import json, re

VB = (1108, 1100)  # plan viewBox used by the site; plan images are 1983 x 1968


def drawings(B):
    t = open(B + '/unit-data.js', encoding='utf-8').read()
    m = re.search(r'UNIT_DRAWINGS\s*=\s*', t)
    D, _ = json.JSONDecoder().raw_decode(t[m.end():])
    return {k: v['polygon'] for k, v in D.items()}


def build(B, units, OFFER, PHASE2, BACK, t, num, FLOOR, pre=''):
    poly = drawings(B)
    OFFER = set(OFFER)
    p2 = set(PHASE2)
    href = lambda uid: f'{pre}?unit={uid}'
    pts = lambda uid: ' '.join(f'{x:.1f},{y:.1f}' for x, y in poly[uid])
    order = {'b1': 0, 'g': 1, 'f1': 2, 'f2': 3}

    def section(key, ids, floors, over, title, date, lead, extra_stats, notes):
        avail = sorted([u for u in units if u['id'] in ids and u['id'] in OFFER], key=lambda u: (order[u['f']], u['id']))
        loaded = sum(u['area'] for u in avail)
        outdoor = sum((u.get('extra') or 0) for u in avail)
        stats = [(num(len(avail), 0), t('وحدة متاحة للإيجار', 'units for lease')),
                 (num(loaded) + ' م²', t('مساحة محمّلة متاحة', 'loaded area for lease'))]
        if outdoor:
            stats.append((num(outdoor) + ' م²', t('تراسات خارجية للمطاعم', 'restaurant outdoor terraces')))
        stats += extra_stats
        stats.append((date, t('موعد التشغيل', 'opening')))
        tabs, panels = [], []
        for i, f in enumerate(floors):
            on = ' on' if i == 0 else ''
            fu = [u for u in units if u['f'] == f and u['id'] in poly]
            mine = [u for u in fu if u['id'] in ids]
            fav = [u for u in avail if u['f'] == f]
            tabs.append(f'<button type="button" class="hp-ptab{on}" data-pfloor="{key}-{f}" aria-pressed="{str(i == 0).lower()}">{FLOOR[f]}'
                        f' <small>{num(len(fav), 0)}</small></button>')
            mask = ''.join(f'<polygon points="{pts(u["id"])}" fill="#000"/>' for u in mine)
            shapes = []
            for u in mine:
                if u['id'] in OFFER:
                    shapes.append(f'<a href="{href(u["id"])}" data-route="unit/{u["id"]}"><polygon class="hp-pu" data-unit="{u["id"]}" points="{pts(u["id"])}">'
                                  f'<title>{u["id"]} · {num(u["area"])} م²</title></polygon></a>')
                else:
                    shapes.append(f'<polygon class="hp-pn" points="{pts(u["id"])}"/>')
            if key == 'p3':
                for b in BACK:
                    if b in poly and byid[b]['f'] == f:
                        shapes.append(f'<polygon class="hp-pb" points="{pts(b)}"/>')
            rows = ''.join(
                f'<tr data-unit="{u["id"]}"><td><a href="{href(u["id"])}" data-route="unit/{u["id"]}"><bdi>{u["id"]}</bdi></a></td>'
                f'<td>{u.get("title") or u["cat"]}</td><td class="num">{num(u["area"])}</td>'
                f'<td class="num">{num(u["extra"]) if u.get("extra") else "—"}</td></tr>' for u in fav)
            table = ('<div class="hp-units-scroll"><table class="hp-units-table hp-ptable"><thead><tr><th>' + t('الوحدة', 'Unit') + '</th><th>'
                     + t('النشاط', 'Use') + '</th><th>' + t('المحمّلة م²', 'Loaded m²') + '</th><th>' + t('التراس الخارجي م²', 'Outdoor terrace m²')
                     + '</th></tr></thead><tbody>' + rows + '</tbody></table></div>') if fav else (
                     '<p class="hp-pempty">' + t('لا توجد وحدات متاحة للإيجار في هذا الدور ضمن المرحلة.', 'No units for lease on this floor in this phase.') + '</p>')
            panels.append(f'<div class="hp-ppanel{on}" data-ppanel="{key}-{f}"><figure class="hp-pmap">'
                          f'<svg viewBox="0 0 {VB[0]} {VB[1]}" role="img" aria-label="{FLOOR[f]}"><defs><mask id="m-{key}-{f}">'
                          f'<rect width="{VB[0]}" height="{VB[1]}" fill="#fff"/>{mask}</mask></defs>'
                          f'<image href="assets/plan-v15-{f}.webp" width="{VB[0]}" height="{VB[1]}"/>'
                          f'<rect width="{VB[0]}" height="{VB[1]}" fill="#f7f4ee" opacity=".78" mask="url(#m-{key}-{f})"/>{"".join(shapes)}</svg>'
                          f'</figure>{table}</div>')
        legend = ('<ul class="hp-plegend"><li><i class="a"></i>' + t('متاحة للإيجار، اضغط لفتح الوحدة', 'For lease, tap to open the unit') + '</li>'
                  '<li><i class="n"></i>' + t('ضمن المرحلة وغير معروضة للإيجار', 'In this phase, not offered for lease') + '</li>'
                  + ('<li><i class="b"></i>' + t('تنضم للمرحلة الثانية مع الوحدة الأمامية', 'Can join phase two with the front unit') + '</li>' if key == 'p3' else '')
                  + '</ul>')
        return (f'<section class="section hp-phase" id="{"phase2" if key == "p2" else "phase3"}"><div class="wrap"><span class="over">{over}</span>'
                f'<h2>{title}</h2><p class="hp-plead">{lead}</p>'
                '<ul class="hp-pstats">' + ''.join(f'<li><b>{a}</b><span>{b}</span></li>' for a, b in stats) + '</ul>'
                f'<div class="hp-ptabs" role="group">{"".join(tabs)}</div>{legend}{"".join(panels)}'
                + ''.join(f'<p class="hp-units-foot">{n}</p>' for n in notes) + '</div></section>')

    byid = {u['id']: u for u in units}
    p3 = {u['id'] for u in units if u['id'] not in p2}
    hyper = byid.get('B01')
    s2 = section('p2', p2, ['g', 'f1'], 'PHASE TWO · JUNE 2027',
                 t('المرحلة الثانية · تشغيل يونيو ٢٠٢٧', 'Phase two · opening June 2027'), t('يونيو ٢٠٢٧', 'June 2027'),
                 t('وحدات الأرضي المطلة على البلازا: المطاعم بتراساتها الخارجية، وواجهة الأزياء، والشوروم والبنوك، ومعها في الدور الأول الفود كورت والبنك والشوروم الدوبلكس.',
                   'The ground-floor units facing the plaza: restaurants with outdoor terraces, the fashion frontage, showrooms and banks, plus the first-floor food court and the duplex bank and showroom.'),
                 [], [t('التراسات الخارجية للمطاعم غير محسوبة في المساحة المحمّلة.', 'Restaurant outdoor terraces are not counted in the loaded area.')])
    s3 = section('p3', p3, ['b1', 'g', 'f1', 'f2'], 'PHASE THREE · DECEMBER 2027',
                 t('المرحلة الثالثة · تشغيل ديسمبر ٢٠٢٧', 'Phase three · opening December 2027'), t('ديسمبر ٢٠٢٧', 'December 2027'),
                 t('باقي المحلات التجارية بالكامل في الأدوار الأربعة، ومعها الهايبر ماركت في البدروم.',
                   'All remaining shops on the four levels, together with the basement hypermarket.'),
                 [(num(hyper['area']) + ' م²', t('الهايبر ماركت في البدروم', 'hypermarket in the basement'))] if hyper else [],
                 [t('الوحدات G25-27 وG29-31 وG33-35 وG37 خلف واجهة الأزياء تنضم للمرحلة الثانية إذا استأجرها مستأجر الوحدة الأمامية الملاصقة لها من الظهر.',
                    'Units G25-27, G29-31, G33-35 and G37 behind the fashion frontage join phase two if leased together with the front unit directly behind them.')])
    t('م²', 'm²')
    return s2, s3
