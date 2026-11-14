// BM25 keyword search: the classic ranking used by search engines.
// It rewards passages that contain the question's rare words, many times,
// and does not over-reward very long passages.
import { tokenize } from './text.js';

export class BM25 {
  constructor(texts, { k1 = 1.5, b = 0.75 } = {}) {
    this.k1 = k1;
    this.b = b;
    this.docs = texts.map((t) => {
      const tf = new Map();
      const tokens = tokenize(t);
      for (const w of tokens) tf.set(w, (tf.get(w) || 0) + 1);
      return { tf, length: tokens.length };
    });
    this.avgLength = this.docs.reduce((n, d) => n + d.length, 0) / Math.max(this.docs.length, 1);
    this.df = new Map();
    for (const d of this.docs) for (const w of d.tf.keys()) this.df.set(w, (this.df.get(w) || 0) + 1);
  }

  idf(word) {
    const n = this.docs.length;
    const df = this.df.get(word) || 0;
    return Math.log(1 + (n - df + 0.5) / (df + 0.5));
  }

  /** Returns [{ index, score }] sorted best first, only passages sharing at least one word. */
  search(query, limit = 20) {
    const words = [...new Set(tokenize(query))];
    const results = [];
    this.docs.forEach((d, index) => {
      let score = 0;
      for (const w of words) {
        const f = d.tf.get(w);
        if (!f) continue;
        const norm = f + this.k1 * (1 - this.b + (this.b * d.length) / (this.avgLength || 1));
        score += this.idf(w) * ((f * (this.k1 + 1)) / norm);
      }
      if (score > 0) results.push({ index, score });
    });
    return results.sort((a, b) => b.score - a.score).slice(0, limit);
  }
}
