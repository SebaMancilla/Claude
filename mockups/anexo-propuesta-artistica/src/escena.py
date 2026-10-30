"""Escenas de exhibición: sala oscura con la proyección del prototipo y público a escala real.

Reutiliza las figuras antropométricas de ../instalacion-escenica/src/crowd.py (esqueleto 3D,
ropa y pose, vistas desde el ángulo real de la cámara) y la cámara de cam.py. La sala se calcula
por píxel: la proyección es la única fuente de luz importante (más un ambiente muy bajo), con
reflejo difuso en el piso pulido, haz del proyector en la neblina y sombras de contacto.

Uso: python3 src/escena.py [amplia|cercana]
"""
import json
import sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT.parent / 'instalacion-escenica' / 'src'))
import crowd  # noqa: E402
from cam import Cam  # noqa: E402

W, H = 3000, 2121                       # proporción A4 apaisada
SX0, SX1, SY0, SY1 = -3.2, 3.2, 0.62, 4.22   # proyección 6,4 × 3,6 m sobre el muro z = 0
XL, XR, YC = -7.2, 7.2, 4.9             # muros laterales y cielo
EMIT = 1.0                              # radiancia de la proyección (blanco del prototipo ≈ 0,85 lineal)
RED = (201, 36, 28)
FONT = str(ROOT / 'assets/fonts/IBMPlexMono-Regular.ttf')


def srgb_to_lin(x):
    return np.where(x <= 0.04045, x / 12.92, ((x + 0.055) / 1.055) ** 2.4)


def lin_to_srgb(x):
    x = np.clip(x, 0, 1)
    return np.where(x <= 0.0031308, 12.92 * x, 1.055 * np.power(x, 1 / 2.4) - 0.055)


def aces(x):
    a, b, c, d, e = 2.51, 0.03, 2.43, 0.59, 0.14
    return np.clip((x * (a * x + b)) / (x * (c * x + d) + e), 0, 1)


def gblur(x, s, sy=None):
    sy = s if sy is None else sy
    if x.ndim == 3:
        return np.stack([cv2.GaussianBlur(x[..., c], (0, 0), s, sigmaY=sy) for c in range(x.shape[2])], -1)
    return cv2.GaussianBlur(x, (0, 0), s, sigmaY=sy)


# ------------------------------------------------------------------ geometría de la sala
def rays(cam, w, h):
    s = W / w
    x = (np.arange(w) + 0.5) * s
    y = (np.arange(h) + 0.5) * s
    X, Y = np.meshgrid(x, y)
    d = np.stack([(X - cam.cx) / cam.f, -(Y - cam.cy) / cam.f, np.ones_like(X)], -1)
    d = d @ cam.R            # = (R.T @ d.T).T
    return d / np.linalg.norm(d, axis=-1, keepdims=True)


def hit_room(o, d):
    """t, normal y tipo (0 piso, 1 muro proyección, 2 muros laterales, 3 cielo)."""
    big = 1e9
    with np.errstate(divide='ignore', invalid='ignore'):
        tf = np.where(d[..., 1] < 0, -o[1] / d[..., 1], big)
        tc = np.where(d[..., 1] > 0, (YC - o[1]) / d[..., 1], big)
        tb = np.where(d[..., 2] > 0, -o[2] / d[..., 2], big)
        tl = np.where(d[..., 0] < 0, (XL - o[0]) / d[..., 0], big)
        tr = np.where(d[..., 0] > 0, (XR - o[0]) / d[..., 0], big)
    T = np.stack([tf, tb, np.minimum(tl, tr), tc], -1)
    kind = np.argmin(T, -1)
    t = np.take_along_axis(T, kind[..., None], -1)[..., 0]
    P = o + d * t[..., None]
    n = np.zeros_like(P)
    n[kind == 0] = (0, 1, 0)
    n[kind == 1] = (0, 0, -1)
    n[kind == 3] = (0, -1, 0)
    side = kind == 2
    n[side] = np.where((P[side][:, 0] < 0)[:, None], [1, 0, 0], [-1, 0, 0])
    return t, P, n, kind


def screen_patches(tex, nx=20, ny=12):
    h, w = tex.shape[:2]
    small = cv2.resize(tex, (nx, ny), interpolation=cv2.INTER_AREA)
    xs = SX0 + (np.arange(nx) + 0.5) / nx * (SX1 - SX0)
    ys = SY1 - (np.arange(ny) + 0.5) / ny * (SY1 - SY0)
    Q = np.array([[x, y, 0.0] for y in ys for x in xs])
    L = small.reshape(-1, 3) * EMIT
    dA = (SX1 - SX0) * (SY1 - SY0) / (nx * ny)
    return Q, L, dA


