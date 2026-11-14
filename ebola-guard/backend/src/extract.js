// Turns a downloaded web page (or a plain-text file) into sections:
// [{ heading, paragraphs: [...] }], keeping only the readable main content.
import * as cheerio from 'cheerio';

import { clean } from './text.js';

const NOISE = 'script, style, noscript, nav, header, footer, aside, form, iframe, svg, button, ' +
  '[role="navigation"], [role="banner"], [role="contentinfo"], [aria-hidden="true"], ' +
  '.breadcrumb, .breadcrumbs, .share, .social, .cookie, .sr-only, .visually-hidden';

const MIN_PARAGRAPH_CHARS = 25;

export function extractFromHtml(html) {
  const $ = cheerio.load(html);
  const title = clean($('h1').first().text()) || clean($('title').first().text());
  $(NOISE).remove();

  const root = ['main', 'article', '[role="main"]', '#content', 'body']
    .map((sel) => $(sel).first())
    .find((el) => el.length && clean(el.text()).length > 200) ?? $('body');

  const sections = [];
  let current = { heading: '', paragraphs: [] };
  const push = () => {
    if (current.paragraphs.length) sections.push(current);
  };

  root.find('h1, h2, h3, h4, p, li, td, dd, blockquote').each((_, node) => {
    const el = $(node);
    const tag = node.tagName.toLowerCase();
    if (/^h[1-4]$/.test(tag)) {
      push();
      current = { heading: clean(el.text()), paragraphs: [] };
      return;
    }
    // Skip containers whose text is already captured by a nested block.
    if (el.find('p, li, td, dd').length) return;
    const text = clean(el.text());
    if (text.length < MIN_PARAGRAPH_CHARS) return;
    if (tag === 'li') current.paragraphs.push(`• ${text}`);
    else current.paragraphs.push(text);
  });
  push();
  return { title, sections: dedupe(sections) };
}

/** Plain text: blank lines separate paragraphs, lines starting with "#" are headings. */
export function extractFromText(text) {
  const sections = [];
  let current = { heading: '', paragraphs: [] };
  let title = '';
  for (const block of String(text).split(/\n\s*\n/)) {
    const line = block.trim();
    if (!line) continue;
    if (line.startsWith('#')) {
      if (current.paragraphs.length) sections.push(current);
      const heading = clean(line.replace(/^#+/, ''));
      if (!title) title = heading;
      current = { heading, paragraphs: [] };
    } else {
      current.paragraphs.push(clean(line));
    }
  }
  if (current.paragraphs.length) sections.push(current);
  return { title, sections: dedupe(sections) };
}

// Web pages often repeat the same sentence (summary boxes, "key points"). Keep the first.
function dedupe(sections) {
  const seen = new Set();
  return sections
    .map((s) => ({
      heading: s.heading,
      paragraphs: s.paragraphs.filter((p) => {
        const key = p.toLowerCase();
        if (seen.has(key)) return false;
        seen.add(key);
        return true;
      }),
    }))
    .filter((s) => s.paragraphs.length);
}
