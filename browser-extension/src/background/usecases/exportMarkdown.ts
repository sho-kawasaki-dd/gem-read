import type { MarkdownExportSettings } from '../../shared/config/phase0';
import type { ExportMarkdownPayload } from '../../shared/contracts/messages';
import {
  downloadMarkdownFile,
  type DownloadMarkdownFileResult,
} from '../gateways/downloadGateway';
import { buildMarkdownExportDocument } from '../services/markdownExportService';

export async function exportMarkdown(
  payload: ExportMarkdownPayload,
  settings: MarkdownExportSettings
): Promise<DownloadMarkdownFileResult> {
  const markdown = buildMarkdownExportDocument(payload, settings);
  return downloadMarkdownFile({
    markdown,
    pageTitle: payload.pageTitle,
  });
}
