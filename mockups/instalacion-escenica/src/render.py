"""Night-time mock-up renderer: relights the original photos with proxy geometry.

Stage 1 (bake): ray-cast proxy geometry, compute unit-intensity light maps
(screen spill with soft pillar shadows, stair back light, planar floor
reflection, volumetric haze) and cache them.
Stage 2 (compose): combine with the photo-derived albedo, tone-map, grade.

Usage: python3 render.py <photo 1|2|3> <option A|B> [out.png] [--rebake]
"""
import os, sys, time
import numpy as np
import cv2
from scipy.ndimage import map_coordinates, gaussian_filter
from scene import *
from content import content, srgb_to_lin
import teorema
from performer import place as place_performer

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.environ.get('MOCKUP_SRC', os.path.join(HERE, '..', 'fotos'))
CACHE = os.environ.get('MOCKUP_CACHE', os.path.join(HERE, '..', '.cache'))
W, H = 1280, 960

OPTIONS = {
    'A': dict(x0=2.54 - 8.0, x1=2.54, y0=0.0, y1=4.0),   # 8 x 4 m landscape, from the stair edge to the left
    'B': dict(x0=0.17, x1=2.17, y0=0.0, y1=5.0),         # 2 x 5 m portrait, next to the stair
}
FRAME_X0 = 2.54 - 8.0     # fluid content defined in hall coordinates -> same pattern scale in both options
CONTENT = os.environ.get('MOCKUP_CONTENT', 'teorema')
SINGER_FEET = np.array([3.30, 1.85, 3.55])   # on the stair landing, right in front of the back light

# stair back light ("contra"): top of the upper flight, aimed down the stairs towards camera
SPOT_POS = np.array([3.28, 4.38, 6.55])
SPOT_TGT = np.array([3.10, 0.0, -1.0])
SPOT_COL = np.array([1.0, 0.84, 0.66])
SPOT_INNER, SPOT_OUTER = np.deg2rad(8.0), np.deg2rad(30.0)

# image regions holding window glass (bright pixels inside become night sky)
WINDOW_BOXES = {
    1: [(885, 345, 985, 490), (1065, 300, 1280, 495), (655, 380, 710, 480), (760, 370, 780, 480),
        (135, 385, 265, 480), (250, 395, 330, 470), (320, 395, 345, 470), (410, 395, 470, 460)],
    2: [(1030, 365, 1095, 530), (1135, 330, 1195, 535), (0, 380, 125, 565), (175, 440, 220, 520),
        (345, 445, 450, 525), (560, 440, 740, 500), (240, 430, 270, 470)],
    3: [(1200, 240, 1280, 485), (660, 365, 760, 400), (120, 230, 165, 480), (480, 360, 500, 520),
        (560, 420, 580, 540), (640, 435, 760, 520)],
}
PERSON = {1: [(577, 377), (582, 377), (585, 383), (584, 388), (589, 391), (592, 398), (594, 408), (595, 413),
              (591, 415), (588, 411), (588, 422), (587, 446), (580, 446), (578.5, 432), (577, 446), (570, 446),
              (570.5, 421), (569.5, 410), (570, 398), (572, 391), (576, 388), (575, 383)]}


def srgb_encode(x):
    x = np.clip(x, 0, 1)
    return np.where(x <= 0.0031308, 12.92 * x, 1.055 * np.power(x, 1 / 2.4) - 0.055)


def lum(x):
    return x[..., 0] * 0.2126 + x[..., 1] * 0.7152 + x[..., 2] * 0.0722


def blur(x, s, sy=None):
    sy = s if sy is None else sy
    if x.ndim == 3:
        return np.stack([cv2.GaussianBlur(x[..., c].astype(np.float32), (0, 0), sigmaX=s, sigmaY=sy) for c in range(x.shape[2])], -1)
    return cv2.GaussianBlur(x.astype(np.float32), (0, 0), sigmaX=s, sigmaY=sy)


def aces(x):
    a, b, c, d, e = 2.51, 0.03, 2.43, 0.59, 0.14
    return np.clip((x * (a * x + b)) / (x * (c * x + d) + e), 0, 1)


