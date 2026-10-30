"""Genera anexo.html (A4 apaisado) a partir de las imágenes de assets/pdf y los datos del
prototipo (assets/datos.json). El PDF se imprime con src/pdf.mjs.

Uso: python3 src/anexo.py
"""
import json
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
D = json.loads((ROOT / 'assets/datos.json').read_text())
URL = 'editor.p5js.org/sebastianmancillah/full/0gzrvNW9W'
TOTAL = 11

# grano de papel (tesela liviana)
rng = np.random.default_rng(7)
g = rng.random((240, 240))
Image.fromarray(np.dstack([np.full((240, 240), 23), np.full((240, 240), 23), np.full((240, 240), 20),
                           (g ** 3 * 16).astype(np.uint8)]).astype(np.uint8), 'RGBA').save(ROOT / 'assets/pdf/grano.png')

# ------------------------------------------------------------------ datos para los gráficos
deg = {x['name']: x['n'] for x in D['degree']}
tags = {}
for i, cr in enumerate(D['grupos']):
    for val, names in cr['grupos'].items():
        for n in names:
            tags.setdefault(n, [None] * 3)[i] = val
uno = sum(1 for v in deg.values() if v == 1)
fam = {val: sum(deg[n] for n in names) / len(names) for val, names in D['grupos'][0]['grupos'].items()}


def vecinos(concepto, i):
    v = tags[concepto][i]
    return v, [n for n in D['grupos'][i]['grupos'][v] if n != concepto]


def svg_sonido():
    s = D['sonido']
    w, h, bw = 480, 236, 10
    out = [f'<svg viewBox="0 0 {w} {h}" class="chart">']
    for i, x in enumerate(s):
        bh = (x['bpm'] - 40) / 140 * 190
        red = i < 3
        out.append(f'<rect x="{i * bw}" y="{205 - bh:.1f}" width="{bw - 2.4}" height="{bh:.1f}" fill="{"#c9241c" if red else "#171714"}" opacity="{1 if red else .82}"/>')
    out.append(f'<line x1="0" y1="205.5" x2="{48 * bw}" y2="205.5" stroke="#171714" stroke-width=".6"/>')
    out.append('<text x="34" y="18" class="t">← MEMORIA · ARCHIVO · CUERPO</text><text x="34" y="27" class="t m">180 BPM · ~1,7 KHZ</text>')
    out.append(f'<text x="{48 * bw}" y="168" class="t" text-anchor="end">24 CONCEPTOS CON 1 VÍNCULO</text><text x="{48 * bw}" y="177" class="t m" text-anchor="end">54 BPM · ~82 HZ</text>')
    out.append(f'<text x="0" y="221" class="t m">48 CONCEPTOS ORDENADOS POR TEMPO</text></svg>')
    return ''.join(out)


def svg_volumen():
    vals = D['volumen']['valores']           # técnica, tema, territorio
    occ = {}
    for n, t in tags.items():
        occ[tuple(t)] = occ.get(tuple(t), 0) + 1
    cell, gap = 9, 14
    w = 5 * (5 * cell) + 4 * gap
    out = [f'<svg viewBox="-2 -12 {w + 4} {5 * cell + 36}" class="chart">']
    for k, tema in enumerate(vals[1]):
        ox = k * (5 * cell + gap)
        out.append(f'<text x="{ox}" y="-4" class="t">{tema.upper()}</text>')
        for i, tec in enumerate(vals[0]):
            for j, ter in enumerate(vals[2]):
                x, y = ox + j * cell + cell / 2, i * cell + cell / 2
                n = occ.get((tec, tema, ter), 0)
                if n:
                    out.append(f'<rect x="{x - 4}" y="{y - 4}" width="8" height="8" fill="#c9241c"/>'
                               f'<text x="{x}" y="{y + 2.3}" class="t w" text-anchor="middle">{n}</text>')
                else:
                    out.append(f'<circle cx="{x}" cy="{y}" r=".8" fill="#171714" opacity=".45"/>')
    out.append(f'<text x="0" y="{5 * cell + 12}" class="t m">CUADRO ← TEMA · FILA ← TÉCNICA · COLUMNA ← TERRITORIO</text>'
               f'<text x="0" y="{5 * cell + 21}" class="t">8 DE 125 CRUCES OCUPADOS</text></svg>')
    return ''.join(out)


def html_territorios():
    ts = D['territorios']
    mx = max(t['peso'] for t in ts)
    rows = []
    for t in ts:
        top = t['peso'] >= 0.119
        rows.append(f'<div class="tb"><span>{t["nombre"].upper()}</span><i style="width:{t["peso"] / mx * 100:.0f}%"'
                    f'{" class=r" if top else ""}></i><b>{round(t["peso"] * 100)}%</b></div>')
    return '<div class="terr">' + ''.join(rows) + '<p class="cap">NORTE → SUR · PESOS DEMOSTRATIVOS, SIN ATENCIÓN DEL PÚBLICO</p></div>'


def html_ritual():
    cols = []
    for i, crit in enumerate(['técnica', 'tema', 'territorio']):
        v, ns = vecinos('ritual', i)
        cols.append(f'<div class="vec"><p class="k">{crit.upper()} · {v}</p><p>{" · ".join(ns)}</p></div>')
    return '<div class="ritual"><p class="rw">ritual</p>' + ''.join(cols) + '</div>'


LAT = [('resonancia', 'frecuencia', 'vibración · señal'), ('interacción', 'glitch', 'gesto · error'),
       ('memoria', 'hardware', 'soportes · digitales'), ('espectro', 'inteligencia artificial', 'fantasmales'),
       ('hardware', 'ritual', 'propuesta curatorial')]


# ------------------------------------------------------------------ piezas comunes
def folio(n, dark=False, label=''):
    return (f'<div class="folio"><span><b>C / I</b> &nbsp;{n:02d} — {TOTAL:02d}</span><span>{label}</span>'
            f'<span>ANEXO · PROPUESTA ARTÍSTICA</span></div>'
            '<i class="rm a"></i><i class="rm b"></i><i class="rm c"></i><i class="rm d"></i>')


def pie():
    return ('<div class="pie"><span>CARTOGRAFÍAS DE LO INVISIBLE · VISUALIZACIÓN DE DATOS Y CREACIÓN CURATORIAL</span>'
            '<span>FONDO DE CREACIÓN ARTÍSTICA INTERDISCIPLINARIA · UNIVERSIDAD FINIS TERRAE</span></div>')


