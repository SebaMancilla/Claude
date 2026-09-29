"""Proxy geometry of the hall + ray casting utilities (world units: meters).

World frame: X along the pillar rows (towards the right wall), Z towards the back
(stair side), Y up. Pillar L1 is at the origin; pillar grid spacing 4.5 m.
"""
import numpy as np
from cams import get, CAMS

GRID = 4.5
PW = 0.29          # pillar half width (0.58 m square)
CAPW = 0.39        # capital half width
CAP_Y = (3.58, 4.0)
PILLAR_H = 4.0

# stair block (landing with the "V" face) and upper flight
BLOCK = dict(x=(2.54, 4.90), y=(0.0, 1.85), z=(2.95, 4.40))
FLIGHT = dict(x=(2.62, 3.95), z0=4.20, z1=7.75, y0=1.85, slope=1.0)
SCREEN_Z = 2.95

ID_NONE, ID_FLOOR, ID_CEIL, ID_PILLAR, ID_BLOCK, ID_FLIGHT, ID_SCREEN, ID_WALL = range(8)


def pillar_positions():
    pos = []
    for X in (-9.0, -4.5, 0.0, 4.5):
        for Z in np.arange(-13.5, 27.1, 4.5):
            pos.append((X, Z))
    return pos


def boxes(include_caps=True):
    """list of (min, max, id, tag)"""
    out = []
    for X, Z in pillar_positions():
        out.append((np.array([X - PW, 0, Z - PW]), np.array([X + PW, PILLAR_H, Z + PW]), ID_PILLAR, (X, Z)))
        if include_caps:
            out.append((np.array([X - CAPW, CAP_Y[0], Z - CAPW]), np.array([X + CAPW, CAP_Y[1], Z + CAPW]), ID_PILLAR, (X, Z)))
    b = BLOCK
    out.append((np.array([b['x'][0], b['y'][0], b['z'][0]]), np.array([b['x'][1], b['y'][1], b['z'][1]]), ID_BLOCK, 'block'))
    out.append((np.array([8.4, 0, -40]), np.array([9.4, 6, 60]), ID_WALL, 'rwall'))
    return out


def ray_dirs(cam, W=1280, H=960, scale=1.0):
    w, h = int(round(W * scale)), int(round(H * scale))
    xs = (np.arange(w) + 0.5) / scale - 0.5
    ys = (np.arange(h) + 0.5) / scale - 0.5
    X, Y = np.meshgrid(xs, ys)
    d = np.stack([(X - cam.cx) / cam.f, -(Y - cam.cy) / cam.f, np.ones_like(X)], -1)
    d = d @ cam.R
    d /= np.linalg.norm(d, axis=-1, keepdims=True)
    return d


def ray_box(o, d, bmin, bmax):
    with np.errstate(divide='ignore', invalid='ignore'):
        inv = 1.0 / d
        t1 = (bmin - o) * inv
        t2 = (bmax - o) * inv
    tn = np.nan_to_num(np.minimum(t1, t2), nan=-np.inf)
    tf = np.nan_to_num(np.maximum(t1, t2), nan=np.inf)
    tmin = tn.max(-1)
    tmax = tf.min(-1)
    axis = tn.argmax(-1)
    hit = (tmax >= tmin) & (tmin > 1e-4)
    return np.where(hit, tmin, np.inf), axis


def seg_blocked_box(p, q, bmin, bmax):
    d = q - p
    with np.errstate(divide='ignore', invalid='ignore'):
        inv = 1.0 / d
        t1 = (bmin - p) * inv
        t2 = (bmax - p) * inv
    tn = np.nan_to_num(np.minimum(t1, t2), nan=-np.inf)
    tf = np.nan_to_num(np.maximum(t1, t2), nan=np.inf)
    tmin = tn.max(-1)
    tmax = tf.min(-1)
    return (tmax >= tmin) & (tmax > 1e-3) & (tmin < 1 - 1e-3)


