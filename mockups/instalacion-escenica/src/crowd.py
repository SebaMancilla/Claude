"""Audience generator: anthropometric 3D skeletons dressed with smooth volumes, rendered
per camera from the correct viewing angle (orthographic billboard at the true pixel scale)
and relit with the installation lights.

World: X along the rows, Y up, Z towards the stair. A person faces `yaw` (radians,
0 = +Z)."""
import numpy as np
import cv2

# ------------------------------------------------------------------ palette
DARK = [(0.018, 0.018, 0.02), (0.022, 0.024, 0.03), (0.02, 0.02, 0.025), (0.03, 0.028, 0.026),
        (0.016, 0.02, 0.032), (0.028, 0.03, 0.022)]
MID = [(0.06, 0.06, 0.065), (0.05, 0.065, 0.09), (0.09, 0.07, 0.05), (0.055, 0.06, 0.04),
       (0.12, 0.11, 0.1), (0.075, 0.05, 0.045), (0.035, 0.05, 0.075)]
BRIGHT = [(0.2, 0.19, 0.17), (0.22, 0.05, 0.04), (0.28, 0.2, 0.08), (0.24, 0.24, 0.23), (0.12, 0.16, 0.2)]
DENIM = [(0.04, 0.055, 0.085), (0.03, 0.04, 0.06), (0.06, 0.07, 0.09)]
HAIR = [(0.012, 0.01, 0.009), (0.025, 0.017, 0.012), (0.05, 0.032, 0.02), (0.12, 0.085, 0.05), (0.02, 0.02, 0.02)]
SKIN = [(0.32, 0.21, 0.16), (0.24, 0.15, 0.11), (0.38, 0.27, 0.21), (0.17, 0.11, 0.08)]


def _pick(rng, lst):
    return np.array(lst[rng.randint(len(lst))], float)


def cloth(rng):
    u = rng.rand()
    c = _pick(rng, DARK) if u < 0.55 else (_pick(rng, MID) if u < 0.88 else _pick(rng, BRIGHT))
    return c * rng.uniform(0.85, 1.15)


# ------------------------------------------------------------------ person spec
def make_person(seed, X, Z, yaw, group_pose=None):
    rng = np.random.RandomState(seed)
    fem = rng.rand() < 0.5
    H = rng.normal(1.60, 0.065) if fem else rng.normal(1.73, 0.07)
    H = float(np.clip(H, 1.50, 1.93))
    build = rng.uniform(0.9, 1.15)
    p = dict(seed=seed, X=X, Z=Z, yaw=yaw, fem=fem, H=H, build=build)
    p['top'] = rng.choice(['jacket', 'coat', 'hoodie', 'tee', 'puffer'], p=[0.3, 0.2, 0.2, 0.15, 0.15])
    p['bottom'] = 'skirt' if (fem and rng.rand() < 0.18) else 'pants'
    if fem and p['top'] == 'coat' and rng.rand() < 0.4:
        p['bottom'] = 'pants'
    hs = ['short', 'long', 'bun', 'pony', 'curly'] if fem else ['short', 'short', 'cap', 'beanie', 'bald', 'curly']
    p['hair'] = rng.choice(hs)
    if p['top'] == 'hoodie' and rng.rand() < 0.3:
        p['hair'] = 'hood'
    p['bag'] = rng.choice(['none', 'none', 'backpack', 'tote', 'cross'], p=[0.45, 0.2, 0.15, 0.1, 0.1])
    poses = ['down', 'pockets', 'onepocket', 'crossed', 'phone', 'drink', 'back']
    w = np.array([0.24, 0.17, 0.16, 0.12, 0.12, 0.12, 0.07])
    p['pose'] = group_pose or rng.choice(poses, p=w / w.sum())
    p['c_top'] = cloth(rng)
    p['c_bot'] = _pick(rng, DENIM) if rng.rand() < 0.45 else _pick(rng, DARK) * rng.uniform(0.8, 1.3)
    p['c_shoe'] = np.array((0.25, 0.25, 0.24)) if rng.rand() < 0.25 else _pick(rng, DARK)
    p['c_hair'] = _pick(rng, HAIR)
    p['c_skin'] = _pick(rng, SKIN)
    p['c_bag'] = _pick(rng, DARK if rng.rand() < 0.7 else MID)
    p['c_hat'] = cloth(rng)
    p['shift'] = rng.choice([-1, 1]) * rng.uniform(0.0, 1.0)     # weight shift
    p['lean'] = rng.normal(0, 0.02)
    p['head_turn'] = rng.normal(0, 0.25)
    p['head_tilt'] = rng.normal(0, 0.05)
    p['blur'] = rng.uniform(1.0, 2.5) if rng.rand() < 0.1 else 0.0   # a few people moving (night exposure)
    return p


