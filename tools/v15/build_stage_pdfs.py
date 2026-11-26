# Rebuild the three stage leasing sheets (Stage 1/2/3) with GROSS (loaded) areas from the Drive sheet.
# Same structure and wording as the originals; areas = gross; totals recomputed. Usage: build_stage_pdfs.py <site.js> <out dir>
import json, sys, html
SITE, OUT = sys.argv[1:3]
s = open(SITE, encoding='utf-8').read()
U, _ = json.JSONDecoder().raw_decode(s[s.index('const UNITS=') + len('const UNITS='):])
G = {u['id']: u['area'] for u in U}
fmt = lambda x: f'{x:,.2f}'
COL = {'مطاعم وكافيهات': '#1f7a6b', 'شوروم': '#4f86c6', 'بنوك وخدمات مالية': '#8fa6c8', 'أزياء': '#e57a8a', 'فود كورت': '#d9a53a',
       'اتصالات': '#20a9b8', 'تجزئة': '#303090', 'ترفيه': '#b050a0', 'إكسسوارات': '#f05a28', 'لايف ستايل': '#3d5a9e', 'صالون وبيوتي': '#c06aa0',
       'محلات صغيرة (أنشطة سريعة)': '#f0b000', 'كيدز إريا / حضانة': '#f2a46b', 'موبايلات': '#7e57c2'}
FLOOR = {'G': 'الأرضي', 'F': 'الأول', 'S': 'التاني', 'B': 'البدروم'}
DATES = [('المرحلة الأولى', '30/6/2027'), ('المرحلة الثانية', '31/12/2027'), ('المرحلة الثالثة', '30/6/2028')]
TERR = [('G06', 111.71), ('G08', 65.36), ('G09', 66.22), ('G11', 68.21), ('G39', 108.08), ('G40', 126.56), ('G41', 82.72)]
GROSS_NOTE = 'كل المساحات المذكورة مساحات إجمالية (Gross) بالمتر المربع، وهي المساحة المحمّلة اللي بيتحسب عليها الإيجار.'