# ---------------------------------------------------------------- screen light
def scr_color(scr, X, Y):
    """linear RGB shown by the screen at hall coordinates X, Y."""
    if CONTENT == 'teorema':
        opt = 'A' if (scr.x1 - scr.x0) > (scr.y1 - scr.y0) else 'B'
        return teorema.sample(opt, (X - scr.x0) / (scr.x1 - scr.x0), (scr.y1 - Y) / (scr.y1 - scr.y0))
    return content(X - FRAME_X0, Y)


def screen_samples(scr, nx, ny):
    xs = scr.x0 + (np.arange(nx) + 0.5) / nx * (scr.x1 - scr.x0)
    ys = scr.y0 + (np.arange(ny) + 0.5) / ny * (scr.y1 - scr.y0)
    X, Y = np.meshgrid(xs, ys)
    Q = np.stack([X.ravel(), Y.ravel(), np.full(X.size, scr.z)], -1)
    cw, ch = (scr.x1 - scr.x0) / nx, (scr.y1 - scr.y0) / ny
    L = []
    for q in Q:
        gx, gy = np.meshgrid(np.linspace(q[0] - cw / 2, q[0] + cw / 2, 9), np.linspace(q[1] - ch / 2, q[1] + ch / 2, 9))
        L.append(scr_color(scr, gx, gy).reshape(-1, 3).mean(0))
    return Q, np.array(L), cw * ch


def screen_irradiance(P, n, Q, L, dA, occ=None, chunk=30000):
    """irradiance from the emissive screen (Lambertian emitter), optional hard occluders."""
    N = P.shape[0]
    E = np.zeros((N, 3))
    for s in range(0, N, chunk):
        p = P[s:s + chunk]; nn = n[s:s + chunk]
        v = Q[None, :, :] - p[:, None, :]
        r2 = (v * v).sum(-1) + 0.04
        r = np.sqrt(r2)
        vn = v / r[..., None]
        cos_r = np.clip((vn * nn[:, None, :]).sum(-1), 0, None)
        cos_s = np.clip(vn[..., 2], 0, None)          # screen normal is -Z
        w = cos_r * cos_s / r2 * dA / np.pi
        if occ:
            pp = p[:, None, :] + 0.02 * vn
            for bmin, bmax in occ:
                w = w * ~seg_blocked_box(pp, Q[None], bmin, bmax)
        E[s:s + chunk] = w @ L
    return E


# ---------------------------------------------------------------- stair spot
def spot_occluders():
    occ = [(np.array([BLOCK['x'][0], BLOCK['y'][0], BLOCK['z'][0]]), np.array([BLOCK['x'][1], BLOCK['y'][1], BLOCK['z'][1]]))]
    occ += slab_boxes()
    bw = 0.22
    occ.append((np.array([-12, 4.0, 4.5 - bw]), np.array([2.35, 5.3, 4.5 + bw])))
    occ.append((np.array([4.28, 4.0, 4.5 - bw]), np.array([12, 5.3, 4.5 + bw])))
    occ.append((np.array([2.35, 4.4, 4.5 - bw]), np.array([4.28, 5.3, 4.5 + bw])))
    occ.append((np.array([-12, 4.0, 9.0 - bw]), np.array([2.35, 5.3, 9.0 + bw])))
    occ.append((np.array([4.28, 4.0, 9.0 - bw]), np.array([12, 5.3, 9.0 + bw])))
    for bmin, bmax, bid, btag in boxes(include_caps=False):
        if bid == ID_PILLAR and abs(btag[0] - 3.0) < 5 and -1 < btag[1] < 10:
            occ.append((bmin, bmax))
    return occ


def spot_dir():
    a = SPOT_TGT - SPOT_POS
    return a / np.linalg.norm(a)


def spot_cone(P):
    v = P - SPOT_POS
    r = np.linalg.norm(v, axis=-1) + 1e-6
    c = (v @ spot_dir()) / r
    ci, co = np.cos(SPOT_INNER), np.cos(SPOT_OUTER)
    k = np.clip((c - co) / (ci - co), 0, 1)
    return k * k * (3 - 2 * k), r, v / r[..., None]


