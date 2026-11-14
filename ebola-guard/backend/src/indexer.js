// Builds the search index from data/sources.json:
// download (or read) each document -> extract text -> chunk -> embed -> save.
import { readFile, writeFile, mkdir } from 'node:fs/promises';
import path from 'node:path';

import { chunkSections } from './chunker.js';
import { extractFromHtml, extractFromText } from './extract.js';

const USER_AGENT = 'EbolaGuardRAG/1.0 (public-health information app; contact: see README)';

async function loadDocument(source, { baseDir, fetchImpl }) {
  if (source.file) {
    const raw = await readFile(path.resolve(baseDir, source.file), 'utf8');
    return source.file.endsWith('.html') || source.file.endsWith('.htm') ? extractFromHtml(raw) : extractFromText(raw);
  }
  const res = await fetchImpl(source.url, { headers: { 'User-Agent': USER_AGENT, 'Accept-Language': source.language || 'en' } });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  const type = res.headers.get('content-type') || '';
  if (type.includes('pdf')) throw new Error('PDF not supported: save it as .txt and use "file" in sources.json');
  return extractFromHtml(await res.text());
}

/**
 * sources: [{ id, org, title, url, language, license, file? }]
 * embedder: optional; without it the index works with keyword search only.
 * Returns { index, report } where report lists what happened per source.
 */
export async function buildIndex({ sources, baseDir = '.', embedder = null, fetchImpl = fetch, chunkOptions, log = () => {} }) {
  const chunks = [];
  const report = [];
  for (const source of sources) {
    try {
      const { title, sections } = await loadDocument(source, { baseDir, fetchImpl });
      const parts = chunkSections(sections, chunkOptions);
      if (!parts.length) throw new Error('no readable text found');
      parts.forEach((p, i) =>
        chunks.push({
          id: `${source.id}#${i + 1}`,
          sourceId: source.id,
          org: source.org,
          title: source.title || title,
          url: source.url,
          language: source.language || 'en',
          section: p.section,
          text: p.text,
        }),
      );
      report.push({ id: source.id, status: 'ok', chunks: parts.length });
      log(`  ✓ ${source.id}: ${parts.length} passages`);
    } catch (err) {
      report.push({ id: source.id, status: 'failed', error: err.message });
      log(`  ✗ ${source.id}: ${err.message}`);
    }
  }

  let embeddingModel = null;
  if (embedder && chunks.length) {
    try {
      log(`Computing embeddings for ${chunks.length} passages with ${embedder.model}…`);
      const vectors = await embedder.embed(chunks.map((c) => `${c.title}. ${c.section}. ${c.text}`), 'passage');
      vectors.forEach((v, i) => (chunks[i].embedding = v.map((x) => Number(x.toFixed(5)))));
      embeddingModel = embedder.model;
    } catch (err) {
      log(`  ! Embeddings skipped (${err.message}). The app will use keyword search only.`);
      chunks.forEach((c) => delete c.embedding);
    }
  }

  const index = {
    builtAt: new Date().toISOString(),
    embeddingModel,
    sources: sources.map((s) => ({ ...s, ...report.find((r) => r.id === s.id) })),
    chunks,
  };
  return { index, report };
}

export async function saveIndex(index, file) {
  await mkdir(path.dirname(file), { recursive: true });
  await writeFile(file, JSON.stringify(index));
}

export async function loadIndex(file) {
  try {
    return JSON.parse(await readFile(file, 'utf8'));
  } catch {
    return null;
  }
}
