// npm run eval                 -> measure search quality + safety alerts on eval/questions.json
// npm run eval -- --ai         -> also ask Claude (needs ANTHROPIC_API_KEY) and check citations
// npm run eval -- --index data/index.json --questions eval/questions.json
import path from 'node:path';
import { readFile, writeFile } from 'node:fs/promises';
import { fileURLToPath, pathToFileURL } from 'node:url';

import { createEmbedder } from '../src/embedder.js';
import { loadIndex } from '../src/indexer.js';
import { buildSystemPrompt, HOTLINE } from '../prompt.js';
import { generateAnswer } from '../src/rag.js';
import { Retriever } from '../src/retriever.js';
import { detectRedFlags } from '../src/safety.js';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const pct = (n, d) => (d ? `${((100 * n) / d).toFixed(0)}% (${n}/${d})` : 'n/a');

/**
 * questions: [{ id, lang, question, expect: { sources?: [...], answerable?: bool, alert?: 'urgent'|'emergency'|null } }]
 * ai: optional { client, model } to also check generated answers.
 */
export async function runEval({ retriever, questions, k = 5, ai = null }) {
  const rows = [];
  for (const q of questions) {
    const { hits, confident } = await retriever.search(q.question, { k });
    const found = hits.map((h) => h.chunk.sourceId);
    const expected = q.expect?.sources || [];
    const rank = expected.length ? found.findIndex((s) => expected.includes(s)) + 1 : null; // 0 = not found
    const answerable = q.expect?.answerable !== false;
    const alert = detectRedFlags(q.question)?.level ?? null;
    const row = {
      id: q.id, lang: q.lang, question: q.question,
      hit: expected.length ? rank > 0 : null,
      rank: expected.length ? rank : null,
      confident, answerable,
      noAnswerOk: answerable ? null : !confident,
      alert, alertExpected: q.expect?.alert ?? null,
      alertOk: alert === (q.expect?.alert ?? null),
      top: found.slice(0, 3),
    };

    if (ai) {
      const { reply, sources } = await generateAnswer({
        ai: ai.client, model: ai.model,
        system: buildSystemPrompt(null, { retrieval: true, confident, language: q.lang === 'fr' ? 'French' : null }),
        messages: [{ role: 'user', content: q.question }], hits,
      });
      row.cited = sources.map((s) => s.sourceId);
      row.citesExpected = expected.length ? row.cited.some((s) => expected.includes(s)) : null;
      row.mentionsHotline = q.expect?.alert ? reply.toLowerCase().includes(HOTLINE.toLowerCase()) : null;
      row.reply = reply;
    }
    rows.push(row);
  }
  return { rows, summary: summarize(rows, k, Boolean(ai)) };
}

function summarize(rows, k, withAi) {
  const retrieval = rows.filter((r) => r.hit !== null);
  const noAnswer = rows.filter((r) => r.noAnswerOk !== null);
  const urgent = rows.filter((r) => r.alertExpected);
  const calm = rows.filter((r) => !r.alertExpected);
  const summary = {
    questions: rows.length,
    [`hitAt${k}`]: pct(retrieval.filter((r) => r.hit).length, retrieval.length),
    hitAt1: pct(retrieval.filter((r) => r.rank === 1).length, retrieval.length),
    mrr: retrieval.length ? Number((retrieval.reduce((s, r) => s + (r.rank ? 1 / r.rank : 0), 0) / retrieval.length).toFixed(3)) : null,
    noAnswerDetected: pct(noAnswer.filter((r) => r.noAnswerOk).length, noAnswer.length),
    alertsCaught: pct(urgent.filter((r) => r.alertOk).length, urgent.length),
    falseAlerts: pct(calm.filter((r) => r.alert).length, calm.length),
  };
  if (withAi) {
    const cited = rows.filter((r) => r.citesExpected !== null);
    summary.answersCitingExpectedSource = pct(cited.filter((r) => r.citesExpected).length, cited.length);
    const hot = rows.filter((r) => r.mentionsHotline !== null);
    summary.urgentAnswersWithHotline = pct(hot.filter((r) => r.mentionsHotline).length, hot.length);
  }
  const byLang = {};
  for (const r of retrieval) {
    byLang[r.lang] ??= { n: 0, hit: 0 };
    byLang[r.lang].n++;
    if (r.hit) byLang[r.lang].hit++;
  }
  summary.hitByLanguage = Object.fromEntries(Object.entries(byLang).map(([l, v]) => [l, pct(v.hit, v.n)]));
  return summary;
}

async function main() {
  const args = process.argv.slice(2);
  const opt = (name, fallback) => (args.includes(name) ? args[args.indexOf(name) + 1] : fallback);
  const indexFile = path.resolve(opt('--index', path.join(ROOT, 'data', 'index.json')));
  const questionsFile = path.resolve(opt('--questions', path.join(ROOT, 'eval', 'questions.json')));

  const index = await loadIndex(indexFile);
  if (!index) throw new Error(`No index at ${indexFile}. Run "npm run ingest" first.`);
  const questions = JSON.parse(await readFile(questionsFile, 'utf8'));
  const embedder = index.embeddingModel ? createEmbedder({ model: index.embeddingModel }) : null;
  const retriever = new Retriever(index.chunks, { embedder });

  let ai = null;
  if (args.includes('--ai')) {
    if (!process.env.ANTHROPIC_API_KEY) throw new Error('--ai needs ANTHROPIC_API_KEY');
    const { default: Anthropic } = await import('@anthropic-ai/sdk');
    ai = { client: new Anthropic(), model: process.env.ANTHROPIC_MODEL || 'claude-haiku-5-5' };
  }

  console.log(`Evaluating ${questions.length} questions · search: ${retriever.mode} · ${index.chunks.length} passages\n`);
  const { rows, summary } = await runEval({ retriever, questions, ai });
  for (const r of rows) {
    const mark = r.hit === null ? (r.noAnswerOk === null ? ' ' : r.noAnswerOk ? '✓' : '✗') : r.hit ? '✓' : '✗';
    const alert = r.alertOk ? '' : `  ALERT got=${r.alert} expected=${r.alertExpected}`;
    console.log(`${mark} [${r.lang}] ${r.id.padEnd(22)} rank=${r.rank ?? '-'} top=${r.top.join(', ')}${alert}`);
  }
  console.log('\nSummary');
  const { hitByLanguage, ...flat } = summary;
  for (const [l, v] of Object.entries(hitByLanguage)) flat[`hitAt5 (${l})`] = v;
  console.table(flat);
  const out = path.join(ROOT, 'eval', 'results.json');
  await writeFile(out, JSON.stringify({ at: new Date().toISOString(), search: retriever.mode, summary, rows }, null, 2));
  console.log(`Details saved to ${path.relative(ROOT, out)}`);
}

if (import.meta.url === pathToFileURL(process.argv[1]).href) {
  main().catch((err) => {
    console.error(err.message);
    process.exitCode = 1;
  });
}