def spot_visible(P, occ, soft=True):
    """fraction of a small (0.25 m) light source visible from P."""
    offs = [np.zeros(3)]
    if soft:
        offs += [np.array(o) * 0.25 for o in ((1, 0, 0), (-1, 0, 0), (0, 0.7, 0.7), (0, -0.7, -0.7))]
    vis = np.zeros(P.shape[:-1])
    for o in offs:
        S = np.broadcast_to(SPOT_POS + o, P.shape)
        v = np.ones(P.shape[:-1], bool)
        for bmin, bmax in occ:
            v &= ~seg_blocked_box(P, S, bmin, bmax)
        v &= ~seg_blocked_flight(P, S)
        vis += v
    return vis / len(offs)


def spot_irradiance(P, n, occ, soft=True):
    cone, r, l = spot_cone(P)
    ndl = np.clip(-(l * n).sum(-1), 0, None)
    E = cone * ndl / (r * r)
    act = E > 1e-6
    vis = np.zeros_like(E)
    if act.any():
        vis[act] = spot_visible(P[act] + 0.01 * n[act], occ, soft)
    return E * vis


# ---------------------------------------------------------------- volumetrics
def make_noise3(seed=5):
    rng = np.random.RandomState(seed)
    g = rng.rand(48, 32, 48).astype(np.float32)
    g = gaussian_filter(g, 1.5, mode='wrap')
    return (g - g.mean()) / g.std()


NOISE3 = make_noise3()


def haze_density(P):
    c = np.stack([(P[..., 0] + 20) / 0.32, (P[..., 1] + 2) / 0.32, (P[..., 2] + 20) / 0.32], 0).reshape(3, -1)
    n1 = map_coordinates(NOISE3, c, order=1, mode='wrap')
    n2 = map_coordinates(NOISE3, c * 2.6 + 7, order=1, mode='wrap')
    return np.clip(1.0 + 0.75 * n1 + 0.35 * n2, 0.05, None).reshape(P.shape[:-1])


def hg(cos, g):
    return (1 - g * g) / (4 * np.pi * np.power(1 + g * g - 2 * g * cos, 1.5))


HAZE_C = np.array([3.30, 2.75, 3.9])          # haze cloud lying along the stairs
HAZE_AX = np.array([0.0, -0.62, -0.785])       # flight direction (downwards, towards camera)
HAZE_R = (3.8, 2.1)                            # semi-axes: along / across


def haze_local(P):
    v = P - HAZE_C
    a = v @ HAZE_AX
    perp = v - a[..., None] * HAZE_AX
    q = (a / HAZE_R[0]) ** 2 + (perp * perp).sum(-1) / HAZE_R[1] ** 2
    taper = 0.3 + 0.7 * np.clip((2.2 - a) / 4.4, 0, 1)
    return np.exp(-1.6 * q) * taper


def volumetric_spot(cam, t_limit, scale, occ, steps=72, g=0.62):
    """single-scattering haze from the stair spot (unit intensity).
    returns (uniform-haze map, local stair-haze map)."""
    d = ray_dirs(cam, W, H, scale)
    h, w = d.shape[:2]
    tl = np.minimum(cv2.resize(t_limit.astype(np.float32), (w, h), interpolation=cv2.INTER_NEAREST), 40.0)
    bmin = np.array([-1.5, 0.0, -9.0]); bmax = np.array([8.0, 6.6, 9.8])
    with np.errstate(divide='ignore', invalid='ignore'):
        t1 = (bmin - cam.C) / d; t2 = (bmax - cam.C) / d
    tn = np.clip(np.nan_to_num(np.minimum(t1, t2), nan=-np.inf).max(-1), 0.3, None)
    tf = np.minimum(np.nan_to_num(np.maximum(t1, t2), nan=np.inf).min(-1), tl)
    acc = np.zeros((h, w)); accl = np.zeros((h, w))
    rng = np.random.RandomState(1)
    jit = rng.rand(h, w)
    live = tf > tn
    for i in range(steps):
        t = tn + (tf - tn) * (i + jit) / steps
        dt = np.clip(tf - tn, 0, None) / steps
        P = cam.C + t[..., None] * d
        cone, r, l = spot_cone(P)
        act = (cone > 1e-4) & live
        if not act.any():
            continue
        Pa = P[act]
        vis = spot_visible(Pa, occ, soft=False)
        dens = haze_density(Pa)
        cosang = (l[act] * d[act]).sum(-1)
        ph = hg(-cosang, g)
        val = dens * cone[act] * vis / (r[act] ** 2 + 0.05) * ph * dt[act]
        acc[act] += val
        accl[act] += val * haze_local(Pa)
    return acc, accl