def flight_y(z):
    f = FLIGHT
    return f['y0'] + f['slope'] * (z - f['z0'])


def flight_t(o, d, mirror=False):
    f = FLIGHT
    s = f['slope']
    sy = -1.0 if mirror else 1.0
    # plane: sy*y = y0 + s (z - z0)
    num = (f['y0'] - s * f['z0']) - (sy * o[..., 1] - s * o[..., 2])
    den = sy * d[..., 1] - s * d[..., 2]
    with np.errstate(divide='ignore', invalid='ignore'):
        t = num / den
    P = o + t[..., None] * d
    ok = (t > 1e-4) & (P[..., 0] >= f['x'][0]) & (P[..., 0] <= f['x'][1]) & (P[..., 2] >= f['z0']) & (P[..., 2] <= f['z1'])
    return np.where(ok, t, np.inf)


def flight_normal():
    s = FLIGHT['slope']
    n = np.array([0, 1.0, -s])
    return n / np.linalg.norm(n)


def seg_blocked_flight(p, q):
    f = FLIGHT
    gp = p[..., 1] - flight_y(p[..., 2])
    gq = q[..., 1] - flight_y(q[..., 2])
    cross = (gp * gq) < 0
    t = gp / np.where(cross, gp - gq, 1)
    X = p + t[..., None] * (q - p)
    inside = (X[..., 0] >= f['x'][0]) & (X[..., 0] <= f['x'][1]) & (X[..., 2] >= f['z0'] - 0.3) & (X[..., 2] <= f['z1'])
    return cross & inside


class Screen:
    def __init__(self, x0, x1, y0, y1, z=SCREEN_Z):
        self.x0, self.x1, self.y0, self.y1, self.z = x0, x1, y0, y1, z

    def t(self, o, d, mirror=False):
        with np.errstate(divide='ignore', invalid='ignore'):
            t = (self.z - o[..., 2]) / d[..., 2]
        P = o + t[..., None] * d
        Py = -P[..., 1] if mirror else P[..., 1]
        ok = (t > 1e-4) & (P[..., 0] >= self.x0) & (P[..., 0] <= self.x1) & (Py >= self.y0) & (Py <= self.y1)
        return np.where(ok, t, np.inf), P

    def area(self):
        return (self.x1 - self.x0) * (self.y1 - self.y0)


def _bbox_px(cam, bmin, bmax, W, H, scale, mirror):
    V = np.array([[x, y, z] for x in (bmin[0], bmax[0]) for y in (bmin[1], bmax[1]) for z in (bmin[2], bmax[2])], float)
    if mirror:
        V[:, 1] *= -1
    pc = cam.cam(V)
    if (pc[:, 2] < 0.05).any():
        return 0, W, 0, H
    q = cam.project(V) * scale
    x0 = int(max(0, np.floor(q[:, 0].min()) - 2)); x1 = int(min(W, np.ceil(q[:, 0].max()) + 2))
    y0 = int(max(0, np.floor(q[:, 1].min()) - 2)); y1 = int(min(H, np.ceil(q[:, 1].max()) + 2))
    return x0, x1, y0, y1


def beam_boxes():
    """ceiling beams around the installation (screen occlusion + spot shadows)."""
    bw = 0.22
    out = []
    for Z in (0.0, 4.5):
        out.append((np.array([-12, 4.0, Z - bw]), np.array([12, 5.3, Z + bw])))
    for X in (-4.5, 0.0, 4.5):
        out.append((np.array([X - bw, 4.0, -12]), np.array([X + bw, 5.3, 12])))
    out.append((np.array([2.14, 4.5, -12]), np.array([2.32, 5.3, 12])))
    return out


def slab_boxes():
    """upper floor slab with the stair opening (for the stair spot shadows)."""
    ox = (2.35, 4.28); oz = (4.72, 9.6); y = (5.2, 5.5)
    return [
        (np.array([-20, y[0], -20]), np.array([ox[0], y[1], 40])),
        (np.array([ox[1], y[0], -20]), np.array([20, y[1], 40])),
        (np.array([ox[0], y[0], -20]), np.array([ox[1], y[1], oz[0]])),
        (np.array([ox[0], y[0], oz[1]]), np.array([ox[1], y[1], 40])),
    ]