QR = (ROOT / 'assets/pdf/qr.svg').read_text().split('?>', 1)[-1]

CSS = '''
@font-face{font-family:'Instrument Serif';src:url(assets/fonts/InstrumentSerif-Regular.ttf)}
@font-face{font-family:'Instrument Serif';font-style:italic;src:url(assets/fonts/InstrumentSerif-Italic.ttf)}
@font-face{font-family:'Newsreader';font-weight:300;src:url(assets/fonts/Newsreader-Light.ttf)}
@font-face{font-family:'Newsreader';font-weight:400;src:url(assets/fonts/Newsreader-Regular.ttf)}
@font-face{font-family:'Newsreader';font-weight:500;src:url(assets/fonts/Newsreader-Medium.ttf)}
@font-face{font-family:'Newsreader';font-style:italic;font-weight:400;src:url(assets/fonts/Newsreader-Italic.ttf)}
@font-face{font-family:'Newsreader';font-style:italic;font-weight:300;src:url(assets/fonts/Newsreader-LightItalic.ttf)}
@font-face{font-family:'Plex';font-weight:300;src:url(assets/fonts/IBMPlexMono-Light.ttf)}
@font-face{font-family:'Plex';font-weight:400;src:url(assets/fonts/IBMPlexMono-Regular.ttf)}
@font-face{font-family:'Plex';font-weight:500;src:url(assets/fonts/IBMPlexMono-Medium.ttf)}
@page{size:297mm 210mm;margin:0}
:root{--paper:#eeede7;--ink:#171714;--red:#c9241c;--muted:#63635c;--line:#c9c8c0;--night:#0b0b0a}
*{box-sizing:border-box;margin:0;padding:0}
html{-webkit-print-color-adjust:exact;print-color-adjust:exact}
body{background:#777;font-family:'Newsreader',serif;color:var(--ink)}
.page{width:297mm;height:210mm;position:relative;overflow:hidden;background:var(--paper);page-break-after:always;break-after:page}
.page.paper{background:url(assets/pdf/grano.png) 0 0/60mm,var(--paper)}
.page.night{background:var(--night);color:var(--paper)}
.folio,.pie{position:absolute;left:15mm;right:15mm;display:flex;justify-content:space-between;font:400 5.6pt/1 'Plex';letter-spacing:.16em;color:var(--muted);z-index:20}
.folio{top:7mm}.pie{bottom:6.3mm}.folio b{color:var(--red);font-weight:500}
.night .folio,.night .pie{color:#8d8c84}
.rm{position:absolute;width:3.2mm;height:3.2mm;z-index:21}
.rm::before,.rm::after{content:'';position:absolute;background:#8d8c84}
.rm::before{left:0;right:0;top:50%;height:.18mm}.rm::after{top:0;bottom:0;left:50%;width:.18mm}
.rm.a{top:5.4mm;left:5.4mm}.rm.b{top:5.4mm;right:5.4mm}.rm.c{bottom:5.4mm;left:5.4mm}.rm.d{bottom:5.4mm;right:5.4mm}
.k{font:500 6.1pt/1.4 'Plex';letter-spacing:.17em;text-transform:uppercase;color:var(--red)}
h1{font:400 66pt/.86 'Instrument Serif';letter-spacing:-.025em}
h2{font:400 31pt/.98 'Instrument Serif';letter-spacing:-.018em;margin:2.2mm 0 0}
h1 em,h2 em,h3 em{font-style:italic}
h3{font:400 15pt/1.05 'Instrument Serif';letter-spacing:-.01em}
p{font:400 8.9pt/1.42 'Newsreader';hyphens:auto}
.lead{font:300 11pt/1.38 'Newsreader';max-width:150mm;margin-top:3mm}
.lead em{font-style:italic}
.cap{font:400 5.4pt/1.5 'Plex';letter-spacing:.08em;color:var(--muted);text-transform:uppercase}
.night .cap{color:#8d8c84}
.m{color:var(--muted)}
.frame{border:.2mm solid var(--ink);display:block;width:100%;object-fit:cover}
.night .frame{border-color:#3a3a35}
.num{font:400 30pt/1 'Instrument Serif';color:var(--red)}
.chart{width:100%;display:block;overflow:visible}
.chart .t{font:400 6.4px 'Plex';letter-spacing:.06em;fill:var(--ink)}.chart .t.m{fill:var(--muted)}.chart .t.w{fill:#eeede7;font-size:5.5px}
.abs{position:absolute}
/* portada */
.cover img.bg{position:absolute;inset:0;width:100%;height:100%;object-fit:cover}
.cover .fade{position:absolute;inset:0;background:linear-gradient(90deg,rgba(11,11,10,.96) 0,rgba(11,11,10,.82) 30%,rgba(11,11,10,0) 52%)}
.cover .reg{position:absolute;top:15mm;left:15mm;font:400 7pt/1.5 'Plex';color:var(--red);letter-spacing:.06em}
.cover .tit{position:absolute;left:15mm;top:56mm;width:118mm}
.cover .sub{font:300 italic 13pt/1.3 'Newsreader';margin-top:7mm;color:#d9d7cf;width:96mm}
.cover .k{margin-bottom:6mm}
.cover .inst{position:absolute;left:15mm;bottom:15mm;font:400 6.2pt/1.75 'Plex';letter-spacing:.15em;color:#b4b2a9}
.cover .tags{position:absolute;right:15mm;bottom:15mm;text-align:right;font:400 6.2pt/1.75 'Plex';letter-spacing:.15em;color:#8d8c84}
/* niveles de relación */
.obra{display:grid;grid-template-columns:86mm 1fr;gap:12mm;align-items:center}
.niveles{margin-top:4.5mm;border-top:.2mm solid var(--line);padding-top:3mm;display:grid;grid-template-columns:13mm 1fr 13mm 1fr;gap:2mm 3mm;align-items:center}
.niveles svg{width:13mm;height:2mm}.niveles p{font-size:7.6pt;line-height:1.3}.niveles b{font-weight:500}
/* formas de ver */
.tiles{display:grid;grid-template-columns:repeat(3,1fr);gap:7mm 6mm;margin-top:7mm}
.tile img{aspect-ratio:1.95/1}
.tile .row{display:flex;align-items:baseline;gap:2.2mm;margin-top:2.2mm}
.tile .row .k{color:var(--red)}
.tile p{font-size:8.1pt;line-height:1.35;margin-top:1mm}
/* hallazgos */
.hz{display:grid;grid-template-columns:repeat(3,1fr);gap:9mm;margin-top:6mm}
.hz .num{margin-bottom:1mm}
.hz h3{margin-bottom:2mm}
.hz p+p{margin-top:1.6mm}
.hz.h2 .vis{height:61mm}
.hz .vis{margin-bottom:3.4mm;height:66mm;display:flex;flex-direction:column;justify-content:flex-end}
.ritual{border:.2mm solid var(--ink);padding:2.6mm 3mm;position:relative}
.ritual .rw{font:400 italic 17pt/1 'Instrument Serif';color:var(--red);margin-bottom:1.6mm}
.vec{border-top:.2mm solid var(--line);padding:1.3mm 0}.vec .k{color:var(--ink);font-size:5.2pt}
.vec p:last-child{font:400 italic 7.4pt/1.3 'Newsreader'}
.lat{display:grid;grid-template-columns:1fr auto;gap:.6mm 2mm;margin-top:2mm;font:400 7.4pt/1.25 'Newsreader'}
.lat span:nth-child(2n){font:400 5.4pt/1.6 'Plex';color:var(--red);letter-spacing:.06em;text-transform:uppercase;text-align:right}
.lat i{color:var(--red);font-style:normal}
.terr{display:grid;gap:.7mm}
.cierre{margin-top:9mm;border-top:.2mm solid var(--ink);padding-top:4mm;font:400 24pt/1.08 'Instrument Serif';letter-spacing:-.01em;max-width:230mm}
.cierre em{color:var(--red)}
.tb{display:grid;grid-template-columns:20mm 1fr 7mm;align-items:center;gap:2mm;font:400 5.2pt/1 'Plex';letter-spacing:.08em}
.tb i{height:1.7mm;background:var(--ink);display:block}.tb i.r{background:var(--red)}.tb b{font-weight:400;text-align:right}
/* estudios */
.est{display:grid;grid-template-columns:1fr 1fr;gap:8mm 9mm;margin-top:7mm}
.est .c{display:grid;grid-template-columns:94mm 1fr;gap:5mm;align-items:start}
.est img{height:56.4mm;object-fit:contain;background:var(--paper)}
.est h3{margin:1mm 0 1.6mm}
.est p{font-size:8.2pt;line-height:1.36}
.est .map{font:400 5.4pt/1.6 'Plex';color:var(--red);letter-spacing:.06em;text-transform:uppercase;margin-top:2mm}
/* tecnologías */
.tec{display:grid;grid-template-columns:24mm 1fr;gap:1.9mm 4mm;margin-top:4mm;border-top:.2mm solid #3a3a35;padding-top:3.4mm}
.tec dt{font:500 6.2pt/1.45 'Plex';letter-spacing:.08em;color:var(--paper);text-transform:uppercase}
.tec dt small{display:block;font-weight:400;color:#8d8c84;letter-spacing:.06em}
.tec dd{font:400 7.9pt/1.35 'Newsreader';color:#d9d7cf}
.tec dd b{font-weight:500;color:var(--paper)}
.tec2{display:grid;grid-template-columns:1fr 1fr;gap:7mm;margin-top:5mm;border-top:.2mm solid #3a3a35;padding-top:3.2mm}
.tec2 p{color:#d9d7cf;font-size:7.8pt;line-height:1.36;margin-top:1.4mm}
ul.prev{list-style:none;margin-top:1.2mm}ul.prev li{font:400 7.5pt/1.32 'Newsreader';color:#d9d7cf;padding:1mm 0;border-bottom:.2mm solid #2a2a26}ul.prev b{font-weight:500;color:var(--paper)}
/* referencias */
.refs{display:flex;gap:5mm;margin-top:17mm;align-items:flex-start}
.ref img{height:76mm;width:auto;display:block}
.ref h3{font-size:14.5pt;margin:2.3mm 0 1.4mm}
.ref p{font-size:8.3pt;line-height:1.36;color:#d9d7cf}
.ref .url{font:400 5.2pt/1.5 'Plex';color:#8d8c84;letter-spacing:.04em;margin-top:1.4mm;word-break:break-all}
.ref .k{margin-top:2mm;display:block}
/* genealogía */
.gen{display:grid;grid-template-columns:repeat(4,1fr);gap:7mm;margin-top:6mm}
.gen .g>.k{border-bottom:.2mm solid var(--ink);padding-bottom:1.5mm;margin-bottom:2.5mm;display:block}
.gen .e{margin-bottom:4.4mm}
.gen .e .a{font:400 5.6pt/1.4 'Plex';letter-spacing:.08em;text-transform:uppercase;color:var(--muted)}
.gen .e h3{font-size:14pt;margin:.6mm 0 1mm}
.gen .e p{font-size:8.2pt;line-height:1.35}
.lin{margin:4mm 0 5mm}.chart .s{font:italic 400 9.5px 'Instrument Serif'}.chart text[fill='#c9241c']{fill:#c9241c}
.lect{border-top:.2mm solid var(--line);margin-top:1mm;padding-top:2.6mm;display:grid;grid-template-columns:24mm 1fr;gap:3mm}
.lect p{font-size:7.9pt}
/* proceso */
.tl{margin-top:7mm;position:relative}
.tl .months{display:grid;grid-template-columns:repeat(10,1fr);font:400 5.4pt/1 'Plex';letter-spacing:.1em;color:var(--muted);border-bottom:.2mm solid var(--ink);padding-bottom:1.6mm}
.tl .ph{display:grid;grid-template-columns:repeat(10,1fr);margin-top:1.6mm;align-items:center}
.tl .bar{height:5.2mm;background:var(--ink);color:var(--paper);font:400 5.4pt/5.2mm 'Plex';letter-spacing:.08em;padding:0 2mm;text-transform:uppercase;white-space:nowrap;overflow:hidden}
.tl .bar.r{background:var(--red)}
.tl .lbl{font:400 7.6pt/1.2 'Newsreader';padding-left:2mm;grid-column:span 4}
.fds{display:grid;grid-template-columns:repeat(5,1fr);gap:5mm;margin-top:4.5mm}.fd{border-top:.6mm solid var(--ink);padding-top:1.6mm}.fd.r{border-color:var(--red)}.fd p{font-size:7.9pt;line-height:1.32;margin-top:.8mm}
.cols3{display:grid;grid-template-columns:1.15fr 1fr 1fr;gap:9mm;margin-top:8mm}
.cols3 .k{display:block;border-bottom:.2mm solid var(--ink);padding-bottom:1.5mm;margin-bottom:2.4mm}
.team p{font-size:8pt;line-height:1.32;margin-bottom:1.8mm}.team b{font-weight:500}
ul.ent{list-style:none}ul.ent li{font:400 8pt/1.32 'Newsreader';padding:1.1mm 0;border-bottom:.2mm solid var(--line)}
ul.ent li::before{content:'— ';color:var(--red)}
.tras{margin-top:5mm;border-top:.2mm solid var(--ink)}
.tras .tr{display:grid;grid-template-columns:30mm 92mm 1fr;gap:5mm;padding:.95mm 0;border-bottom:.2mm solid var(--line);align-items:baseline}
.tras .tr p{font-size:7.7pt;line-height:1.3}.tras .tr .cap{color:var(--ink)}.tras .tr.h p{color:var(--red)}
.tras h3{margin:2.6mm 0 1.4mm}
.qr{display:flex;gap:4mm;align-items:center}
.qr svg{width:20mm;height:20mm}.qr svg path{fill:var(--ink)}
'''


