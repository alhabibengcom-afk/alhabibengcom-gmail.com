"""Refine old->new drawing alignment: zero-padded correlation (no wrap), plan area only."""
import json, sys
import numpy as np
from PIL import Image, ImageFilter, ImageOps
OLD, NEW = sys.argv[1], sys.argv[2]
pairs = {'b1': 'basement', 'g': 'ground', 'f1': 'first', 'f2': 'second'}
D = 0.3
def edges(im):
    g = ImageOps.grayscale(im.convert('RGB')).filter(ImageFilter.FIND_EDGES)
    return (np.asarray(g, dtype=np.float32) > 40).astype(np.float32)
def corr(big, small):
    H, W = big.shape; h, w = small.shape
    P = (H + h, W + w)
    F = np.fft.rfft2(big - big.mean(), s=P) * np.conj(np.fft.rfft2(small - small.mean(), s=P))
    c = np.fft.irfft2(F, s=P)
    y, x = np.unravel_index(np.argmax(c), c.shape)
    if y > H: y -= P[0]
    if x > W: x -= P[1]
    return float(c.max() / (np.sqrt((small ** 2).sum()) + 1e-6)), x, y
out = {}
for o, n in pairs.items():
    old = Image.open(f'{OLD}/{o}.png'); new = Image.open(f'{NEW}/{n}.jpg')
    x0 = int(new.width * 0.28)
    nb = edges(new.crop((x0, 0, new.width, new.height)).resize((int((new.width - x0) * D), int(new.height * D))))
    best = None
    for s in np.arange(1.25, 2.0, 0.005):
        ob = edges(old.resize((int(old.width * s * D), int(old.height * s * D))))
        sc, x, y = corr(nb, ob)
        if best is None or sc > best[0]: best = (sc, float(s), x / D + x0, y / D)
    out[o] = {'score': round(best[0], 2), 's': round(best[1], 4), 'dx': round(best[2], 1), 'dy': round(best[3], 1)}
    print(o, out[o], flush=True)
json.dump(out, open(f'{NEW}/align.json', 'w'), indent=1)
