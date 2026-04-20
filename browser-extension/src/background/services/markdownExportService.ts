import type { MarkdownExportSettings } from '../../shared/config/phase0';
import type {
  AnalysisAction,
  AnalyzeUsageMetrics,
  ArticleContext,
  ExportMarkdownPayload,
  SelectionSessionItem,
} from '../../shared/contracts/messages';

export interface BuildMarkdownExportDocumentOptions {
  exportedAt?: Date;
}

export function buildMarkdownExportDocument(
  payload: ExportMarkdownPayload,
  settings: MarkdownExportSettings,
  options: BuildMarkdownExportDocumentOptions = {}
): string {
  const exportedAt = options.exportedAt ?? new Date();
  const translatedText = payload.translatedText?.trim();
  const explanation = payload.explanation?.trim() ?? '';

  if (!translatedText && !explanation) {
    throw new Error('No Gemini result is available to export.');
  }

  const lines: string[] = [];

  if (settings.includeYamlFrontmatter) {
    lines.push('---');
    lines.push(`title: ${toYamlString(payload.pageTitle)}`);
    lines.push(`exportedAt: ${toYamlString(exportedAt.toISOString())}`);
    lines.push(`action: ${toYamlString(payload.action)}`);
    lines.push(`pageTitle: ${toYamlString(payload.pageTitle)}`);
    lines.push(`pageUrl: ${toYamlString(payload.pageUrl)}`);
    if (payload.modelName?.trim()) {
      lines.push(`modelName: ${toYamlString(payload.modelName.trim())}`);
    }
    lines.push(`selectionCount: ${resolveSelections(payload).length}`);
    lines.push('---');
    lines.push('');
  }

  lines.push(`# ${payload.pageTitle.trim() || 'Gemini Export'}`);
  lines.push('');
  lines.push(`- Exported At: ${exportedAt.toISOString()}`);
  lines.push(`- Action: ${formatActionLabel(payload.action)}`);
  lines.push(`- Model: ${payload.modelName?.trim() || 'Not recorded'}`);
  lines.push(
    `- Source Page: [${escapeMarkdownLinkText(payload.pageTitle)}](${payload.pageUrl})`
  );
  lines.push('');

  const selections = resolveSelections(payload);
  if (settings.includeSelections && selections.length > 0) {
    lines.push('## Selections');
    lines.push('');
    selections.forEach((selection, index) => {
      lines.push(`${index + 1}. ${selection}`);
    });
    lines.push('');
  }

  if (translatedText) {
    lines.push('## Gemini Response');
    lines.push('');
    lines.push(translatedText);
    lines.push('');
  }

  if (settings.includeExplanation && explanation) {
    lines.push('## Explanation');
    lines.push('');
    lines.push(explanation);
    lines.push('');
  }

  if (settings.includeRawResponse && payload.rawResponse?.trim()) {
    lines.push('## Raw Response');
    lines.push('');
    lines.push('```text');
    lines.push(payload.rawResponse.trim());
    lines.push('```');
    lines.push('');
  }

  if (settings.includeArticleMetadata && payload.articleContext) {
    lines.push(...buildArticleMetadataSection(payload.articleContext));
  }

  if (settings.includeUsageMetrics && hasUsageMetrics(payload.usage)) {
    lines.push(...buildUsageSection(payload.usage));
  }

  return trimTrailingBlankLines(lines).join('\n');
}

function resolveSelections(payload: ExportMarkdownPayload): string[] {
  if (payload.sessionItems?.length) {
    return payload.sessionItems
      .map((item) => item.selection.text.trim())
      .filter((value) => value.length > 0);
  }

  const selectedText = payload.selectedText?.trim();
  return selectedText ? [selectedText] : [];
}

function buildArticleMetadataSection(articleContext: ArticleContext): string[] {
  const lines = ['## Article Metadata', ''];
  lines.push(`- Title: ${articleContext.title}`);
  lines.push(`- URL: ${articleContext.url}`);
  lines.push(`- Source: ${articleContext.source}`);
  lines.push(`- Text Length: ${articleContext.textLength}`);
  if (articleContext.byline) {
    lines.push(`- Byline: ${articleContext.byline}`);
  }
  if (articleContext.siteName) {
    lines.push(`- Site Name: ${articleContext.siteName}`);
  }
  if (articleContext.excerpt) {
    lines.push(`- Excerpt: ${articleContext.excerpt}`);
  }
  lines.push(`- Body Hash: ${articleContext.bodyHash}`);
  lines.push('');
  return lines;
}

function buildUsageSection(usage: AnalyzeUsageMetrics | undefined): string[] {
  const lines = ['## Usage Metrics', ''];
  if (usage?.promptTokenCount !== undefined) {
    lines.push(`- Prompt Tokens: ${usage.promptTokenCount}`);
  }
  if (usage?.cachedContentTokenCount !== undefined) {
    lines.push(`- Cached Content Tokens: ${usage.cachedContentTokenCount}`);
  }
  if (usage?.candidatesTokenCount !== undefined) {
    lines.push(`- Candidate Tokens: ${usage.candidatesTokenCount}`);
  }
  if (usage?.totalTokenCount !== undefined) {
    lines.push(`- Total Tokens: ${usage.totalTokenCount}`);
  }
  lines.push('');
  return lines;
}

function hasUsageMetrics(usage: AnalyzeUsageMetrics | undefined): boolean {
  return (
    usage?.promptTokenCount !== undefined ||
    usage?.cachedContentTokenCount !== undefined ||
    usage?.candidatesTokenCount !== undefined ||
    usage?.totalTokenCount !== undefined
  );
}

function formatActionLabel(action: AnalysisAction): string {
  if (action === 'translation_with_explanation') {
    return 'Translation With Explanation';
  }
  if (action === 'custom_prompt') {
    return 'Custom Prompt';
  }
  return 'Translation';
}

function toYamlString(value: string): string {
  return JSON.stringify(value);
}

function escapeMarkdownLinkText(value: string): string {
  return value.replaceAll('[', '\\[').replaceAll(']', '\\]');
}

function trimTrailingBlankLines(lines: string[]): string[] {
  const nextLines = [...lines];
  while (nextLines.at(-1) === '') {
    nextLines.pop();
  }
  return nextLines;
}

export function buildSelectionSummary(
  sessionItems: SelectionSessionItem[]
): string[] {
  return sessionItems
    .map((item) => item.selection.text.trim())
    .filter((value) => value.length > 0);
}