STAGES = [
 dict(no=1, name='المرحلة الأولى', file='Happiness_Plaza_Stage1_Leasing',
      desc='الأرضي والأول حوالين البلازا الداخلية: مطاعم بتراسات مكشوفة، أزياء على الواجهة، بنوك وشوروم دوبلكس، اتصالات على المدخل الرئيسي، والفود كورت.',
      handover=('1/1/2027', '30/6/2027'), deadline='مارس 2027', terraces=True,
      units=[('G01','اتصالات','على المدخل الرئيسي'),('G04','شوروم','دوبلكس مع F05-07'),('G05','بنوك وخدمات مالية','دوبلكس مع F08'),
             ('G06','مطاعم وكافيهات','على البلازا + تراس 111.71 م²'),('G08','مطاعم وكافيهات','على البلازا + تراس 65.36 م²'),('G09','مطاعم وكافيهات','على البلازا + تراس 66.22 م²'),
             ('G11','مطاعم وكافيهات','على البلازا + تراس 68.21 م²'),('G26-28','أزياء','واجهة على البلازا'),('G30-32','أزياء','واجهة على البلازا'),('G34-36','أزياء','واجهة على البلازا'),
             ('G38','أزياء','واجهة على البلازا'),('G39','مطاعم وكافيهات','على البلازا + تراس 108.08 م²'),('G40','مطاعم وكافيهات','على البلازا + تراس 126.56 م²'),
             ('G41','مطاعم وكافيهات','على البلازا + تراس 82.72 م²'),('G42','مطاعم وكافيهات','على البلازا'),('G42-1','مطاعم وكافيهات','على البلازا'),
             ('G44','شوروم','دوبلكس مع F46-48'),('G49','اتصالات','جنب المدخل الرئيسي'),
             ('F05-07','شوروم','دوبلكس مع G04'),('F08','بنوك وخدمات مالية','دوبلكس مع G05'),('F46-48','شوروم','دوبلكس مع G44'),
             ('F36','فود كورت','قعدة فود كورت مشتركة'),('F37','فود كورت','قعدة فود كورت مشتركة'),('F38','فود كورت','بتفويض المالك'),('F39','فود كورت','بتفويض المالك'),
             ('F40','فود كورت','بتفويض المالك'),('F41','فود كورت','بتفويض المالك'),('F42','فود كورت','بتفويض المالك'),('F42-1','فود كورت','بتفويض المالك'),
             ('F43','فود كورت','بتفويض المالك'),('F44','مطاعم وكافيهات','بتفويض المالك – فود كورت')],
      same=[('الحبيب ستور','G16-21 + F16-20','معرض على دورين – تشغيل الحبيب'),('صيدلية الحبيب','G46','تشغيل الحبيب'),('صيدلية / طبي','G02','وحدة مملوكة – بتفتح مع المرحلة'),
            ('اتصالات','G01-1','وحدة مملوكة – بتفتح مع المرحلة'),('مطاعم على البلازا','G13 ، G15','وحدات مملوكة – بتفتح مع المرحلة')],
      notes=[GROSS_NOTE, 'الوحدات الدوبلكس (أرضي + أول بسلم داخلي) تتعرض على نفس المستأجر.', 'وحدات المالك في الفود كورت تتعرض بعد توقيع المالك على تفويض الحبيب.']),
 dict(no=2, name='المرحلة الثانية', file='Happiness_Plaza_Stage2_Leasing',
      desc='استكمال الأرضي والأول، والدور الثاني بالكامل: ترفيه، مطاعم وكافيهات، بلوكات تجزئة كبيرة مناسبة للبراندات، وإكسسوارات ولايف ستايل.',
      handover=('1/7/2027', '31/12/2027'), deadline='سبتمبر 2027', terraces=False,
      units=[('G07-12','إكسسوارات',''),('G12-14','إكسسوارات',''),('G25-27','أزياء','بلوك الأزياء'),('G29-31','أزياء','بلوك الأزياء'),('G33-35','أزياء','بلوك الأزياء'),
             ('G37','أزياء','بلوك الأزياء'),('G43-1','محلات صغيرة (أنشطة سريعة)',''),('G44-1','لايف ستايل',''),
             ('F01','إكسسوارات',''),('F01-1','إكسسوارات',''),('F02','إكسسوارات',''),('F02-1','إكسسوارات',''),('F03','إكسسوارات',''),('F09-11','أزياء',''),('F12-15','أزياء',''),
             ('F45-1','محلات صغيرة (أنشطة سريعة)',''),('F46','صالون وبيوتي',''),('F56-57','لايف ستايل',''),('F58-61','مطاعم وكافيهات','على واجهة الـ void'),
             ('S04','تجزئة',''),('S07','ترفيه',''),('S08','ترفيه',''),('S10-13','مطاعم وكافيهات',''),('S14-18','تجزئة',''),('S19-22','تجزئة',''),('S23-27','تجزئة',''),
             ('S28','تجزئة',''),('S29','تجزئة',''),('S30-34','تجزئة',''),('S35-37','تجزئة',''),('S38-39','تجزئة',''),('S40','تجزئة',''),('S41','تجزئة',''),
             ('S46','مطاعم وكافيهات',''),('S47','مطاعم وكافيهات','')],
      same=[('باقي وحدات المرحلة','67 وحدة','وحدات مملوكة للغير أو معروضة للبيع – بتفتح في نفس الميعاد'),('صالون وبيوتي','F45','وحدة مملوكة جنب F46')],
      notes=[GROSS_NOTE, 'الوحدات المضمومة بتتعرض كوحدة واحدة بكودها.', 'تحديد نشاط كل وحدة ملزم حسب الزوننج المعتمد للمول.']),
 dict(no=3, name='المرحلة الثالثة', file='Happiness_Plaza_Stage3_Leasing',
      desc='دور البدروم مع افتتاح الحبيب ماركت (هايبر ماركت 5,562.28 م²): وحدات قدام مدخل الهايبر مباشرة، وأعلى كثافة زيارات يومية في المول.',
      handover=('1/1/2028', '30/6/2028'), deadline='مارس 2028', terraces=False,
      units=[('B02','إكسسوارات','قدام مدخل الهايبر'),('B03','موبايلات','قدام مدخل الهايبر'),('B04','كيدز إريا / حضانة','جنب منطقة التزلج')],
      same=[('الحبيب ماركت – هايبر ماركت','B01','5,562.28 م² – تشغيل الحبيب ومُحرّك الحركة الرئيسي للدور'),('مسجد + منطقة تزلج','B05','خدمات للزوار في نفس الدور'),('جراج على مستويين','البدروم','مباشر على الدور')],
      notes=[GROSS_NOTE, 'الوحدات المضمومة بتتعرض كوحدة واحدة بكودها.', 'تحديد نشاط كل وحدة ملزم حسب الزوننج المعتمد للمول.']),
]
CSS = open(OUT + '/stage.css', encoding='utf-8').read()

