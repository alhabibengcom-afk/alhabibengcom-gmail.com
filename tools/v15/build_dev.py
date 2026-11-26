"""Replace the 'owner' section of the brand guide with the profile of
Al-Habeeb for Development & Investment LLC.

Usage: python3 build_dev.py SITE_DIR
Order of the story: retail (Al Habeeb Market chain), farms, then real estate
development, design and contracting. Facts come from the unit data, the leasing
guide and the Al-Habeeb Company Profile 2026. Adds the English strings to
i18n-en.js and the styles to pro.css.
"""
import json
import re
import sys

B = sys.argv[1]
EN = {}


def t(ar, en):
    EN[ar] = en
    return ar


FACTS = [
    (t('٤ فروع', '4 branches'), t('سلسلة الحبيب ماركت منذ ٢٠٠٨ في قنا والبحر الأحمر', 'Al Habeeb Market, since 2008, in Qena and the Red Sea')),
    (t('٢ مليون طائر', '2 million birds'), t('طاقة الدواجن السنوية في مزارع الحبيب', 'Annual poultry capacity at Al Habeeb Farms')),
    (t('٣٬٠٠٠ رأس', '3,000 head'), t('ماشية سنويًا في مزارع الحبيب', 'Of livestock a year at Al Habeeb Farms')),
    (t('التطوير العقاري', 'Real estate'), t('منذ ٢٠٢١ بمشروع هابينس بلازا', 'Since 2021, with Happiness Plaza')),
    (t('التصميم والمقاولات', 'Design & build'), t('منذ ٢٠٠٨ في قنا', 'Since 2008, in Qena')),
    (t('٢٠٬٠٠٠ م²', '20,000 m²'), t('أرض هابينس بلازا', 'Happiness Plaza site')),
]

LINES = [
    (t('٠١', '01'), t('التجزئة: سلسلة الحبيب ماركت', 'Retail: the Al Habeeb Market chain'),
     t('تأسست سلسلة الحبيب ماركت عام ٢٠٠٨، ولها ٤ فروع في محافظتي قنا والبحر الأحمر، منها الفرع الرئيسي في قنا وفرع الغردقة، وتطبيق للطلب أونلاين. وفي هابينس بلازا يشغّل الحبيب هايبر ماركت B01 بمساحة ٥٬٥٦٢ م² بأقسام الأغذية الطازجة والسلع سريعة التداول والمنسوجات والسلع غير الغذائية، إلى جانب الحبيب ستور وصيدلية الحبيب.',
       'Al Habeeb Market was founded in 2008 and has 4 branches in Qena and Red Sea governorates, including its main Qena branch and a Hurghada branch, plus an app for online orders. At Happiness Plaza, Al-Habeeb runs the 5,562 m² B01 hypermarket with fresh food, fast-moving goods, textiles and non-food departments, alongside Al Habeeb Store and Al Habeeb Pharmacy.'),
     'retail'),
    (t('٠٢', '02'), t('الزراعة: مزارع الحبيب', 'Agriculture: Al Habeeb Farms'),
     t('تأسست مزارع الحبيب عام ٢٠١٤ على الكيلو ١٧ طريق قنا سفاجا للإنتاج الحيواني والداجني: تسمين العجول، وإنتاج الدواجن، وتربية الأغنام. نمت طاقة الدواجن من ٥٠٠ ألف طائر سنويًا إلى ٢ مليون طائر في ٢٠٢٢، وطاقة الماشية ٣٬٠٠٠ رأس سنويًا.',
       'Founded in 2014 at kilometre 17 on the Qena–Safaga road for livestock and poultry production: calf fattening, poultry and sheep. Poultry capacity grew from 500,000 birds a year to 2 million in 2022; livestock capacity is 3,000 head a year.'),
     'farms'),
    (t('٠٣', '03'), t('التطوير العقاري', 'Real estate development'),
     t('بدأ في ٢٠٢١ بمشروع هابينس بلازا عند مدخل قنا الجديدة: أرض ٢٠٬٠٠٠ م²، وبلازا مشتركة ٤٬٠٠٠ م²، وثلاث مراحل هي الفندق والترفيه ثم المحلات ثم الهايبر ماركت.',
       'Launched in 2021 with Happiness Plaza at the entrance of New Qena: a 20,000 m² site, a 4,000 m² shared plaza and three phases: hotel and leisure, retail, then the hypermarket.'),
     'develop'),
    (t('٠٤', '04'), t('التصميم والمقاولات', 'Design and contracting'),
     t('من خلال الحبيب للهندسة والمقاولات منذ ٢٠٠٨: تصميم معماري وإنشائي وكهروميكانيكا، ومقاولات عامة وإدارة تنفيذ، ومصنع خرسانة سابقة الصب وورش معادن ونجارة.',
       'Through Al-Habeeb Engineering & Contracting since 2008: architectural, structural and MEP design, general contracting and construction management, a precast factory and metal and joinery workshops.'),
     'build'),
]

