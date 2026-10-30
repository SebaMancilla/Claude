// Capturas del prototipo web (prototipo/cartografias.html, v1.4) en distintos estados.
// p5 y Tone.js se sirven desde vendor/ (la sesión no tiene acceso al CDN); la cámara no se usa.
// Uso: node src/capturas.mjs [nombre ...]
import { createRequire } from 'node:module';
import path from 'node:path';
import fs from 'node:fs';
import { fileURLToPath } from 'node:url';

const { chromium } = createRequire(import.meta.url)('playwright');
const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const PAGE = 'file://' + path.join(ROOT, 'prototipo/cartografias.html');
const LIBS = [['**/p5.min.js', 'vendor/p5.min.js'], ['**/Tone.js', 'vendor/Tone.js']].map(([p, f]) => [p, fs.readFileSync(path.join(ROOT, f))]);
const OUT = path.join(ROOT, 'assets/capturas');

// Recorrido que deja atención en algunos conceptos (subrayado rojo) antes de capturar.
const VISITAS = `for (const n of ['memoria','cuerpo','hardware','ritual','escucha']) selectNode(byName(n)); closeDetail();`;
const SHOTS = [
  { name: '01_glosario', hash: 'criterio=0&interes=memoria&peso=35' },
  { name: '02_tema_peso', hash: 'criterio=1&interes=archivo&peso=90' },
  { name: '03_radar', hash: 'criterio=0&interes=memoria&peso=35&radar=1', wait: 6200 },
  { name: '04_invisibles', hash: 'criterio=0&interes=memoria&peso=35&invisibles=1', wait: 5200 },
  { name: '05_mapa', hash: 'criterio=3&interes=memoria&peso=35', run: VISITAS, wait: 5200 },
  { name: '06_mapa_lugar', hash: 'criterio=3&interes=memoria&peso=35&lugar=Valparaíso', wait: 5200 },
  { name: '07_volumen', hash: 'criterio=0&interes=memoria&peso=35&volumen=1', wait: 5200 },
  { name: '08_ficha_latentes', hash: 'criterio=0&interes=hardware&peso=40&invisibles=1&concepto=hardware' },
  { name: '09_latente', hash: 'criterio=0&interes=hardware&peso=40&invisibles=1',
    run: `selectNode(byName('hardware')); showRelation(latent.find(L => L.key === pairKey(byName('hardware'), byName('ritual'))));` },
  { name: '10_emergente', hash: 'criterio=1&interes=escucha&peso=40',
    run: `${VISITAS} for (const n of ['escucha','código','escucha','código']) selectNode(byName(n)); showRelation(edges.find(e => e.kind === 'emergent'));` },
  { name: '11_proyeccion', hash: 'criterio=0&interes=archivo&peso=60&invisibles=1', projection: true, wait: 5200 },
  { name: '12_proyeccion_mapa', hash: 'criterio=3&interes=memoria&peso=40', projection: true, run: VISITAS, wait: 5200 },
];

const only = process.argv.slice(2);
const browser = await chromium.launch();
for (const s of SHOTS) {
  if (only.length && !only.includes(s.name)) continue;
  const ctx = await browser.newContext({ viewport: { width: 1600, height: 900 }, deviceScaleFactor: 2 });
  for (const [pat, body] of LIBS) await ctx.route(pat, r => r.fulfill({ body, contentType: 'text/javascript' }));
  const page = await ctx.newPage();
  page.on('pageerror', e => console.error(s.name, e.message));
  await page.goto(PAGE + '#' + s.hash);
  await page.waitForFunction(() => window.cartografias?.getState().nodes === 48);
  await page.waitForTimeout(300);
  if (s.run) await page.evaluate(s.run);
  if (s.projection) {
    await page.keyboard.press('p');
    await page.waitForTimeout(400);
  }
  await page.waitForTimeout(s.wait ?? 4500);
  await page.evaluate(() => { document.getElementById('toast').hidden = true; document.getElementById('exit-projection').style.visibility = 'hidden'; });
  await page.screenshot({ path: path.join(OUT, s.name + '.png') });
  if (s.projection) {   // posiciones de las palabras, para que el gesto de las escenas apunte a una
    const pos = await page.evaluate(() => nodes.map(n => ({ name: n.name, x: n.sx, y: n.sy, w: n.tw, fs: n.fs })));
    fs.writeFileSync(path.join(OUT, s.name + '.json'), JSON.stringify(pos));
  }
  console.log(s.name, JSON.stringify(await page.evaluate(() => window.cartografias.getState())));
  await ctx.close();
}
await browser.close();
