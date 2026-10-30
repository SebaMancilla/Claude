// Extrae del prototipo (v1.4) los datos que sostienen los hallazgos del anexo:
// vínculos por tipo, relaciones latentes, pesos territoriales, celdas vacías del volumen 3D,
// vecinos de un concepto según cada criterio y densidad sonora. Escribe assets/datos.json.
import { createRequire } from 'node:module';
import path from 'node:path';
import fs from 'node:fs';
import { fileURLToPath } from 'node:url';

const { chromium } = createRequire(import.meta.url)('playwright');
const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1600, height: 900 } });
for (const [pat, file] of [['**/p5.min.js', 'vendor/p5.min.js'], ['**/Tone.js', 'vendor/Tone.js']]) {
  const body = fs.readFileSync(path.join(ROOT, file));
  await page.route(pat, r => r.fulfill({ body, contentType: 'text/javascript' }));
}
await page.goto('file://' + path.join(ROOT, 'prototipo/cartografias.html'));
await page.waitForFunction(() => window.cartografias?.getState().nodes === 48);
await page.waitForTimeout(800);
const datos = await page.evaluate(() => {
  const name = i => DATA[i].name;
  const byKind = {};
  for (const e of edges) byKind[e.kind] = (byKind[e.kind] || 0) + 1;
  const degree = DATA.map(d => ({ name: d.name, n: neighbors(d.id).length }));
  // vecinos por criterio: con quién comparte grupo cada concepto
  const crit = ['técnica', 'tema', 'territorio'];
  const grupos = crit.map((c, i) => {
    const g = {};
    for (const d of DATA) (g[d.tags[i]] ??= []).push(d.name);
    return { criterio: c, grupos: g };
  });
  const latentes = latent.map(L => ({ a: name(L.a), b: name(L.b), origen: L.origin, improbabilidad: L.imp,
    compartidas: L.shared.slice(0, 4), razon: L.reason }));
  // territorio: dónde vive cada concepto y peso de cada lugar
  const b = bounds();
  updateMap(b, 1);
  const territorios = TERRITORIES.map((T, t) => ({ nombre: T.name, peso: +T.share.toFixed(3),
    hogar: DATA.filter(d => homeOf[d.id] === t).map(d => d.name),
    top: DATA.map(d => ({ n: d.name, s: terrShare[d.id][t] })).sort((x, y) => y.s - x.s).slice(0, 4).map(x => x.n + ' ' + Math.round(x.s * 100) + '%') }));
  // volumen 3D: combinaciones técnica × tema × territorio ocupadas y vacías
  const vals = [0, 1, 2].map(i => [...new Set(DATA.map(d => d.tags[i]))]);
  const ocupadas = new Set(DATA.map(d => d.tags.join('|')));
  const posibles = vals[0].length * vals[1].length * vals[2].length;
  // densidad sonora (misma fórmula que sonicFocus)
  const sonido = DATA.map(d => {
    const rels = relationsOf(d.id);
    const w = rels.reduce((s, r) => s + (r.kind === 'inferred' ? .7 : r.kind === 'latent' ? .45 + r.strength * .4 : 1) * (.8 + r.strength * .4), 0);
    const dd = Math.max(0, Math.min(1, (w - 1) / 7));
    return { name: d.name, rels: rels.length, bpm: Math.round(54 + dd * 126), hz: Math.round(82 * Math.pow(2, dd * 4.4)) };
  }).sort((x, y) => y.bpm - x.bpm);
  return { byKind, edges: edges.length, latentes: latentes.length, degree: degree.sort((a, b) => b.n - a.n),
    grupos, latentesLista: latentes, territorios, volumen: { valores: vals, ocupadas: ocupadas.size, posibles }, sonido };
});
fs.writeFileSync(path.join(ROOT, 'assets/datos.json'), JSON.stringify(datos, null, 1));
console.log(JSON.stringify({ byKind: datos.byKind, edges: datos.edges, latentes: datos.latentes, volumen: datos.volumen,
  top: datos.degree.slice(0, 6), bottom: datos.degree.slice(-6) }, null, 0));
await browser.close();
