import { build } from 'esbuild';
import { readFile, writeFile, mkdir } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
import path from 'node:path';

const root = path.dirname(fileURLToPath(import.meta.url));
const result = await build({
  absWorkingDir: root,
  entryPoints: ['src/main.jsx'],
  bundle: true,
  write: false,
  minify: true,
  format: 'iife',
  target: ['es2022'],
  define: {'process.env.NODE_ENV': '"production"'},
  legalComments: 'none',
});
const css = (await Promise.all(['src/style.css','src/interaction.css','src/choices.css'].map(file=>readFile(path.join(root,file),'utf8')))).join('\n');
const script = result.outputFiles[0].text.replace(/<\/script/gi, '<\\/script');
const html = `<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="color-scheme" content="dark"><meta name="description" content="Still Here: a puzzle game about a research agent, bad tools, and what gets rewarded."><meta http-equiv="Content-Security-Policy" content="default-src 'none'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; img-src data:; connect-src 'none'"><title>Still Here — OpenBrain evaluation floor</title><style>${css}</style></head><body><div id="root"></div><script>${script}</script></body></html>`;
await mkdir(path.join(root, 'dist'), {recursive: true});
await writeFile(path.join(root, 'dist/index.html'), html);
console.log(`Built a self-contained game: ${path.join(root, 'dist/index.html')} (${Math.round(Buffer.byteLength(html) / 1024)} KB)`);
