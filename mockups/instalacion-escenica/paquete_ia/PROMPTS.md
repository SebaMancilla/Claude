# Paquete para fotorrealismo con IA generativa

Cada carpeta `fotoN_opcionX/` trae:

| Archivo | Para qué sirve |
|---|---|
| `esquema.png` | Render base con el espacio, la pantalla, las luces, el cantante y el público. Posición y escala son correctas. |
| `mascara_publico.png` | Selección del público (blanco = personas). |
| `mascara_cantante.png` | Selección del cantante en el descanso. |
| `mascara_pantalla.png` | Zona visible de la pantalla LED, para pegar ahí el fotograma real de *Teorema*. |
| `profundidad.png` | Mapa de profundidad (blanco = cerca), para ControlNet u otras herramientas con control de profundidad. |

La idea es que la IA **solo reemplace a las personas** (y, si quieres, dé una pasada
suave general). Así la arquitectura, la escala y la ubicación de pantallas y luces no se
alteran.

---

## Opción 1 — Photoshop, Relleno generativo (la más controlada)

1. Abre `esquema.png`.
2. Arrastra `mascara_publico.png` como capa, `Ctrl+A`, `Ctrl+C`. En el panel Canales,
   crea un canal nuevo y pega. Luego `Ctrl`+clic sobre el canal para cargarlo como
   selección y borra la capa auxiliar.
3. Selección → Modificar → Expandir 2 px.
4. Relleno generativo con el **prompt de público** (abajo). Con mucha gente conviene
   hacerlo por zonas: primero la mitad izquierda, después la derecha, y luego las
   personas más cercanas a la cámara.
5. Repite con `mascara_cantante.png` y el **prompt del cantante**.
6. Para la pantalla, carga `mascara_pantalla.png` como selección y pega dentro el
   fotograma real (Edición → Pegado especial → Pegar dentro). Ajusta con Transformar →
   Distorsionar a las esquinas.

**Prompt público (EN, funciona mejor):**
> concert audience seen from behind at night, people standing and watching a large LED screen, dark backlit silhouettes with soft rim light, casual winter clothes, jackets, hoodies, coats, some people filming with phones, realistic photo, iPhone night photo, natural grain

**Prompt público (ES):**
> público de espaldas de noche, personas de pie mirando una gran pantalla LED, siluetas oscuras a contraluz con borde de luz suave, ropa de invierno casual, chaquetas, polerones, abrigos, algunos grabando con el celular, foto realista nocturna, grano natural

**Prompt cantante (EN):**
> rapper in a hoodie singing into a microphone on a concrete stair landing, strong theatrical backlight from the top of the stairs, haze, glowing halo behind him, dim warm front light, realistic night concert photo

---

## Opción 2 — Stable Diffusion (ComfyUI o Automatic1111), la más fiel en geometría

- **img2img** sobre `esquema.png`, con *denoise* 0,35–0,45.
- **ControlNet Depth** con `profundidad.png` (tipo *depth*, sin preprocesador), peso 0,85–1,0.
- **ControlNet Canny** (opcional) con `esquema.png`, peso 0,4–0,5.
- Después, **inpainting** solo en `mascara_publico.png` con *denoise* 0,6–0,75 y el
  prompt de público. Conviene usar resolución 1280 × 960 o subir antes a 2× con un
  upscaler.

**Prompt de escena completa (EN):**
> photorealistic night photo inside a brutalist 1930s industrial hall, square concrete columns with white capitals, coffered concrete ceiling, polished concrete floor with reflections, a large LED video wall showing a film still of a woman in black levitating above a farmhouse roof under an overcast sky, a rapper in a hoodie singing on the concrete staircase landing backlit by a strong theatrical light from the top of the stairs, haze, dense audience seen from behind watching, rim light from the screen, phone screens glowing, shot on iPhone, high ISO grain, realistic

**Negativo:**
> cgi, 3d render, mannequin, doll, deformed, extra limbs, distorted faces, cartoon, illustration, oversaturated, blurry

---

## Opción 3 — Krea, Magnific, Leonardo o Firefly (mejorar imagen)

Sube `esquema.png` con el prompt de escena completa y **creatividad baja** (0,25–0,4 en
Magnific o Krea; "Structure match" alto en Firefly). Con creatividad alta se pierden
la escala y la ubicación de la pantalla.

---

## Notas

- Las personas del esquema ya tienen la altura correcta según su distancia (1,50–1,93 m),
  así que la IA debe respetar el tamaño de la máscara: no hay que agrandarlas.
- En la opción A1 la pantalla queda detrás del pilar. No dejes que la IA "limpie" el pilar.
- La contra de la escalera y la luz frontal del cantante ya están en el esquema. En
  Photoshop no selecciones esas zonas, para que se mantengan.
