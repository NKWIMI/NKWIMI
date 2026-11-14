import express from 'express';
import Anthropic from '@anthropic-ai/sdk';
import { pathToFileURL, fileURLToPath } from 'node:url';
import { readFileSync } from 'node:fs';
import path from 'node:path';

import { buildSystemPrompt } from './prompt.js';
import { createEmbedder } from './src/embedder.js';
import { loadIndex } from './src/indexer.js';
import { buildQuery, generateAnswer, retrievalOnlyAnswer, sanitizeMessages } from './src/rag.js';
import { Retriever } from './src/retriever.js';
import { detectRedFlags } from './src/safety.js';

export { sanitizeMessages };

const HERE = path.dirname(fileURLToPath(import.meta.url));
const MODEL = process.env.ANTHROPIC_MODEL || 'claude-haiku-5-5';
const MAX_CONTEXT_CHARS = 2000;
const TOP_K = Number(process.env.TOP_K) || 5;
export const INDEX_FILE = process.env.INDEX_FILE || path.join(HERE, 'data', 'index.json');

/** Very small in-memory rate limiter (per IP). Use Redis etc. at scale. */
function rateLimiter({ windowMs = 60_000, max = 15 } = {}) {
  const hits = new Map();
  return (req, res, next) => {
    const now = Date.now();
    const key = req.ip;
    const entry = hits.get(key);
    if (!entry || now - entry.start > windowMs) {
      hits.set(key, { start: now, count: 1 });
      return next();
    }
    if (++entry.count > max) {
      return res.status(429).json({ error: 'Too many messages. Please wait a minute and try again.' });
    }
    next();
  };
}

/**
 * client: Anthropic client (or a fake in tests). null = no AI.
 * retriever: search over official documents (RAG). Without it, or with an
 *   empty index, the assistant works exactly like the first version.
 * index: the loaded document index (for /api/sources and /health).
 */
