# Instalación escénica — mockups nocturnos

Mockups de dos opciones de pantalla LED sobre las 3 fotos del espacio, de noche, con
luz de contra bajando por la escalera y el rapero Teorema cantando en el descanso.

| | Opción A — LED horizontal 8 × 4 m | Opción B — LED vertical 2 × 5 m |
|---|---|---|
| Foto 1 | `renders/foto1_opcionA.png` | `renders/foto1_opcionB.png` |
| Foto 2 | `renders/foto2_opcionA.png` | `renders/foto2_opcionB.png` |
| Foto 3 | `renders/foto3_opcionA.png` | `renders/foto3_opcionB.png` |

Hoja comparativa: `renders/comparativa.jpg`.

## Cómo se construyó la escala

Las fotos no traen datos de cámara, así que se calibró cada una a partir de la
grilla de pilares (4,5 m entre ejes). Con las bases de los pilares se resolvió
la cámara de cada foto (focal, altura, orientación) con error medio de ~3 px, y
las tres quedaron en un mismo sistema de coordenadas del espacio:

| Foto | Lente equivalente | Altura de cámara |
|---|---|---|
| 1 | ~15 mm (gran angular) | 1,46 m |
| 2 | ~15 mm (gran angular) | 1,51 m |
| 3 | ~26 mm | 1,31 m |

Medidas que salen de la calibración (verificadas contra la persona en el descanso):

- Pilares de ~0,58 m, capitel hasta **~4,0 m** = fondo de las vigas principales.
- Losa a 5,2 m (la cota que diste): las vigas principales tienen ~1,2 m de alto.
- Descanso de la escalera a ~1,85 m. Frente del bloque de la escalera (cara con la "V")
  a 2,95 m detrás de la fila de pilares más cercana.
- Entre el pilar más cercano y la escalera quedan ~2,25 m libres.

## Opción A — horizontal

- **8,0 × 4,0 m**, apoyada en el piso, en el plano del frente de la escalera, desde el
  borde izquierdo de la escalera 8 m hacia la izquierda. Queda **detrás** del pilar más
  cercano, que la tapa parcialmente según el punto de vista.
- La altura libre bajo las vigas es ~4,0 m, así que no entra más alta. Con 4 m de alto,
  la relación queda en 2:1. Un 16:9 real con esa altura mediría 7,1 × 4 m, y un 3:2,
  6 × 4 m. El script lo cambia con una línea (`OPTIONS` en `src/render.py`).

## Opción B — vertical

- **2,0 × 5,0 m**, en el mismo plano, en el hueco entre el pilar y la escalera.
- Los 5 m suben dentro del casetón del cielo, entre la viga del pilar y una viga
  secundaria. Ese casetón mide ~1,95 m de ancho libre, así que 2 m quedan justos
  (conviene verificarlo en terreno).

## Escalera

- Foco en lo alto del tramo superior (~4,4 m), apuntando escalera abajo hacia el
  público ("contra" frontal a cámara), blanco cálido, haz de ~60°, con haze
  concentrado en el cubo de la escalera.
- El rapero es una **silueta genérica** a contraluz: no reproduce su cara ni su
  parecido. En la foto 1 cae justo donde está la persona real del descanso.

## Contenido de la pantalla

La imagen de la pantalla es un **placeholder que evoca la escena de la levitación
de _Teorema_** (Pasolini, 1968): Emilia de negro suspendida sobre el techo de la
casa de campo, con cielo nublado. No es el fotograma real. Para usar el fotograma
real (se recorta a pantalla completa en cada formato):

```bash
MOCKUP_FRAME=ruta/al/fotograma.jpg python3 src/render.py 3 A renders/foto3_opcionA.png --rebake
```

En la opción A, lo que cae en el centro de la pantalla queda detrás del pilar en
las fotos 2 y 3. Por eso en el placeholder la figura está en el tercio derecho.

## Regenerar

```bash
pip install numpy scipy opencv-python-headless pillow
cd mockups/instalacion-escenica
python3 src/render.py <foto 1|2|3> <A|B> renders/fotoN_opcionX.png --rebake
python3 src/sheet.py renders renders/comparativa.jpg 'foto{ph}_opcion{opt}.png'
```

Archivos de `src/`: `cams.py` (cámaras calibradas), `scene.py` (geometría del espacio
y raycasting), `render.py` (iluminación nocturna, derrame de la pantalla, reflejo en
el piso pulido, haze volumétrico), `teorema.py` (contenido de la pantalla),
`performer.py` (silueta del cantante), `content.py` (ruido y utilidades de color),
`sheet.py` (hoja comparativa).
