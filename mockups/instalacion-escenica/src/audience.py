"""Generic audience figures (seen from behind, facing the installation) as camera-facing
billboards placed in hall coordinates, so the same crowd appears at true scale in every photo."""
import numpy as np
import cv2

PPM = 220

# (X, Z, height, kind, flip)  X/Z in hall meters, people look towards the screen / stair (+Z)
CROWD = [
    # in front of the stair, watching the singer
    (2.05, 1.95, 1.72, 'coat', 0), (2.75, 1.35, 1.80, 'pockets', 1), (3.55, 1.75, 1.63, 'longhair', 0),
    (4.25, 1.05, 1.76, 'cap', 1), (5.35, 1.65, 1.69, 'phone', 0), 
    (1.35, 0.85, 1.66, 'longhair', 1), (5.95, 0.55, 1.78, 'coat', 1),
    # centre of the hall
    (1.55, -0.75, 1.74, 'pockets', 0), (2.35, -1.55, 1.60, 'bun', 1), (0.35, -2.05, 1.82, 'coat', 0),
    (3.35, -2.25, 1.71, 'cap', 0), (-1.05, -1.05, 1.68, 'phone', 1), (-2.05, -0.25, 1.79, 'backpack', 1),
    (-0.75, 1.35, 1.64, 'longhair', 0), (0.95, 2.25, 1.75, 'pockets', 1),
    # left, in front of the long screen
    (-3.05, 1.25, 1.77, 'coat', 1), (-2.35, 2.05, 1.62, 'bun', 0), (-4.15, 1.95, 1.73, 'pockets', 0),
    (-3.65, -1.35, 1.81, 'cap', 1), (-5.15, 0.65, 1.66, 'longhair', 1), (-1.55, 2.45, 1.86, 'coat', 0),
    # right side, near the windows
    (6.35, -0.95, 1.74, 'pockets', 0), (6.95, 0.95, 1.61, 'longhair', 0), (5.75, -2.45, 1.80, 'coat', 1),
    (7.35, -1.95, 1.69, 'bun', 1),
    # a few closer to the cameras
    (-1.25, -3.05, 1.78, 'coat', 0),
]

COATS = [(0.045, 0.045, 0.05), (0.06, 0.05, 0.045), (0.035, 0.04, 0.055), (0.08, 0.075, 0.07),
         (0.05, 0.03, 0.03), (0.03, 0.045, 0.04), (0.10, 0.09, 0.08)]
HAIR = [(0.02, 0.015, 0.012), (0.05, 0.03, 0.02), (0.12, 0.08, 0.05), (0.03, 0.03, 0.03)]
SKIN = [(0.30, 0.20, 0.15), (0.22, 0.14, 0.10), (0.36, 0.25, 0.19)]