def gbuffer(cam, screen=None, scale=1.0, ceil_y=4.3, mirror=False, W=1280, H=960):
    """Ray cast the proxy scene. mirror=True casts against the scene mirrored below
    the floor (planar reflection of the polished concrete)."""
    d = ray_dirs(cam, W, H, scale)
    h, w = d.shape[:2]
    o = cam.C
    t = np.full((h, w), np.inf)
    oid = np.zeros((h, w), int)
    nrm = np.zeros((h, w, 3))
    sy = -1.0 if mirror else 1.0
    with np.errstate(divide='ignore', invalid='ignore'):
        if not mirror:
            tf = np.where(d[..., 1] < 0, -o[1] / d[..., 1], np.inf)
            m = tf < t
            t[m] = tf[m]; oid[m] = ID_FLOOR; nrm[m] = [0, 1, 0]
            tc = np.where(d[..., 1] > 0, (ceil_y - o[1]) / d[..., 1], np.inf)
        else:
            tc = np.where(d[..., 1] < 0, (-ceil_y - o[1]) / d[..., 1], np.inf)
    m = tc < t
    t[m] = tc[m]; oid[m] = ID_CEIL; nrm[m] = [0, -1, 0]
    for bmin, bmax, bid, btag in boxes():
        x0, x1, y0, y1 = _bbox_px(cam, bmin, bmax, w, h, scale, mirror)
        if x1 <= x0 or y1 <= y0:
            continue
        bm, bM = bmin.copy(), bmax.copy()
        if mirror:
            bm[1], bM[1] = -bmax[1], -bmin[1]
        dd = d[y0:y1, x0:x1]
        tb, ax = ray_box(o, dd, bm, bM)
        sub_t = t[y0:y1, x0:x1]
        m = tb < sub_t
        if not m.any():
            continue
        sub_t[m] = tb[m]
        oid[y0:y1, x0:x1][m] = bid
        n = np.zeros(m.shape + (3,))
        iy, ix = np.nonzero(m)
        a = ax[m]
        n[iy, ix, a] = -np.sign(dd[iy, ix, a])
        if mirror:
            n[..., 1] *= -1
        nrm[y0:y1, x0:x1][m] = n[m]
    tfl = flight_t(o, d, mirror)
    m = tfl < t
    t[m] = tfl[m]; oid[m] = ID_FLIGHT; nrm[m] = flight_normal()
    t_scene = t.copy()
    id_scene = oid.copy()
    scr = np.zeros((h, w), bool)
    if screen is not None:
        ts, _ = screen.t(o, d, mirror)
        t_occ = np.where(oid == ID_CEIL, np.inf, t)
        for bmin, bmax in beam_boxes():
            bm, bM = bmin.copy(), bmax.copy()
            if mirror:
                bm[1], bM[1] = -bmax[1], -bmin[1]
            tb, _ = ray_box(o, d, bm, bM)
            t_occ = np.minimum(t_occ, tb)
        scr = ts < t_occ
        t[scr] = ts[scr]; oid[scr] = ID_SCREEN; nrm[scr] = [0, 0, -1]
    far = ~np.isfinite(t)
    t[far] = 60.0
    P = o + t[..., None] * d
    if mirror:
        P[..., 1] *= -1
    nrm[far] = -d[far]
    return dict(t=t, P=P, n=nrm, id=oid, d=d, id_scene=id_scene, t_scene=t_scene, screen=scr)


def pillar_occluders(center, radius=10.0):
    out = []
    for bmin, bmax, bid, btag in boxes():
        if bid != ID_PILLAR:
            continue
        X, Z = btag
        if abs(X - center[0]) < radius and abs(Z - center[2]) < radius:
            out.append((bmin, bmax))
    return out