def page_cover():
    return f"""<section class="page night cover">
<img class="bg" src="assets/pdf/portada.jpg"><div class="fade"></div>
<i class="rm a"></i><i class="rm b"></i><i class="rm c"></i><i class="rm d"></i>
<div class="reg">C / I<br>001—048</div>
<div class="tit"><p class="k">Anexo · Propuesta artística</p>
<h1>Cartografías<br><em>de lo invisible</em></h1>
<p class="sub">Visualización de datos y creación curatorial. Obra audiovisual e interactiva sobre la base de artistas de Plataforma Arte y Medios.</p></div>
<div class="inst">FONDO DE CREACIÓN ARTÍSTICA INTERDISCIPLINARIA<br>UNIVERSIDAD FINIS TERRAE · FACULTAD DE ARTES · FACULTAD DE INGENIERÍA<br>PLATAFORMA ARTE Y MEDIOS (PAM) · 2026—2027</div>
<div class="tags">ESPACIALIZACIÓN<br>SONIFICACIÓN<br>TEMPORALIZACIÓN<br>COMPOSICIÓN GENERATIVA</div>
</section>"""


def nivel(svg, title, text):
    return f'<svg viewBox="0 0 50 8">{svg}</svg><p><b>{title}.</b> {text}</p>'


def page_obra():
    L = lambda dash, col='#171714', w=1.4: f'<line x1="0" y1="4" x2="50" y2="4" stroke="{col}" stroke-width="{w}" stroke-dasharray="{dash}"/>'
    niveles = ''.join([
        nivel(L('none'), 'Documentada', 'Vínculo respaldado por el catálogo o por una fuente.'),
        nivel(L('2 5'), 'Propuesta', 'Afinidad calculada por reglas o algoritmos. Debe contrastarse.'),
        nivel(L('none', '#c9241c'), 'Interpretada', 'Conexión que traza una persona durante la visita.'),
        nivel(L('1.5 4', '#c9241c', 1.8), 'Latente ∴', 'Afinidad poco probable entre registros de categorías distintas.'),
        nivel(L('7 3', '#c9241c'), 'Emergente ⇄', 'Relación que se crea por el uso repetido del público.'),
    ])
    return f"""<section class="page paper">{folio(2, label='OBRA Y ARCHIVO')}
<div class="abs obra" style="left:15mm;top:16mm;right:15mm;bottom:14mm"><div>
<p class="k">01 · Obra y archivo</p>
<h2>La obra y el<br><em>archivo de PAM</em></h2>
<p class="lead" style="font-size:10.4pt">Obra audiovisual interactiva en formato web que trabaja con la base de artistas de Plataforma Arte y Medios (PAM): artistas, colectivos y obras del cruce entre arte, ciencia y tecnología, con sus técnicas, temas, cronologías y territorios.</p>
<p style="margin-top:3.2mm">El público cambia criterios, da peso a intereses y recorre conexiones. Cada decisión reorganiza la imagen y el sonido del conjunto y deja ver que la lectura del archivo depende del criterio con que se ordena.</p>
<p style="margin-top:1.8mm">El mockup que acompaña este anexo es una prueba conceptual. Sus datos de entrada son los 48 conceptos del Glosario Medial. En la obra, esos nodos pasarán a ser perfiles de artistas, colectivos y obras del catálogo de PAM.</p>
<div class="qr" style="margin-top:6mm">{QR}<p class="cap">Versión web del mockup<br><span style="color:var(--ink)">{URL}</span></p></div>
</div>
<div><img class="frame" src="assets/pdf/cap_01_glosario.jpg" style="aspect-ratio:16/9">
<p class="cap" style="margin-top:2.6mm">Mockup v1.4, vista general. Datos de entrada: 48 conceptos del Glosario Medial, con 55 vínculos y 46 relaciones latentes. Todavía no incluye registros del catálogo de PAM.</p>
<p style="margin-top:4mm;font-size:8pt">La obra distingue tres niveles de relación. El mockup agrega dos variantes.</p>
<div class="niveles" style="margin-top:2mm">{niveles}</div>
</div></div>
{pie()}</section>"""


