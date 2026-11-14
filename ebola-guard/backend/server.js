import express from 'express';
import Anthropic from '@anthropic-ai/sdk';
import { pathToFileURL, fileURLToPath } from 'node:url';
import { readFileSync } from 'node:fs';
import path from 'node:path';

import { buildSystemPrompt } from './prompt.js';

const MODEL = process.env.ANTHROPIC_MODEL || 'claude-haiku-5-5';
const MAX_MESSAGES = 20;
const MAX_CHARS = 2000;
const MAX_CONTEXT_CHARS = 2000;

/**
 * Clean the chat history coming from the app: valid roles only, trimmed,
 * length-limited, starting with a user turn, no repeated roles, ending with
 * the user's latest question. Returns null if nothing usable is left.
 */
export function sanitizeMessages(input) {
  if (!Array.isArray(input)) return null;
  const cleaned = [];
  for (const m of input.slice(-MAX_MESSAGES)) {
    if (!m || (m.role !== 'user' && m.role !== 'assistant')) continue;
    if (typeof m.content !== 'string') continue;
    const content = m.content.trim().slice(0, MAX_CHARS);
    if (!content) continue;
    const last = cleaned[cleaned.length - 1];
    if (last && last.role === m.role) {
      last.content += '\n\n' + content; // merge consecutive same-role turns
    } else {
      cleaned.push({ role: m.role, content });
    }
  }
  while (cleaned.length && cleaned[0].role !== 'user') cleaned.shift();
  if (!cleaned.length || cleaned[cleaned.length - 1].role !== 'user') return null;
  return cleaned;
}

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

export function createApp({ client } = {}) {
  const ai =
    client !== undefined
      ? client
      : process.env.ANTHROPIC_API_KEY
        ? new Anthropic({ apiKey: process.env.ANTHROPIC_API_KEY })
        : null;

  const app = express();
  app.set('trust proxy', 1);
  app.use(express.json({ limit: '64kb' }));

  app.get('/health', (_req, res) => res.json({ ok: true, ai: Boolean(ai) }));

  // Outbreak map data. Edit data/outbreak-map.json when WHO / the Ministry
  // of Health publish new areas or treatment centres: apps update on next open.
  app.get('/api/outbreak-map', (_req, res) => {
    try {
      const file = path.join(path.dirname(fileURLToPath(import.meta.url)), 'data', 'outbreak-map.json');
      const data = JSON.parse(readFileSync(file, 'utf8'));
      res.set('Cache-Control', 'public, max-age=900');
      res.json(data);
    } catch (err) {
      console.error('Map data error:', err.message);
      res.status(500).json({ error: 'Map data unavailable' });
    }
  });

  app.post('/api/chat', rateLimiter(), async (req, res) => {
    const messages = sanitizeMessages(req.body?.messages);
    if (!messages) {
      return res.status(400).json({ error: 'Please type a question.' });
    }
    if (!ai) {
      return res.status(503).json({ error: 'The assistant is not configured yet.' });
    }

    const ctx = req.body?.screeningContext;
    const screeningContext =
      typeof ctx === 'string' && ctx.trim() ? ctx.trim().slice(0, MAX_CONTEXT_CHARS) : null;

    const voice = req.body?.mode === 'voice';
    const language = typeof req.body?.language === 'string' ? req.body.language.slice(0, 40) : null;

    try {
      const response = await ai.messages.create({
        model: MODEL,
        max_tokens: voice ? 400 : 800,
        system: buildSystemPrompt(screeningContext, { voice, language }),
        messages,
      });
      const reply = (response.content || [])
        .filter((b) => b.type === 'text')
        .map((b) => b.text)
        .join('\n')
        .trim();
      if (!reply) {
        return res.status(502).json({ error: 'The assistant could not answer. Please rephrase.' });
      }
      // Do not log message content: it is sensitive health information.
      res.json({ reply });
    } catch (err) {
      console.error('AI request failed:', err?.status, err?.message);
      res.status(502).json({ error: 'The assistant is unavailable right now. Please try again.' });
    }
  });

  // User reports of bad AI answers (Google Play AI-generated content policy).
  app.post('/api/report', rateLimiter({ max: 10 }), (req, res) => {
    const message = typeof req.body?.message === 'string' ? req.body.message.slice(0, MAX_CHARS) : '';
    const reason = typeof req.body?.reason === 'string' ? req.body.reason.slice(0, 200) : '';
    if (!message) return res.status(400).json({ error: 'Nothing to report.' });
    // TODO: store in a database / send to your moderation inbox.
    console.warn('[REPORT]', JSON.stringify({ at: new Date().toISOString(), reason, message }));
    res.json({ ok: true });
  });

  return app;
}

// Start the server when run directly (node server.js).
if (import.meta.url === pathToFileURL(process.argv[1]).href) {
  const port = Number(process.env.PORT) || 8080;
  createApp().listen(port, () => {
    console.log(`Ebola Guard backend on http://localhost:${port} (model: ${MODEL})`);
  });
}
