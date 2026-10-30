// Imprime anexo.html como PDF A4 apaisado.
// Uso: node src/pdf.mjs [salida.pdf]
import { createRequire } from 'node:module';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const { chromium } = createRequire(import.meta.url)('playwright');
const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const out = process.argv[2] || path.join(ROOT, 'Anexo_Propuesta_Artistica_Cartografias.pdf');
const browser = await chromium.launch();
const page = await browser.newPage();
await page.goto('file://' + path.join(ROOT, 'anexo.html'), { waitUntil: 'load' });
await page.evaluate(() => document.fonts.ready);
await page.pdf({ path: out, width: '297mm', height: '210mm', printBackground: true, preferCSSPageSize: true });
await browser.close();
console.log('ok', out);