def page_escena():
    return f"""<section class="page night">
<img src="assets/pdf/esc_amplia.jpg" style="position:absolute;inset:0;width:100%;height:100%;object-fit:cover">
{folio(3, True, 'EXHIBICIÓN')}
<div class="abs" style="left:0;right:0;bottom:0;height:52mm;background:linear-gradient(180deg,rgba(11,11,10,0),rgba(11,11,10,.88) 55%)"></div>
<div class="abs" style="left:15mm;top:17mm;width:118mm">
<p class="k">02 · Exhibición</p>
<h2 style="color:var(--paper)">Exhibición <em>en sala</em></h2></div>
<div class="abs" style="left:15mm;bottom:12mm;width:132mm">
<p style="color:#e4e2da;font-size:9.4pt">La obra se presenta en proyección o pantalla grande, con audio estéreo, y funciona sin conexión a internet. Se recorre con ratón, pantalla táctil o teclado. Con una cámara se suma el gesto: la pinza sobre un nombre lo selecciona y abre su ficha, y la mano abierta desplaza el conjunto. El sonido corresponde al elemento seleccionado.</p>
</div>
<p class="cap abs" style="right:15mm;bottom:12mm;text-align:right;color:#a9a79f">Simulación de montaje · proyección de 6,4 × 3,6 m · figuras a escala<br>En pantalla, el mockup en modo proyección con la capa «Invisibles»</p>
</section>"""


