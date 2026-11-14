// Test helpers: a tiny fake embedder and a fake Claude client, so the tests
// run anywhere, offline, without downloading a model or paying for the API.
import { normalize } from '../src/text.js';

// Words that mean the same thing in English and French share one "concept",
// so the fake embedder behaves like a (very small) multilingual model.
const CONCEPTS = {
  fever: ['fever', 'fievre', 'chills', 'temperature'],
  symptom: ['symptom', 'symptoms', 'symptome', 'symptomes', 'signs', 'signes'],
  vaccine: ['vaccine', 'vaccin', 'ervebo', 'injection'],
  spread: ['spread', 'spreads', 'contact', 'fluids', 'transmission'],
  burial: ['burial', 'burials', 'body', 'died', 'corps', 'enterrement'],
  insect: ['mosquito', 'mosquitoes', 'insects', 'moustique'],
  football: ['football', 'world', 'cup'],
};

export function fakeEmbedder(dims = 64) {
  const lookup = new Map();
  Object.keys(CONCEPTS).forEach((c, i) => CONCEPTS[c].forEach((w) => lookup.set(w, i)));
  const hash = (w) => [...w].reduce((h, ch) => (h * 31 + ch.charCodeAt(0)) >>> 0, 7) % dims;
  return {
    model: 'fake-embedder',
    async embed(texts) {
      return texts.map((t) => {
        const v = new Array(dims).fill(0);
        for (const w of normalize(t).split(/[^a-z0-9]+/).filter((x) => x.length > 2)) {
          const slot = lookup.has(w) ? lookup.get(w) : 10 + hash(w) % (dims - 10);
          v[slot] += lookup.has(w) ? 3 : 1;
        }
        const n = Math.hypot(...v) || 1;
        return v.map((x) => x / n);
      });
    },
  };
}

/** A fake Anthropic client that records the request and cites search result 0. */
export function fakeClaude({ text = 'Symptoms start 2 to 21 days after contact.', fail = false } = {}) {
  const calls = [];
  return {
    calls,
    messages: {
      async create(args) {
        calls.push(args);
        if (fail) throw Object.assign(new Error('boom'), { status: 500 });
        return {
          content: [
            { type: 'text', text: text, citations: [{ type: 'search_result_location', search_result_index: 0, source: 'x', title: 'x', cited_text: 'x', start_block_index: 0, end_block_index: 0 }] },
            { type: 'text', text: ' Call the hotline if you feel sick.' },
          ],
        };
      },
    },
  };
}