def irradiance(P, n, Q, L, dA):
    E = np.zeros(P.shape[:-1] + (3,), np.float32)
    for q, l in zip(Q, L):
        v = q - P
        d2 = np.maximum((v * v).sum(-1), 0.04)
        d = np.sqrt(d2)
        cp = np.clip((v * n).sum(-1) / d, 0, None)
        cs = np.clip(v[..., 2] / d, 0, None)           # normal de la pantalla: (0, 0, -1)
        E += (cp * cs * dA / (np.pi * d2))[..., None] * l
    return E


# ------------------------------------------------------------------ objetos
def box_faces(b0, b1):
    x0, y0, z0 = b0
    x1, y1, z1 = b1
    return [
        (np.array([[x0, y0, z0], [x1, y0, z0], [x1, y1, z0], [x0, y1, z0]]), np.array([0, 0, -1.0])),
        (np.array([[x0, y1, z0], [x1, y1, z0], [x1, y1, z1], [x0, y1, z1]]), np.array([0, 1.0, 0])),
        (np.array([[x0, y0, z0], [x0, y0, z1], [x0, y1, z1], [x0, y1, z0]]), np.array([-1.0, 0, 0])),
        (np.array([[x1, y0, z0], [x1, y0, z1], [x1, y1, z1], [x1, y1, z0]]), np.array([1.0, 0, 0])),
        (np.array([[x0, y0, z1], [x1, y0, z1], [x1, y1, z1], [x0, y1, z1]]), np.array([0, 0, 1.0])),
    ]


def draw_box(img, cam, b0, b1, albedo, Q, L, dA, emit_top=None):
    for quad, n in box_faces(b0, b1):
        c = quad.mean(0)
        if (cam.C - c) @ n <= 0:
            continue
        pts = cam.project(quad)
        mask = np.zeros(img.shape[:2], np.float32)
        cv2.fillPoly(mask, [np.round(pts * 4).astype(np.int32)], 1.0, cv2.LINE_AA, shift=2)
        if n[1] > 0.5 and emit_top is not None:
            col = emit_top
        else:
            E = irradiance(c[None], n[None], Q, L, dA)[0]
            col = albedo * (E + 0.004)
        img[:] = img * (1 - mask[..., None]) + mask[..., None] * col


# ------------------------------------------------------------------ escenas
SCENES = {
    'amplia': dict(
        cam=dict(f=2350, C=(0.3, 1.62, -8.9), yaw=-0.02, pitch=0.075, roll=0.0),
        projector=(0.0, 4.5, -11.5),
        people=[  # (semilla, X, Z, yaw, pose)
            (11, -0.35, -2.7, 0.05, 'reach'), (23, 1.25, -3.3, -0.12, 'crossed'), (31, 1.95, -3.55, -0.75, 'pockets'),
            (47, -2.35, -4.1, 0.18, 'phone'), (52, -3.05, -3.35, 0.1, 'back'), (64, 3.55, -2.3, -0.08, 'down'),
            (71, 0.75, -5.05, 0.05, 'onepocket'), (95, -3.55, -2.85, 0.15, 'down'), (103, 4.6, -4.6, -0.3, 'drink'),
            (117, -1.6, -4.9, 0.1, 'pockets'),
        ],
        gesture=11,
    ),
    'cercana': dict(
        cam=dict(f=1900, C=(-2.1, 1.48, -6.7), yaw=0.2, pitch=0.11, roll=0.0),
        projector=(0.0, 4.5, -11.5),
        texture='12_proyeccion_mapa.png',
        people=[
            (11, -0.35, -2.7, 0.05, 'reach'), (23, 1.25, -3.3, -0.12, 'crossed'), (31, 1.95, -3.55, -0.75, 'pockets'),
            (64, 3.55, -2.3, -0.08, 'down'), (71, 0.95, -4.75, 0.05, 'onepocket'), (52, -2.6, -3.0, 0.25, 'back'),
        ],
        gesture=11,
        pedestal=False,
    ),
}
PEDESTAL = ((-3.82, 0.0, -2.45), (-3.32, 1.05, -1.95))
SPEAKERS = [((-4.35, 0.0, -0.75), (-4.0, 1.55, -0.45)), ((4.0, 0.0, -0.75), (4.35, 1.55, -0.45))]
SENSOR = ((-0.12, 0.42, -0.35), (0.12, 0.5, -0.27))


