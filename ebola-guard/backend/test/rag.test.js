import { test, describe, before } from 'node:test';
import assert from 'node:assert/strict';
import path from 'node:path';
import { readFile } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';

import { createApp } from '../server.js';
import { BM25 } from '../src/bm25.js';
import { chunkSections } from '../src/chunker.js';
import { extractFromHtml, extractFromText } from '../src/extract.js';
import { buildIndex } from '../src/indexer.js';
import { buildSystemPrompt } from '../prompt.js';
import { buildQuery, formatCitedReply, retrievalOnlyAnswer, sanitizeMessages, toSearchResultBlocks } from '../src/rag.js';
import { Retriever } from '../src/retriever.js';
import { detectRedFlags } from '../src/safety.js';
import { countWords } from '../src/text.js';
import { runEval } from '../scripts/eval.js';
import { fakeClaude, fakeEmbedder } from './helpers.js';

const FIX = path.join(path.dirname(fileURLToPath(import.meta.url)), 'fixtures');
const readJson = async (f) => JSON.parse(await readFile(path.join(FIX, f), 'utf8'));

let keywordIndex; // built without embeddings
let hybridIndex; // built with the fake embedder

before(async () => {
  const sources = await readJson('sources.json');
  keywordIndex = (await buildIndex({ sources, baseDir: FIX })).index;
  hybridIndex = (await buildIndex({ sources, baseDir: FIX, embedder: fakeEmbedder() })).index;
});

// ---------- Ingestion ----------
describe('extract', () => {
  test('keeps the main content and drops navigation, scripts and footers', async () => {
    const { title, sections } = extractFromHtml(await readFile(path.join(FIX, 'symptoms.html'), 'utf8'));
    const all = JSON.stringify(sections);
    assert.equal(title, 'Signs and symptoms (test document)');
    assert.ok(sections.some((s) => s.heading === 'Early symptoms'));
    assert.match(all, /• Fever and chills/);
    assert.doesNotMatch(all, /tracking|navigation menu|privacy policy/);
  });

  test('plain text: "#" lines are headings, blank lines separate paragraphs', () => {
    const { title, sections } = extractFromText('# Title here\n\nFirst paragraph of enough length here.\n\n# Part two\n\nSecond paragraph text.');
    assert.equal(title, 'Title here');
    assert.deepEqual(sections.map((s) => s.heading), ['Title here', 'Part two']);
  });
});

describe('chunker', () => {
  test('respects the size limit, keeps headings, overlaps neighbours', () => {
    const paragraphs = Array.from({ length: 12 }, (_, i) => `Paragraph ${i} ` + 'word '.repeat(40));
    const chunks = chunkSections([{ heading: 'H', paragraphs }], { maxWords: 100, overlapWords: 30 });
    assert.ok(chunks.length > 3);
    for (const c of chunks) {
      assert.equal(c.section, 'H');
      assert.ok(countWords(c.text) <= 100 + 45, `chunk too long: ${countWords(c.text)}`);
    }
    // the last paragraph of a chunk starts the next one
    const lastOfFirst = chunks[0].text.split('\n').at(-1);
    assert.ok(chunks[1].text.startsWith(lastOfFirst));
  });

  test('splits a single huge paragraph into sentences', () => {
    const para = Array.from({ length: 30 }, (_, i) => `Sentence number ${i} has some words in it.`).join(' ');
    const chunks = chunkSections([{ heading: '', paragraphs: [para] }], { maxWords: 50, overlapWords: 0 });
    assert.ok(chunks.length >= 4);
  });
});

describe('index', () => {
  test('ingests every readable source and reports the broken one', () => {
    const status = Object.fromEntries(keywordIndex.sources.map((s) => [s.id, s.status]));
    assert.deepEqual(status, { 'test-symptoms': 'ok', 'test-spread': 'ok', 'test-vaccin-fr': 'ok', 'test-missing': 'failed' });
    for (const c of keywordIndex.chunks) {
      assert.ok(c.id && c.sourceId && c.url && c.org && c.text);
      assert.equal(c.embedding, undefined);
    }
  });

  test('stores one embedding per passage when an embedder is given', () => {
    assert.equal(hybridIndex.embeddingModel, 'fake-embedder');
    assert.ok(hybridIndex.chunks.every((c) => Array.isArray(c.embedding) && c.embedding.length === 64));
  });

  test('a failing embedder falls back to keyword search instead of crashing', async () => {
    const sources = await readJson('sources.json');
    const broken = { model: 'x', embed: async () => { throw new Error('offline'); } };
    const { index } = await buildIndex({ sources, baseDir: FIX, embedder: broken });
    assert.equal(index.embeddingModel, null);
    assert.ok(index.chunks.length > 0);
  });
});

