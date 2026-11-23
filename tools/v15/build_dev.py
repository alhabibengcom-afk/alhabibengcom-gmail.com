"""Replace the 'owner' section of the brand guide with a full developer profile.

Usage: python3 build_dev.py SITE_DIR
Facts come from the Al-Habeeb Company Profile 2026 (AR/EN, v2). Adds the English
strings to i18n-en.js and the styles to pro.css.
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
    (t('٢٠٠٨', '2008'), t('تأسست المجموعة في قنا', 'Group founded in Qena')),
    (t('٣', '3'), t('مجالات عمل متكاملة: تصميم وتنفيذ وتطوير', 'Integrated business lines: design, build, develop')),
    (t('٣', '3'), t('وحدات إنتاج داخلية: خرسانة سابقة الصب ومعادن ونجارة', 'In-house production units: precast, metal, joinery')),
    (t('٢٠٬٠٠٠ م²', '20,000 m²'), t('أرض هابينس بلازا، المشروع الرئيسي للمجموعة', 'Happiness Plaza site, the group’s flagship development')),
    (t('٧', '7'), t('قطاعات: تجاري وفندقي وترفيهي وإداري وطبي وسكني وديني', 'Sectors: retail, hospitality, leisure, workplace, healthcare, residential, religious')),
    ('LOD 400', t('نماذج BIM حتى مستوى التنفيذ', 'BIM models developed to construction level')),
]

MODEL = [
    (t('٠١', '01'), t('تصميم', 'Design'),
     t('معماري وإنشائي وكهروميكانيكا، ورسومات تنفيذية، ونماذج BIM حتى مستوى LOD 400، ومواصفات وحصر كميات.',
       'Architecture, structure and MEP; construction drawings; LOD 300 and LOD 400 models; specifications and quantity take-off.')),
    (t('٠٢', '02'), t('تنفيذ', 'Build'),
     t('مقاولات عامة وإدارة تنفيذ وإشراف موقعي، تدعمها ورش الخرسانة سابقة الصب والمعادن والنجارة.',
       'General contracting, construction management and site supervision, supported by our own precast, metal and joinery workshops.')),
    (t('٠٣', '03'), t('تطوير', 'Develop'),
     t('دخلت المجموعة التطوير العقاري في ٢٠٢١ بمشروع هابينس بلازا عند مدخل قنا الجديدة.',
       'The group entered real estate development in 2021 with Happiness Plaza at the entrance of New Qena.')),
]

WHY = [
    (t('مطوّر ينفّذ بنفسه', 'A developer that builds'),
     t('صمّمت المجموعة ونفّذت مبنى الفندق والترفيه في المرحلة الأولى: ٧٬٠٠٠ م² من بدروم وثلاثة أدوار، وفندق بوتيك من ١٤ غرفة، ومقر الحبيب. اكتمل التنفيذ والتشطيبات، والافتتاح مقرر في ديسمبر ٢٠٢٦.',
       'The group designed and built the phase one hotel and leisure building: 7,000 m² over a basement and three levels, a 14-room boutique hotel and Al-Habeeb’s headquarters. Construction and finishes are complete; opening is planned for December 2026.')),
    (t('فريق واحد من الفكرة إلى التسليم', 'One team from idea to handover'),
     t('يُنسَّق المعماري والإنشائي والكهروميكانيكا قبل بدء التنفيذ، فتقل التعديلات في الموقع ويُسلَّم كل جزء بالمواصفة المتفق عليها.',
       'Architecture, structure and MEP are coordinated before work starts, so fewer changes reach site and every package is delivered to the agreed specification.')),
    (t('ورش إنتاج داخلية', 'In-house workshops'),
     t('مصنع الخرسانة سابقة الصب وورش المعادن والنجارة تمنح المجموعة تحكمًا مباشرًا في الجودة والتكلفة والوقت.',
       'The precast factory and the metal and joinery workshops give the group direct control over quality, cost and time.')),
    (t('الحبيب يشغّل داخل المول', 'Al-Habeeb operates inside the mall'),
     t('يشغّل الحبيب بنفسه هايبر ماركت B01 بمساحة ٥٬٥٦٢ م² والحبيب ستور وصيدلية الحبيب. وتتولى JKFacilities إدارة المشروع وتشغيله وتنسيق التأجير.',
       'Al-Habeeb runs the 5,562 m² B01 hypermarket, Al Habeeb Store and Al Habeeb Pharmacy itself. JKFacilities manages and operates the project and coordinates leasing.')),
]

PHASE1 = [('lakeside', t('الجزيرة على البحيرة', 'Lakeside island')),
          ('restaurant', t('المطعم والكافيه', 'Restaurant & café')),
          ('gym', t('الجيم', 'Gym')),
          ('gallery', t('ممر المحلات', 'Retail gallery'))]

PROJECTS = [
    ('building', t('تطوير · تصميم · تنفيذ', 'Develop · Design · Build'), t('هابينس بلازا', 'Happiness Plaza'),
     t('مدخل قنا الجديدة، الحي الأول. فندق ومطاعم وكافيهات وهايبر ماركت وجيم وسبا ومنطقة أطفال وفود كورت وجزيرة على البحيرة حول بلازا مشتركة.',
       'Entrance of New Qena, District 1. A hotel, restaurants and cafés, a hypermarket, gym and spa, kids’ zone, food court and lakeside island around a shared plaza.'),
     [(t('٢٠٬٠٠٠ م²', '20,000 m²'), t('مساحة الأرض', 'Site area')), (t('٤٬٠٠٠ م²', '4,000 m²'), t('البلازا المشتركة', 'Shared plaza')),
      (t('٢٠٢١', '2021'), t('بدء التطوير', 'Development launched'))]),
    ('masa', t('تصميم · تنفيذ', 'Design · Build'), t('الماسة مول', 'Al Masa Mall'),
     t('وحدات تجارية بواجهات حديثة وتفاصيل معمارية مدروسة، مخططة لتعظيم العائد الاستثماري وتجربة الزائر.',
       'Retail units with modern shopfronts and careful architectural detailing, planned to maximise investment return and the visitor experience.'),
     [(t('٣٬٢٠٠ م²', '3,200 m²'), t('مساحة مبنية', 'Built-up area'))]),
    ('infinity', t('تصميم · تنفيذ', 'Design · Build'), t('إنفينيتي مول', 'Infinity Mall'),
     t('مشروع متعدد الاستخدامات بفكرة معمارية تدعم التوسع التجاري ونمو الاستثمار على المدى الطويل.',
       'A mixed-use scheme with an architectural concept designed to support commercial expansion and long-term investment growth.'),
     [(t('٢٠٬٠٠٠ م²', '20,000 m²'), t('إجمالي المساحة', 'Total area'))]),
    ('homes', t('تصميم · تنفيذ', 'Design · Build'), t('فيلات وعمارات سكنية', 'Villas and residences'),
     t('في قنا الجديدة وأسوان الجديدة، بواجهات كلاسيكية ومعاصرة تُنفَّذ كما رُسمت.',
       'In New Qena and New Aswan, with classical and contemporary façades built exactly as drawn.'), []),
]

PARTNERS = [t('البنك الأهلي المصري', 'National Bank of Egypt'), t('المقاولون العرب', 'The Arab Contractors'),
            t('أوراسكوم للإنشاءات', 'Orascom Construction'), t('مجموعة طلعت مصطفى', 'Talaat Moustafa Group'),
            t('البحر الأحمر الدولية', 'Red Sea Global'), t('معمار المرشدي', 'Memar Al-Morshedy'),
            t('سيمكس', 'CEMEX'), t('أسمنت النهضة', 'Al Nahda Cement'), t('حديد عز', 'Ezz Steel'),
            t('حديد المصريين', 'Egyptian Steel')]

h = []
h.append('<section class="section dev" id="owner"><div class="wrap">')
h.append('<header class="dev-head"><span class="over">ALHABEEB GROUP · EST. 2008</span>')
h.append('<h2>' + t('شركة الحبيب للتنمية والاستثمار', 'Al-Habeeb for Development & Investment') + '</h2>')
h.append('<p class="dev-lead">' + t(
    'المالكة والمطوّرة لهابينس بلازا. تنتمي إلى مجموعة الحبيب التي تأسست في قنا عام ٢٠٠٨، وتعمل في التصميم الهندسي والمقاولات والتطوير العقاري، إلى جانب تجارة التجزئة من خلال الحبيب ماركت والاستثمار الزراعي.',
    'Owner and developer of Happiness Plaza. It is part of the Al-Habeeb group, founded in Qena in 2008, which works across engineering design, contracting and real estate development, as well as retail through Al Habeeb Market and agricultural investment.') + '</p>')
h.append('<p class="dev-motto">' + t('نبني اليوم لمستقبل أفضل.', 'Building today for a better tomorrow.') + '</p></header>')
h.append('<div class="dev-facts" role="list">')
for b, s in FACTS:
    h.append(f'<div role="listitem"><b>{b}</b><span>{s}</span></div>')
h.append('</div>')
h.append('<div class="dev-block"><span class="over">DESIGN · BUILD · DEVELOP</span><h3>' + t('من أول رسم حتى التسليم، تحت سقف واحد', 'From first sketch to handover, under one roof') + '</h3>')
h.append('<div class="dev-model">')
for n, title, body in MODEL:
    h.append(f'<article><i>{n}</i><h4>{title}</h4><p>{body}</p></article>')
h.append('</div></div>')
h.append('<div class="dev-why"><div class="dev-why-copy"><span class="over">WHY IT MATTERS TO YOUR BRAND</span><h3>' + t('ماذا يعني ذلك لبراندك؟', 'What this means for your brand') + '</h3><ul>')
for title, body in WHY:
    h.append(f'<li><strong>{title}</strong><p>{body}</p></li>')
h.append('</ul></div><figure class="dev-phase"><div class="dev-phase-grid">')
for k, cap in PHASE1:
    h.append(f'<div><img loading="lazy" src="assets/developer/{k}.webp" alt="{cap}"><span>{cap}</span></div>')
h.append('</div><figcaption>' + t('المرحلة الأولى كما نُفّذت: مبنى الفندق والترفيه بتصميم وتنفيذ الحبيب.', 'Phase one as built: the hotel and leisure building, designed and built by Al-Habeeb.') + '</figcaption></figure></div>')
h.append('<div class="dev-block"><span class="over">SELECTED PROJECTS</span><h3>' + t('مشروعات مختارة', 'Selected projects') + '</h3><div class="dev-projects">')
for img, tag, name, body, figs in PROJECTS:
    h.append(f'<article><img loading="lazy" src="assets/developer/{img}.webp" alt="{name}"><div class="dev-proj-body"><small>{tag}</small><h4>{name}</h4><p>{body}</p>')
    if figs:
        h.append('<dl>' + ''.join(f'<div><dt>{v}</dt><dd>{l}</dd></div>' for v, l in figs) + '</dl>')
    h.append('</div></article>')
h.append('</div></div>')
h.append('<div class="dev-vm"><div><span class="over">VISION</span><p>' + t('أن نكون شركة رائدة في البناء والتشييد، نطوّر الابتكار والاستدامة باستمرار.', 'To be a leading company in construction and building, continuously advancing innovation and sustainability.') + '</p></div>')
h.append('<div><span class="over">MISSION</span><p>' + t('تقديم حلول هندسية متكاملة تلبي احتياجات العملاء بأعلى جودة وكفاءة، وبشفافية واحترافية في كل مرحلة.', 'To deliver integrated engineering solutions that meet client needs with the highest quality and efficiency, and with transparency and professionalism at every stage.') + '</p></div>')
h.append('<div><span class="over">VALUES</span><p>' + t('الجودة · الابتكار · الاستدامة · النزاهة', 'Quality · Innovation · Sustainability · Integrity') + '</p></div></div>')
h.append('<div class="dev-partners"><span class="over">PARTNERS IN SUCCESS</span><h3>' + t('نعمل مع أسماء يثق بها السوق', 'We work alongside names the market trusts') + '</h3><p>'
         + t('بنوك ومطورون ومقاولون وموردو مواد عملت معهم المجموعة.', 'Banks, developers, contractors and material suppliers the group has worked with.') + '</p><ul>')
h.append(''.join(f'<li>{p}</li>' for p in PARTNERS) + '</ul></div>')
h.append('<div class="dev-links p4links">')
for href, small, strong in [
        ('https://alhabeeb.org/', t('المالك والمطوّر', 'Owner and developer'), t('مجموعة شركات الحبيب', 'Al-Habeeb Group')),
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
.dev-head { max-width: 860px; }
.dev-lead { margin-top: 18px; font-size: clamp(17px, 1.5vw, 20px); }
.dev-motto { margin-top: 14px; font: 400 clamp(20px, 2vw, 26px)/1.5 Edition, Arabic, serif; color: var(--pro-gold) !important; }
.dev-facts { display: grid; grid-template-columns: repeat(6, 1fr); margin-top: clamp(36px, 5vw, 60px); border-top: 1px solid rgba(255,255,255,.16); border-bottom: 1px solid rgba(255,255,255,.16); }
.dev-facts > div { padding: 22px 18px 26px; border-inline-end: 1px solid rgba(255,255,255,.12); }
.dev-facts > div:last-child { border-inline-end: 0; }
.dev-facts b { display: block; font: 400 clamp(24px, 2.4vw, 34px)/1.3 Edition, Arabic, serif; color: var(--pro-gold); white-space: nowrap; }
.dev-facts span { display: block; margin-top: 6px; font-size: 13.5px; line-height: 1.6; color: #cfd6cd; }
.dev-block { margin-top: clamp(56px, 7vw, 96px); }
.dev-model { display: grid; grid-template-columns: repeat(3, 1fr); gap: 18px; }
.dev-model article { background: var(--pro-green-2); border: 1px solid rgba(255,255,255,.1); border-radius: 6px; padding: 26px 24px; }
.dev-model i { display: block; font: 700 12px/1 Arial, sans-serif; letter-spacing: .18em; color: var(--pro-gold); font-style: normal; margin-bottom: 14px; }
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
.dev-projects { display: grid; grid-template-columns: repeat(4, 1fr); gap: 18px; }
.dev-projects article { background: #f4f1e9; color: var(--ink); border-radius: 6px; overflow: hidden; display: flex; flex-direction: column; }
.dev-projects img { width: 100%; aspect-ratio: 4 / 3; object-fit: cover; }
.dev-proj-body { padding: 18px 18px 20px; display: flex; flex-direction: column; flex: 1; }
.dev-proj-body small { font-size: 12px; color: var(--pro-gold-ink); font-weight: 700; }
.dev .dev-proj-body h4 { color: var(--ink); margin-top: 4px; }
.dev .dev-proj-body p { color: #4d5751; font-size: 14px; line-height: 1.8; margin-top: 6px; }
.dev-proj-body dl { display: flex; flex-wrap: wrap; gap: 6px 18px; margin: auto 0 0; padding-top: 14px; }
.dev-proj-body dt { font: 400 20px/1.3 Edition, Arabic, serif; color: var(--pro-green); white-space: nowrap; }
.dev-proj-body dd { margin: 0; font-size: 12px; color: #6a716c; }
.dev-vm { display: grid; grid-template-columns: repeat(3, 1fr); gap: 18px; margin-top: clamp(56px, 7vw, 96px); }
.dev-vm > div { border-top: 2px solid var(--pro-gold); padding-top: 16px; }
.dev-vm p { font-size: 16px; color: #e7ebe3; }
.dev-partners { margin-top: clamp(56px, 7vw, 96px); }
.dev-partners ul { list-style: none; margin: 18px 0 0; padding: 0; display: flex; flex-wrap: wrap; gap: 10px; }
.dev-partners li { padding: 8px 16px; border: 1px solid rgba(226,195,139,.45); border-radius: 999px; font-size: 14px; color: #f1ead9; }
.dev-links { display: flex; flex-wrap: wrap; gap: 12px; margin-top: 36px; }
.dev .company-action { color: #f4f1e9; border-color: rgba(255,255,255,.28); }
.dev .company-action small { color: #b9c2b7; }
@media (max-width: 1100px) {
  .dev-facts { grid-template-columns: repeat(3, 1fr); }
  .dev-facts > div:nth-child(3n) { border-inline-end: 0; }
  .dev-facts > div:nth-child(-n+3) { border-bottom: 1px solid rgba(255,255,255,.12); }
  .dev-projects { grid-template-columns: 1fr 1fr; }
}
@media (max-width: 760px) {
  .dev-facts { grid-template-columns: 1fr 1fr; }
  .dev-facts > div { border-inline-end: 0; border-bottom: 1px solid rgba(255,255,255,.12); padding: 18px 12px 20px 0; }
  .dev-facts > div:nth-child(odd) { border-inline-end: 1px solid rgba(255,255,255,.12); padding-inline-end: 12px; }
  .dev-facts > div:nth-child(even) { padding-inline-start: 14px; }
  .dev-facts b { font-size: 26px; }
  .dev-model, .dev-why, .dev-vm, .dev-projects { grid-template-columns: 1fr; }
}
'''
p = B + '/pro.css'
s = open(p, encoding='utf-8').read()
s = re.sub(r'\n/\* ---------- Developer profile \(v15\) ---------- \*/.*', '', s, flags=re.S)
open(p, 'w', encoding='utf-8').write(s.rstrip() + '\n' + CSS)
print('section', len(html), 'strings', len(EN))
