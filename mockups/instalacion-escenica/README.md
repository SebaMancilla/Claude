# Instalación escénica — mockups nocturnos

Mockups de noche sobre las 3 fotos del espacio (las fotos no se reemplazan, se
re-iluminan). En todas las vistas:

- la pantalla LED muestra la escena de la levitación de *Teorema* (Pasolini, 1968; placeholder, ver abajo);
- una luz de contra baja por la escalera desde arriba, frontal a cámara, con haze;
- el rapero Teorema canta en el descanso, con una luz frontal tenue;
- hay público a escala real (las mismas personas en las 3 fotos, ubicadas en planta).

| | A1 — horizontal detrás del pilar | A2 — horizontal delante del pilar | B — vertical |
|---|---|---|---|
| Foto 1 | `renders/foto1_opcionA1.png` | `renders/foto1_opcionA2.png` | `renders/foto1_opcionB.png` |
| Foto 2 | `renders/foto2_opcionA1.png` | `renders/foto2_opcionA2.png` | `renders/foto2_opcionB.png` |
| Foto 3 | `renders/foto3_opcionA1.png` | `renders/foto3_opcionA2.png` | `renders/foto3_opcionB.png` |

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

Medidas que salen de la calibración (verificadas contra la persona que aparece en el descanso de la foto 1):

- Pilares de ~0,58 m, capitel hasta **~4,0 m** = fondo de las vigas principales.
- Losa a 5,2 m (la cota que diste): las vigas principales tienen ~1,2 m de alto.
- Descanso de la escalera a ~1,85 m. El frente del bloque de la escalera (la cara con
  la "V") está 2,95 m detrás de la fila de pilares más cercana.
- Entre el pilar más cercano y la escalera quedan ~2,25 m libres.

## Opciones de pantalla

**A1 — horizontal detrás del pilar.** 8,0 × 4,0 m, apoyada en el piso, en el plano del
frente de la escalera y a borde con ella (desde el canto de la escalera, 8 m hacia la
izquierda). El pilar más cercano queda por delante y la tapa en parte, según la vista.

**A2 — horizontal delante del pilar.** La misma pantalla de 8 × 4 m, adelantada hasta
justo delante de la fila de pilares (0,55 m delante del eje, sin tocar el capitel). Su
canto derecho queda alineado con el canto de la escalera. Desde la foto 1 tapa la
escalera, porque la cámara la mira en diagonal.

En ambas, la altura libre bajo las vigas es ~4,0 m, así que no entra más alta. Con 4 m
de alto, la relación queda en 2:1. Un 16:9 real con esa altura mediría 7,1 × 4 m, y un
3:2, 6 × 4 m. Se cambia en `OPTIONS`, en `src/render.py`.

**B — vertical.** 2,0 × 5,0 m, en el plano del frente de la escalera y a borde con ella,
en el hueco entre el pilar y la escalera. Los 5 m suben dentro del casetón del cielo.
Según la lectura de las fotos, hay una viga secundaria (fondo a ~4,5 m) que pasa sobre
el borde de la escalera, así que los últimos ~0,5 m del canto derecho podrían chocar con
ella. Conviene verificarlo en terreno.

## Escalera

- **Contra:** foco en lo alto del tramo superior (~4,4 m), apuntando escalera abajo
  hacia el público, blanco cálido, haz de ~60°, con haze concentrado en el cubo de la
  escalera. Desde la foto 2 queda justo detrás de la cabeza del cantante.
- **Frontal tenue:** foco colgado a ~3,9 m, unos 7,5 m delante del descanso, apuntado
  al pecho del cantante, con haz estrecho (~20°) y baja intensidad.
- **Cantante:** es una **figura genérica** (capucha y micrófono): no reproduce la cara
  ni el parecido del artista. En la foto 1 cae justo donde está la persona real del descanso.

## Público

28 personas genéricas de espaldas (1,60–1,86 m), ubicadas en planta frente a la
pantalla y a la escalera. Como son las mismas en las 3 fotos, la escala es consistente.
Tienen filo de luz de la pantalla y de la contra, sombra de contacto y recorte en el
reflejo del piso. En A2 se omiten las personas que quedarían detrás de la pantalla.
La lista está en `CROWD`, en `src/audience.py`.

## Contenido de la pantalla

La imagen de la pantalla es un **placeholder que evoca la escena de la levitación de
_Teorema_**: Emilia de negro suspendida sobre el techo de la casa de campo, con cielo
nublado. No es el fotograma real. Para usar el fotograma real (se recorta a pantalla
completa en cada formato):

```bash
MOCKUP_FRAME=ruta/al/fotograma.jpg python3 src/render.py 3 A renders/foto3_opcionA1.png --rebake
```

En A1, lo que cae en el centro de la pantalla queda detrás del pilar en las fotos 2 y 3.
Por eso en el placeholder la figura está en el tercio derecho.

## Regenerar

```bash
pip install numpy scipy opencv-python-headless pillow
cd mockups/instalacion-escenica
python3 src/render.py <foto 1|2|3> <A|A2|B> renders/fotoN_opcionX.png --rebake
python3 src/sheet.py renders renders/comparativa.jpg 'foto{ph}_opcion{opt}.png'
```

`--rebake` recalcula la geometría y los mapas de luz (~2–3 min por imagen). Sin él, se
reutiliza la caché en `.cache/` y solo se recompone (segundos), lo que sirve para
ajustar la exposición y las intensidades (`DEFAULT` en `src/render.py`).

Archivos de `src/`:

- `cams.py`: cámaras calibradas.
- `scene.py`: geometría del espacio y raycasting.
- `render.py`: iluminación nocturna, derrame de la pantalla, reflejo en el piso pulido y haze volumétrico.
- `teorema.py`: contenido de la pantalla.
- `performer.py`: el cantante.
- `audience.py`: el público.
- `content.py`: ruido y utilidades de color.
- `sheet.py`: hoja comparativa.
