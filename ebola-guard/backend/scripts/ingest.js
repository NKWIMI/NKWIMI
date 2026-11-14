// npm run ingest            -> download sources, chunk, embed, save data/index.json
// npm run ingest -- --no-embed   -> keyword search only (no model download)
// npm run ingest -- --sources path/to/sources.json --out path/to/index.json
import path from 'node:path';
import { readFile } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';

import { createEmbedder } from '../src/embedder.js';
import { buildIndex, saveIndex } from '../src/indexer.js';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const args = process.argv.slice(2);
const opt = (name, fallback) => {
  const i = args.indexOf(name);
  return i >= 0 ? args[i + 1] : fallback;
};

const sourcesFile = path.resolve(opt('--sources', path.join(ROOT, 'data', 'sources.json')));
const outFile = path.resolve(opt('--out', path.join(ROOT, 'data', 'index.json')));
const embed = !args.includes('--no-embed');

const sources = JSON.parse(await readFile(sourcesFile, 'utf8'));
console.log(`Ingesting ${sources.length} sources from ${path.relative(ROOT, sourcesFile)}`);

const { index, report } = await buildIndex({
  sources,
  baseDir: path.dirname(sourcesFile),
  embedder: embed ? createEmbedder() : null,
  log: (line) => console.log(line),
});
await saveIndex(index, outFile);

const ok = report.filter((r) => r.status === 'ok');
console.log(`\nSaved ${index.chunks.length} passages from ${ok.length}/${report.length} sources to ${path.relative(ROOT, outFile)}`);
console.log(`Search mode: ${index.embeddingModel ? `hybrid (keywords + ${index.embeddingModel})` : 'keywords only'}`);
if (ok.length < report.length) {
  console.log('Some sources failed: check their URL in sources.json, or save the page and use "file" instead of downloading.');
  process.exitCode = ok.length ? 0 : 1;
}
