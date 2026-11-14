// Text helpers shared by the keyword search and the chunker.

// Very common words that carry no meaning for search (English + French).
const STOPWORDS = new Set(`
a an and are as at be by can do does for from has have how i if in is it its me my of on or our so that the
their them there these they this to was we what when where which who why will with you your
au aux avec ce ces dans de des du elle en est et il ils je la le les leur mais me mon ne nous on ou par pas
pour qu que qui sa se ses son sur ta te tu un une vos votre vous y est-ce
`.split(/\s+/).filter(Boolean));

/** Lowercase and remove accents, so "fièvre" and "fievre" match. */
export function normalize(text) {
  return String(text ?? '')
    .normalize('NFD')
    .replace(/[̀-ͯ]/g, '')
    .toLowerCase();
}

/** Split text into search words: letters/digits only, no stopwords, no 1-letter words. */
export function tokenize(text) {
  return normalize(text)
    .split(/[^a-z0-9]+/)
    .filter((w) => w.length > 1 && !STOPWORDS.has(w));
}

/** Collapse runs of whitespace into single spaces. */
export function clean(text) {
  return String(text ?? '').replace(/\s+/g, ' ').trim();
}

export function countWords(text) {
  return clean(text).split(' ').filter(Boolean).length;
}

/** Split a paragraph into sentences (good enough for EN/FR prose). */
export function splitSentences(text) {
  return clean(text).split(/(?<=[.!?])\s+(?=[A-ZÀ-Ý0-9"«(])/u).filter(Boolean);
}