export function createApp({ client, retriever = null, index = null, model = MODEL, rateLimit = {} } = {}) {
  const ai =
    client !== undefined
      ? client
      : process.env.ANTHROPIC_API_KEY
        ? new Anthropic({ apiKey: process.env.ANTHROPIC_API_KEY })
        : null;
  const rag = retriever && retriever.chunks.length > 0 ? retriever : null;

  const app = express();
  app.set('trust proxy', 1);
  app.use(express.json({ limit: '64kb' }));
  // Web demo of the assistant (Ask + document Library), handy for testing in a browser.
  app.use(express.static(path.join(HERE, 'public')));

  app.get('/health', (_req, res) =>
    res.json({
      ok: true,
      ai: Boolean(ai),
      mode: ai ? 'ai' : rag ? 'retrieval-only' : 'off',
      search: rag ? rag.mode : 'none',
      documents: index?.sources?.filter((s) => s.status === 'ok').length ?? 0,
      passages: rag?.chunks.length ?? 0,
      indexBuiltAt: index?.builtAt ?? null,
    }),
  );

  // Outbreak map data. Edit data/outbreak-map.json when WHO / the Ministry
  // of Health publish new areas or treatment centres: apps update on next open.
  app.get('/api/outbreak-map', (_req, res) => {
    try {
      const file = path.join(HERE, 'data', 'outbreak-map.json');
      const data = JSON.parse(readFileSync(file, 'utf8'));
      res.set('Cache-Control', 'public, max-age=900');
      res.json(data);
    } catch (err) {
      console.error('Map data error:', err.message);
      res.status(500).json({ error: 'Map data unavailable' });
    }
  });

  // The library of official documents the assistant answers from.
  app.get('/api/sources', (_req, res) =>
    res.json({
      builtAt: index?.builtAt ?? null,
      sources: (index?.sources || []).map(({ id, org, title, url, language, license, status, chunks: n }) => ({
        id, org, title, url, language, license, status, passages: n ?? 0,
      })),
    }),
  );

  // Search only (no AI): shows which passages the assistant would read.
  app.get('/api/search', async (req, res) => {
    const q = String(req.query.q || '').slice(0, 500);
    if (!q.trim()) return res.status(400).json({ error: 'Missing ?q=' });
    if (!rag) return res.status(503).json({ error: 'The document index is not built yet. Run: npm run ingest' });
    const { hits, confident, topDense, topKeyword } = await rag.search(q, { k: TOP_K });
    res.json({
      query: q, confident, topDense, topKeyword,
      hits: hits.map((h) => ({ id: h.chunk.id, org: h.chunk.org, title: h.chunk.title, section: h.chunk.section, url: h.chunk.url, score: h.score, bm25: h.bm25, dense: h.dense, text: h.chunk.text })),
    });
  });

  app.post('/api/chat', rateLimiter(rateLimit), async (req, res) => {
    const messages = sanitizeMessages(req.body?.messages);
    if (!messages) {
      return res.status(400).json({ error: 'Please type a question.' });
    }
    if (!ai && !rag) {
      return res.status(503).json({ error: 'The assistant is not configured yet.' });
    }

    const ctx = req.body?.screeningContext;
    const screeningContext =
      typeof ctx === 'string' && ctx.trim() ? ctx.trim().slice(0, MAX_CONTEXT_CHARS) : null;

    const voice = req.body?.mode === 'voice';
    const language = typeof req.body?.language === 'string' ? req.body.language.slice(0, 40) : null;
    const alert = detectRedFlags(messages[messages.length - 1].content);

    let hits = [];
    let confident = true;
    if (rag) ({ hits, confident } = await rag.search(buildQuery(messages), { k: TOP_K }));

    // No API key yet: show the best official passages with their sources.
    if (!ai) {
      return res.json({ ...retrievalOnlyAnswer(hits, { confident, language }), alert, mode: 'retrieval-only' });
    }

    try {
      const system = buildSystemPrompt(screeningContext, { voice, language, retrieval: Boolean(rag), confident });
      const maxTokens = voice ? 400 : 800;
      let reply;
      let sources = [];
      if (rag) {
        ({ reply, sources } = await generateAnswer({ ai, model, system, messages, hits, maxTokens }));
      } else {
        const response = await ai.messages.create({ model, max_tokens: maxTokens, system, messages });
        reply = (response.content || [])
          .filter((b) => b.type === 'text')
          .map((b) => b.text)
          .join('\n')
          .trim();
      }
      if (!reply) {
        return res.status(502).json({ error: 'The assistant could not answer. Please rephrase.' });
      }
      // Do not log message content: it is sensitive health information.
      res.json({ reply, sources, alert, mode: 'ai' });
    } catch (err) {
      console.error('AI request failed:', err?.status, err?.message);
      res.status(502).json({ error: 'The assistant is unavailable right now. Please try again.' });
    }
  });

  // User reports of bad AI answers (Google Play AI-generated content policy).
  app.post('/api/report', rateLimiter({ max: 10 }), (req, res) => {
    const message = typeof req.body?.message === 'string' ? req.body.message.slice(0, 2000) : '';
    const reason = typeof req.body?.reason === 'string' ? req.body.reason.slice(0, 200) : '';
    if (!message) return res.status(400).json({ error: 'Nothing to report.' });
    // TODO: store in a database / send to your moderation inbox.
    console.warn('[REPORT]', JSON.stringify({ at: new Date().toISOString(), reason, message }));
    res.json({ ok: true });
  });

  return app;
}

/** Load the document index (if built) and start the server. */
export async function start() {
  const index = await loadIndex(INDEX_FILE);
  if (!index) console.warn('No document index yet: answers will not cite sources. Run "npm run ingest" to build it.');
  const embedder = index?.embeddingModel ? createEmbedder({ model: index.embeddingModel }) : null;
  const retriever = new Retriever(index?.chunks || [], { embedder });
  const app = createApp({ retriever, index });

  const port = Number(process.env.PORT) || 8080;
  app.listen(port, () => {
    console.log(`Ebola Guard backend on http://localhost:${port} (model: ${MODEL})`);
    console.log(`  documents: ${index?.sources?.filter((s) => s.status === 'ok').length ?? 0}, passages: ${retriever.chunks.length}, search: ${retriever.chunks.length ? retriever.mode : 'off'}`);
    console.log(`  AI: ${process.env.ANTHROPIC_API_KEY ? 'on' : 'off (no ANTHROPIC_API_KEY: answers show official passages only)'}`);
  });
}

// Start the server when run directly (node server.js).
if (import.meta.url === pathToFileURL(process.argv[1]).href) start();