# ---------------------------------------------------------------- bake
def bake(photo, option):
    T0 = time.time()
    cam = get(photo)
    scr = Screen(**OPTIONS[option]) if option in OPTIONS else None
    gb = gbuffer(cam, scr)
    P, n, oid = gb['P'], gb['n'], gb['id']
    out = dict(t=gb['t'], t_scene=gb['t_scene'], id=oid, id_scene=gb['id_scene'], screen=gb['screen'], P=P.astype(np.float32),
               d=gb['d'].astype(np.float32))
    print(' gbuffer', round(time.time() - T0, 1))
    Pf, nf = P.reshape(-1, 3), n.reshape(-1, 3)
    # lighting normal for the stairs: treads face up
    nl = nf.copy()
    nl[oid.ravel() == ID_FLIGHT] = [0, 1, 0]

    # --- screen spill
    E_scr = np.zeros((H * W, 3), np.float32)
    if scr is not None:
        nx, ny = (16, 8) if option == 'A' else (4, 10)
        Q, Ls, dA = screen_samples(scr, nx, ny)
        front = (Pf[:, 2] < scr.z - 0.01) & (oid.ravel() != ID_SCREEN)
        E_scr[front] = screen_irradiance(Pf[front], nl[front], Q, Ls, dA)
        # soft shadow factor at quarter res with a coarser sample set
        q = 0.25
        gq = gbuffer(cam, scr, scale=q)
        Pq, nq = gq['P'].reshape(-1, 3), gq['n'].reshape(-1, 3)
        fq = (Pq[:, 2] < scr.z - 0.01) & (gq['id'].ravel() != ID_SCREEN)
        Q2, L2, dA2 = screen_samples(scr, 8, 4) if option == 'A' else screen_samples(scr, 2, 6)
        occ = []
        for bmin, bmax, bid, btag in boxes(include_caps=False):
            if bid == ID_PILLAR and btag[1] < scr.z and btag[1] > -10 and scr.x0 - 6 < btag[0] < scr.x1 + 6:
                occ.append((bmin, bmax))
        Es = np.zeros((Pq.shape[0], 3)); Eu = np.zeros((Pq.shape[0], 3))
        Es[fq] = screen_irradiance(Pq[fq], nq[fq], Q2, L2, dA2, occ)
        Eu[fq] = screen_irradiance(Pq[fq], nq[fq], Q2, L2, dA2)
        ratio = np.where(lum(Eu) > 1e-7, (lum(Es) + 1e-9) / (lum(Eu) + 1e-9), 1.0).reshape(gq['id'].shape)
        ratio = cv2.resize(ratio.astype(np.float32), (W, H), interpolation=cv2.INTER_LINEAR)
        ratio = blur(ratio, 2.0)
        E_scr *= ratio.reshape(-1, 1)
        out['scrQ'], out['scrL'], out['scrdA'] = Q, Ls, dA
        print(' screen light', round(time.time() - T0, 1))
    out['E_scr'] = E_scr.reshape(H, W, 3)

    # --- stair spot on surfaces
    socc = spot_occluders()
    E_spot = np.zeros(H * W, np.float32)
    act = oid.ravel() != ID_SCREEN
    E_spot[act] = spot_irradiance(Pf[act], nl[act], socc)
    out['E_spot'] = E_spot.reshape(H, W)
    print(' spot light', round(time.time() - T0, 1))

    # --- planar reflection of the polished floor (half res mirror pass)
    gm = gbuffer(cam, scr, scale=0.5, mirror=True)
    Pm, nm, idm = gm['P'].reshape(-1, 3), gm['n'].reshape(-1, 3), gm['id'].ravel()
    nlm = nm.copy(); nlm[idm == ID_FLIGHT] = [0, 1, 0]
    hm, wm = gm['id'].shape
    R_emit = np.zeros((Pm.shape[0], 3)); R_scr = np.zeros((Pm.shape[0], 3)); R_spot = np.zeros(Pm.shape[0])
    solid = (idm != ID_NONE) & (idm != ID_SCREEN)
    if scr is not None:
        s_m = idm == ID_SCREEN
        R_emit[s_m] = scr_color(scr, Pm[s_m, 0], Pm[s_m, 1])
        f2 = solid & (Pm[:, 2] < scr.z)
        R_scr[f2] = screen_irradiance(Pm[f2], nlm[f2], out['scrQ'], out['scrL'], out['scrdA'])
    R_spot[solid] = spot_irradiance(Pm[solid], nlm[solid], socc, soft=False)
    out['R_emit'] = R_emit.reshape(hm, wm, 3).astype(np.float32)
    out['R_scr'] = R_scr.reshape(hm, wm, 3).astype(np.float32)
    out['R_spot'] = R_spot.reshape(hm, wm).astype(np.float32)
    out['R_solid'] = solid.reshape(hm, wm)
    print(' reflection', round(time.time() - T0, 1))

    # --- volumetric haze from the spot (half res)
    v1, v2 = volumetric_spot(cam, gb['t'], 0.5, socc)
    out['vol'] = v1.astype(np.float32); out['vol_l'] = v2.astype(np.float32)
    print(' volumetric', round(time.time() - T0, 1))
    return out


