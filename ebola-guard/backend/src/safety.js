// A small rule-based safety net that works even without the AI:
// if the user describes THEIR OWN danger signs, the app shows an alert
// with the hotline, whatever the model answers.
//
// It is a keyword heuristic (English, French, Lingala, Swahili), not a
// diagnosis. The AI prompt has the same rules; this is the backstop.
import { normalize } from './text.js';

const FIRST_PERSON = [
  /\b(i|i'm|im|i've|ive|my|me)\b/, // English
  /\b(je|j|j'ai|moi|mon|ma|mes|nous)\b/, // French
  /\b(nazali|nazo|ngai|na ngai|nayoki)\b/, // Lingala
  /\b(nina|nimekuwa|mimi|yangu|nime\w*)\b/, // Swahili
];

const EMERGENCY_SIGNS = [
  /\bbleed\w*/, /\bblood\b/, /\bvomit\w* blood/, /\bconfus\w*/, /\bfaint\w*/, /\bunconscious/, /\bcan'?t breathe|difficulty breathing|short(ness)? of breath/,
  /\bsaign\w*/, /\bsang\b/, /\bevanoui\w*/, /\bconfus\w*/, /\bdu mal a respirer|respire mal/,
  /\bmakila\b/, // Lingala: blood
  /\bdamu\b/, /\bkuzimia\b/, // Swahili: blood, fainting
];

const SYMPTOMS = [
  /\bfever\w*/, /\bhigh temperature/, /\bheadache\w*/, /\bvomit\w*/, /\bdiarrh\w*/, /\bweak(ness)?\b/, /\bmuscle pain/, /\bsore throat/, /\bstomach pain/,
  /\bfievre\w*/, /\bmal(s|ux)? de tete/, /\bvomi\w*/, /\bdiarrhee\w*/, /\bfaiblesse|fatigue\w*/, /\bmal de ventre|douleurs?/,
  /\bmolunge\b/, /\bmotu ezo bola/, /\bkosanza\b/, /\bpulupulu\b/, // Lingala: fever/heat, headache, vomiting, diarrhoea
  /\bhoma\b/, /\bkutapika\b/, /\bkuhara\w*/, /\bmaumivu\b/, // Swahili: fever, vomiting, diarrhoea, pain
];

const EXPOSURE = [
  /\b(touch\w*|wash\w*|care\w* for|cared|nurs\w*|contact)\b.*\b(sick|ill|dead|body|corpse|patient|ebola)/,
  /\bfuneral|burial|buried\b/, /\bsomeone (with|who had) ebola/, /\boutbreak area|travel\w* (to|from)/,
  /\b(touche|lave|soigne|contact)\w*\b.*\b(malade|mort|defunt|corps|ebola)/, /\bfunerailles|enterrement|deuil\b/,
  /\bmatanga\b/, /\bmokufi\b/, // Lingala: funeral/mourning, dead person
  /\bmazishi\b/, /\bmaiti\b/, /\bmgonjwa wa ebola/, // Swahili: burial, corpse, Ebola patient
];

/**
 * Returns null, or { level: 'emergency' | 'urgent', reasons: [...] }.
 * emergency = danger sign described by the user themself.
 * urgent    = possible exposure + a symptom, described by the user themself.
 */
export function detectRedFlags(text) {
  const t = normalize(text).replace(/[’`]/g, "'");
  if (!FIRST_PERSON.some((r) => r.test(t))) return null;
  const has = (list) => list.some((r) => r.test(t));
  if (has(EMERGENCY_SIGNS)) return { level: 'emergency', reasons: ['danger sign'] };
  if (has(EXPOSURE) && has(SYMPTOMS)) return { level: 'urgent', reasons: ['possible exposure', 'symptom'] };
  return null;
}