def _draw(kind, h, seed):
    rng = np.random.RandomState(seed)
    s = h / 1.75
    Wc, Hc = int(1.3 * PPM), int(2.05 * PPM)
    mask = np.zeros((Hc, Wc), np.float32)
    alb = np.zeros((Hc, Wc, 3), np.float32)
    ox = Wc / 2
    coat = np.array(COATS[rng.randint(len(COATS))]); hair = np.array(HAIR[rng.randint(len(HAIR))])
    skin = np.array(SKIN[rng.randint(len(SKIN))]); pants = np.array([0.03, 0.03, 0.035]) * rng.uniform(0.7, 1.4)
    L = cv2.LINE_AA

    def P(l):
        return np.array([[ox + x * s * PPM, Hc - y * s * PPM] for x, y in l], np.int32)

    def poly(l, c):
        cv2.fillPoly(mask, [P(l)], 1.0, L); cv2.fillPoly(alb, [P(l)], tuple(float(v) for v in c), L)

    def ell(cx, cy, ax, ay, c, ang=0):
        C = (int(ox + cx * s * PPM), int(Hc - cy * s * PPM)); A = (int(ax * s * PPM), int(ay * s * PPM))
        cv2.ellipse(mask, C, A, ang, 0, 360, 1.0, -1, L); cv2.ellipse(alb, C, A, ang, 0, 360, tuple(float(v) for v in c), -1, L)

    def limb(a, b, w, c):
        pa, pb = P([a])[0], P([b])[0]; t = max(1, int(w * s * PPM))
        cv2.line(mask, tuple(pa), tuple(pb), 1.0, t, L); cv2.line(alb, tuple(pa), tuple(pb), tuple(float(v) for v in c), t, L)

    sw = rng.uniform(0.2, 0.235)          # half shoulder width
    hw = sw * rng.uniform(0.78, 0.9)
    # legs
    st = rng.uniform(0.07, 0.13)
    poly([(-hw, 0.9), (-0.01, 0.9), (-0.035, 0.45), (-st + 0.04, 0.03), (-st - 0.07, 0.03), (-hw + 0.02, 0.5)], pants)
    poly([(0.01, 0.9), (hw, 0.9), (hw - 0.02, 0.5), (st + 0.07, 0.03), (st - 0.04, 0.03), (0.035, 0.45)], pants)
    ell(-st - 0.01, 0.03, 0.065, 0.03, (0.02, 0.02, 0.02)); ell(st + 0.01, 0.03, 0.065, 0.03, (0.02, 0.02, 0.02))
    # torso / coat
    low = 0.62 if kind == 'coat' else 0.86
    poly([(-sw, 1.43), (-sw * 0.55, 1.49), (sw * 0.55, 1.49), (sw, 1.43), (sw + 0.015, 1.2), (hw + 0.03, low),
          (-hw - 0.03, low), (-sw - 0.015, 1.2)], coat)
    # neck + head
    poly([(-0.05, 1.46), (0.05, 1.46), (0.045, 1.56), (-0.045, 1.56)], skin * 0.6)
    ell(0, 1.64, 0.088, 0.108, hair)
    if kind == 'longhair':
        poly([(-0.1, 1.66), (0.1, 1.66), (0.12, 1.36), (0.02, 1.33), (-0.12, 1.36)], hair)
    if kind == 'bun':
        ell(0, 1.755, 0.045, 0.04, hair)
    if kind == 'cap':
        ell(0, 1.69, 0.095, 0.07, coat * 0.7 + 0.01)
    if kind == 'backpack':
        poly([(-0.16, 1.4), (0.16, 1.4), (0.18, 1.02), (-0.18, 1.02)], coat * 0.6 + np.array([0.01, 0.012, 0.015]))
    # arms
    if kind == 'pockets':
        for g in (-1, 1):
            limb((g * sw, 1.4), (g * (sw + 0.07), 1.12), 0.09, coat)
            limb((g * (sw + 0.07), 1.12), (g * (hw - 0.01), 0.95), 0.08, coat)
    elif kind == 'phone':
        g = 1
        limb((-sw, 1.4), (-sw - 0.035, 1.1), 0.085, coat); limb((-sw - 0.035, 1.1), (-sw - 0.02, 0.86), 0.075, coat)
        limb((sw - 0.02, 1.42), (sw + 0.07, 1.63), 0.085, coat); limb((sw + 0.07, 1.63), (0.17, 1.8), 0.075, coat)
        poly([(0.11, 1.79), (0.22, 1.79), (0.22, 1.96), (0.11, 1.96)], (0.02, 0.02, 0.025))
    else:
        for g in (-1, 1):
            limb((g * sw, 1.4), (g * (sw + 0.03), 1.1), 0.085, coat)
            limb((g * (sw + 0.03), 1.1), (g * (sw + 0.015), 0.84), 0.075, coat)
            ell(g * (sw + 0.012), 0.8, 0.035, 0.045, skin)
    return mask, alb, ox, Hc


_TPL = {}


def template(i):
    if i not in _TPL:
        X, Z, h, kind, flip = CROWD[i]
        m, a, ox, Hc = _draw(kind, h, seed=100 + i)
        if flip:
            m = m[:, ::-1].copy(); a = a[:, ::-1].copy()
        _TPL[i] = (m, a, ox, Hc)
    return _TPL[i]


def _affine(cam, feet, ox, Hc, ppm, up_sign=1.0):
    q = cam.project(feet[None])[0]
    Z = cam.cam(feet[None])[0, 2]
    s = cam.f / Z / ppm
    q2 = cam.project((feet + [0, up_sign * 1.7, 0])[None])[0]
    up = (q2 - q) / np.linalg.norm(q2 - q)
    right = np.array([-up[1], up[0]]) * up_sign
    A = np.array([[right[0] * s, -up[0] * s, 0.0], [right[1] * s, -up[1] * s, 0.0]])
    A[:, 2] = q - A[:, :2] @ np.array([ox, Hc])
    return A, s * ppm


def place(cam, i, W, H, exclude=None):
    """mask, albedo, mirrored (floor reflection) mask, distance, px-per-meter, feet pixel"""
    X, Z, h, kind, flip = CROWD[i]
    feet = np.array([X, 0.0, Z])
    if cam.cam(feet[None])[0, 2] < 1.0:
        return None
    m, a, ox, Hc = template(i)
    A, ppm_img = _affine(cam, feet, ox, Hc, PPM)
    mask = cv2.warpAffine(m, A, (W, H), flags=cv2.INTER_AREA)
    alb = cv2.warpAffine(a, A, (W, H), flags=cv2.INTER_AREA)
    Am, _ = _affine(cam, feet, ox, Hc, PPM, up_sign=-1.0)
    mirror = cv2.warpAffine(m, Am, (W, H), flags=cv2.INTER_AREA)
    dist = np.linalg.norm(feet + [0, 1.0, 0] - cam.C)
    q = cam.project(feet[None])[0]
    return np.clip(mask, 0, 1), alb, np.clip(mirror, 0, 1), dist, ppm_img, q
