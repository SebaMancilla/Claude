"""Comparison sheet: rows = photos 1..3, columns = options."""
import sys, os
from PIL import Image, ImageDraw, ImageFont

COLS = [('A', 'A1 · horizontal 8×4 m detrás del pilar'), ('A2', 'A2 · horizontal 8×4 m delante del pilar'),
        ('B', 'B · vertical 2×5 m a borde de escalera')]


def font(sz, bold=False):
    f = '/usr/share/fonts/truetype/dejavu/DejaVuSans%s.ttf' % ('-Bold' if bold else '')
    return ImageFont.truetype(f, sz) if os.path.exists(f) else ImageFont.load_default()


def make(indir, out, names):
    tw, th = 800, 600
    pad, head, lab = 24, 120, 40
    Wd = pad * (len(COLS) + 1) + tw * len(COLS)
    Hd = head + 3 * (th + lab + pad) + pad
    sheet = Image.new('RGB', (Wd, Hd), (14, 14, 16))
    d = ImageDraw.Draw(sheet)
    d.text((pad, 24), 'Instalación escénica · Teorema · mockups nocturnos', fill=(235, 235, 235), font=font(36, True))
    d.text((pad, 74), 'Pantalla LED (placeholder de la levitación de Teorema, Pasolini) · contra en la escalera con el rapero '
                      'Teorema + frontal tenue · público a escala', fill=(165, 165, 172), font=font(20))
    for r, ph in enumerate((1, 2, 3)):
        for c, (opt, label) in enumerate(COLS):
            fn = os.path.join(indir, names.format(ph=ph, opt=opt))
            im = Image.open(fn).convert('RGB').resize((tw, th), Image.LANCZOS)
            x = pad + c * (tw + pad); y = head + r * (th + lab + pad)
            d.text((x, y + 6), f'Foto {ph} — {label}', fill=(220, 220, 220), font=font(21, True))
            sheet.paste(im, (x, y + lab))
    sheet.save(out, quality=90)


if __name__ == '__main__':
    make(sys.argv[1], sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else '{ph}{opt}.png')
