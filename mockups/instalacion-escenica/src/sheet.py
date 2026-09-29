"""Comparison sheet: rows = photos 1..3, columns = option A | option B."""
import sys, os
import numpy as np
import cv2
from PIL import Image, ImageDraw, ImageFont

def font(sz, bold=False):
    for f in (['/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'] if bold else []) + ['/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf']:
        if os.path.exists(f):
            return ImageFont.truetype(f, sz)
    return ImageFont.load_default()

def make(indir, out, names):
    tw, th = 960, 720
    pad, head, lab = 24, 110, 44
    Wd = pad * 3 + tw * 2
    Hd = head + 3 * (th + lab + pad) + pad
    sheet = Image.new('RGB', (Wd, Hd), (14, 14, 16))
    d = ImageDraw.Draw(sheet)
    d.text((pad, 26), 'Instalación escénica · mockups nocturnos', fill=(235, 235, 235), font=font(34, True))
    d.text((pad, 70), 'Opción A: LED horizontal 8 × 4 m   ·   Opción B: LED vertical 2 × 5 m   ·   contra en la escalera',
           fill=(170, 170, 175), font=font(20))
    for r, ph in enumerate((1, 2, 3)):
        for c, opt in enumerate(('A', 'B')):
            im = Image.open(os.path.join(indir, names.format(ph=ph, opt=opt))).convert('RGB').resize((tw, th), Image.LANCZOS)
            x = pad + c * (tw + pad); y = head + r * (th + lab + pad)
            d.text((x, y + 6), f'Foto {ph} — Opción {opt}', fill=(220, 220, 220), font=font(24, True))
            sheet.paste(im, (x, y + lab))
    sheet.save(out, quality=90)

if __name__ == '__main__':
    make(sys.argv[1], sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else '{ph}{opt}.png')
