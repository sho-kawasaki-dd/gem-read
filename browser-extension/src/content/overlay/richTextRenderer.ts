import DOMPurify from 'dompurify';
import katexStyles from 'katex/dist/katex.min.css?inline';
import renderMathInElement from 'katex/contrib/auto-render';
import { marked } from 'marked';

export const RICH_TEXT_STYLE_BLOCK = `
${katexStyles}

.rich-text {
  color: inherit;
}

.rich-text > :first-child {
  margin-top: 0;
}

.rich-text > :last-child {
  margin-bottom: 0;
}

.rich-text h1,
.rich-text h2,
.rich-text h3,
.rich-text h4 {
  margin: 0.9em 0 0.45em;
  color: #fef3c7;
  font-weight: 700;
  line-height: 1.25;
}

.rich-text p,
.rich-text ul,
.rich-text ol,
.rich-text blockquote,
.rich-text pre,
.rich-text table {
  margin: 0.65em 0;
}

.rich-text ul,
.rich-text ol {
  padding-inline-start: 1.3em;
}

.rich-text li + li {
  margin-top: 0.28em;
}

.rich-text blockquote {
  padding: 0.75em 1em;
  border-left: 3px solid rgba(96, 165, 250, 0.65);
  background: rgba(30, 41, 59, 0.52);
  color: #dbeafe;
}

.rich-text a {
  color: #93c5fd;
}

.rich-text strong {
  color: #fff7ed;
}

.rich-text hr {
  border: 0;
  border-top: 1px solid rgba(148, 163, 184, 0.22);
  margin: 1em 0;
}

.rich-text code {
  padding: 0.12em 0.35em;
  border-radius: 0.4em;
  background: rgba(15, 23, 42, 0.78);
  color: #fcd34d;
  font-family: 'Cascadia Code', 'Consolas', monospace;
  font-size: 0.92em;
}

.rich-text pre {
  overflow-x: auto;
  padding: 0.95em 1em;
  border-radius: 0.8em;
  background: rgba(2, 6, 23, 0.84);
  border: 1px solid rgba(148, 163, 184, 0.14);
}

.rich-text pre code {
  padding: 0;
  border-radius: 0;
  background: transparent;
  color: #e2e8f0;
}

.rich-text table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.94em;
}

.rich-text th,
.rich-text td {
  padding: 0.55em 0.65em;
  border: 1px solid rgba(148, 163, 184, 0.16);
  text-align: left;
  vertical-align: top;
}

.rich-text th {
  background: rgba(30, 41, 59, 0.7);
  color: #fde68a;
}

.rich-text .katex-display {
  overflow-x: auto;
  overflow-y: hidden;
  padding: 0.25em 0;
}
`;

const MATH_DELIMITERS = [
  { left: '$$', right: '$$', display: true },
  { left: '\\[', right: '\\]', display: true },
  { left: '$', right: '$', display: false },
  { left: '\\(', right: '\\)', display: false },
];

/**
 * Gemini の text response は HTML として信用せず、Markdown parse -> sanitize -> KaTeX の順で描画する。
 * どこかで失敗しても overlay 全体を壊さず、plain text へ戻すのが責務。
 */
export function renderRichText(container: HTMLElement, sourceText: string): void {
  container.classList.add('rich-text');

  if (!sourceText.trim()) {
    container.textContent = '';
    container.dataset.renderMode = 'plain';
    return;
  }

  try {
    const html = marked.parse(sourceText, {
      async: false,
      breaks: true,
      gfm: true,
    }) as string;
    // AI 応答をそのまま innerHTML に入れず、許可済み HTML だけへ落としてから math render へ渡す。
    const sanitizedHtml = DOMPurify.sanitize(html, {
      USE_PROFILES: { html: true },
    }) as string;

    container.innerHTML = sanitizedHtml;
    renderMathInElement(container, {
      delimiters: MATH_DELIMITERS,
      ignoredTags: ['script', 'noscript', 'style', 'textarea', 'pre', 'code'],
      throwOnError: false,
      strict: 'ignore',
    });
    container.dataset.renderMode = 'rich';
  } catch {
    container.textContent = sourceText;
    container.dataset.renderMode = 'plain';
  }
}