// Cuts sections into passages ("chunks") small enough to search precisely,
// but big enough to make sense alone. Each chunk keeps its section heading.
import { countWords, splitSentences } from './text.js';

export function chunkSections(sections, { maxWords = 220, overlapWords = 40 } = {}) {
  const chunks = [];
  for (const { heading, paragraphs } of sections) {
    // Long paragraphs are split into sentences first.
    const units = paragraphs.flatMap((p) => (countWords(p) > maxWords ? splitSentences(p) : [p]));

    let buffer = []; // units in the chunk being built
    let fresh = 0; // how many of them are new (not overlap from the previous chunk)
    const words = () => buffer.reduce((n, u) => n + countWords(u), 0);

    const flush = () => {
      chunks.push({ section: heading, text: buffer.join('\n') });
      // Carry the last ~overlapWords words into the next chunk, so an idea cut
      // in two is still found whole in one of them.
      const keep = [];
      let kept = 0;
      for (let i = buffer.length - 1; i > 0 && kept < overlapWords; i--) {
        keep.unshift(buffer[i]);
        kept += countWords(buffer[i]);
      }
      buffer = kept <= overlapWords * 2 ? keep : [];
      fresh = 0;
    };

    for (const unit of units) {
      const n = countWords(unit);
      if (words() + n > maxWords) {
        if (fresh > 0) flush();
        else buffer = []; // only overlap left: drop it rather than repeat it alone
      }
      buffer.push(unit);
      fresh++;
    }
    if (fresh > 0) chunks.push({ section: heading, text: buffer.join('\n') });
  }
  return dedupeChunks(chunks);
}

function dedupeChunks(chunks) {
  const seen = new Set();
  return chunks.filter((c) => {
    const key = `${c.section}\n${c.text}`;
    if (seen.has(key)) return false;
    seen.add(key);
    return true;
  });
}