WHY = [
    (t('تاجر تجزئة قبل أن يكون مطوّرًا', 'A retailer before a developer'),
     t('تعمل المجموعة في التجزئة منذ ٢٠٠٨ من خلال ٤ فروع للحبيب ماركت، فتعرف ما يحتاجه المتجر من موقع وحركة وخدمات، وتخطط المول على هذا الأساس.',
       'The group has run Al Habeeb Market since 2008, with 4 branches today, so it knows what a store needs from its location, footfall and services, and plans the mall on that basis.')),
    (t('الهايبر ماركت مُشغَّل من المالك', 'An owner-operated anchor'),
     t('هايبر ماركت الحبيب في البدروم يشغّله المالك نفسه، ومعه الحبيب ستور وصيدلية الحبيب، فيجلب زيارات متكررة للمول من أول يوم.',
       'The owner runs Al Habeeb Hypermarket in the basement, together with Al Habeeb Store and Al Habeeb Pharmacy, bringing repeat visits to the mall from day one.')),
    (t('مطوّر يبني بنفسه', 'A developer that builds'),
     t('صمّمت المجموعة ونفّذت مبنى الفندق والترفيه في المرحلة الأولى: ٧٬٠٠٠ م² من بدروم وثلاثة أدوار، وفندق بوتيك من ١٤ غرفة. اكتمل التنفيذ والتشطيبات، والمرحلة الأولى قيد التشغيل والافتتاح الرسمي في ديسمبر ٢٠٢٦.',
       'The group designed and built the phase one hotel and leisure building: 7,000 m² over a basement and three levels, with a 14-room boutique hotel. Construction and finishes are complete; phase one is in operation, with the official opening in December 2026.')),
    (t('إدارة وتشغيل متخصصة', 'Specialist management'),
     t('تتولى JKFacilities إدارة المشروع وتشغيله وتنسيق التأجير ومزيج الأنشطة.',
       'JKFacilities manages and operates the project and coordinates leasing and the tenant mix.')),
]

PHASE1 = [('market-sign', t('الحبيب ماركت', 'Al Habeeb Market')),
          ('market-fresh', t('قسم الخضار والفاكهة', 'Fresh produce')),
          ('lakeside', t('الجزيرة على البحيرة', 'Lakeside island')),
          ('restaurant', t('المطعم والكافيه', 'Restaurant & café'))]

