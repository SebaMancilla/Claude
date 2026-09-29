"""Generic backlit singer silhouette (no likeness): hoodie, mic raised to the mouth,
free arm gesturing. Built in meters (origin at the feet, y up) and projected as a
camera-facing billboard."""
import numpy as np
import cv2

PPM = 400  # canvas pixels per meter


def silhouette():
    Wc, Hc = int(1.4 * PPM), int(2.0 * PPM)
    m = np.zeros((Hc, Wc), np.uint8)
    ox = Wc / 2
    P = lambda l: np.array([[ox + x * PPM, Hc - y * PPM] for x, y in l], np.int32)
    L = cv2.LINE_AA
    # legs (loose trousers), relaxed stance
    cv2.fillPoly(m, [P([(-0.19, 0.86), (-0.015, 0.86), (-0.05, 0.40), (-0.08, 0.06), (-0.235, 0.05), (-0.21, 0.42)])], 255, L)
    cv2.fillPoly(m, [P([(0.015, 0.86), (0.19, 0.86), (0.21, 0.42), (0.24, 0.05), (0.085, 0.06), (0.055, 0.40)])], 255, L)
    # shoes
    cv2.ellipse(m, (int(ox - 0.16 * PPM), int(Hc - 0.035 * PPM)), (int(0.1 * PPM), int(0.04 * PPM)), 0, 0, 360, 255, -1, L)
    cv2.ellipse(m, (int(ox + 0.17 * PPM), int(Hc - 0.035 * PPM)), (int(0.1 * PPM), int(0.04 * PPM)), 0, 0, 360, 255, -1, L)
    # hoodie torso
    cv2.fillPoly(m, [P([(-0.25, 1.44), (-0.12, 1.50), (0.12, 1.50), (0.25, 1.44), (0.28, 1.25), (0.26, 0.98),
                        (0.23, 0.80), (-0.23, 0.80), (-0.26, 0.98), (-0.28, 1.25)])], 255, L)
    # hood + head, slightly tilted towards the mic
    cv2.ellipse(m, (int(ox + 0.01 * PPM), int(Hc - 1.635 * PPM)), (int(0.125 * PPM), int(0.145 * PPM)), -8, 0, 360, 255, -1, L)
    cv2.fillPoly(m, [P([(-0.14, 1.47), (-0.12, 1.60), (0.12, 1.60), (0.15, 1.47)])], 255, L)
    # mic arm: raised elbow out to the side, hand + mic at the mouth
    cv2.line(m, tuple(P([(0.23, 1.43)])[0]), tuple(P([(0.43, 1.39)])[0]), 255, int(0.105 * PPM), L)
    cv2.line(m, tuple(P([(0.43, 1.39)])[0]), tuple(P([(0.15, 1.585)])[0]), 255, int(0.085 * PPM), L)
    cv2.ellipse(m, tuple(P([(0.135, 1.59)])[0]), (int(0.05 * PPM), int(0.045 * PPM)), 30, 0, 360, 255, -1, L)
    cv2.line(m, tuple(P([(0.12, 1.60)])[0]), tuple(P([(0.07, 1.63)])[0]), 255, int(0.045 * PPM), L)  # mic head
    # free arm, open gesture towards the audience
    th = int(0.10 * PPM)
    cv2.line(m, tuple(P([(-0.22, 1.40)])[0]), tuple(P([(-0.38, 1.17)])[0]), 255, th, L)
    cv2.line(m, tuple(P([(-0.38, 1.17)])[0]), tuple(P([(-0.56, 1.13)])[0]), 255, int(0.08 * PPM), L)
    cv2.ellipse(m, tuple(P([(-0.60, 1.14)])[0]), (int(0.055 * PPM), int(0.04 * PPM)), -15, 0, 360, 255, -1, L)
    return m.astype(np.float32) / 255.0, ox, Hc


def albedo(sil, ox, Hc):
    a = np.zeros(sil.shape + (3,), np.float32)
    a[:] = (0.055, 0.055, 0.062)                      # charcoal hoodie
    yy = np.arange(sil.shape[0])[:, None] * np.ones((1, sil.shape[1]))
    y_m = (Hc - yy) / PPM
    a[y_m < 0.86] = (0.035, 0.036, 0.042)             # trousers
    a[y_m < 0.08] = (0.10, 0.10, 0.10)                # sneakers
    face = np.zeros(sil.shape, np.uint8)
    cv2.ellipse(face, (int(ox + 0.02 * PPM), int(Hc - 1.60 * PPM)), (int(0.07 * PPM), int(0.085 * PPM)), 0, 0, 360, 1, -1)
    a[face > 0] = (0.16, 0.105, 0.08)                 # face in the shadow of the hood
    for cx, cy in ((0.135, 1.59), (-0.60, 1.14)):
        hand = np.zeros(sil.shape, np.uint8)
        cv2.ellipse(hand, (int(ox + cx * PPM), int(Hc - cy * PPM)), (int(0.055 * PPM), int(0.05 * PPM)), 0, 0, 360, 1, -1)
        a[hand > 0] = (0.26, 0.17, 0.13)
    return a * sil[..., None]


def roundness(sil):
    d = cv2.distanceTransform((sil > 0.5).astype(np.uint8), cv2.DIST_L2, 5) / (0.09 * PPM)
    return np.clip(d, 0, 1) ** 0.6


def place(cam, feet, W, H, with_albedo=False):
    """returns (mask HxW float, depth to the performer[, albedo, roundness])."""
    sil, ox, Hc = silhouette()
    feet = np.asarray(feet, float)
    q = cam.project(feet[None])[0]
    Z = cam.cam(feet[None])[0, 2]
    s = cam.f / Z / PPM                     # image px per canvas px
    # upright billboard: use projection of a point 1.78 m above to get the image-vertical direction
    q2 = cam.project((feet + [0, 1.78, 0])[None])[0]
    up = (q2 - q) / np.linalg.norm(q2 - q)
    right = np.array([-up[1], up[0]])
    A = np.array([[right[0] * s, -up[0] * s, 0.0], [right[1] * s, -up[1] * s, 0.0]])
    # canvas point (ox, Hc) -> q
    A[:, 2] = q - A[:, :2] @ np.array([ox, Hc])
    mask = cv2.warpAffine(sil, A, (W, H), flags=cv2.INTER_AREA, borderValue=0)
    dist = np.linalg.norm(feet + [0, 0.9, 0] - cam.C)
    if not with_albedo:
        return np.clip(mask, 0, 1), dist
    alb = cv2.warpAffine(albedo(sil, ox, Hc), A, (W, H), flags=cv2.INTER_AREA)
    rnd = cv2.warpAffine(roundness(sil), A, (W, H), flags=cv2.INTER_AREA)
    return np.clip(mask, 0, 1), dist, alb, rnd
