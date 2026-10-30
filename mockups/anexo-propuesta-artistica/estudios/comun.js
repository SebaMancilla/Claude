// Datos y utilidades compartidas por los estudios p5.
// Los 48 conceptos vienen del Glosario Medial del prototipo; los 59 registros son
// DEMOSTRATIVOS (generados con semilla fija): no corresponden al catálogo de PAM.
'use strict';

const PAL = {
  paper: '#eeede7', ink: '#171714', red: '#c9241c', muted: '#63635c', line: '#c9c8c0', night: '#0b0b0a',
};

const CONCEPTOS = [
  ['memoria', 'archivo'], ['archivo', 'archivo'], ['archivo vivo', 'archivo'], ['archivo digital', 'archivo'],
  ['cuerpo', 'acción'], ['corporalidad', 'acción'], ['presencia', 'acción'], ['afecto', 'acción'],
  ['percepción', 'acción'], ['interacción', 'acción'], ['interfaz', 'acción'], ['performance', 'acción'],
  ['ritual', 'acción'], ['oralidad', 'acción'], ['ancestralidad', 'acción'], ['comunidad', 'acción'],
  ['cartografía', 'materia'], ['paisaje', 'materia'], ['deriva', 'materia'], ['naturaleza', 'materia'],
  ['ecosistema', 'materia'], ['bioarte', 'materia'], ['materia', 'materia'], ['resonancia', 'materia'],
  ['escucha', 'sonido'], ['arte sonoro', 'sonido'], ['memoria sonora', 'sonido'], ['frecuencia', 'sonido'],
  ['espacialización', 'sonido'], ['espectro', 'sonido'], ['código', 'código'], ['arte generativo', 'código'],
  ['programación', 'código'], ['glitch', 'código'], ['máquina', 'código'], ['hardware', 'código'],
  ['cibernética', 'código'], ['redes', 'código'], ['internet', 'código'], ['net art', 'código'],
  ['inteligencia artificial', 'código'], ['aprendizaje automático', 'código'], ['obsolescencia', 'código'],
  ['futuros', 'código'], ['conocimiento situado', 'archivo'], ['experimentación', 'archivo'],
  ['laboratorio', 'archivo'], ['documentación', 'archivo'],
].map(([name, family], id) => ({ id, name, family }));

const FAMILIAS = ['archivo', 'acción', 'materia', 'sonido', 'código'];

// Correspondencia sonora del prototipo: escala de 8 grados, 3 octavas desde 110 Hz.
const ESCALA = [0, 2, 5, 7, 9, 12, 14, 17];
const semitono = id => ESCALA[id % 8] + (id % 3) * 12;
const frecuencia = id => 110 * Math.pow(2, semitono(id) / 12);

function mulberry32(a) {
  return function () {
    a |= 0; a = (a + 0x6d2b79f5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

const TECNICAS = ['electrónica', 'código', 'sonido', 'video', 'bioarte', 'instalación', 'net art', 'performance'];
const TEMAS = ['memoria', 'territorio', 'cuerpo', 'ecología', 'tecnología', 'archivo'];
const CIUDADES = [
  ['Arica', -18.48], ['Antofagasta', -23.65], ['La Serena', -29.9], ['Valparaíso', -33.05], ['Santiago', -33.45],
  ['Concepción', -36.83], ['Temuco', -38.74], ['Valdivia', -39.81], ['Puerto Montt', -41.47], ['Punta Arenas', -53.16],
];
const PESO_CIUDAD = [1, 1, 1, 4, 14, 3, 1, 2, 1, 1];

function pickW(r, items, w) {
  const tot = w.reduce((a, b) => a + b, 0);
  let x = r() * tot;
  for (let i = 0; i < items.length; i++) { x -= w[i]; if (x <= 0) return items[i]; }
  return items[items.length - 1];
}

// 59 registros demostrativos con vacíos de información explícitos (null).
function registrosDemo(seed = 59) {
  const r = mulberry32(seed);
  const out = [];
  for (let i = 0; i < 59; i++) {
    const colectivo = r() < 0.22;
    const tecnica = pickW(r, TECNICAS, [3, 3, 3, 2, 1, 2, 1.5, 2]);
    const tema = TEMAS[Math.floor(r() * TEMAS.length)];
    let ciudad = r() < 0.12 ? null : (r() < 0.14 ? 'extranjero' : pickW(r, CIUDADES, PESO_CIUDAD)[0]);
    let anio = r() < 0.15 ? null : Math.round(1966 + Math.pow(r(), 0.55) * 58);
    out.push({
      id: i, colectivo, tecnica, tema, ciudad, anio,
      afin: Math.floor(r() * 48),            // concepto afín (propuesta algorítmica demo)
      j: r(), k: r(), l: r(),                 // azar estable para disposición
    });
  }
  return out;
}

// Modo still: ?still&w=..&h=.. fija tamaño y tiempo para capturas del anexo.
const Q = new URLSearchParams(location.search);
const STILL = Q.has('still');
const SIZE = () => STILL ? [Number(Q.get('w') || 1600), Number(Q.get('h') || 1000)] : [innerWidth, innerHeight];
function marcaRegistro(p, x, y, s = 5, col = PAL.muted) {
  p.push(); p.stroke(col); p.strokeWeight(0.7); p.line(x - s, y, x + s, y); p.line(x, y - s, x, y + s); p.pop();
}
function listo() { if (STILL) { window.__listo = true; } }