PROJECTS = [
    ('building', t('تطوير · تصميم · تنفيذ', 'Develop · Design · Build'), t('هابينس بلازا', 'Happiness Plaza'),
     t('مدخل قنا الجديدة، الحي الأول. فندق ومطاعم وكافيهات وهايبر ماركت وجيم وسبا ومنطقة أطفال وفود كورت وجزيرة على البحيرة حول بلازا مشتركة.',
       'Entrance of New Qena, District 1. A hotel, restaurants and cafés, a hypermarket, gym and spa, kids’ zone, food court and lakeside island around a shared plaza.'),
     [(t('٢٠٬٠٠٠ م²', '20,000 m²'), t('مساحة الأرض', 'Site area')), (t('٤٬٠٠٠ م²', '4,000 m²'), t('البلازا المشتركة', 'Shared plaza')),
      (t('٢٠٢١', '2021'), t('بدء التطوير', 'Development launched'))]),
    ('market-sign', t('تجزئة · تشغيل المالك', 'Retail · Owner-operated'), t('هايبر ماركت الحبيب', 'Al Habeeb Hypermarket'),
     t('الوحدة B01 في بدروم هابينس بلازا، بأقسام الأغذية الطازجة والسلع اليومية والمنسوجات والسلع غير الغذائية.',
       'Unit B01 in the Happiness Plaza basement, with fresh food, daily goods, textiles and non-food departments.'),
     [(t('٥٬٥٦٢ م²', '5,562 m²'), t('مساحة الوحدة', 'Unit area'))]),
]

PARTNERS = [
    (t('جهات حكومية', 'Government authorities'), [t('جهاز مدينة قنا الجديدة', 'New Qena City Authority'), t('جهاز مدينة أسوان الجديدة', 'New Aswan City Authority')]),
    (t('البنوك', 'Banks'), [t('البنك الأهلي المصري', 'National Bank of Egypt'), t('البنك الأهلي القطري', 'QNB')]),
    (t('التطوير والمقاولات', 'Development & contracting'), [t('AMA للتطوير العقاري', 'AMA Real Estate Development'), t('المقاولون العرب', 'The Arab Contractors'), t('أوراسكوم للإنشاءات', 'Orascom Construction'),
        t('مجموعة طلعت مصطفى', 'Talaat Moustafa Group'), t('البحر الأحمر الدولية', 'Red Sea Global'), t('معمار المرشدي', 'Memar Al-Morshedy')]),
    (t('مواد البناء', 'Building materials'), [t('سيمكس', 'CEMEX'), t('أسمنت النهضة', 'Al Nahda Cement'), t('حديد عز', 'Ezz Steel'), t('حديد المصريين', 'Egyptian Steel')]),
]

ICON = {
    'retail': '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 7h16l-1.5 11h-13z M8 7a4 4 0 0 1 8 0"/></svg>',
    'farms': '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 21V9 M12 13c-4 0-6-3-6-6 3 0 6 2 6 6z M12 11c4 0 6-3 6-6-3 0-6 2-6 6z M5 21h14"/></svg>',
    'develop': '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M3 21h18 M5 21V9l7-5 7 5v12 M9 21v-6h6v6"/></svg>',
    'build': '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M3 21h18 M6 21V5h4v16 M10 9h8l-2 4 M16 13v8"/></svg>',
}

h = []
h.append('<section class="section dev" id="owner"><div class="wrap">')
h.append('<header class="dev-head"><span class="over">AL-HABEEB FOR DEVELOPMENT &amp; INVESTMENT LLC</span>')
h.append('<h2>' + t('الحبيب للتنمية والاستثمار ش.م.م.', 'Al-Habeeb for Development & Investment LLC') + '</h2>')
h.append('<p class="dev-lead">' + t(
    'المالكة والمطوّرة لهابينس بلازا، وهي مجموعة من الشركات تعمل في تجارة التجزئة من خلال سلسلة الحبيب ماركت، والإنتاج الزراعي من خلال مزارع الحبيب، والتطوير العقاري والتصميم والمقاولات. تأسست المجموعة ونمت وتطورت في محافظة قنا.',
    'Owner and developer of Happiness Plaza. It is a group of companies working in retail through the Al Habeeb Market chain, agriculture through Al Habeeb Farms, and real estate development, design and contracting. The group was founded, grew and developed in Qena Governorate.') + '</p></header>')
