// Hybrid retrieval: keyword search (BM25) + meaning search (embeddings),
// merged with Reciprocal Rank Fusion. Keywords catch exact names ("Ervebo"),
// embeddings catch paraphrases and other languages.
import { BM25 } from './bm25.js';
import { cosine } from './embedder.js';

const RRF_K = 60;

export class Retriever {
  /**
   * chunks: [{ id, sourceId, title, org, url, language, section, text, embedding? }]
   * embedder: optional, { embed(texts, kind) } - without it, keyword search only.
   */
  constructor(chunks, { embedder = null, minDenseScore = Number(process.env.MIN_DENSE_SCORE) || 0.8 } = {}) {
    this.chunks = chunks;
    this.bm25 = new BM25(chunks.map((c) => `${c.title} ${c.section} ${c.text}`));
    this.hasVectors = chunks.length > 0 && chunks.every((c) => Array.isArray(c.embedding));
    this.embedder = this.hasVectors ? embedder : null;
    this.minDenseScore = minDenseScore;
  }

  get mode() {
    return this.embedder ? 'hybrid' : 'keyword';
  }

  async search(query, { k = 5, pool = 30 } = {}) {
    if (!this.chunks.length || !String(query).trim()) return { hits: [], confident: false };

    const keyword = this.bm25.search(query, pool);
    let dense = [];
    if (this.embedder) {
      let q;
      try {
        [q] = await this.embedder.embed([query], 'query');
      } catch (err) {
        // Model unavailable (e.g. offline first run): keep working with keywords.
        console.error('Embedding model unavailable, using keyword search only:', err.message);
        this.embedder = null;
        return this.search(query, { k, pool });
      }
      dense = this.chunks
        .map((c, index) => ({ index, score: cosine(q, c.embedding) }))
        .sort((a, b) => b.score - a.score)
        .slice(0, pool);
    }

    const fused = new Map();
    const add = (list, field) =>
      list.forEach((r, rank) => {
        const entry = fused.get(r.index) || { index: r.index, rrf: 0, bm25: null, dense: null };
        entry.rrf += 1 / (RRF_K + rank + 1);
        entry[field] = Number(r.score.toFixed(4));
        fused.set(r.index, entry);
      });
    add(keyword, 'bm25');
    add(dense, 'dense');

    const hits = [...fused.values()]
      .sort((a, b) => b.rrf - a.rrf)
      .slice(0, k)
      .map((h) => ({ chunk: this.chunks[h.index], score: Number(h.rrf.toFixed(5)), bm25: h.bm25, dense: h.dense }));

    // "Confident" = at least one passage really matches. Without it, the
    // assistant says it could not find the answer in the official documents.
    const topDense = dense[0]?.score ?? 0;
    const topKeyword = keyword[0]?.score ?? 0;
    const confident = this.embedder ? topDense >= this.minDenseScore || topKeyword >= 4 : topKeyword >= 2;
    return { hits, confident, topDense: Number(topDense.toFixed(4)), topKeyword: Number(topKeyword.toFixed(3)) };
  }
}
