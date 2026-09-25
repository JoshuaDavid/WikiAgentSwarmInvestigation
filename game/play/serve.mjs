import { createServer } from 'node:http';
import { readFile } from 'node:fs/promises';
import { createReadStream } from 'node:fs';
import { fileURLToPath } from 'node:url';
import path from 'node:path';
import { CONNECTIONS, FALLBACK_CONNECTION } from './src/connections.js';

const htmlPath = fileURLToPath(new URL('./dist/index.html', import.meta.url));
const repositoryRoot = fileURLToPath(new URL('../../', import.meta.url));
const evidenceFiles = new Set([FALLBACK_CONNECTION,...Object.values(CONNECTIONS)].flatMap(entry => entry.sources || []).filter(source => source.localUrl).map(source => fileURLToPath(new URL(source.localUrl.split('#')[0], new URL('./dist/index.html', import.meta.url)))));
const port = Number(process.env.STILL_HERE_PORT || 8766);
createServer(async (req, res) => {
  try {
    const pathname = decodeURIComponent(new URL(req.url, 'http://localhost').pathname);
    if (pathname === '/' || pathname === '/index.html') {
      res.writeHead(302, {Location:'/game/play/dist/index.html'}); res.end(); return;
    }
    if (pathname === '/game/play/dist/index.html') {
      res.setHeader('Content-Type', 'text/html; charset=utf-8'); res.end(await readFile(htmlPath)); return;
    }
    const relative = pathname.slice(1);
    const target = path.resolve(repositoryRoot, relative);
    const permitted = evidenceFiles.has(target) || (relative.startsWith('game/') && /\.(md|txt|json)$/.test(relative));
    if (!permitted || !target.startsWith(path.resolve(repositoryRoot) + path.sep)) { res.writeHead(404); res.end('Not found.'); return; }
    res.setHeader('Content-Type', 'text/plain; charset=utf-8');
    res.setHeader('X-Content-Type-Options', 'nosniff');
    const stream = createReadStream(target);
    stream.on('error', () => { if (!res.headersSent) res.writeHead(404); res.end('Evidence file not found.'); });
    stream.pipe(res);
  } catch { res.writeHead(404); res.end('File not found. Build the game with npm run build.'); }
}).listen(port, '127.0.0.1', () => console.log(`Still Here: http://127.0.0.1:${port}`));