h.append('<div class="dev-facts" role="list">')
for b, s in FACTS:
    h.append(f'<div role="listitem"><b>{b}</b><span>{s}</span></div>')
h.append('</div>')
h.append('<div class="dev-block"><span class="over">OUR BUSINESSES</span><h3>' + t('مجالات أعمال المجموعة', 'The group’s businesses') + '</h3>')
h.append('<div class="dev-model dev-lines">')
for n, title, body, ic in LINES:
    h.append(f'<article><span class="dev-ic">{ICON[ic]}</span><i>{n}</i><h4>{title}</h4><p>{body}</p></article>')
h.append('</div></div>')
h.append('<div class="dev-why"><div class="dev-why-copy"><span class="over">WHY IT MATTERS TO YOUR BRAND</span><h3>' + t('ماذا يعني ذلك لبراندك؟', 'What this means for your brand') + '</h3><ul>')
for title, body in WHY:
    h.append(f'<li><strong>{title}</strong><p>{body}</p></li>')
h.append('</ul></div><figure class="dev-phase"><div class="dev-phase-grid">')
for k, cap in PHASE1:
    h.append(f'<div><img loading="lazy" src="assets/developer/{k}.webp" alt="{cap}"><span>{cap}</span></div>')
h.append('</div><figcaption>' + t('تصميم الحبيب ماركت داخل المول، والمرحلة الأولى كما نُفّذت.', 'The Al Habeeb Market design inside the mall, and phase one as built.') + '</figcaption></figure></div>')
h.append('<div class="dev-block"><span class="over">SELECTED PROJECTS</span><h3>' + t('مشروعات مختارة', 'Selected projects') + '</h3><div class="dev-projects">')
for img, tag, name, body, figs in PROJECTS:
    h.append(f'<article><img loading="lazy" src="assets/developer/{img}.webp" alt="{name}"><div class="dev-proj-body"><small>{tag}</small><h4>{name}</h4><p>{body}</p>')
    if figs:
        h.append('<dl>' + ''.join(f'<div><dt>{v}</dt><dd>{l}</dd></div>' for v, l in figs) + '</dl>')
    h.append('</div></article>')
h.append('</div></div>')
h.append('<div class="dev-partners"><span class="over">PARTNERS IN SUCCESS</span><h3>' + t('نعمل مع أسماء يثق بها السوق', 'We work alongside names the market trusts') + '</h3><p>'
         + t('جهات حكومية وبنوك ومطورون ومقاولون وموردون تعاملت معهم المجموعة.', 'Government authorities, banks, developers, contractors and suppliers the group has worked with.') + '</p><div class="dev-pgroups">')
for label, names in PARTNERS:
    h.append(f'<div class="dev-pgroup"><h4>{label}</h4><ul>' + ''.join(f'<li>{n}</li>' for n in names) + '</ul></div>')
h.append('</div></div>')
h.append('<div class="dev-links p4links">')
for href, small, strong in [
        ('https://alhabeeb.org/', t('المالك والمطوّر', 'Owner and developer'), t('مجموعة شركات الحبيب', 'Al-Habeeb Group')),
        ('https://alhabeebmarket.com/', t('التجزئة', 'Retail'), t('الحبيب ماركت', 'Al Habeeb Market')),
        ('https://alhabeebfarms.com/', t('الإنتاج الحيواني والداجني', 'Livestock and poultry'), t('مزارع الحبيب', 'Al Habeeb Farms')),
        ('https://alhabeebconst.com/', t('التصميم والتنفيذ', 'Design and construction'), t('الحبيب للهندسة والمقاولات', 'Al-Habeeb Engineering & Contracting')),
        ('https://alhabeebconst.com/Virtual-Tour/', t('هابينس بلازا', 'Happiness Plaza'), t('الجولة الافتراضية', 'Virtual tour'))]:
    h.append(f'<a class="company-action" href="{href}" rel="noopener noreferrer"><span aria-hidden="true" class="company-glyph">↗</span><span><small>{small}</small><strong>{strong}</strong></span></a>')
