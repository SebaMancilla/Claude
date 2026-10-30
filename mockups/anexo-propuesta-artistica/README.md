# Anexo · Propuesta artística — Cartografías de lo invisible

PDF horizontal (A4 apaisado, 11 páginas) para el Fondo de Creación Artística
Interdisciplinaria: `Anexo_Propuesta_Artistica_Cartografias.pdf`.

La obra trabaja con la base de artistas de Plataforma Arte y Medios (PAM). El mockup
(`prototipo/cartografias.html`, v1.4) es una prueba conceptual que usa como datos de entrada
los 48 conceptos del Glosario Medial; en la obra esos nodos pasan a ser perfiles de artistas,
colectivos y obras. El anexo lo explica en la página 6 («Del glosario a los perfiles»).

| Página | Contenido |
|---|---|
| 1 | Portada (estudio p5 «vórtice del archivo») |
| 2 | Obra y archivo, niveles de relación, QR al mockup |
| 3 | Exhibición: simulación de sala con público |
| 4 | Seis vistas del prototipo |
| 5–6 | Hallazgos de la prueba conceptual y traslado a perfiles |
| 7 | Estudios p5.js para el catálogo de artistas |
| 8 | Tecnologías del mockup y desarrollos previos |
| 9 | Referencias visuales (Instagram) |
| 10 | Referentes y línea de tiempo |
| 11 | Proceso, equipo y resultados |

## Cómo se arma

Requiere Node con Playwright (Chromium) y Python 3 con numpy, opencv, scipy, Pillow y qrcode.

```
node src/capturas.mjs      # capturas del mockup (p5 y Tone.js desde vendor/)
node src/datos.mjs         # datos del mockup para los hallazgos → assets/datos.json
node src/stills.mjs        # imágenes de los estudios p5 (estudios/*.html)
python3 src/escena.py      # simulaciones de sala (usa ../instalacion-escenica/src/crowd.py)
python3 src/preparar.py    # recortes, JPEG livianos, limpieza de referencias y QR → assets/pdf
python3 src/anexo.py       # anexo.html
node src/pdf.mjs           # PDF
```

Las capturas PNG originales (`assets/capturas/*.png`, ~33 MB) no se versionan: se regeneran con
`src/capturas.mjs`. Las versiones usadas en el PDF están en `assets/pdf/`.

## Notas

- **Datos.** Todo es demostrativo: los 48 conceptos del glosario, los pesos territoriales del
  mockup y los 59 perfiles ficticios de los estudios. Ninguna cifra corresponde al catálogo de PAM.
- **Hallazgos.** Las cifras de las páginas 5 y 6 salen de `assets/datos.json`, extraído del
  mockup: 55 vínculos, 46 latentes, 24 conceptos con un solo vínculo, 8 de 125 cruces ocupados
  en 3D y pesos territoriales del Mapa.
- **Escenas.** Figuras de `instalacion-escenica/src/crowd.py`. A ese módulo se le agregó la pose
  `reach` (brazo alzado hacia la pantalla) y el registro de articulaciones `_joints`, que se usa
  para dibujar los 21 puntos de mano de MediaPipe. Las poses existentes no cambian.
- **Referencias visuales.** Las cuatro imágenes son capturas de Instagram aportadas por el equipo.
  Se asignaron a los enlaces en el orden en que se compartieron; la autoría queda por confirmar.
  Se taparon los botones de la interfaz de Instagram y se recortaron avatares.
- **Desarrollos previos.** Glosario Medial, Glosario Navegable, Radar de Valparaíso, Nadir y
  Píxeles expandidos aparecen solo como texto (página 8): sus archivos están en el computador del
  autor y no se pudieron capturar desde esta sesión.
- **Tipografías.** Instrument Serif, Newsreader e IBM Plex Mono (Google Fonts, licencia OFL).
