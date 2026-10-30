// Renderiza los estudios p5 en modo still (tamaño y tiempo fijos) para el anexo.
// Uso: node src/stills.mjs [nombre ...]
import { createRequire } from 'node:module';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const { chromium } = createRequire(import.meta.url)('playwright');
const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const STILLS = {
  portada: [1485, 1050],
  espacializacion: [1500, 900],
  sonificacion: [1500, 900],
  temporalizacion: [1000, 1000],
  recorridos: [1500, 900],
};
const only = process.argv.slice(2);
const browser = await chromium.launch();
for (const [name, [w, h]] of Object.entries(STILLS)) {
  if (only.length && !only.includes(name)) continue;
  const page = await browser.newPage({ viewport: { width: w, height: h }, deviceScaleFactor: 2 });
  page.on('pageerror', e => console.error(name, e.message));
  await page.goto('file://' + path.join(ROOT, `estudios/${name}.html`) + `?still&w=${w}&h=${h}`);
  await page.waitForFunction(() => window.__listo === true, null, { timeout: 30000 });
  await page.screenshot({ path: path.join(ROOT, `assets/estudios/${name}.png`) });
  console.log('ok', name);
  await page.close();
}
await browser.close();