def tile(img, k, name, text):
    return f'<div class="tile"><img class="frame" src="assets/pdf/{img}"><div class="row"><span class="k">{k}</span><h3>{name}</h3></div><p>{text}</p></div>'


def page_formas():
    tiles = ''.join([
        tile('cap_01_glosario_campo.jpg', '01', 'Glosario', 'Ordena por técnica, tema o territorio. Cada criterio agrupa los elementos de otra manera.'),
        tile('cap_02_tema_peso_campo.jpg', '02', 'Dar peso', 'El interés que elige el público atrae hacia el centro los elementos relacionados.'),
        tile('cap_03_radar_campo.jpg', '03', '<em>Radar</em>', 'Un barrido recorre los vínculos en el tiempo, los hace sonar y revela relaciones latentes.'),
        tile('cap_04_invisibles_campo.jpg', '04', '<em>Invisibles</em>', 'Muestra afinidades poco probables entre elementos de técnica, tema y territorio distintos.'),
        tile('cap_05_mapa_campo.jpg', '05', 'Mapa', 'Chile como cartograma. Cada territorio se alarga según cuánto se menciona y cuánta atención recibe.'),
        tile('cap_07_volumen_campo.jpg', '06', '3D', 'Técnica, tema y territorio como tres ejes. Cada elemento se ubica en el cruce de sus categorías.'),
    ])
    return f"""<section class="page paper">{folio(4, label='VISTAS DEL PROTOTIPO')}
<div class="abs" style="left:15mm;top:17mm;right:15mm">
<p class="k">03 · Vistas del prototipo</p>
<h2>Seis vistas <em>del mismo conjunto</em></h2>
<p class="lead">Las seis vistas usan los mismos 48 conceptos y cada una los ordena con otro criterio. Cambia qué elementos quedan cerca, cuáles se destacan y cuáles suenan. En la obra se aplicarán a los perfiles de artistas.</p>
<div class="tiles">{tiles}</div></div>
{pie()}</section>"""


def page_hallazgos1():
    lat = ''.join(f'<span>{a} <i>∴</i> {b}</span><span>{w}</span>' for a, b, w in LAT)
    return f"""<section class="page paper">{folio(5, label='HALLAZGOS I')}
<div class="abs" style="left:15mm;top:17mm;right:15mm">
<p class="k">04 · Hallazgos</p>
<h2>Hallazgos de la <em>prueba conceptual</em></h2>
<p class="lead">Observaciones hechas con el mockup sobre datos demostrativos. Cada una muestra información que no aparece al leer las fichas por separado e indica qué se buscará en los perfiles de PAM.</p>
<div class="hz">
<div><div class="vis">{html_ritual()}</div><p class="num">1</p><h3>Un elemento, <em>tres grupos</em></h3>
<p>En su ficha, «ritual» tiene tres etiquetas. En pantalla, cada criterio lo ubica junto a once conceptos distintos: con cuerpo y performance por técnica, con archivo y documentación por tema, y con paisaje y deriva por territorio.</p>
<p>Con los perfiles pasará lo mismo. Los vecinos de un artista cambian si se ordena por herramienta, por tema o por territorio, y la obra muestra cuál criterio está activo.</p></div>
<div><div class="vis">{svg_sonido()}</div><p class="num">2</p><h3>La cantidad de vínculos <em>se escucha</em></h3>
<p>Con el sonido activo, el elemento seleccionado suena según sus relaciones. «Memoria», con 13 vínculos, suena agudo y rápido. {uno} de los 48 conceptos tienen un solo vínculo y suenan graves y lentos.</p>
<p>Los vínculos se concentran en archivo y cuerpo; sonido, materia y código promedian menos de dos. En un catálogo de artistas, pocos vínculos pueden indicar falta de documentación y no menor relevancia.</p></div>
<div><div class="vis"><img class="frame" src="assets/pdf/cap_09_latente_campo.jpg" style="aspect-ratio:2.35/1"><div class="lat">{lat}</div></div><p class="num">3</p><h3>Afinidades <em>poco probables</em></h3>
<p>La capa Invisibles propone 46 relaciones entre conceptos que no comparten técnica, tema ni territorio. 40 surgen de palabras poco frecuentes presentes en ambas definiciones y 6 son ejemplos curatoriales.</p>
<p>En PAM, el mismo procedimiento podrá acercar una obra hecha con circuitos y microcontroladores a una pintura que representa circuitos. Son hipótesis que se contrastarán con las obras y las fuentes.</p></div>
</div></div>
{pie()}</section>"""


TRASLADO = [
    ('Nodo', 'Concepto del glosario (48)', 'Perfil de artista, colectivo u obra (59 entradas iniciales y al menos 12 por incorporar)'),
    ('Ficha', 'Definición del Glosario Medial', 'Texto autorizado del catálogo, con su fuente y estado de validación'),
    ('Categorías', 'Técnica, tema y territorio de prueba', 'Herramientas, lenguajes, temas, materiales y motivos; territorio de origen, residencia, producción o exhibición'),
    ('Documentada', 'La definición de un concepto nombra a otro', 'Relación registrada en el catálogo, como integrantes de un colectivo u obras exhibidas juntas'),
    ('Propuesta y latente', 'Reglas locales sobre palabras compartidas', 'Algoritmos de afinidad y búsqueda semántica con IA, marcados como sugerencia'),
    ('Interpretada', 'Lectura del público y relaciones emergentes', 'Interpretaciones de participantes, registradas aparte y revisadas en el laboratorio'),
    ('Vacíos', 'Pesos territoriales simulados', 'Datos ausentes señalados como tales, sin completarlos por inferencia'),
]