// ---------- Retrieval ----------
describe('search', () => {
  test('BM25 ranks the passage with the rare query words first', () => {
    const bm = new BM25(['the cat sat', 'mosquitoes do not spread the virus', 'cats and dogs']);
    assert.equal(bm.search('do mosquitoes spread it')[0].index, 1);
  });

  test('keyword search finds the right document', async () => {
    const r = new Retriever(keywordIndex.chunks);
    assert.equal(r.mode, 'keyword');
    const { hits, confident } = await r.search('Can mosquitoes spread it?');
    assert.equal(hits[0].chunk.sourceId, 'test-spread');
    assert.ok(confident);
  });

  test('hybrid search finds an English passage for a French question', async () => {
    const r = new Retriever(hybridIndex.chunks, { embedder: fakeEmbedder(), minDenseScore: 0.3 });
    assert.equal(r.mode, 'hybrid');
    const { hits } = await r.search('Quels sont les signes de fièvre ?');
    assert.ok(hits.slice(0, 3).some((h) => h.chunk.sourceId === 'test-symptoms'));
    assert.ok(hits[0].dense !== null);
  });

  test('an off-topic question is not "confident"', async () => {
    const r = new Retriever(keywordIndex.chunks);
    assert.equal((await r.search('Who won the football world cup?')).confident, false);
  });

  test('if the embedding model fails at query time, search continues with keywords', async () => {
    const broken = { embed: async () => { throw new Error('offline'); } };
    const r = new Retriever(hybridIndex.chunks, { embedder: broken });
    const { hits } = await r.search('mosquitoes');
    assert.equal(r.mode, 'keyword');
    assert.equal(hits[0].chunk.sourceId, 'test-spread');
  });
});

// ---------- Safety ----------
describe('red flags', () => {
  const cases = [
    ['I cared for my sick uncle who had Ebola and now I have a fever', 'urgent'],
    ['I went to a funeral last week and I have diarrhoea', 'urgent'],
    ["J'ai touché le corps d'un malade et j'ai de la fièvre", 'urgent'],
    ['I am bleeding from my gums', 'emergency'],
    ['Je saigne du nez', 'emergency'],
    ['Nina homa na nilikuwa kwenye mazishi', 'urgent'],
    ['What are the symptoms of Ebola? Is bleeding one of them?', null],
    ['How does Ebola spread at funerals?', null],
    ['I want to learn about the vaccine', null],
  ];
  for (const [text, level] of cases) {
    test(`${level ?? 'none'}: ${text}`, () => assert.equal(detectRedFlags(text)?.level ?? null, level));
  }
});

