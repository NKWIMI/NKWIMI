// Embeddings: each text becomes a list of 384 numbers that represents its meaning.
// Texts with similar meaning get similar numbers, even across languages
// (a French question can find an English passage).
//
// The model runs on your own computer through transformers.js: no API key, no cost.
// The first run downloads it once (about 120 MB) from Hugging Face.

export const DEFAULT_MODEL = process.env.EMBEDDING_MODEL || 'Xenova/multilingual-e5-small';

export function createEmbedder({ model = DEFAULT_MODEL, batchSize = 16 } = {}) {
  let extractorPromise = null;
  const load = async () => {
    if (!extractorPromise) {
      extractorPromise = import('@huggingface/transformers').then(({ pipeline }) =>
        pipeline('feature-extraction', model, { dtype: 'q8' }),
      );
    }
    return extractorPromise;
  };

  return {
    model,
    /**
     * kind = 'query' for questions, 'passage' for documents.
     * The e5 model was trained with these prefixes and works best with them.
     */
    async embed(texts, kind = 'passage') {
      const extractor = await load();
      const out = [];
      for (let i = 0; i < texts.length; i += batchSize) {
        const batch = texts.slice(i, i + batchSize).map((t) => `${kind}: ${t}`);
        const tensor = await extractor(batch, { pooling: 'mean', normalize: true });
        out.push(...tensor.tolist());
      }
      return out;
    },
  };
}

/** Cosine similarity of two normalized vectors = their dot product. */
export function cosine(a, b) {
  let s = 0;
  for (let i = 0; i < a.length; i++) s += a[i] * b[i];
  return s;
}