def page_hallazgos2():
    filas = ''.join(f'<div class="tr"><p class="cap">{a}</p><p>{b}</p><p>{c}</p></div>' for a, b, c in TRASLADO)
    return f"""<section class="page paper">{folio(6, label='HALLAZGOS II')}
<div class="abs" style="left:15mm;top:17mm;right:15mm">
<div class="hz h2" style="margin-top:0">
<div><div class="vis"><img class="frame" src="assets/pdf/cap_07_volumen_campo.jpg" style="aspect-ratio:3/1;margin-bottom:2.4mm">{svg_volumen()}</div><p class="num">4</p><h3>Cruces <em>vacíos</em></h3>
<p>En 3D, cada concepto ocupa el cruce de su técnica, su tema y su territorio. De 125 cruces posibles hay 8 ocupados, porque las tres clasificaciones de prueba casi coinciden.</p>
<p>Esa redundancia no se ve en una tabla. Por eso el diagnóstico del catálogo separará herramientas, lenguajes, temas, materiales y motivos representados.</p></div>
<div><div class="vis"><img class="frame" src="assets/pdf/cap_05_mapa_campo.jpg" style="aspect-ratio:3/1;margin-bottom:2.4mm">{html_territorios()}</div><p class="num">5</p><h3>Territorio y <em>vacío documental</em></h3>
<p>Mapa dibuja Chile como cartograma. Cada lugar se alarga según cuánto se menciona y según la atención que reciben sus conceptos. Con pesos demostrativos, Santiago, Antofagasta y Chiloé tienen cerca de 12 % cada uno y Punta Arenas 6 %.</p>
<p>Un territorio con poco peso indica un vacío documental y no ausencia de actividad artística.</p></div>
<div><div class="vis"><img class="frame" src="assets/pdf/cap_10_emergente.jpg" style="aspect-ratio:16/9"></div><p class="num">6</p><h3>Relaciones <em>creadas por el uso</em></h3>
<p>Si alguien pasa dos veces entre dos conceptos sin vínculo, se crea una relación emergente (⇄), aquí entre «escucha» y «código». No proviene del catálogo ni de las reglas.</p>
<p>La atención baja a la mitad cada 4 minutos y lo revelado cada 40. Estas relaciones se registran aparte de las documentadas.</p></div>
</div>
<div class="tras"><h3>Del glosario <em>a los perfiles</em></h3>
<div class="tr h"><p class="cap"></p><p class="cap">En el mockup</p><p class="cap">En la obra</p></div>{filas}</div>
</div>
{pie()}</section>"""


def est(img, name, text, mapping):
    return f'<div class="c"><img class="frame" src="assets/pdf/{img}"><div><h3>{name}</h3><p>{text}</p><p class="map">{mapping}</p></div></div>'


def page_estudios():
    cells = ''.join([
        est('est_espacializacion.jpg', 'Espacialización', 'Compara dos lecturas de los mismos perfiles: el territorio documentado y una proximidad conceptual propuesta. Las curvas unen ambas posiciones para que la cercanía visual no se lea como cercanía geográfica.', 'posición ← territorio / afinidad · ○ dato ausente'),
        est('est_sonificacion.jpg', 'Sonificación', 'Partitura de una vuelta del radar. Cada elemento suena cuando el barrido lo alcanza, de modo que el recorrido se puede seguir sin mirar la pantalla.', 'altura ← elemento · timbre ← familia · panorama ← posición · intensidad ← interés'),
        est('est_temporalizacion.jpg', '<em>Temporalización</em>', 'El ángulo indica el año y cada anillo una técnica. Los perfiles sin fecha se dibujan vacíos, en un sector propio.', 'ángulo ← año · anillo ← técnica · cuerda ← tema'),
        est('est_recorridos.jpg', 'Composición <em>generativa</em>', 'Superpone los recorridos de muchos visitantes sobre el glosario. En rojo, un recorrido con sus pasos numerados.', 'grosor ← frecuencia de paso · anillos ← visitas'),
    ])
    return f"""<section class="page paper">{folio(7, label='ESTUDIOS')}
<div class="abs" style="left:15mm;top:17mm;right:15mm">
<p class="k">05 · Estudios</p>
<h2>Estudios para el <em>catálogo de artistas</em></h2>
<p class="lead">Cuatro estudios en p5.js, hechos para este anexo con 59 perfiles ficticios de artistas y colectivos, la misma cantidad de entradas del corpus de partida de PAM. Prueban las cuatro operaciones del proyecto y servirán de base para el laboratorio.</p>
<div class="est">{cells}</div></div>
{pie()}</section>"""


def page_tecnologias():
    return f"""<section class="page night">
<img src="assets/pdf/esc_cercana.jpg" style="position:absolute;left:0;top:0;height:100%;width:142mm;object-fit:cover;object-position:58% 50%">
{folio(8, True, 'TECNOLOGÍAS')}
<div class="abs" style="left:152mm;top:17mm;right:15mm">
<p class="k">06 · Tecnologías</p>
<h2 style="color:var(--paper)">Tecnologías <em>del mockup</em></h2>
<dl class="tec">
<dt>p5.js 2.3<small>imagen y movimiento</small></dt><dd>Dibujo en canvas con física de resortes, inercia y colisiones, proyección 3D propia y un cartograma de Chile que se deforma en vivo.</dd>
<dt>Tone.js 14.8<small>sonificación</small></dt><dd>Cada vínculo del elemento seleccionado suena según su tipo: tono senoidal (glosario), clic (afinidad), FM (lectura del público o emergente) y un tono casi inaudible (latente). <b>Con muchas relaciones el sonido es agudo y rápido, hasta 180 bpm; con pocas, grave y lento, 54 bpm.</b></dd>
<dt>MediaPipe<small>hand landmarker · 21 puntos</small></dt><dd>Seguimiento de la mano con cámara. La pinza selecciona y abre; la mano abierta desplaza el conjunto o gira el volumen. Es opcional y necesita conexión para descargarse. El resto funciona sin internet, con p5.js y Tone.js incluidos en el HTML.</dd>
<dt>Reglas locales<small>sin IA conectada</small></dt><dd>Un vínculo es documentado cuando la definición de un concepto nombra a otro. Las latentes se calculan por palabras poco frecuentes compartidas entre categorías distintas.</dd>
<dt>Vida del archivo<small>registro del uso</small></dt><dd>La atención, lo revelado, las huellas y las relaciones emergentes se guardan en el navegador y disminuyen con el tiempo.</dd>
<dt>Acceso<small>varias entradas</small></dt><dd>Ratón, pantalla táctil y teclado, índice alfabético, anuncios para lectores de pantalla, movimiento reducido y modo proyección. Cada estado de la vista se puede compartir con un enlace.</dd>
</dl>
<div class="tec2">
<div><p class="k" style="color:#8d8c84">En el proyecto</p>
<p>Los conceptos se reemplazarán por perfiles del catálogo de PAM normalizado (59 entradas y al menos 12 por incorporar), con fuentes y estados de validación. Se evaluarán búsqueda semántica con IA sobre textos autorizados, YOLO para etiquetas visuales revisables y realidad aumentada en sala, según los resultados de los prototipos.</p>
<p>El espacio aporta proyector o pantalla grande y audio estéreo. El proyecto aporta computador, cámara web y periféricos.</p></div>
<div><p class="k" style="color:#8d8c84">Desarrollos previos en p5.js</p>
<ul class="prev">
<li><b>Glosario Medial.</b> Nube de palabras, deriva suave, selección con cambio de escala y ficha. Es la base principal del mockup.</li>
<li><b>Glosario Navegable.</b> Órbitas elípticas y profundidad por escala y opacidad.</li>
<li><b>Radar de Valparaíso.</b> Trayectorias y lectura orbital; origen de la capa Radar.</li>
<li><b>Nadir.</b> Capa orbital que se superpone y se retira; posiciones y trazas a distintos ritmos.</li>
<li><b>Píxeles expandidos · Data 1.</b> Motor Atlas: redistribución por criterios, foco ampliado y vecinos conectados.</li>
</ul></div></div>
</div>
<p class="cap abs" style="left:15mm;bottom:12mm;color:#a9a79f">Simulación · gesto de pinza sobre la vista Mapa</p>
</section>"""