def rebake_volume(photo, option, b):
    cam = get(photo)
    v1, v2 = volumetric_spot(cam, b['t'], 0.5, spot_occluders())
    b['vol'] = v1.astype(np.float32); b['vol_l'] = v2.astype(np.float32)
    return b


def load_or_bake(photo, option, rebake=False, revol=False):
    os.makedirs(CACHE, exist_ok=True)
    fn = os.path.join(CACHE, f'{photo}{option}.npz')
    if os.path.exists(fn) and not rebake:
        b = dict(np.load(fn))
        if revol or 'vol_l' not in b:
            b = rebake_volume(photo, option, b)
            np.savez_compressed(fn, **b)
        return b
    b = bake(photo, option)
    np.savez_compressed(fn, **b)
    return b


# ---------------------------------------------------------------- compose
DEFAULT = dict(exposure=1.0, amb=0.030, scr_disp=0.46, scr_light=1.5, spot_I=22.0, haze=0.012, haze_l=0.35, refl=0.5,
               scr_glow=0.10, src=1.0)


def compose(photo, option, b, params=None, out=None):
    p = dict(DEFAULT)
    if params:
        p.update(params)
    img = cv2.imread(os.path.join(SRC, f'{photo}.jpg'))[:, :, ::-1].astype(np.float32) / 255.0
    lin = srgb_to_lin(img)
    oid, id_scene = b['id'], b['id_scene']
    scr = Screen(**OPTIONS[option]) if option in OPTIONS else None

    # albedo: flatten the daylight distribution, keep texture
    L0 = lum(lin)
    bl = blur(L0, 30) + 0.02
    bl_floor = blur(L0, 70) + 0.02
    is_floor = id_scene == ID_FLOOR
    k = np.where(is_floor, 0.95, 0.72)
    base = np.where(is_floor, bl_floor, bl)
    albedo = np.clip(lin * np.power(0.22 / base, k)[..., None], 0, 0.9)

    hsv = cv2.cvtColor((img * 255).astype(np.uint8)[:, :, ::-1], cv2.COLOR_BGR2HSV).astype(np.float32) / 255.0
    V, S = hsv[..., 2], hsv[..., 1]
    wreg = np.zeros((H, W), np.float32)
    for x0, y0, x1, y1 in WINDOW_BOXES.get(photo, []):
        wreg[y0:y1, x0:x1] = 1
    glass = np.clip((V - 0.55) / 0.2, 0, 1) * np.clip((0.4 - S) / 0.15, 0, 1) * wreg
    glass *= (id_scene != ID_PILLAR) & (id_scene != ID_FLOOR)
    glass = blur(glass, 0.7)
    tube = ((hsv[..., 0] * 180 > 10) & (hsv[..., 0] * 180 < 40) & (S > 0.4) & (V > 0.78)).astype(np.float32)
    tube *= (np.arange(H)[:, None] < 520)
    tube = np.clip(blur(cv2.dilate(tube, np.ones((3, 3))), 1.2) * 1.5, 0, 1)
    albedo = albedo * (1 - tube[..., None]) + tube[..., None] * 0.10

    # lighting
    amb_map = np.clip(blur(L0, 60) / L0.mean(), 0.35, 2.2)
    E_amb = p['amb'] * np.array([0.52, 0.66, 1.0]) * (0.45 + 0.55 * amb_map[..., None])
    E_scr = b['E_scr'] * p['scr_light']
    E_spot = b['E_spot'][..., None] * SPOT_COL * p['spot_I']
    E_spot = E_spot * np.where(id_scene == ID_FLIGHT, 0.35, 1.0)[..., None]   # camera sees mostly risers
    E_spot = 0.5 * blur(E_spot, 1.0) + 0.5 * blur(E_spot, 5.0)
    E = E_amb + E_scr + E_spot
    col = albedo * E

    vol_full = cv2.resize(b['vol'] * p['haze'] + b['vol_l'] * p['haze_l'], (W, H), interpolation=cv2.INTER_CUBIC)

    if photo in PERSON:
        pm = np.zeros((H, W), np.uint8)
        cv2.fillPoly(pm, [np.round(np.array(PERSON[photo]) * 4).astype(np.int32)], 1, lineType=cv2.LINE_AA, shift=2)
        pm = blur(pm.astype(np.float32), 0.6)
        rim = np.clip(pm - cv2.erode(pm, np.ones((3, 3))), 0, 1)
        rim *= np.clip(1.2 - (np.arange(H)[:, None] - 377) / 70.0, 0.25, 1)
        col = col * (1 - pm[..., None]) + pm[..., None] * albedo * E_amb * 0.5
        col += rim[..., None] * SPOT_COL * 0.5

    sky = np.array([0.008, 0.013, 0.032]) * (0.7 + 0.6 * np.clip(L0 / 0.8, 0, 1))[..., None]
    col = col * (1 - glass[..., None]) + glass[..., None] * sky

    # emissive LED screen
    emissive_full = np.zeros((H, W, 3), np.float32)
    if scr is not None:
        sm = b['screen']
        Ps = b['P'][sm].astype(np.float64)
        c = scr_color(scr, Ps[:, 0], Ps[:, 1]) * p['scr_disp']
        u = Ps[:, 0] - scr.x0; v = Ps[:, 1] - scr.y0
        seam = np.minimum(np.abs((u + 0.25) % 0.5 - 0.25), np.abs((v + 0.25) % 0.5 - 0.25))
        c *= (0.94 + 0.06 * np.clip(seam / 0.012, 0, 1))[:, None]
        edge = np.minimum.reduce([u, scr.x1 - scr.x0 - u, v, scr.y1 - scr.y0 - v])
        c *= np.clip((edge - 0.025) / 0.015, 0, 1)[:, None]
        emissive_full[sm] = c
        smf = sm.astype(np.float32)
        smask = blur(smf, 0.5)
        em = blur(emissive_full, 0.5) / np.maximum(blur(smf, 0.5), 1e-3)[..., None]
        col = col * (1 - smask[..., None]) + smask[..., None] * em

    # floor reflection
    floor = blur((oid == ID_FLOOR).astype(np.float32), 0.8)
    hm, wm = b['R_spot'].shape
    albedo_c = np.array([0.30, 0.27, 0.24])
    refl = b['R_emit'] * p['scr_disp'] + albedo_c * (b['R_scr'] * p['scr_light'] + b['R_spot'][..., None] * SPOT_COL * p['spot_I'])
    refl = refl + b['R_solid'][..., None] * albedo_c * p['amb'] * np.array([0.52, 0.66, 1.0]) * 0.6
    refl = cv2.resize(refl.astype(np.float32), (W, H), interpolation=cv2.INTER_LINEAR)
    refl = 0.55 * blur(refl, 2.0, 8) + 0.45 * blur(refl, 6, 22)
    cosv = np.clip(-b['d'][..., 1], 0, 1)
    fres = 0.04 + 0.96 * np.power(1 - cosv, 5)
    polish = np.clip(0.6 + 1.2 * (blur(L0, 2.5) / bl_floor - 1.0), 0.3, 1.3)
    col = col + refl * (p['refl'] * np.clip(fres * 2.2, 0, 1) * polish * floor)[..., None]

    # haze: spot volumetric + soft atmospheric glow around the screen
    vol = np.clip(vol_full, 0, None) * p['spot_I']
    col = col + blur(vol, 1.0)[..., None] * SPOT_COL
    if scr is not None:
        g1 = blur(emissive_full, 25) * 0.6 + blur(emissive_full, 70) * 0.4
        col = col + g1 * p['scr_glow']

    cam = get(photo)
    # the singer on the landing: backlit silhouette with a warm rim
    sm_, sdist = place_performer(cam, SINGER_FEET, W, H)
    sm_ = sm_ * (b['t'] > sdist - 0.3)
    if sm_.max() > 0:
        q_src = cam.project(SPOT_POS[None])[0]
        er = cv2.erode(sm_, np.ones((3, 3)))
        edge = np.clip(sm_ - er, 0, 1)
        gy_, gx_ = np.gradient(blur(sm_, 1.2))
        yy_, xx_ = np.mgrid[0:H, 0:W]
        dx, dy = q_src[0] - xx_, q_src[1] - yy_
        dn = np.sqrt(dx * dx + dy * dy) + 1e-3
        facing = np.clip(-(gx_ * dx + gy_ * dy) / (np.sqrt(gx_ ** 2 + gy_ ** 2) + 1e-6) / dn, 0, 1)
        rim = edge * (0.35 + 0.65 * facing) * np.exp(-dn / 160.0)
        dark = albedo * E_amb * 0.35
        col = col * (1 - sm_[..., None]) + sm_[..., None] * (dark + 0.25 * blur(vol, 1.0)[..., None] * SPOT_COL)
        col += rim[..., None] * SPOT_COL * 1.4
    # the fixture itself (frontal to camera): small hot core, occluded by geometry in front
    q = cam.project(SPOT_POS[None])[0]
    dist = np.linalg.norm(SPOT_POS - cam.C)
    xi, yi = int(round(q[0])), int(round(q[1]))
    if 0 <= xi < W and 0 <= yi < H:
        yy, xx = np.mgrid[0:H, 0:W]
        occl = blur((b['t_scene'] < dist - 0.4).astype(np.float32), 1.0) if 't_scene' in b else 0
        cone = spot_cone(cam.C[None])[0][0]
        core = np.exp(-((xx - q[0]) ** 2 + (yy - q[1]) ** 2) / (2 * 1.6 ** 2))
        halo = np.exp(-np.sqrt((xx - q[0]) ** 2 + (yy - q[1]) ** 2) / 22.0)
        vis = (1 - (occl if np.isscalar(occl) else occl)) * (1 - blur(sm_, 1.0))
        col += ((core * 60 + halo * 0.35) * vis * p['src'] * (0.25 + cone))[..., None] * SPOT_COL

    hdr = col * p['exposure']
    bright = np.clip(hdr - 0.5, 0, None)
    bloom = 0.5 * blur(bright, 3) + 0.35 * blur(bright, 12) + 0.25 * blur(bright, 36) + 0.15 * blur(bright, 90)
    hdr = hdr + bloom * 0.5
    o = aces(hdr * 1.5) * np.array([0.975, 0.99, 1.035])
    yy, xx = np.mgrid[0:H, 0:W]
    vig = 1 - 0.25 * (((xx - W / 2) / (W / 2)) ** 2 + ((yy - H / 2) / (H / 2)) ** 2) ** 1.4
    o = srgb_encode(o * vig[..., None])
    rng = np.random.RandomState(7)
    o = np.clip(o + rng.randn(H, W, 1) * 0.010 + rng.randn(H, W, 3) * 0.005, 0, 1)
    res = (o * 255 + 0.5).astype(np.uint8)
    if out:
        cv2.imwrite(out, res[:, :, ::-1])
    return res


if __name__ == '__main__':
    ph = int(sys.argv[1]); opt = sys.argv[2]
    args = [a for a in sys.argv[3:] if not a.startswith('--')]
    out = args[0] if args else os.path.join(HERE, 'out', f'{ph}{opt}.png')
    t0 = time.time()
    b = load_or_bake(ph, opt, rebake='--rebake' in sys.argv)
    compose(ph, opt, b, out=out)
    print('done', ph, opt, round(time.time() - t0, 1))