# ------------------------------------------------------------------ skeleton + volumes (person local)
def _ik(S, T, L1, L2, hint):
    d = T - S
    dist = np.linalg.norm(d)
    dist = np.clip(dist, abs(L1 - L2) + 1e-3, L1 + L2 - 1e-3)
    u = d / (np.linalg.norm(d) + 1e-9)
    T = S + u * dist
    a = (L1 ** 2 - L2 ** 2 + dist ** 2) / (2 * dist)
    b = np.sqrt(max(L1 ** 2 - a ** 2, 0))
    v = hint - (hint @ u) * u
    v /= np.linalg.norm(v) + 1e-9
    return S + a * u + b * v, T


def parts_local(p):
    """list of primitives in person-local meters (x = person's left, y up, z forward):
    ('cap', a, b, ra, rb, mat) tapered capsules and ('loft', sections, mat) with sections
    [(y, cx, cz, half_width, half_depth), ...] (elliptic cross-sections)."""
    rng = np.random.RandomState(p['seed'] + 7)
    H, fem, bu = p['H'], p['fem'], p['build']
    s = H / 1.73
    P = []

    def cap(a, b, ra, rb, m):
        P.append(('cap', np.array(a, float), np.array(b, float), ra, rb, m))

    def loft(secs, m):
        P.append(('loft', [tuple(float(v) for v in sc) for sc in secs], m))

    sh = p['shift'] * 0.028                                  # pelvis shift towards the loaded leg
    lean = p['lean']
    ct = {'jacket': 0.022, 'coat': 0.03, 'hoodie': 0.03, 'tee': 0.006, 'puffer': 0.05}[p['top']]
    wb = bu * s
    # anthropometric torso sections (y, half width, half depth) before clothing
    if not fem:
        T = [(0.846, 0.058, 0.055), (0.832, 0.115, 0.07), (0.812, 0.195, 0.095), (0.785, 0.205, 0.105),
             (0.74, 0.19, 0.115), (0.68, 0.172, 0.112), (0.61, 0.158, 0.105), (0.56, 0.16, 0.1), (0.52, 0.165, 0.1)]
    else:
        T = [(0.846, 0.054, 0.05), (0.832, 0.1, 0.062), (0.812, 0.172, 0.085), (0.785, 0.178, 0.095),
             (0.74, 0.165, 0.11), (0.68, 0.148, 0.1), (0.61, 0.135, 0.092), (0.56, 0.155, 0.095), (0.52, 0.175, 0.1)]
    hem = {'jacket': 0.47, 'coat': 0.29, 'hoodie': 0.465, 'tee': 0.5, 'puffer': 0.47}[p['top']]
    secs = []
    for y, hw, hd in T:
        f = (y - 0.52) / (0.846 - 0.52)
        cx = sh * (1 - f) + lean * f
        extra = ct if y < 0.84 else ct * 0.5
        secs.append((y * H, cx, -0.005, hw * wb + extra, hd * wb + extra))
    # garment below the waist
    if p['top'] == 'coat':
        secs += [(0.44 * H, sh, 0.0, 0.185 * wb + ct, 0.12 * wb + ct), (0.36 * H, sh, 0.0, 0.2 * wb + ct, 0.13 * wb + ct),
                 (0.29 * H, sh, 0.0, 0.215 * wb + ct, 0.14 * wb + ct)]
    else:
        secs += [(hem * H, sh, 0.0, 0.17 * wb + ct, 0.105 * wb + ct)]
    loft(secs, 'top')
    if p['top'] == 'puffer':
        p['_quilt'] = True
    # pelvis / trousers bridge
    loft([(0.40 * H, sh, 0.0, 0.15 * wb, 0.095 * wb), (0.47 * H, sh, 0.0, 0.165 * wb, 0.1 * wb),
          (0.53 * H, sh, 0.0, 0.16 * wb, 0.098 * wb)], 'bot')
    if p['bottom'] == 'skirt':
        loft([(0.33 * H, sh, 0.0, 0.2 * wb, 0.15 * wb), (0.45 * H, sh, 0.0, 0.175 * wb, 0.12 * wb),
              (0.53 * H, sh, 0.0, 0.15 * wb, 0.1 * wb)], 'bot')
    # --- legs (IK), weight on one leg
    hip_y = 0.505 * H
    hip_half = (0.085 if not fem else 0.09) * wb
    L_leg = (0.505 * H - 0.07 * s) * 1.004
    L_th, L_sh = L_leg * 0.5, L_leg * 0.5
    lp = 0.014 if p['bottom'] == 'pants' else 0.0
    mat_leg = 'bot' if p['bottom'] == 'pants' else 'skin_leg'
    for side in (1, -1):
        hip = np.array([sh + side * hip_half, hip_y + side * p['shift'] * 0.01, 0.0])
        load = (p['shift'] * side) > 0
        foot = np.array([hip[0] + side * (0.02 + (0.0 if load else 0.05 * rng.rand())), 0.07 * s,
                         (0.0 if load else rng.uniform(0.02, 0.09))])
        knee, ank = _ik(hip, foot, L_th, L_sh, np.array([0.0, 0, 1.0]))
        cap(hip, knee, 0.078 * wb + lp, 0.055 * wb + lp, mat_leg)
        cap(knee, ank, 0.053 * wb + lp, 0.037 * s + lp * 0.8, mat_leg)
        cap(ank + [0, -0.025, -0.035], ank + [side * 0.01, -0.035, 0.17 * s], 0.043 * s, 0.037 * s, 'shoe')
    # --- neck, head, hair
    neck = np.array([lean, 0.838 * H, -0.01])
    cap(neck + [0, -0.02, 0], neck + [0, 0.06, 0.01], 0.047 * s, 0.043 * s, 'skin')
    head = neck + np.array([p['head_tilt'] * 0.4, 0.1 * H, 0.02])
    hr = (0.086 if not fem else 0.081) * s
    cap(head + [0, -0.025, -0.005], head + [0, 0.028, -0.01], hr * 0.93, hr, 'skin')
    cap(head + [0, -0.05, 0.04], head + [0, -0.075, 0.055], hr * 0.66, hr * 0.5, 'skin')
    cap(head + [0.075 * s, -0.01, 0.0], head + [0.075 * s, -0.03, 0.005], 0.018 * s, 0.015 * s, 'skin')   # ears
    cap(head + [-0.075 * s, -0.01, 0.0], head + [-0.075 * s, -0.03, 0.005], 0.018 * s, 0.015 * s, 'skin')
    hc = head + [0, 0.012, -0.012]
    hair = p['hair']
    if hair in ('short', 'curly', 'long', 'bun', 'pony'):
        extra = 0.03 if hair == 'curly' else (0.014 if fem else 0.008)
        cap(hc + [0, -0.02, -0.012], hc + [0, 0.02, -0.018], hr + extra, hr + extra * 0.85, 'hair')
    if hair == 'long':
        L = rng.uniform(0.16, 0.3) * s
        y0 = hc[1] - 0.02
        loft([(y0 - L, hc[0], -0.06, 0.105 * s, 0.05), (y0 - L * 0.5, hc[0], -0.05, 0.11 * s, 0.06),
              (y0, hc[0], -0.03, hr + 0.012, hr * 0.8)], 'hair')
    if hair == 'bun':
        cap(hc + [0, 0.055, -0.075], hc + [0, 0.065, -0.085], 0.042 * s, 0.042 * s, 'hair')
    if hair == 'pony':
        cap(hc + [0, 0.02, -0.092], hc + [0.01, -0.2 * s, -0.12], 0.033 * s, 0.02 * s, 'hair')
    if hair == 'cap':
        cap(hc + [0, -0.005, -0.012], hc + [0, 0.028, -0.012], hr + 0.013, hr + 0.006, 'hat')
        cap(hc + [0, -0.01, 0.07], hc + [0, -0.018, 0.155], 0.016, 0.014, 'hat')
    if hair == 'beanie':
        cap(hc + [0, 0.0, -0.012], hc + [0, 0.05, -0.02], hr + 0.016, hr + 0.002, 'hat')
    if hair == 'hood':
        cap(hc + [0, -0.03, -0.035], hc + [0, 0.03, -0.035], hr + 0.035, hr + 0.03, 'top')
    elif p['top'] == 'hoodie':
        cap(neck + [0, 0.0, -0.075], neck + [0, 0.04, -0.085], 0.072 * s, 0.066 * s, 'top')
    # --- arms
    L_ua, L_fa = 0.186 * H, 0.16 * H
    ra_u, ra_f = 0.046 * wb + ct * 0.8, 0.038 * wb + ct * 0.6
    sh_half = (T[2][1] - 0.02) * wb
    pose = p['pose']
    chest = np.array([lean, 0.72 * H, 0.0])
    pel = np.array([sh, hip_y, 0.0])
    for side in (1, -1):
        S = np.array([side * sh_half + lean, 0.795 * H - side * p['shift'] * 0.01, -0.01])
        if pose == 'down' or (pose == 'onepocket' and side == -1) or (pose in ('phone', 'drink') and side == -1):
            Tg = S + [side * 0.035, -(L_ua + L_fa) * 0.95, 0.04 + 0.03 * rng.rand()]
            hint = np.array([side * 0.15, 0, -1.0])
        elif pose in ('pockets', 'onepocket'):
            Tg = np.array([sh + side * (hip_half + 0.05), hip_y - 0.02, 0.07])
            hint = np.array([side * 1.0, 0, -0.4])
        elif pose == 'crossed':
            Tg = chest + [-side * 0.08, -0.04, 0.2]
            hint = np.array([side * 0.7, -0.7, 0.1])
        elif pose == 'back':
            Tg = pel + [side * 0.03, 0.07, -0.15]
            hint = np.array([side * 0.8, 0, 0.3])
        elif pose == 'phone':
            Tg = head + [side * 0.08, 0.14, 0.34]
            hint = np.array([side * 1.0, -0.7, 0.0])
        elif pose == 'drink':
            Tg = chest + [side * 0.1, -0.05, 0.28]
            hint = np.array([side * 0.5, -1.0, -0.2])
        else:
            Tg = S + [side * 0.035, -(L_ua + L_fa) * 0.95, 0.04]
            hint = np.array([0, 0, -1.0])
        E, Hd = _ik(S, Tg, L_ua, L_fa, hint)
        cap(S + [0, 0.01, 0], E, ra_u, ra_u * 0.86, 'top')
        cap(E, Hd, ra_f, ra_f * 0.82, 'top' if p['top'] != 'tee' else 'skin')
        dirh = (Hd - E) / (np.linalg.norm(Hd - E) + 1e-9)
        if not (pose in ('pockets',) or (pose == 'onepocket' and side == 1)):
            cap(Hd, Hd + dirh * 0.075 * s, 0.035 * s, 0.03 * s, 'skin')
        if pose == 'phone' and side == 1:
            p['_phone'] = Hd + dirh * 0.07
        if pose == 'drink' and side == 1:
            cap(Hd + [0, 0.0, 0.02], Hd + [0, 0.12, 0.02], 0.032, 0.036, 'cup')
    # --- bags
    back = -(T[4][2] * wb + ct)
    if p['bag'] == 'backpack':
        loft([(0.58 * H, lean, back - 0.07, 0.15 * s, 0.075), (0.66 * H, lean, back - 0.08, 0.16 * s, 0.085),
              (0.78 * H, lean, back - 0.06, 0.14 * s, 0.07)], 'bag')
    elif p['bag'] == 'tote':
        sd = 1 if rng.rand() < 0.5 else -1
        loft([(0.33 * H, sh + sd * 0.26 * s, 0.0, 0.14 * s, 0.05), (0.47 * H, sh + sd * 0.25 * s, 0.0, 0.12 * s, 0.045)], 'bag')
    elif p['bag'] == 'cross':
        loft([(0.45 * H, sh + 0.17 * s, 0.07, 0.09 * s, 0.035), (0.53 * H, sh + 0.17 * s, 0.07, 0.09 * s, 0.035)], 'bag')
    return P