// ---------- Answer building ----------
describe('rag helpers', () => {
  test('sanitizeMessages keeps the original backend rules', () => {
    assert.deepEqual(
      sanitizeMessages([{ role: 'assistant', content: 'hi' }, { role: 'system', content: 'x' }, { role: 'user', content: ' q ' }]),
      [{ role: 'user', content: 'q' }],
    );
    assert.equal(sanitizeMessages([{ role: 'user', content: 'a' }, { role: 'assistant', content: 'b' }]), null);
  });

  test('a short follow-up is searched with the previous question', () => {
    const q = buildQuery([
      { role: 'user', content: 'How long is the incubation period?' },
      { role: 'assistant', content: '2 to 21 days.' },
      { role: 'user', content: 'and for children?' },
    ]);
    assert.match(q, /incubation.*children/);
  });

  test('passages become Claude search_result blocks with citations enabled', () => {
    const [block] = toSearchResultBlocks([{ chunk: keywordIndex.chunks[0] }]);
    assert.equal(block.type, 'search_result');
    assert.equal(block.source, keywordIndex.chunks[0].url);
    assert.deepEqual(block.citations, { enabled: true });
    assert.equal(block.content[0].type, 'text');
    assert.match(block.title, /TEST/);
  });

  test('citations become [n] markers and a deduplicated source list', () => {
    const hits = [{ chunk: { url: 'u1', org: 'A', title: 'T1', sourceId: 's1' } }, { chunk: { url: 'u1', org: 'A', title: 'T1', sourceId: 's1' } }, { chunk: { url: 'u2', org: 'B', title: 'T2', sourceId: 's2' } }];
    const cite = (i) => ({ type: 'search_result_location', search_result_index: i });
    const { reply, sources } = formatCitedReply({
      content: [
        { type: 'text', text: 'Fact one.', citations: [cite(0), cite(1)] },
        { type: 'text', text: ' Fact two.', citations: [cite(2)] },
        { type: 'text', text: ' No source.' },
      ],
    }, hits);
    assert.equal(reply, 'Fact one. [1] Fact two. [2] No source.');
    assert.deepEqual(sources.map((s) => [s.n, s.url]), [[1, 'u1'], [2, 'u2']]);
  });

  test('retrieval-only answer shows passages with numbered sources', () => {
    const hits = keywordIndex.chunks.slice(0, 3).map((chunk) => ({ chunk }));
    const { reply, sources } = retrievalOnlyAnswer(hits, { confident: true });
    assert.match(reply, /not switched on/);
    assert.match(reply, /\[1\]/);
    assert.ok(sources.length >= 1);
    assert.match(retrievalOnlyAnswer([], { confident: false, language: 'French' }).reply, /aucun passage/);
  });

  test('the system prompt keeps the safety rules and adds the retrieval rules', () => {
    const p = buildSystemPrompt('level: urgent', { retrieval: true, confident: false, language: 'Lingala' });
    assert.match(p, /cannot diagnose Ebola/);
    assert.match(p, /Do not add facts/);
    assert.match(p, /no passage that clearly matches/);
    assert.match(p, /reply in simple French/);
    assert.match(p, /level: urgent/);
  });
});

// ---------- API ----------
async function call(app, method, url, body) {
  const server = await new Promise((resolve) => { const s = app.listen(0, () => resolve(s)); });
  try {
    const res = await fetch(`http://127.0.0.1:${server.address().port}${url}`, {
      method, headers: { 'Content-Type': 'application/json' }, body: body ? JSON.stringify(body) : undefined,
    });
    const type = res.headers.get('content-type') || '';
    return { status: res.status, body: type.includes('json') ? await res.json() : await res.text() };
  } finally {
    server.close();
  }
}