h.append('</div></div></section>')
html = ''.join(h)

p = B + '/index.html'
s = open(p, encoding='utf-8').read()
i = s.index('id="owner"')
a = s.rfind('<section', 0, i)
b = s.index('</section>', i) + len('</section>')
s = s[:a] + html + s[b:]
open(p, 'w', encoding='utf-8').write(s)

p = B + '/i18n-en.js'
s = open(p, encoding='utf-8').read()
i = s.index('{'); j = s.rindex('}')
d = json.loads(s[i:j + 1])
d.update(EN)
open(p, 'w', encoding='utf-8').write(s[:i] + json.dumps(d, ensure_ascii=False, separators=(',', ':')) + s[j + 1:])

CSS = r'''
/* ---------- Developer profile (v15) ---------- */
.dev { background: var(--pro-green); color: #eef0e8; padding: clamp(64px, 9vw, 120px) 0; }
.dev .over { color: var(--pro-gold); }
.dev h2 { color: #fbf8f0; }
.dev h3 { color: #fbf8f0; font-size: clamp(22px, 2.4vw, 32px); line-height: 1.45; margin-bottom: 22px; }
.dev h4 { margin: 0; font-size: 20px; line-height: 1.5; color: #fbf8f0; }
.dev p { color: #d4dbd2; }
.dev-head { max-width: 880px; }
.dev-lead { margin-top: 18px; font-size: clamp(17px, 1.5vw, 20px); }
.dev-facts { display: grid; grid-template-columns: repeat(6, 1fr); margin-top: clamp(36px, 5vw, 60px); border-top: 1px solid rgba(255,255,255,.16); border-bottom: 1px solid rgba(255,255,255,.16); }
.dev-facts > div { padding: 22px 18px 26px; border-inline-end: 1px solid rgba(255,255,255,.12); }
.dev-facts > div:last-child { border-inline-end: 0; }
.dev-facts b { display: block; font: 400 clamp(20px, 1.9vw, 28px)/1.35 Edition, Arabic, serif; color: var(--pro-gold); }
.dev-facts span { display: block; margin-top: 6px; font-size: 13.5px; line-height: 1.6; color: #cfd6cd; }
.dev-block { margin-top: clamp(56px, 7vw, 96px); }
.dev-model { display: grid; grid-template-columns: repeat(4, 1fr); gap: 18px; }
.dev-model article { background: var(--pro-green-2); border: 1px solid rgba(255,255,255,.1); border-radius: 6px; padding: 26px 24px; }
.dev-ic { display: inline-grid; place-items: center; width: 44px; height: 44px; border-radius: 50%; border: 1px solid rgba(226,195,139,.5); margin-bottom: 14px; }
.dev-ic svg { width: 22px; height: 22px; fill: none; stroke: var(--pro-gold); stroke-width: 1.6; stroke-linecap: round; stroke-linejoin: round; }
.dev-model i { display: block; font: 700 12px/1 Arial, sans-serif; letter-spacing: .18em; color: var(--pro-gold); font-style: normal; margin-bottom: 10px; }
.dev-model p { margin-top: 8px; font-size: 15px; line-height: 1.85; }
.dev-why { display: grid; grid-template-columns: 1fr 1.05fr; gap: clamp(28px, 5vw, 72px); align-items: start; margin-top: clamp(56px, 7vw, 96px); }
.dev-why ul { list-style: none; margin: 0; padding: 0; }
.dev-why li { padding: 18px 0; border-top: 1px solid rgba(255,255,255,.14); }
.dev-why li strong { display: block; font-size: 18px; color: #fbf8f0; }
.dev-why li p { margin-top: 6px; font-size: 15px; line-height: 1.85; }
.dev-phase { margin: 0; }
.dev-phase-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; }
.dev-phase-grid > div { position: relative; overflow: hidden; border-radius: 4px; aspect-ratio: 4 / 3; }
.dev-phase-grid img { width: 100%; height: 100%; object-fit: cover; }
.dev-phase-grid span { position: absolute; inset-inline-start: 8px; bottom: 8px; padding: 2px 10px; font-size: 12.5px; color: #fff; background: rgba(12, 24, 20, .72); border-radius: 3px; }
.dev-phase figcaption { margin-top: 10px; font-size: 13.5px; color: #b9c3b8; }
.dev-projects { display: grid; grid-template-columns: repeat(2, 1fr); gap: 18px; }
.dev-projects article { background: #f4f1e9; color: var(--ink); border-radius: 6px; overflow: hidden; display: flex; flex-direction: column; }
.dev-projects img { width: 100%; aspect-ratio: 16 / 9; object-fit: cover; }
.dev-proj-body { padding: 18px 18px 20px; display: flex; flex-direction: column; flex: 1; }
.dev-proj-body small { font-size: 12px; color: var(--pro-gold-ink); font-weight: 700; }
.dev .dev-proj-body h4 { color: var(--ink); margin-top: 4px; }
.dev .dev-proj-body p { color: #4d5751; font-size: 14px; line-height: 1.8; margin-top: 6px; }
.dev-proj-body dl { display: flex; flex-wrap: wrap; gap: 6px 18px; margin: auto 0 0; padding-top: 14px; }
.dev-proj-body dt { font: 400 20px/1.3 Edition, Arabic, serif; color: var(--pro-green); white-space: nowrap; }
.dev-proj-body dd { margin: 0; font-size: 12px; color: #6a716c; }
.dev-partners { margin-top: clamp(56px, 7vw, 96px); }
.dev-pgroups { display: grid; grid-template-columns: repeat(4, 1fr); gap: 18px 24px; margin-top: 22px; }
.dev-pgroup h4 { font-size: 15px; color: var(--pro-gold); margin-bottom: 10px; }
.dev-partners ul { list-style: none; margin: 0; padding: 0; display: flex; flex-wrap: wrap; gap: 8px; }
.dev-partners li { padding: 8px 16px; border: 1px solid rgba(226,195,139,.45); border-radius: 999px; font-size: 14px; color: #f1ead9; }
.dev-links { display: flex; flex-wrap: wrap; gap: 12px; margin-top: 36px; }
.dev .company-action { color: #f4f1e9; border-color: rgba(255,255,255,.28); }
.dev .company-action small { color: #b9c2b7; }
@media (max-width: 1100px) {
  .dev-facts { grid-template-columns: repeat(3, 1fr); }
  .dev-facts > div:nth-child(3n) { border-inline-end: 0; }
  .dev-facts > div:nth-child(-n+3) { border-bottom: 1px solid rgba(255,255,255,.12); }
  .dev-model, .dev-projects, .dev-pgroups { grid-template-columns: 1fr 1fr; }
}
@media (max-width: 760px) {
  .dev-facts { grid-template-columns: 1fr 1fr; }
  .dev-facts > div { border-inline-end: 0; border-bottom: 1px solid rgba(255,255,255,.12); padding: 18px 12px 20px 0; }
  .dev-facts > div:nth-child(odd) { border-inline-end: 1px solid rgba(255,255,255,.12); padding-inline-end: 12px; }
  .dev-facts > div:nth-child(even) { padding-inline-start: 14px; }
  .dev-model, .dev-why, .dev-projects, .dev-pgroups { grid-template-columns: 1fr; }
}
'''
p = B + '/pro.css'
s = open(p, encoding='utf-8').read()
s = re.sub(r'\n/\* ---------- Developer profile \(v15\) ---------- \*/.*', '', s, flags=re.S)
open(p, 'w', encoding='utf-8').write(s.rstrip() + '\n' + CSS)
print('section', len(html), 'strings', len(EN))
