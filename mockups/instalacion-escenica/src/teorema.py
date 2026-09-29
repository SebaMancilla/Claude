"""Screen content: placeholder evoking the levitation scene of Pasolini's *Teorema* (1968)
(Emilia, dressed in black, floating above the farmhouse roof against a pale sky).

If a real frame is supplied (env MOCKUP_FRAME=path/to/frame.jpg) it is used instead,
cropped to fill each screen (cover fit, centred).
"""
import os
import numpy as np
import cv2
from content import fbm, srgb_to_lin

_CACHE = {}


def _figure(canvas, cx, top, h, color=(14, 12, 13)):
    """Emilia: black dress and shawl, arms opened downwards, levitating (feet pointing down)."""
    s = h / 1.0
    pts = lambda l: np.array([[cx + x * s, top + y * s] for x, y in l], np.int32)
    ov = canvas.copy()
    SS = 4
    big = cv2.resize(ov, None, fx=SS, fy=SS, interpolation=cv2.INTER_NEAREST)
    P = lambda l: (pts(l) * SS).astype(np.int32)
    # head + hair
    cv2.ellipse(big, (int(cx * SS), int((top + 0.075 * s) * SS)), (int(0.052 * s * SS), int(0.07 * s * SS)), 0, 0, 360, color, -1, cv2.LINE_AA)
    # shawl / shoulders
    cv2.fillPoly(big, [P([(-0.07, 0.13), (0.07, 0.13), (0.14, 0.2), (0.12, 0.32), (-0.12, 0.32), (-0.14, 0.2)])], color, cv2.LINE_AA)
    # long dress, slightly flared, hanging
    cv2.fillPoly(big, [P([(-0.11, 0.28), (0.11, 0.28), (0.13, 0.55), (0.15, 0.86), (0.05, 0.9), (-0.05, 0.9), (-0.15, 0.86), (-0.13, 0.55)])], color, cv2.LINE_AA)
    # legs / feet pointing down
    cv2.fillPoly(big, [P([(-0.05, 0.88), (-0.01, 0.88), (-0.02, 0.99), (-0.045, 1.0)])], color, cv2.LINE_AA)
    cv2.fillPoly(big, [P([(0.01, 0.88), (0.05, 0.88), (0.045, 1.0), (0.02, 0.99)])], color, cv2.LINE_AA)
    # arms opened downwards
    for sg in (-1, 1):
        cv2.fillPoly(big, [P([(sg * 0.11, 0.17), (sg * 0.14, 0.22), (sg * 0.33, 0.43), (sg * 0.36, 0.47),
                              (sg * 0.34, 0.49), (sg * 0.29, 0.46), (sg * 0.1, 0.27)])], color, cv2.LINE_AA)
    return cv2.resize(big, (canvas.shape[1], canvas.shape[0]), interpolation=cv2.INTER_AREA)