REFS = [
    ('ref_1.jpg', 'Colección <em>en volumen</em>', 'Las imágenes forman una esfera. El conjunto se percibe antes que cada pieza.', 'instagram.com/p/DXTNiy9DhgG', ''),
    ('ref_2.jpg', 'Dos lecturas <em>en espejo</em>', 'Los mismos puntajes en un gráfico radial duplicado y reflejado, con escalas y cifras legibles.', 'instagram.com/p/DJ6p2IiNtpg', ''),
    ('ref_3.jpg', 'Vórtice <em>taxonómico</em>', 'Objetos ordenados por semejanza visual con CLIP y UMAP. La proximidad la calcula un modelo y no responde a una categoría. Se relaciona con la capa Invisibles y con la búsqueda semántica del proyecto.', 'instagram.com/p/Dc8V99ps_SH', 'Particularmente atingente'),
    ('ref_4.jpg', 'Código <em>visible</em>', 'El código que genera la figura gira junto con ella. Las reglas que producen la imagen quedan a la vista.', 'instagram.com/p/DZahCr3jFab', 'Atingente'),
]


def page_refs():
    items = ''.join(f'<div class="ref"><img src="assets/pdf/{img}"><span class="k">{tag or "&nbsp;"}</span><h3>{t}</h3><p>{d}</p><p class="url">{u}</p></div>' for img, t, d, u, tag in REFS)
    return f"""<section class="page night">{folio(9, True, 'REFERENCIAS VISUALES')}
<div class="abs" style="left:15mm;top:17mm;right:15mm">
<p class="k">07 · Referencias visuales</p>
<h2 style="color:var(--paper)">Referencias <em>visuales</em></h2>
<div class="refs">{items}</div>
<p class="cap" style="margin-top:6mm">Referencias reunidas por el equipo. Autoría y créditos por confirmar.</p>
</div></section>"""


GEN = [
    ('Archivo como constelación', [
        ('Aby Warburg · 1924–1929', 'Atlas Mnemosyne', 'Paneles de imágenes relacionadas por afinidad y no por cronología. Antecedente de la lectura de un archivo como constelación.'),
        ('Refik Anadol · 2017', 'Archive Dreaming', 'Recorrido con aprendizaje automático por 1,7 millones de documentos del archivo SALT, en Estambul, en una sala inmersiva.'),
        ('Diagne, Barradeau, Doury · 2018', 't-SNE Map', 'Obras de Google Arts &amp; Culture dispuestas según una semejanza visual calculada.'),
    ]),
    ('Datos, territorio y mediación', [
        ('Chile · 1971–1973', 'Proyecto Cybersyn', 'Sala de operaciones para visualizar en tiempo real datos de la economía del país. Antecedente chileno de cibernética y visualización.'),
        ('Iconoclasistas · 2013', 'Manual de mapeo colectivo', 'Metodología de cartografía crítica y participativa desarrollada en América Latina.'),
        ('Subirós y De Vicente · 2014', 'Big Bang Data', 'Exposición del CCCB sobre la datificación, que también se presentó en Santiago. La visualización como experiencia pública y crítica.'),
    ]),
    ('Sonificación', [
        ('Mark Hansen y Ben Rubin · 2001–2002', 'Listening Post', 'Texto de miles de salas de chat convertido en voz, sonido y luz en tiempo real.'),
        ('Ryoji Ikeda · 2006–', 'datamatics', 'Datos convertidos en material audiovisual a escala de sala.'),
        ('NASA Chandra · SYSTEM Sounds · 2020–', 'A Universe of Sound', 'Sonificación de datos astronómicos, diseñada también para personas ciegas o con baja visión.'),
    ]),
    ('Temporalización', [
        ('Charles Joseph Minard · 1869', 'Campaña de Rusia', 'Tiempo, espacio, temperatura y pérdidas de un ejército en un solo gráfico.'),
        ('W. E. B. Du Bois · 1900', 'Retratos de datos', 'Gráficos sobre la población afroamericana para la Exposición de París.'),
        ('Giorgia Lupi y Stefanie Posavec · 2014–2015', 'Dear Data', 'Datos cotidianos registrados durante un año en postales dibujadas a mano.'),
    ]),
]


# (año, nombre, nivel): nivel > 0 arriba, < 0 abajo; |2| se aleja de la línea para no chocar
LINEA = [(1869, 'Minard', 1), (1900, 'Du Bois', -1), (1924, 'Warburg', 1), (1971, 'Cybersyn', -1),
         (2001, 'Listening Post', 1), (2006, 'datamatics', -1), (2013, 'Iconoclasistas', 1), (2014, 'Big Bang Data · Dear Data', -1),
         (2017, 'Archive Dreaming', 2), (2018, 't-SNE Map', -2), (2020, 'A Universe of Sound', 1),
         (2026, 'Cartografías de lo invisible', -1)]


