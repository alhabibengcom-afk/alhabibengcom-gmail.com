import json, sys
S, B = sys.argv[1:3]
NOTE = 'موضع تقريبي على الواجهة بحسب ترتيب الوحدات في المسقط'
def interp(xc, ref):
    ref = sorted(ref)
    for (a, pa), (b, pb) in zip(ref, ref[1:]):
        if a <= xc <= b:
            return pa + (xc - a) / (b - a) * (pb - pa)
    (a, pa), (b, pb) = (ref[-2], ref[-1]) if xc > ref[-1][0] else (ref[0], ref[1])
    return pa + (xc - a) / (b - a) * (pb - pa)
row = {'F22': 636, 'F24': 582, 'F26': 527, 'F28': 472, 'F30': 416, 'F32': 372, 'F32-1': 342, 'F34': 307}
photos = {'1000893966': ([(612, .09), (505, .27), (399, .44), (307, .57)], (.09, .44), (.57, .38)),
          '1000893969': ([(612, .09), (505, .22), (399, .34), (307, .42)], (.09, .435), (.42, .40))}
new = {}
for pid, (ref, l, r) in photos.items():
    for u, xc in row.items():
        x = interp(xc, ref)
        y = l[1] + (x - l[0]) / (r[0] - l[0]) * (r[1] - l[1])
        new.setdefault(u, []).append({'photo': pid, 'x': round(x, 4), 'y': round(y, 4), 'note': NOTE, 'basis': 'approximate'})
for u, x, y in [('F09-11', .235, .52), ('F12-15', .35, .48), ('F16-20', .66, .42), ('S10-13', .36, .34)]:
    new.setdefault(u, []).append({'photo': '1000893865', 'x': x, 'y': y, 'note': NOTE, 'basis': 'approximate'})
json.dump(new, open(S + '/mk/new.json', 'w'), ensure_ascii=False, indent=0)
print({u: [(m['photo'][-3:], m['x'], m['y']) for m in v] for u, v in new.items()})