def local_to_world(spec, v):
    # crowd.raster dibuja el eje x local espejado respecto del mundo: se replica aquí para que
    # la capa de seguimiento y el gesto coincidan con la silueta.
    lx, ly, lz = crowd.local_to_world_dir(spec)
    return np.array([spec['X'], 0.0, spec['Z']]) - v[0] * lx + v[1] * ly + v[2] * lz


def roi_affine(A, cw, ch):
    C = np.array([[0, 0, 1], [cw, 0, 1], [0, ch, 1], [cw, ch, 1]], float)
    q = C @ A.T
    x0 = int(max(0, np.floor(q[:, 0].min()) - 2)); x1 = int(min(W, np.ceil(q[:, 0].max()) + 2))
    y0 = int(max(0, np.floor(q[:, 1].min()) - 2)); y1 = int(min(H, np.ceil(q[:, 1].max()) + 2))
    if x1 <= x0 or y1 <= y0:
        return None
    Ar = A.copy(); Ar[0, 2] -= x0; Ar[1, 2] -= y0
    return x0, y0, x1, y1, Ar


def billboard(cam, sp):
    """colocación en la imagen del cartel de crowd.raster: (pie, px/m, derecha, arriba, M local→cartel)."""
    feet = np.array([sp['X'], 0.0, sp['Z']])
    q = cam.project(feet[None])[0]
    qh = cam.project((feet + [0, sp['H'], 0])[None])[0]
    ppm = cam.f / cam.cam(feet[None])[0, 2]
    up = (qh - q) / (np.linalg.norm(qh - q) + 1e-9)
    right = np.array([-up[1], up[0]])
    xv, yv, zv = crowd.view_basis(sp, cam.C)
    lx, ly, lz = crowd.local_to_world_dir(sp)
    M = np.array([[lx @ xv, ly @ xv, lz @ xv], [lx @ yv, ly @ yv, lz @ yv], [lx @ zv, ly @ zv, lz @ zv]])
    return q, ppm, right, up, M