def material_colors(p):
    return {'top': p['c_top'], 'bot': p['c_bot'], 'shoe': p['c_shoe'], 'skin': p['c_skin'],
            'skin_leg': p['c_skin'] * 0.8, 'hair': p['c_hair'], 'hat': p['c_hat'], 'bag': p['c_bag'],
            'cup': np.array((0.3, 0.3, 0.3))}


MAT_ID = {'top': 0, 'bot': 1, 'shoe': 2, 'skin': 3, 'skin_leg': 4, 'hair': 5, 'hat': 6, 'bag': 7, 'cup': 8}


# ------------------------------------------------------------------ view + raster
def view_basis(p, cam_pos):
    """returns (xv, yv, zv) world unit vectors: zv towards the camera (horizontal)."""
    to_c = np.array([cam_pos[0] - p['X'], 0.0, cam_pos[2] - p['Z']])
    zv = to_c / np.linalg.norm(to_c)
    yv = np.array([0, 1.0, 0])
    xv = np.cross(yv, zv)
    return xv, yv, zv


def local_to_world_dir(p):
    f = np.array([np.sin(p['yaw']), 0, np.cos(p['yaw'])])     # facing
    left = np.cross(np.array([0, 1.0, 0]), f)
    return left, np.array([0, 1.0, 0]), f