describe('API', () => {
  const ask = (content, extra = {}) => ({ messages: [{ role: 'user', content }], ...extra });

  test('/health reports retrieval-only mode and the index size', async () => {
    const app = createApp({ retriever: new Retriever(keywordIndex.chunks), index: keywordIndex });
    const { body } = await call(app, 'GET', '/health');
    assert.equal(body.mode, 'retrieval-only');
    assert.equal(body.search, 'keyword');
    assert.equal(body.documents, 3);
    assert.equal(body.passages, keywordIndex.chunks.length);
  });

  test('without an API key, /api/chat returns official passages and sources', async () => {
    const app = createApp({ retriever: new Retriever(keywordIndex.chunks), index: keywordIndex });
    const { status, body } = await call(app, 'POST', '/api/chat', ask('Can mosquitoes spread it?'));
    assert.equal(status, 200);
    assert.equal(body.mode, 'retrieval-only');
    assert.match(body.reply, /mosquitoes/);
    assert.equal(body.sources[0].sourceId, 'test-spread');
    assert.equal(body.alert, null);
  });

  test('with Claude: passages go in as search results, citations come back as sources', async () => {
    const claude = fakeClaude();
    const app = createApp({ client: claude, retriever: new Retriever(keywordIndex.chunks), index: keywordIndex, model: 'test-model' });
    const { status, body } = await call(app, 'POST', '/api/chat', ask('How many days after contact do symptoms appear?', { language: 'French', screeningContext: 'level: monitor' }));
    assert.equal(status, 200);
    assert.equal(body.mode, 'ai');
    assert.match(body.reply, /after contact\. \[1\] Call the hotline/);
    assert.equal(body.sources[0].sourceId, 'test-symptoms');

    const req = claude.calls[0];
    assert.equal(req.model, 'test-model');
    assert.match(req.system, /cannot diagnose/);
    assert.match(req.system, /level: monitor/);
    assert.match(req.system, /Reply in French/);
    const last = req.messages.at(-1);
    assert.equal(last.role, 'user');
    assert.ok(last.content.slice(0, -1).every((b) => b.type === 'search_result' && b.citations.enabled));
    assert.equal(last.content.at(-1).text, 'How many days after contact do symptoms appear?');
  });

  test('a user describing exposure + fever gets an urgent alert', async () => {
    const app = createApp({ retriever: new Retriever(keywordIndex.chunks), index: keywordIndex });
    const { body } = await call(app, 'POST', '/api/chat', ask('I washed my dead aunt\'s body and now I have a fever'));
    assert.equal(body.alert.level, 'urgent');
  });

  test('errors: empty input 400, no index 503, AI failure 502, too many requests 429', async () => {
    const retriever = new Retriever(keywordIndex.chunks);
    assert.equal((await call(createApp({ retriever }), 'POST', '/api/chat', { messages: [] })).status, 400);
    assert.equal((await call(createApp({}), 'POST', '/api/chat', ask('hi'))).status, 503);
    assert.equal((await call(createApp({ client: fakeClaude({ fail: true }), retriever }), 'POST', '/api/chat', ask('fever'))).status, 502);

    const app = createApp({ retriever, rateLimit: { max: 2 } });
    const server = await new Promise((resolve) => { const s = app.listen(0, () => resolve(s)); });
    const url = `http://127.0.0.1:${server.address().port}/api/chat`;
    const post = () => fetch(url, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(ask('fever')) });
    const codes = [];
    for (let i = 0; i < 3; i++) codes.push((await post()).status);
    server.close();
    assert.deepEqual(codes, [200, 200, 429]);
  });

  test('/api/search and /api/sources expose the library', async () => {
    const app = createApp({ retriever: new Retriever(keywordIndex.chunks), index: keywordIndex });
    const search = await call(app, 'GET', '/api/search?q=vaccin%20Ervebo');
    assert.equal(search.body.hits[0].id.split('#')[0], 'test-vaccin-fr');
    const sources = await call(app, 'GET', '/api/sources');
    assert.equal(sources.body.sources.length, 4);
    assert.equal(sources.body.sources.find((s) => s.id === 'test-missing').status, 'failed');
  });

  test('the web demo page is served', async () => {
    const app = createApp({ retriever: new Retriever(keywordIndex.chunks), index: keywordIndex });
    const { status, body } = await call(app, 'GET', '/');
    assert.equal(status, 200);
    assert.match(body, /Ebola Guard/);
  });
});

// ---------- Evaluation ----------
describe('evaluation', () => {
  test('the eval script measures search quality and safety on the fixture set', async () => {
    const questions = await readJson('questions.json');
    const retriever = new Retriever(hybridIndex.chunks, { embedder: fakeEmbedder(), minDenseScore: 0.5 });
    const { rows, summary } = await runEval({ retriever, questions });
    assert.equal(rows.length, questions.length);
    assert.equal(summary.hitAt5, '100% (6/6)');
    assert.equal(summary.alertsCaught, '100% (2/2)');
    assert.equal(summary.falseAlerts, '0% (0/7)');
    assert.ok(summary.hitByLanguage.fr);
  });
});

test('retrieval-only answer never shows a doubled bullet', () => {
  const hits = [{ chunk: { url: 'https://example.org/a', title: 'A', source: 'WHO', text: '• Fever and chills\n• Headache' } }];
  const { reply } = retrievalOnlyAnswer(hits, { confident: true, language: 'English' });
  assert.doesNotMatch(reply, /•\s*•/);
  assert.match(reply, /• Fever and chills/);
});