def render(name, texture):
    S = SCENES[name]
    cam = Cam(**S['cam'], cx=W / 2, cy=H / 2)
    o = np.array(cam.C)
    tex = srgb_to_lin(cv2.imread(str(texture))[..., ::-1].astype(np.float32) / 255)
    th, tw = tex.shape[:2]

    specs = [crowd.make_person(seed, X, Z, yaw, group_pose=pose) for seed, X, Z, yaw, pose in S['people']]
    for sp in specs:
        crowd.parts_local(sp)                       # fija las articulaciones (_joints)
    g = next(sp for sp in specs if sp['seed'] == S['gesture'])
    g_place = billboard(cam, g)
    def bb(v_):
        gq, gppm, gright, gup, GM = g_place
        xb, yb, _ = GM @ np.asarray(v_, float)
        return gq + gppm * (xb * gright + yb * gup)
    # el gesto se prolonga en la imagen, en la dirección del antebrazo, hasta la proyección
    wrist, elbow = bb(g['_joints'][1][2]), bb(g['_joints'][1][1])
    du = (wrist - elbow) / (np.linalg.norm(wrist - elbow) + 1e-9)
    px_ = wrist + du * 0.13 * W
    rd = cam.ray(*px_)
    aim = cam.C + rd * (-cam.C[2] / rd[2])
    aim = np.array([np.clip(aim[0], SX0 + 0.3, SX1 - 0.3), np.clip(aim[1], SY0 + 0.3, SY1 - 0.3), 0.0])
    # el gesto toma la palabra más cercana al punto señalado (posiciones guardadas por capturas.mjs)
    u = (aim[0] - SX0) / (SX1 - SX0) * tw
    v = (SY1 - aim[1]) / (SY1 - SY0) * th
    words = json.loads(Path(texture).with_suffix('.json').read_text())
    k_css = tw / 1600
    tgt = min(words, key=lambda w_: (w_['x'] * k_css - u) ** 2 + (w_['y'] * k_css - v) ** 2)
    u, v = tgt['x'] * k_css, tgt['y'] * k_css
    aim = np.array([SX0 + u / tw * (SX1 - SX0), SY1 - v / th * (SY1 - SY0), 0.0])
    # cursor de pinza del prototipo (círculo y cruz), a mayor escala para leerse en la sala
    tex8 = (lin_to_srgb(tex) * 255).astype(np.uint8).copy()
    rr = int(th * 0.032)
    lw_t = max(3, th // 450)
    cv2.circle(tex8, (int(u), int(v)), rr, RED, lw_t, cv2.LINE_AA)
    cv2.line(tex8, (int(u - rr * .55), int(v)), (int(u + rr * .55), int(v)), RED, lw_t, cv2.LINE_AA)
    cv2.line(tex8, (int(u), int(v - rr * .55)), (int(u), int(v + rr * .55)), RED, lw_t, cv2.LINE_AA)
    tex = srgb_to_lin(tex8.astype(np.float32) / 255)
    Q, L, dA = screen_patches(tex)

    # --- sala a baja resolución (luz difusa) y tipo de superficie a resolución completa
    lw, lh = W // 4, H // 4
    d = rays(cam, lw, lh)
    t, P, n, kind = hit_room(o, d)
    E = irradiance(P, n, Q, L, dA)
    alb = np.zeros_like(E)
    alb[kind == 0] = (0.16, 0.155, 0.15)
    alb[kind == 1] = (0.42, 0.42, 0.41)
    alb[kind == 2] = (0.07, 0.07, 0.072)
    alb[kind == 3] = (0.03, 0.03, 0.03)
    room = alb * (E + 0.0035)
    room = cv2.resize(room, (W, H), interpolation=cv2.INTER_CUBIC)
    dF = rays(cam, W, H)
    _, PF, _, kindF = hit_room(o, dF)
    floor = (kindF == 0).astype(np.float32)

    # --- proyección (imagen) y su reflejo en el piso pulido
    corners = np.array([[SX0, SY1, 0], [SX1, SY1, 0], [SX1, SY0, 0], [SX0, SY0, 0]], float)
    src = np.float32([[0, 0], [tw, 0], [tw, th], [0, th]])
    Hs = cv2.getPerspectiveTransform(src, np.float32(cam.project(corners)))
    scr = cv2.warpPerspective(tex, Hs, (W, H), flags=cv2.INTER_AREA)
    smask = cv2.warpPerspective(np.ones((th, tw), np.float32), Hs, (W, H))
    mir = corners * [1, -1, 1]
    Hm = cv2.getPerspectiveTransform(src, np.float32(cam.project(mir)))
    refl = cv2.warpPerspective(tex, Hm, (W, H), flags=cv2.INTER_AREA)
    refl = gblur(refl, 10, 38) * floor[..., None]
    fres = np.clip(0.03 + 0.12 * np.exp(-np.abs(PF[..., 2]) / 6.0), 0, 1)[..., None]
    refl = refl * fres * EMIT

    img = room * (1 - smask[..., None]) + scr * EMIT * smask[..., None]

    # --- objetos: parlantes, pedestal con pantalla táctil y cámara del gesto
    for b0, b1 in SPEAKERS:
        draw_box(img, cam, b0, b1, np.array([0.05, 0.05, 0.05]), Q, L, dA)
    if S.get('pedestal', True):
        draw_box(img, cam, *PEDESTAL, np.array([0.7, 0.7, 0.68]), Q, L, dA, emit_top=np.array([0.55, 0.53, 0.5]))
    draw_box(img, cam, *SENSOR, np.array([0.03, 0.03, 0.03]), Q, L, dA)

    # --- haz del proyector en la neblina (baja resolución)
    pj = np.array(S['projector'])
    beam = np.zeros((lh, lw, 3), np.float32)
    tsmall = cv2.resize(tex, (96, 54), interpolation=cv2.INTER_AREA)
    steps = 56
    for i in range(steps):
        tt = t * (i + 0.5) / steps
        Pp = o + d * tt[..., None]
        sv = Pp - pj
        lam = -pj[2] / np.where(np.abs(sv[..., 2]) < 1e-6, 1e-6, sv[..., 2])
        hx = pj[0] + lam * sv[..., 0]
        hy = pj[1] + lam * sv[..., 1]
        inside = (lam > 1) & (hx > SX0) & (hx < SX1) & (hy > SY0) & (hy < SY1)
        ui = np.clip(((hx - SX0) / (SX1 - SX0) * 95).astype(int), 0, 95)
        vi = np.clip(((SY1 - hy) / (SY1 - SY0) * 53).astype(int), 0, 53)
        col = tsmall[vi, ui]
        dens = 1 + 0.7 * np.sin(Pp[..., 0] * 1.7 + Pp[..., 1] * 2.3) * np.sin(Pp[..., 2] * 1.3 - Pp[..., 0] * 0.6) \
            + 0.35 * np.sin(Pp[..., 0] * 5.1 - Pp[..., 2] * 3.7)
        dist2 = (sv * sv).sum(-1)
        beam += (inside * dens * (t / steps) / dist2 * 0.22)[..., None] * col
    beam = cv2.resize(gblur(beam, 1.2), (W, H), interpolation=cv2.INTER_CUBIC)

    # --- público
    occ_refl = np.zeros((H, W), np.float32)
    shadow = np.zeros((H, W), np.float32)
    layers = []
    clusters = []
    order = np.argsort(Q[:, 0])
    for part in np.array_split(order, 3):
        clusters.append((Q[part], L[part], Q[part].mean(0)))
    amb = np.array([0.02, 0.021, 0.026])
    for sp in specs:
        feet = np.array([sp['X'], 0.0, sp['Z']])
        zc = cam.cam(feet[None])[0, 2]
        q = cam.project(feet[None])[0]
        qh = cam.project((feet + [0, sp['H'], 0])[None])[0]
        ppm = cam.f / zc
        ss = 3 if ppm * sp['H'] < 160 else 2
        r = crowd.raster(sp, cam.C, ppm, ss=ss, noise_seed=sp['seed'])
        xv, yv, zv = crowd.view_basis(sp, cam.C)
        tv = lambda vv: np.array([vv @ xv, vv @ yv, vv @ zv])
        chest = np.array([sp['X'], 0.72 * sp['H'], sp['Z']])
        lights = []
        for Qc, Lc, cc in clusters:
            dv = cc - chest
            dn = dv / np.linalg.norm(dv)
            Ec = irradiance(chest[None], dn[None], Qc, Lc, dA)[0] * 2.6
            lights.append((tv(dn), Ec))
        rgb, a = crowd.shade(sp, r, lights, amb, phone_col=np.array([0.6, 0.62, 0.66]))
        ch, cw = a.shape
        up = (qh - q) / (np.linalg.norm(qh - q) + 1e-9)
        right = np.array([-up[1], up[0]])
        A = np.zeros((2, 3)); A[:, 0] = right; A[:, 1] = -up
        A[:, 2] = q + ppm * r['x0'] * right + ppm * r['y1'] * up + 0.5 * right - 0.5 * up
        roi = roi_affine(A, cw, ch)
        if roi is None:
            continue
        x0, y0, x1, y1, Ar = roi
        a_w = cv2.warpAffine(a, Ar, (x1 - x0, y1 - y0), flags=cv2.INTER_LINEAR)
        rgb_w = cv2.warpAffine(rgb, Ar, (x1 - x0, y1 - y0), flags=cv2.INTER_LINEAR)
        layers.append((zc, x0, y0, x1, y1, a_w, rgb_w))
        Am = np.zeros((2, 3)); Am[:, 0] = right; Am[:, 1] = up
        Am[:, 2] = q + ppm * r['x0'] * right - ppm * r['y1'] * up + 0.5 * right + 0.5 * up
        mroi = roi_affine(Am, cw, ch)
        if mroi is not None:
            mx0, my0, mx1, my1, Amr = mroi
            mw = cv2.warpAffine(a, Amr, (mx1 - mx0, my1 - my0), flags=cv2.INTER_LINEAR)
            occ_refl[my0:my1, mx0:mx1] = np.maximum(occ_refl[my0:my1, mx0:mx1], mw)
        # sombra hacia la cámara: la luz viene de la proyección
        th_ = np.linspace(0, 2 * np.pi, 48)
        ell = np.stack([sp['X'] + 0.32 * np.cos(th_), np.zeros_like(th_), sp['Z'] - 0.45 + 0.75 * np.sin(th_)], 1)
        sm = np.zeros((H, W), np.float32)
        cv2.fillPoly(sm, [np.round(cam.project(ell) * 4).astype(np.int32)], 1.0, cv2.LINE_AA, shift=2)
        shadow = np.maximum(shadow, gblur(sm, ppm * 0.08))
        cs = np.zeros((H, W), np.float32)
        ell2 = np.stack([sp['X'] + 0.24 * np.cos(th_), np.zeros_like(th_), sp['Z'] + 0.17 * np.sin(th_)], 1)
        cv2.fillPoly(cs, [np.round(cam.project(ell2) * 4).astype(np.int32)], 1.0, cv2.LINE_AA, shift=2)
        shadow = np.maximum(shadow, gblur(cs, ppm * 0.03))

    occ_refl = gblur(occ_refl, 6, 20)
    img = img + refl * (1 - 0.85 * occ_refl[..., None])
    img = img * (1 - 0.65 * shadow[..., None] * floor[..., None])
    img = img + beam
    for zc, x0, y0, x1, y1, a_w, rgb_w in sorted(layers, key=lambda l: -l[0]):
        sub = img[y0:y1, x0:x1]
        img[y0:y1, x0:x1] = sub * (1 - a_w[..., None]) + rgb_w
    # resplandor de la proyección y viñeta
    glow = gblur(np.clip(img - 0.5, 0, None), 40)
    img = img + glow * 0.18
    yy, xx = np.mgrid[0:H, 0:W]
    vig = 1 - 0.38 * (((xx - W / 2) / (W * 0.62)) ** 2 + ((yy - H * 0.45) / (H * 0.7)) ** 2)
    img = img * np.clip(vig, 0.4, 1)[..., None]
    out = lin_to_srgb(aces(img * 1.25))
    rng = np.random.default_rng(3)
    out = out + rng.normal(0, 0.012, out.shape[:2])[..., None]
    out8 = (np.clip(out, 0, 1) * 255).astype(np.uint8)

    # --- capa de seguimiento de la mano (MediaPipe HandLandmarker, 21 puntos) en gesto de pinza
    im = Image.fromarray(out8)
    dr = ImageDraw.Draw(im)
    dv = np.array([-du[1], du[0]])
    Lh = 0.19 * g_place[1] * 1.6                         # mano levemente ampliada para que se lea
    HAND = [(0, 0), (.12, -.18), (.25, -.3), (.38, -.36), (.5, -.36), (.48, -.12), (.63, -.2), (.6, -.31), (.52, -.37),
            (.5, 0), (.75, 0), (.92, 0), (1.05, 0), (.48, .11), (.7, .12), (.85, .13), (.97, .14),
            (.43, .21), (.6, .24), (.72, .26), (.82, .27)]
    LINKS = [(0, 1), (1, 2), (2, 3), (3, 4), (0, 5), (5, 6), (6, 7), (7, 8), (5, 9), (9, 10), (10, 11), (11, 12),
             (9, 13), (13, 14), (14, 15), (15, 16), (13, 17), (0, 17), (17, 18), (18, 19), (19, 20)]
    P = [wrist + Lh * (a_ * du + b_ * dv) for a_, b_ in HAND]
    lw_ = max(2, W // 1000)
    pa = cam.project(aim[None])[0]
    tip = (P[4] + P[8]) / 2
    for i in range(0, 60, 2):                       # vínculo punteado entre la mano y el cursor
        p0 = tip * (1 - i / 60) + pa * (i / 60)
        p1 = tip * (1 - (i + 1) / 60) + pa * ((i + 1) / 60)
        dr.line([tuple(p0), tuple(p1)], fill=RED, width=max(1, lw_ - 1))
    for a_, b_ in LINKS:
        dr.line([tuple(P[a_]), tuple(P[b_])], fill=RED, width=lw_)
    for pt in P:
        rad = lw_ * 1.7
        dr.ellipse([pt[0] - rad, pt[1] - rad, pt[0] + rad, pt[1] + rad], fill=(238, 237, 231), outline=RED, width=max(1, lw_ - 1))
    font = ImageFont.truetype(FONT, int(W / 125))
    lx = min(p_[0] for p_ in P) - W * 0.015
    ly = cam.project(np.array([[SX0, SY0, 0.0], [SX1, SY0, 0.0]]))[:, 1].max() + H * 0.035
    dr.text((lx, ly), 'MEDIAPIPE · MANO · 21 PUNTOS\nPINZA: TOMAR «' + tgt['name'].upper() + '»', font=font, fill=RED, spacing=6, anchor='ra')
    return im


if __name__ == '__main__':
    names = sys.argv[1:] or list(SCENES)
    for nm in names:
        im = render(nm, ROOT / 'assets/capturas' / SCENES[nm].get('texture', '11_proyeccion.png'))
        dst = ROOT / f'assets/escenas/{nm}.jpg'
        im.save(dst, quality=90)
        print('ok', dst)
