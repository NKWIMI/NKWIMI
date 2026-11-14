// The RAG answer step: question -> search official passages -> Claude answers
// from them with citations -> reply + numbered sources for the app.
import { clean } from './text.js';

const MAX_MESSAGES = 20;
const MAX_CHARS = 2000;

/**
 * Clean the chat history coming from the app (same rules as the original
 * Ebola Guard backend): valid roles, trimmed, merged, ending with the user.
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
    if (last && last.role === m.role) last.content += '\n\n' + content;
    else cleaned.push({ role: m.role, content });
  }
  while (cleaned.length && cleaned[0].role !== 'user') cleaned.shift();
  if (!cleaned.length || cleaned[cleaned.length - 1].role !== 'user') return null;
  return cleaned;
}

/**
 * What to search for: the latest question. A very short follow-up
 * ("and children?") is searched together with the previous question.
 */
export function buildQuery(messages) {
  const users = messages.filter((m) => m.role === 'user').map((m) => m.content);
  const last = users[users.length - 1] || '';
  if (last.split(/\s+/).length < 5 && users.length > 1) return `${users[users.length - 2]} ${last}`;
  return last;
}

/** One Claude "search_result" block per retrieved passage, citations enabled. */
export function toSearchResultBlocks(hits) {
  return hits.map(({ chunk }) => ({
    type: 'search_result',
    source: chunk.url,
    title: [chunk.org, chunk.title, chunk.section].filter(Boolean).join(' · '),
    content: [{ type: 'text', text: chunk.text }],
    citations: { enabled: true },
  }));
}

/** Public description of a passage, as shown under an answer. */
export function describeSource(chunk, n) {
  return {
    n,
    sourceId: chunk.sourceId,
    org: chunk.org,
    title: chunk.title,
    section: chunk.section || null,
    url: chunk.url,
    language: chunk.language,
  };
}

/**
 * Ask Claude. The retrieved passages go into the latest user turn as
 * search_result blocks; Claude's reply comes back as text blocks, some with
 * citations pointing at those passages (search_result_index).
 */
export async function generateAnswer({ ai, model, system, messages, hits, maxTokens = 800 }) {
  const history = messages.slice(0, -1);
  const question = messages[messages.length - 1].content;
  const response = await ai.messages.create({
    model,
    max_tokens: maxTokens,
    system,
    messages: [
      ...history,
      { role: 'user', content: [...toSearchResultBlocks(hits), { type: 'text', text: question }] },
    ],
  });
  return formatCitedReply(response, hits);
}

/**
 * Turn Claude's text blocks + citations into one reply with [1] [2] markers,
 * and a deduplicated list of the sources actually cited.
 */
export function formatCitedReply(response, hits) {
  const numberByUrl = new Map();
  const sources = [];
  const numberFor = (hitIndex) => {
    const chunk = hits[hitIndex]?.chunk;
    if (!chunk) return null;
    if (!numberByUrl.has(chunk.url)) {
      numberByUrl.set(chunk.url, sources.length + 1);
      sources.push(describeSource(chunk, sources.length + 1));
    }
    return numberByUrl.get(chunk.url);
  };

  let reply = '';
  for (const block of response?.content || []) {
    if (block.type !== 'text') continue;
    reply += block.text;
    const cited = (block.citations || [])
      .filter((c) => c.type === 'search_result_location')
      .map((c) => numberFor(c.search_result_index))
      .filter((n) => n !== null);
    const unique = [...new Set(cited)];
    if (unique.length) reply += unique.map((n) => ` [${n}]`).join('');
  }
  return { reply: reply.replace(/[ \t]+\n/g, '\n').trim(), sources };
}

const RETRIEVAL_ONLY_TEXT = {
  en: {
    intro: 'The AI assistant is not switched on yet, so here are the most relevant passages from the official documents:',
    none: 'The AI assistant is not switched on yet, and no official passage matches this question. Try other words, or ask a health worker.',
  },
  fr: {
    intro: "L'assistant IA n'est pas encore activé. Voici les passages les plus pertinents des documents officiels :",
    none: "L'assistant IA n'est pas encore activé et aucun passage officiel ne correspond à cette question. Essayez d'autres mots ou demandez à un agent de santé.",
  },
};

/** Without an API key: show the best passages themselves, with their sources. */
export function retrievalOnlyAnswer(hits, { confident, language } = {}) {
  const t = language === 'French' ? RETRIEVAL_ONLY_TEXT.fr : RETRIEVAL_ONLY_TEXT.en;
  if (!confident || !hits.length) return { reply: t.none, sources: [] };
  const top = hits.slice(0, 3);
  const sources = [];
  const numberByUrl = new Map();
  const lines = top.map(({ chunk }) => {
    if (!numberByUrl.has(chunk.url)) {
      numberByUrl.set(chunk.url, sources.length + 1);
      sources.push(describeSource(chunk, sources.length + 1));
    }
    const excerpt = clean(chunk.text);
    const short = excerpt.length > 420 ? `${excerpt.slice(0, 417).replace(/\s+\S*$/, '')}…` : excerpt;
    return `• ${short} [${numberByUrl.get(chunk.url)}]`;
  });
  return { reply: `${t.intro}\n\n${lines.join('\n\n')}`, sources };
}