def placeholder(w, h, fig_x, fig_top, fig_h, roof_y, chimney_x, seed=11):
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    v = yy / h
    # overcast Lombard sky: cool grey on top, milky warm near the horizon
    top = np.array([112, 124, 138], np.float32); hor = np.array([206, 205, 194], np.float32)
    k = np.clip(v / max(roof_y, 1e-3), 0, 1) ** 0.8
    img = top * (1 - k[..., None]) + hor * k[..., None]
    sc = 3.0 / max(w, h)
    cl = fbm(xx * sc * 1.3 + 3, yy * sc * 3.2, 5, seed)
    img += (cl * 42)[..., None] * np.array([1.0, 1.0, 0.98])
    # distant poplars on the horizon
    rng = np.random.RandomState(seed)
    trees = img.copy()
    for i in range(int(w / h * 6) + 2):
        px = rng.uniform(-0.05, 1.05) * w
        ph = rng.uniform(0.10, 0.2) * h
        pw = ph * rng.uniform(0.1, 0.16)
        base = roof_y * h - rng.uniform(0.0, 0.02) * h
        tone = rng.uniform(120, 150)
        cv2.ellipse(trees, (int(px), int(base)), (int(pw), int(ph)), 0, 180, 360, (tone - 6, tone + 2, tone - 10), -1, cv2.LINE_AA)
    trees = cv2.GaussianBlur(trees, (0, 0), 0.004 * h + 1)
    img = img * 0.35 + trees * 0.65
    # farmhouse seen from the yard, looking up: roof slope (coppi), eave shadow, ochre facade
    ry = int(roof_y * h)
    eave = int((roof_y + 0.10) * h)
    rel = np.clip((yy - ry) / max(eave - ry, 1), 0, 1)
    rowh = 0.010 * h + 0.018 * h * rel                       # tile rows widen towards the eave
    phase = np.cumsum(1.0 / rowh[:, :1], axis=0)[:, 0]
    rows = (np.sin(phase * np.pi)[:, None] * 0.5 + 0.5) * np.ones((1, w))
    cols = np.sin(xx / (0.02 * h) * np.pi + (np.floor(phase)[:, None] % 2) * np.pi / 2) * 0.5 + 0.5
    tile = np.array([112, 62, 44], np.float32) * (0.68 + 0.2 * rows[..., None] + 0.1 * cols[..., None])
    tile *= (0.8 + 0.35 * rel[..., None])
    tile *= (0.9 + 0.25 * fbm(xx * sc * 5, yy * sc * 5, 3, seed + 3)[..., None])
    roofm = (yy >= ry) & (yy < eave)
    img = np.where(roofm[..., None], tile, img)
    cv2.line(img, (0, ry), (w, ry), (84, 48, 36), max(2, int(0.007 * h)), cv2.LINE_AA)
    # eave shadow and facade
    fac = np.array([178, 150, 104], np.float32) * (0.9 + 0.12 * fbm(xx * sc * 4, yy * sc * 4, 3, seed + 7)[..., None])
    shade = np.clip((yy - eave) / (0.035 * h), 0, 1)
    fac = fac * (0.35 + 0.65 * shade[..., None])
    img = np.where((yy >= eave)[..., None], fac, img)
    ww = int(0.05 * min(w, h)); wh = int(0.075 * min(w, h))
    for fx in np.arange(0.08, 1.0, 0.16):
        x0 = int(fx * w)
        if abs(fx - fig_x) < 0.03:
            continue
        cv2.rectangle(img, (x0, eave + int(0.03 * h)), (x0 + ww, eave + int(0.03 * h) + wh), (46, 38, 32), -1)
    # chimney
    cw = int(0.045 * h); ch = int(0.10 * h)
    cxp = int(chimney_x * w)
    cv2.rectangle(img, (cxp - cw // 2, ry - ch), (cxp + cw // 2, ry + int(0.03 * h)), (140, 108, 84), -1)
    cv2.rectangle(img, (cxp - cw // 2 - 6, ry - ch - 8), (cxp + cw // 2 + 6, ry - ch + 6), (96, 60, 46), -1)
    # Emilia levitating
    img = _figure(img, fig_x * w, fig_top * h, fig_h * h)
    # film look: soft, warm-green cast, vignette, grain
    img = cv2.GaussianBlur(img, (0, 0), max(0.8, 0.0012 * h))
    img = img * np.array([0.98, 1.0, 0.94])
    vig = 1 - 0.22 * (((xx - w / 2) / (w / 2)) ** 2 + ((yy - h / 2) / (h / 2)) ** 2)
    img *= vig[..., None]
    img += np.random.RandomState(seed + 5).randn(h, w, 1) * 3.0
    return np.clip(img, 0, 255).astype(np.uint8)


def frame_for(option):
    """RGB uint8 image for a screen option."""
    if option in _CACHE:
        return _CACHE[option]
    path = os.environ.get('MOCKUP_FRAME')
    target = (2000, 1000) if option == 'A' else (800, 2000)
    if path and os.path.exists(path):
        src = cv2.imread(path)[:, :, ::-1]
        tw, th = target
        s = max(tw / src.shape[1], th / src.shape[0])
        r = cv2.resize(src, (int(np.ceil(src.shape[1] * s)), int(np.ceil(src.shape[0] * s))), interpolation=cv2.INTER_AREA)
        x0 = (r.shape[1] - tw) // 2; y0 = (r.shape[0] - th) // 2
        img = r[y0:y0 + th, x0:x0 + tw]
    elif option == 'A':
        img = placeholder(2000, 1000, fig_x=0.71, fig_top=0.12, fig_h=0.38, roof_y=0.72, chimney_x=0.28)
    else:
        img = placeholder(800, 2000, fig_x=0.5, fig_top=0.2, fig_h=0.22, roof_y=0.8, chimney_x=0.74)
    _CACHE[option] = img
    return img


def sample(option, u, v):
    """linear RGB at screen coords u (0 left .. 1 right), v (0 top .. 1 bottom)."""
    key = ('lin', option)
    if key not in _CACHE:
        _CACHE[key] = srgb_to_lin(frame_for(option).astype(np.float64) / 255.0)
    img = _CACHE[key]
    h, w = img.shape[:2]
    x = np.clip(np.asarray(u, float) * w - 0.5, 0, w - 1.001)
    y = np.clip(np.asarray(v, float) * h - 0.5, 0, h - 1.001)
    x0 = np.floor(x).astype(int); y0 = np.floor(y).astype(int)
    fx = (x - x0)[..., None]; fy = (y - y0)[..., None]
    return (img[y0, x0] * (1 - fx) * (1 - fy) + img[y0, x0 + 1] * fx * (1 - fy)
            + img[y0 + 1, x0] * (1 - fx) * fy + img[y0 + 1, x0 + 1] * fx * fy)
