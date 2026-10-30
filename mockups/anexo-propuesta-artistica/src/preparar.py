"""Prepara las imágenes del anexo: recortes de capturas, versiones JPEG livianas, limpieza de los
elementos de interfaz de Instagram en las referencias y código QR de la versión web.

Uso: python3 src/preparar.py
"""
from pathlib import Path

import qrcode
import qrcode.image.svg
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
A = ROOT / 'assets'
OUT = A / 'pdf'
OUT.mkdir(exist_ok=True)
URL = 'https://editor.p5js.org/sebastianmancillah/full/0gzrvNW9W'


def jpg(src, dst, width=None, box=None, q=88):
    im = Image.open(src).convert('RGB')
    if box:
        im = im.crop(box)
    if width and im.width > width:
        im = im.resize((width, round(im.height * width / im.width)), Image.LANCZOS)
    im.save(OUT / dst, quality=q, optimize=True, progressive=True)


# capturas (3200 × 1800): campo del mapa sin cabecera ni controles, y versiones completas
CAMPO = (0, 276, 3200, 1560)
for n in ['01_glosario', '02_tema_peso', '03_radar', '04_invisibles', '05_mapa', '07_volumen', '10_emergente', '08_ficha_latentes', '09_latente', '06_mapa_lugar']:
    jpg(A / f'capturas/{n}.png', f'cap_{n}_campo.jpg', 1500, CAMPO)
for n in ['01_glosario', '09_latente', '10_emergente', '06_mapa_lugar']:
    jpg(A / f'capturas/{n}.png', f'cap_{n}.jpg', 2200)
# estudios p5 y escenas
for n in ['espacializacion', 'sonificacion', 'temporalizacion', 'recorridos']:
    jpg(A / f'estudios/{n}.png', f'est_{n}.jpg', 2000, q=90)
jpg(A / 'estudios/portada.png', 'portada.jpg', 2970, q=90)
for n in ['amplia', 'cercana']:
    jpg(A / f'escenas/{n}.jpg', f'esc_{n}.jpg', 3000, q=88)

# referencias compartidas: se tapan los botones de la interfaz y se recortan avatares y bordes
im = Image.open(A / 'referencias/2.webp').convert('RGB')
ImageDraw.Draw(im).ellipse((1124, 698, 1182, 756), fill=(247, 246, 238))
im.crop((0, 0, 1206, 1400)).save(OUT / 'ref_2.jpg', quality=90)
im = Image.open(A / 'referencias/4.webp').convert('RGB')
ImageDraw.Draw(im).ellipse((1012, 604, 1080, 672), fill=(255, 255, 255))
im.crop((0, 0, 1086, 1200)).save(OUT / 'ref_4.jpg', quality=90)
Image.open(A / 'referencias/1.webp').convert('RGB').save(OUT / 'ref_1.jpg', quality=90)
Image.open(A / 'referencias/3.webp').convert('RGB').crop((0, 0, 792, 1222)).save(OUT / 'ref_3.jpg', quality=90)

# QR de la versión web
qr = qrcode.QRCode(border=0, error_correction=qrcode.constants.ERROR_CORRECT_M)
qr.add_data(URL)
qr.make(fit=True)
qr.make_image(image_factory=qrcode.image.svg.SvgPathImage).save(str(OUT / 'qr.svg'))
print('ok', len(list(OUT.iterdir())), 'archivos en', OUT)
