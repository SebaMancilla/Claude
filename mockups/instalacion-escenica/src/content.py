"""Generative LED content, defined in screen meters so both options share the same scale."""
import numpy as np


def _fade(t):
    return t * t * t * (t * (t * 6 - 15) + 10)


def perlin(x, y, seed=0):
    rng = np.random.RandomState(seed)
    perm = rng.permutation(256)
    perm = np.concatenate([perm, perm])
    ang = rng.rand(256) * 2 * np.pi
    gx, gy = np.cos(ang), np.sin(ang)
    xi = np.floor(x).astype(int)
    yi = np.floor(y).astype(int)
    xf = x - xi
    yf = y - yi
    xi &= 255
    yi &= 255

    def g(ix, iy, dx, dy):
        h = perm[perm[ix] + iy]
        return gx[h] * dx + gy[h] * dy

    n00 = g(xi, yi, xf, yf)
    n10 = g((xi + 1) & 255, yi, xf - 1, yf)
    n01 = g(xi, (yi + 1) & 255, xf, yf - 1)
    n11 = g((xi + 1) & 255, (yi + 1) & 255, xf - 1, yf - 1)
    u = _fade(xf)
    v = _fade(yf)
    return (n00 * (1 - u) + n10 * u) * (1 - v) + (n01 * (1 - u) + n11 * u) * v


def fbm(x, y, octaves=5, seed=0):
    s = 0.0
    a = 0.5
    f = 1.0
    for o in range(octaves):
        s = s + a * perlin(x * f, y * f, seed + o * 17)
        f *= 2.02
        a *= 0.5
    return s


PALETTE = np.array([
    [0.00, 0x06, 0x05, 0x22],
    [0.18, 0x1a, 0x12, 0x5e],
    [0.36, 0x2a, 0x4c, 0xc8],
    [0.52, 0x7a, 0x2c, 0xb8],
    [0.66, 0xe0, 0x3a, 0x86],
    [0.80, 0xff, 0x7a, 0x3c],
    [0.92, 0xff, 0xc0, 0x6e],
    [1.00, 0xff, 0xef, 0xd2],
], float)


def palette(t):
    t = np.clip(t, 0, 1)
    out = np.zeros(t.shape + (3,))
    for c in range(3):
        out[..., c] = np.interp(t, PALETTE[:, 0], PALETTE[:, c + 1] / 255.0)
    return out


def srgb_to_lin(c):
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


def content(x_m, y_m, seed=3):
    """x_m: meters from the left of the installation frame, y_m: meters from the floor (up).
    returns linear RGB in [0,1]."""
    sc = 0.33
    x = x_m * sc
    y = y_m * sc
    # domain warping -> flowing, liquid shapes
    qx = fbm(x + 0.0, y + 0.0, 4, seed)
    qy = fbm(x + 5.2, y + 1.3, 4, seed + 1)
    rx = fbm(x + 3.5 * qx + 1.7, y + 3.5 * qy + 9.2, 5, seed + 2)
    ry = fbm(x + 3.5 * qx + 8.3, y + 3.5 * qy + 2.8, 5, seed + 3)
    f = fbm(x + 3.0 * rx, y + 3.0 * ry, 6, seed + 4)
    f = 0.5 + 0.95 * f
    # horizon: warm low, deep blue high
    h = np.clip(y_m / 5.0, 0, 1)
    t = 0.62 * f + 0.55 * (1 - h) - 0.12 + 0.25 * (np.sqrt(rx * rx + ry * ry) - 0.25)
    col = palette(t)
    # fine filaments
    ridge = 1 - np.abs(fbm(x * 2.2 + 2 * rx, y * 2.2 + 2 * ry, 4, seed + 9))
    ridge = np.clip((ridge - 0.72) / 0.28, 0, 1) ** 3
    col = col + ridge[..., None] * np.array([1.0, 0.85, 0.75]) * 0.35
    return srgb_to_lin(np.clip(col, 0, 1))