def svg_linea():
    W_ = 1000
    X = lambda y: (0.36 * (y - 1860) / 130 if y <= 1990 else 0.36 + 0.64 * (y - 1990) / 40) * W_
    out = [f'<svg viewBox="-10 -62 {W_ + 20} 124" class="chart linea">',
           f'<line x1="0" y1="0" x2="{W_}" y2="0" stroke="#171714" stroke-width=".8"/>',
           f'<line x1="{X(1990)}" y1="-5" x2="{X(1990)}" y2="5" stroke="#171714" stroke-width=".6" stroke-dasharray="1.5 2"/>',
           f'<text x="{X(1990) + 4}" y="12" class="t m">DESDE 1990 LA ESCALA SE AMPLÍA</text>']
    for y, n, lv in LINEA:
        x = X(y)
        red = y == 2026
        up = lv > 0
        reach = 16 if abs(lv) == 1 else 36
        col = '#c9241c' if red else '#171714'
        out.append(f'<circle cx="{x:.1f}" cy="0" r="{4 if red else 2.6}" fill="{col}"/>')
        out.append(f'<line x1="{x:.1f}" y1="{-4 if up else 4}" x2="{x:.1f}" y2="{-reach if up else reach}" stroke="{col}" stroke-width=".5"/>')
        yy = -(reach + 14) if up else reach + 12
        out.append(f'<text x="{x:.1f}" y="{yy}" class="t" text-anchor="middle" fill="{col}">{y}</text>'
                   f'<text x="{x:.1f}" y="{yy + 9}" class="s" text-anchor="middle" fill="{col}">{n}</text>')
    out.append('</svg>')
    return ''.join(out)


def page_genealogia():
    cols = ''
    for title, entries in GEN:
        es = ''.join(f'<div class="e"><p class="a">{a}</p><h3>{t}</h3><p>{d}</p></div>' for a, t, d in entries)
        cols += f'<div class="g"><span class="k">{title}</span>{es}</div>'
    return f"""<section class="page paper">{folio(10, label='REFERENTES')}
<div class="abs" style="left:15mm;top:17mm;right:15mm">
<p class="k">08 · Referentes</p>
<h2>Referentes de <em>visualización y sonificación</em></h2>
<div class="gen">{cols}</div>
<div class="lin">{svg_linea()}</div>
<div class="lect"><span class="k">Lecturas</span><p>Lev Manovich, <em>The Language of New Media</em> (2001) y Cultural Analytics · Nicolas Bourriaud, <em>Esthétique relationnelle</em> (1998) · Donna Haraway, «Situated Knowledges» (1988) · Mitchell Whitelaw, «Generous Interfaces for Digital Cultural Collections» (2015) · Brian Mackern, <em>netart latino database</em> (registro del net.art latinoamericano, 2000–2005).</p></div>
</div>
{pie()}</section>"""


def page_proceso():
    months = ''.join(f'<span>MES {i}</span>' for i in range(1, 11))
    fases = [(1, 2, 'Diagnóstico', 'Diagnóstico del catálogo y acuerdos sobre permisos, preguntas, categorías y fuentes.', False),
             (2, 5, 'Normalización y prototipos', 'Jornadas formativas, normalización de la información y primeros prototipos audiovisuales.', False),
             (5, 8, 'Obra web', 'Implementación e integración de espacialización, sonificación y composición generativa.', True),
             (8, 9, 'Laboratorio', 'Laboratorio curatorial y pruebas con participantes con distintas necesidades de acceso.', False),
             (9, 10, 'Exhibición', 'Montaje, exhibición, transferencia y memoria.', True)]
    rows = ''
    for a, b, name, desc, red in fases:
        rows += '<div class="ph">' + (f'<span style="grid-column:span {a - 1}"></span>' if a > 1 else '')
        rows += f'<div class="bar{" r" if red else ""}" style="grid-column:span {b - a + 1}">{name}</div></div>'
    descs = ''.join(f'<div class="fd{" r" if red else ""}"><p class="cap">MES {a}–{b}</p><p>{desc}</p></div>' for a, b, name, desc, red in fases)
    return f"""<section class="page paper">{folio(11, label='PROCESO')}
<div class="abs" style="left:15mm;top:17mm;right:15mm">
<p class="k">09 · Proceso</p>
<h2>Proceso <em>y equipo</em></h2>
<div class="tl"><div class="months">{months}</div>{rows}</div>
<div class="fds">{descs}</div>
<div class="cols3">
<div class="team"><span class="k">Equipo</span>
<p><b>Valentina Montero.</b> Responsable del proyecto (ad honorem); criterios curatoriales y documentales de PAM.</p>
<p><b>Dirección Artística y de Interacción.</b> Supervisa y coordina el desarrollo: lenguaje audiovisual, interacción e integración de la obra.</p>
<p><b>Darío Fernando Rojas Díaz.</b> Mentor y supervisor de los estudiantes de Ingeniería; revisión técnica de los prototipos.</p>
<p><b>Dos estudiantes de Arte.</b> Gestión, ampliación y homologación del archivo; propuestas de visualización y cruces. <b>Dos estudiantes de Ingeniería.</b> Estructuras interactivas y algorítmicas, integración de datos y montaje web.</p></div>
<div><span class="k">Resultados comprometidos</span><ul class="ent">
<li>Obra web audiovisual e interactiva, funcional y documentada.</li>
<li>Catálogo normalizado, con diccionario de categorías y protocolo de actualización.</li>
<li>Al menos tres exploraciones curatoriales documentadas.</li>
<li>Memoria técnica y conceptual, con los ensayos integrados y descartados.</li></ul></div>
<div><span class="k">Exhibición y mediación</span>
<p style="font-size:8pt;line-height:1.34">Proyector o pantalla grande con audio estéreo en un espacio profesional por confirmar, y una demostración abierta en la Universidad Finis Terrae. Dos jornadas formativas y un laboratorio interdisciplinario. La mediación explicará los criterios que generan cada conexión.</p>
<div class="qr" style="margin-top:4mm">{QR}<p class="cap">Mockup en línea<br><span style="color:var(--ink)">{URL}</span></p></div></div>
</div></div>
<p class="cap abs" style="left:15mm;bottom:11.5mm">Imágenes: capturas del mockup v1.4, estudios en p5.js y simulaciones de sala hechos para este anexo · Datos demostrativos</p>
{pie()}</section>"""


html = f"""<!doctype html><html lang="es"><head><meta charset="utf-8"><title>Cartografías de lo invisible — Anexo propuesta artística</title>
<style>{CSS}</style></head><body>
{page_cover()}{page_obra()}{page_escena()}{page_formas()}{page_hallazgos1()}{page_hallazgos2()}{page_estudios()}{page_tecnologias()}{page_refs()}{page_genealogia()}{page_proceso()}
</body></html>"""
(ROOT / 'anexo.html').write_text(html)
print('ok anexo.html', len(html), 'bytes ·', uno, 'conceptos con un solo vínculo ·', {k: round(v, 2) for k, v in fam.items()})
