# Corrections from the Drive sheet (1S6tCpmT…, 25 Nov 2026) shared by build_lite.py and build_full.py.
# Land 17,784.57 m² (contracts); the open court inside the mall is 1,856.70 m² (internal plaza 1,227.84 + restaurant terraces 628.86).
import re
def apply(s, t):
    R = [
        (r'<b>٢٠٬٠٠٠ م²</b><span>أرض هابينس بلازا</span>', '<b>١٧٬٧٨٥ م²</b><span>' + t('أرض هابينس بلازا حسب العقود', 'Happiness Plaza site, per the contracts') + '</span>'),
        (r'<dt>٢٠٬٠٠٠ م²</dt><dd>مساحة الأرض</dd>', '<dt>١٧٬٧٨٥ م²</dt><dd>' + t('مساحة الأرض حسب العقود', 'Site area per the contracts') + '</dd>'),
        (r'<dt>٤٬٠٠٠ م²</dt><dd>البلازا المشتركة</dd>', '<dt>١٬٨٥٧ م²</dt><dd>' + t('البلازا الداخلية مع تراسات المطاعم', 'Internal plaza with restaurant terraces') + '</dd>'),
        (r'<strong>أرض (?:٢٠٬٠٠٠|١٧٬٧٨٥) م² وبلازا مفتوحة ٤٬٠٠٠ م²</strong>', '<strong>' + t('أرض ١٧٬٧٨٥ م² وبلازا داخلية ١٬٨٥٧ م²', 'A 17,785 m² site and a 1,857 m² internal plaza') + '</strong>'),
        (r'تجتمع جميع مراحل هابينس بلازا حول بلازا مشتركة مساحتها ٤٬٠٠٠ م²\. تربط البلازا بين المحلات والمطاعم والفندق والأنشطة الترفيهية\.',
         t('تجتمع جميع مراحل هابينس بلازا حول بلازا داخلية مفتوحة مساحتها ١٬٨٥٧ م² مع تراسات المطاعم. تربط البلازا بين المحلات والمطاعم والفندق والأنشطة الترفيهية.',
           'All phases of Happiness Plaza come together around a 1,857 m² open internal plaza with the restaurant terraces. The plaza links the stores, restaurants, hotel and leisure attractions.')),
        (r'<strong>٤٬٠٠٠ <span>م²</span></strong><p>مساحة البلازا المشتركة</p>', '<strong>١٬٨٥٧ <span>م²</span></strong><p>' + t('البلازا الداخلية مع تراسات المطاعم', 'Internal plaza with restaurant terraces') + '</p>'),
    ]
    R.append((r'نسبة تعاقدية من صافي مبيعات الفرع، وفق آلية الحساب المتفق عليها\.', t('نسبة تعاقدية من مبيعات الفرع، وفق آلية الحساب المتفق عليها.', 'An agreed percentage of the branch’s sales, per the agreed calculation method.')))
    for a, b in R:
        s, n = re.subn(a, b, s)
    t('١٬٨٥٧', '1,857'); t('١٧٬٧٨٥ م²', '17,785 m²'); t('١٬٨٥٧ م²', '1,857 m²')
    body = re.sub(r'<script.*?</script>', '', s, flags=re.S)
    for bad in ['٢٠٬٠٠٠ م²', '٤٬٠٠٠ م²', '>٤٬٠٠٠ <', 'صافي', 'الصافي']:
        assert bad not in body, bad
    return s