def _smin(a, b, k):
    h = np.clip(0.5 + 0.5 * (b - a) / k, 0, 1)
    return b * (1 - h) + a * h - k * h * (1 - h)


def _loft_rows(secs, gy):
    from scipy.interpolate import PchipInterpolator
    secs = sorted(secs, key=lambda t: t[0])
    ys = np.array([t[0] for t in secs])
    vals = np.array([t[1:] for t in secs])
    if len(ys) == 1:
        return None
    f = PchipInterpolator(ys, vals, axis=0, extrapolate=False)
    v = f(np.clip(gy, ys[0], ys[-1]))
    return ys[0], ys[-1], v


def raster(p, cam_pos, ppm, ss=3, noise_seed=0):
    """render in the person's billboard plane (orthographic). canvas origin: feet centre,
    x = camera right, y up, z towards the camera."""
    parts = parts_local(p)
    lx, ly, lz = local_to_world_dir(p)
    xv, yv, zv = view_basis(p, cam_pos)
    M = np.array([[lx @ xv, ly @ xv, lz @ xv], [lx @ yv, ly @ yv, lz @ yv], [lx @ zv, ly @ zv, lz @ zv]])
    cphi, sphi = lx @ xv, lz @ xv            # ellipse extent along view x
    cpz, spz = lx @ zv, lz @ zv
    V = []
    xmin, xmax, ymax = 1e9, -1e9, -1e9
    for pr in parts:
        if pr[0] == 'cap':
            _, a, b, ra, rb, m = pr
            a2, b2 = M @ a, M @ b
            V.append(('cap', a2, b2, ra, rb, m))
            xmin = min(xmin, a2[0] - ra, b2[0] - rb); xmax = max(xmax, a2[0] + ra, b2[0] + rb)
            ymax = max(ymax, a2[1] + ra, b2[1] + rb)
        else:
            _, secs, m = pr
            vs = []
            for y, cx, cz, hw, hd in secs:
                c = M @ np.array([cx, y, cz])
                w = np.sqrt((hw * cphi) ** 2 + (hd * sphi) ** 2)
                dz = np.sqrt((hw * cpz) ** 2 + (hd * spz) ** 2)
                vs.append((y, c[0], c[2], w, dz))
                xmin = min(xmin, c[0] - w); xmax = max(xmax, c[0] + w); ymax = max(ymax, y)
            V.append(('loft', vs, m))
    phone = None
    if '_phone' in p:
        phone = M @ p['_phone']
        xmin = min(xmin, phone[0] - 0.1); xmax = max(xmax, phone[0] + 0.1); ymax = max(ymax, phone[1] + 0.12)
    xmin -= 0.04; xmax += 0.04; ymax += 0.04; ymin = -0.03
    pp = ppm * ss
    w = int(np.ceil((xmax - xmin) * pp)) + 2
    h = int(np.ceil((ymax - ymin) * pp)) + 2
    gx = xmin + (np.arange(w) + 0.5) / pp
    gy = ymax - (np.arange(h) + 0.5) / pp
    X, Y = np.meshgrid(gx, gy)
    sdf = np.full((h, w), 1e3)
    zbest = np.full((h, w), -1e3)
    nx = np.zeros((h, w)); ny = np.zeros((h, w)); nz = np.ones((h, w))
    mat = np.zeros((h, w), np.int32)
    rng = np.random.RandomState(noise_seed)
    fz = cv2.resize(rng.randn(max(2, h // 4), max(2, w // 4)).astype(np.float32), (w, h), interpolation=cv2.INTER_CUBIC)
    kk = 0.022
    for pr in V:
        m = pr[-1]
        if pr[0] == 'cap':
            _, a, b, ra, rb, m = pr
            ab = b[:2] - a[:2]
            L2 = ab @ ab + 1e-9
            t = np.clip(((X - a[0]) * ab[0] + (Y - a[1]) * ab[1]) / L2, 0, 1)
            cx = a[0] + t * ab[0]; cy = a[1] + t * ab[1]
            dx = X - cx; dy = Y - cy
            d = np.sqrt(dx * dx + dy * dy)
            r = ra + (rb - ra) * t
            if m == 'hair':
                r = r + fz * 0.005
            sd = d - r
            zc = a[2] + (b[2] - a[2]) * t
            rr = np.maximum(r, 1e-4)
            nxx = dx / rr; nyy = dy / rr
            nzz = np.sqrt(np.clip(1 - nxx * nxx - nyy * nyy, 0, 1))
            zf = zc + rr * nzz
        else:
            _, vs, m = pr
            res = _loft_rows(vs, gy)
            if res is None:
                continue
            y0, y1, v = res
            cxr, czr, wr, dzr = v[:, 0][:, None], v[:, 1][:, None], np.maximum(v[:, 2], 1e-4)[:, None], v[:, 3][:, None]
            if m == 'hair':
                wr = wr + fz * 0.006
            dxl = X - cxr
            sd = np.maximum(np.abs(dxl) - wr, np.maximum(y0 - Y, Y - y1))
            u = np.clip(dxl / wr, -1, 1)
            s1 = np.sqrt(np.clip(1 - u * u, 0, 1))
            zf = czr + dzr * s1
            nxx = u / wr; nzz = s1 / np.maximum(dzr, 1e-3)
            nn = np.sqrt(nxx ** 2 + nzz ** 2) + 1e-9
            nxx = nxx / nn; nzz = nzz / nn; nyy = np.zeros_like(nxx)
        sdf = _smin(sdf, sd, kk) if m not in ('hair', 'cup', 'bag') else np.minimum(sdf, sd)
        better = (sd < 0) & (zf > zbest)
        zbest = np.where(better, zf, zbest)
        nx = np.where(better, nxx, nx); ny = np.where(better, nyy, ny); nz = np.where(better, nzz, nz)
        mat = np.where(better, MAT_ID[m], mat)
    alpha = np.clip(0.5 - sdf * pp, 0, 1)
    # silhouette-edge normals from the SDF gradient (rim light on shoulders / head tops)
    gyy, gxx = np.gradient(cv2.GaussianBlur(sdf.astype(np.float32), (0, 0), 1.0))
    gn = np.sqrt(gxx ** 2 + gyy ** 2) + 1e-9
    ex, ey = gxx / gn, -gyy / gn
    edge_w = np.exp(np.clip(sdf, None, 0) / 0.018)
    nx = nx * (1 - edge_w) + ex * edge_w
    ny = ny * (1 - edge_w) + ey * edge_w
    nz = nz * (1 - edge_w) + 0.1 * edge_w
    nn = np.sqrt(nx * nx + ny * ny + nz * nz) + 1e-9
    out = dict(alpha=alpha, nx=nx / nn, ny=ny / nn, nz=nz / nn, mat=mat, x0=xmin, y1=ymax, pp=pp, ss=ss, w=w, h=h)
    if phone is not None:
        out['phone'] = (phone, -(M @ np.array([0, 0, 1.0])))
    return out


def fold_noise(h, w, seed, scale=6):
    rng = np.random.RandomState(seed)
    n = rng.randn(max(2, h // scale), max(2, w // scale)).astype(np.float32)
    n = cv2.resize(n, (w, h), interpolation=cv2.INTER_CUBIC)
    return cv2.GaussianBlur(n, (0, 0), 1.5)


def shade(p, r, lights, amb, phone_col=None):
    """lights: list of (L view-space unit vector, E rgb). returns premultiplied rgb, alpha at final res."""
    cols = material_colors(p)
    table = np.zeros((len(MAT_ID), 3))
    for k, i in MAT_ID.items():
        table[i] = cols[k]
    alb = table[r['mat']]
    h, w = r['alpha'].shape
    fold = fold_noise(h, w, p['seed'], scale=max(3, int(r['pp'] * 0.05)))
    alb = alb * (1 + 0.18 * fold[..., None])
    if p.get('_quilt'):
        yy = (np.arange(h)[:, None] / r['pp'])
        band = 0.8 + 0.2 * np.abs(np.sin(yy * np.pi / 0.11))
        alb = alb * np.where((r['mat'] == MAT_ID['top'])[..., None], band[..., None], 1.0)
    n = np.stack([r['nx'], r['ny'], r['nz']], -1)
    # cloth folds perturb normals a little
    n[..., 0] += 0.12 * fold; n /= np.linalg.norm(n, axis=-1, keepdims=True)
    E = amb[None, None] * (0.5 + 0.5 * np.clip(n[..., 1], -1, 1))[..., None]
    is_hair = (r['mat'] == MAT_ID['hair'])
    sheen = np.zeros((h, w, 3))
    for L, El in lights:
        L = np.asarray(L, float); El = np.asarray(El, float)
        ndl = n @ L
        E = E + El[None, None] * np.clip((ndl + 0.3) / 1.3, 0, None)[..., None] ** 1.5
        rim = np.clip(1 - n[..., 2], 0, 1) ** 3 * np.clip(n[..., 0] * L[0] + n[..., 1] * L[1], 0, None)
        sheen += (rim * (0.35 + 0.8 * is_hair))[..., None] * El[None, None] * 0.25
    col = alb * E + sheen
    a = r['alpha']
    rgb = col * a[..., None]
    if phone_col is not None and 'phone' in r:
        c, nph = r['phone']
        if nph[2] > 0.15:
            pp = r['pp']
            cxp = (c[0] - r['x0']) * pp; cyp = (r['y1'] - c[1]) * pp
            hw = 0.036 * pp * max(abs(nph[2]), 0.25); hh = 0.07 * pp
            ph = np.zeros((h, w), np.float32)
            cv2.rectangle(ph, (int(cxp - hw), int(cyp - hh)), (int(cxp + hw), int(cyp + hh)), 1.0, -1)
            ph = cv2.GaussianBlur(ph, (0, 0), 0.6 * r['ss'])
            ph = ph * (1 - a)          # behind the body
            rgb = rgb + ph[..., None] * np.asarray(phone_col)[None, None]
            a = np.clip(a + ph, 0, 1)
    ss = r['ss']
    W2, H2 = max(1, int(round(w / ss))), max(1, int(round(h / ss)))
    rgb = cv2.resize(rgb.astype(np.float32), (W2, H2), interpolation=cv2.INTER_AREA)
    a = cv2.resize(a.astype(np.float32), (W2, H2), interpolation=cv2.INTER_AREA)
    if p.get('blur', 0) > 0:
        k = p['blur'] * r['pp'] / ss / 120.0
        if k >= 1.0:
            ker = np.ones((1, int(round(k)) * 2 + 1), np.float32); ker /= ker.sum()
            rgb = cv2.filter2D(rgb, -1, ker); a = cv2.filter2D(a, -1, ker)
    return rgb, a


# ------------------------------------------------------------------ crowd layout (hall coordinates)
CAMS_XZ = [(-3.50, -6.38), (3.71, -7.62), (2.30, -7.27)]
PILLARS = [(X, Z) for X in (-9.0, -4.5, 0.0, 4.5) for Z in (-9.0, -4.5, 0.0, 4.5)]


def front_limit(X, option):
    """max Z allowed at lateral position X (clearance in front of screen / stair)."""
    if option == 'A2' and -6.2 < X < 2.95:
        return -0.55 - 0.85
    if 2.3 <= X <= 5.2:
        return 2.95 - 1.05              # in front of the stair landing
    if X > 5.2:
        return 2.35                     # lower flight
    return 2.95 - 0.8                   # in front of the screen plane


def density(X, Z):
    if Z > 0.2:
        return 2.1
    if Z > -2.2:
        return 1.55
    return 0.8


def layout(option, seed=11, n_try=40000):
    rng = np.random.RandomState(seed)
    pts = []
    for _ in range(n_try):
        X = rng.uniform(-7.2, 7.9); Z = rng.uniform(-4.6, 2.4)
        if Z > front_limit(X, option):
            continue
        if any(abs(X - px) < 0.62 and abs(Z - pz) < 0.62 for px, pz in PILLARS):
            continue
        if any(np.hypot(X - cx, Z - cz) < 4.4 for cx, cz in CAMS_XZ):
            continue
        dens = density(X, Z)
        rmin = max(0.52, 1.0 / np.sqrt(dens) * 0.8)
        if any((X - a) ** 2 + (Z - b) ** 2 < rmin ** 2 for a, b in pts):
            continue
        if rng.rand() > dens / 2.1:
            continue
        pts.append((X, Z))
    people = []
    singer = np.array([3.3, 3.55])
    for i, (X, Z) in enumerate(pts):
        # attention: singer for the right half, screen for the rest
        if X > 1.2 or option == 'B':
            tgt = singer if X > 0.3 else np.array([1.4 if option == 'B' else X * 0.6 - 1.0, 3.0])
        else:
            tgt = np.array([X * 0.55 - 0.9, 3.0 if option != 'A2' else -0.55])
        yaw = np.arctan2(tgt[0] - X, tgt[1] - Z) + rng.normal(0, 0.18)
        people.append(dict(X=X, Z=Z, yaw=yaw, seed=5000 + i))
    # small conversation groups: turn close neighbours towards each other
    for i, a in enumerate(people):
        if rng.rand() < 0.22:
            d = [(np.hypot(a['X'] - b['X'], a['Z'] - b['Z']), j) for j, b in enumerate(people) if j != i]
            dmin, j = min(d)
            if dmin < 1.0:
                b = people[j]
                ya = np.arctan2(b['X'] - a['X'], b['Z'] - a['Z'])
                a['yaw'] = 0.55 * a['yaw'] + 0.45 * ya
                b['yaw'] = 0.55 * b['yaw'] + 0.45 * (ya + np.pi)
    return people