def bars(rows, color=None):
    mx = max(a for _, _, a in rows) or 1
    return ''.join(f'<div class="bar"><span class="bl"><i style="background:{color or COL.get(k, "#1f5f6b")}"></i>{html.escape(k)}</span>'
                   f'<span class="bt"><b style="width:{a / mx * 100:.1f}%;background:{color or COL.get(k, "#1f5f6b")}"></b></span>'
                   f'<span class="bv">{n} وحدة · {fmt(a)} م²</span></div>' for k, n, a in rows)

for st in STAGES:
    rows = [(c, act, note, G[c]) for c, act, note in st['units']]
    total = sum(r[3] for r in rows); n = len(rows)
    acts = {}
    for c, act, note, a in rows: acts.setdefault(act, [0, 0.0]); acts[act][0] += 1; acts[act][1] += a
    acts = sorted(((k, v[0], v[1]) for k, v in acts.items()), key=lambda x: -x[2])
    floors = {}
    for c, act, note, a in rows: floors.setdefault(c[0], [0, 0.0]); floors[c[0]][0] += 1; floors[c[0]][1] += a
    forder = [f for f in 'BGFS' if f in floors]
    terr = sum(a for _, a in TERR) if st['terraces'] else 0
    stats = [(str(n), 'وحدة متاحة'), (fmt(total), 'م² مساحة إجمالية')] + ([(fmt(terr), 'م² تراسات خارجية')] if terr else [])
    h0, h1 = st['handover']; op = DATES[st['no'] - 1][1]; nn = f'0{st["no"]}'
    head = lambda: f'<header><span>هابينس بلازا · {st["name"]}</span><span class="en">HAPPINESS PLAZA · STAGE {nn}</span></header>'
    foot = lambda p: f'<footer><span>Happiness Plaza · {st["name"]} · بيان وحدات للإيجار</span><span>الحبيب للتنمية والاستثمار · صفحة {p}</span></footer>'
    cover = (f'<section class="pg cover"><div class="band"></div><div class="brand"><b>HAPPINESS PLAZA</b><span>هابينس بلازا · قنا الجديدة</span></div>'
             f'<p class="stage">STAGE {nn} · LEASING</p><h1>{st["name"]}<br>الوحدات المتاحة للإيجار</h1><p class="desc">{st["desc"]}</p>'
             '<div class="cstats">' + ''.join(f'<div><b>{a}</b><span>{b}</span></div>' for a, b in stats + [(op, 'موعد الافتتاح')]) + '</div>'
             f'<p class="pill">تسليم الوحدات للتجهيز: {h0} ← {h1}</p>'
             '<div class="cfoot"><span>الحبيب للتنمية والاستثمار · المالك والمطوّر</span><span>نوفمبر 2026</span></div></section>')
    tl = ''.join(f'<div class="{"on" if i == st["no"] - 1 else ""}"><b>{a}</b><span>افتتاح {d}</span></div>' for i, (a, d) in enumerate(DATES))
    ov = (f'<section class="pg">{head()}<div class="body"><h2>نظرة عامة</h2><p class="box">{st["desc"]}</p>'
          '<div class="stats">' + ''.join(f'<div><b>{a}</b><span>{b}</span></div>' for a, b in [(str(n), 'وحدة متاحة للإيجار'), (fmt(total), 'م² مساحة إجمالية')]
                                          + ([(fmt(terr), 'م² تراسات خارجية (7)')] if terr else []) + [(str(len(acts)), 'نشاط تجاري')]) + '</div>'
          f'<h2>الجدول الزمني للمشروع</h2><div class="tl">{tl}</div>'
          f'<h2>توزيع الأنشطة</h2>{bars(acts)}'
          f'<h2>التوزيع على الأدوار</h2>{bars([(FLOOR[f], floors[f][0], floors[f][1]) for f in forder], "#1b5563")}'
          f'<div class="note"><b>الجدول الزمني للتجهيز</b><ul><li>تسليم الوحدات للمستأجرين للتجهيز: من {h0} إلى {h1}.</li><li>الافتتاح الرسمي للمرحلة: {op}.</li>'
          f'<li>آخر موعد مقترح لتوقيع العقود لضمان الافتتاح: {st["deadline"]}.</li></ul></div></div>{foot(2)}</section>')
    trs = ''
    for f in forder:
        trs += f'<tr class="grp"><td colspan="4">الدور {FLOOR[f]} — {floors[f][0]} وحدة · {fmt(floors[f][1])} م²</td></tr>'
        trs += ''.join(f'<tr><td class="c">{c}</td><td><i style="background:{COL.get(act, "#1f5f6b")}"></i>{html.escape(act)}</td><td class="n">{fmt(a)}</td><td class="m">{html.escape(note)}</td></tr>'
                       for c, act, note, a in rows if c[0] == f)
    trs += f'<tr class="tot"><td colspan="2">الإجمالي ({n} وحدة)</td><td class="n">{fmt(total)}</td><td></td></tr>'
    tbl = f'<h2>بيان الوحدات المتاحة للإيجار</h2><table class="t"><thead><tr><th>الوحدة</th><th>النشاط</th><th>المساحة<br>الإجمالية م²</th><th>ملاحظات</th></tr></thead><tbody>{trs}</tbody></table>'
    extra = ''
    if st['terraces']:
        extra += ('<h2>التراسات الخارجية على البلازا</h2><table class="t s"><thead><tr><th>الكود</th><th>الوصف</th><th>المساحة م²</th></tr></thead><tbody>'
                  + ''.join(f'<tr><td class="c">{c}-OUT</td><td>تراس مكشوف تابع للوحدة {c}</td><td class="n">{fmt(a)}</td></tr>' for c, a in TERR)
                  + f'<tr class="tot"><td colspan="2">الإجمالي</td><td class="n">{fmt(terr)}</td></tr></tbody></table>')
    extra += ('<h2>وحدات بتفتح في نفس المرحلة (للعلم)</h2><table class="t s"><thead><tr><th>النشاط</th><th>الوحدة</th><th>ملاحظات</th></tr></thead><tbody>'
              + ''.join(f'<tr><td><b>{html.escape(a)}</b></td><td class="c">{b}</td><td class="m">{html.escape(c)}</td></tr>' for a, b, c in st['same']) + '</tbody></table>')
    extra += '<div class="note"><b>ملاحظات الطرح</b><ul>' + ''.join(f'<li>{x}</li>' for x in st['notes']) + '<li>أسعار الإيجار وشروط التعاقد تتعتمد من الحبيب للتنمية والاستثمار قبل أي عرض نهائي، والتوافر النهائي والحجز من خلال إدارة التأجير.</li></ul></div>'
    lst = f'<section class="pg flow">{head()}<div class="body">{tbl}{extra}</div></section>'
    doc = f'<!doctype html><html lang="ar" dir="rtl"><head><meta charset="utf-8"><title>{st["file"]}</title><style>{CSS}</style></head><body>{cover}{ov}{lst}</body></html>'
    open(f'{OUT}/{st["file"]}.html', 'w', encoding='utf-8').write(doc)
    print(st['file'], n, 'units', fmt(total), 'm² gross', ('terraces ' + fmt(terr)) if terr else '', [(k, c, fmt(a)) for k, c, a in acts])
