import { RICH_TEXT_STYLE_BLOCK } from './richTextRenderer';

export const PANEL_STYLE_BLOCK = `
  :host {
    all: initial;
  }
  ${RICH_TEXT_STYLE_BLOCK}
  .panel {
    position: fixed;
    top: 16px;
    right: 16px;
    width: min(460px, calc(100vw - 32px));
    max-height: calc(100vh - 32px);
    overflow: auto;
    box-sizing: border-box;
    padding: 16px;
    border-radius: 18px;
    background:
      radial-gradient(circle at top right, rgba(251, 191, 36, 0.18), transparent 30%),
      linear-gradient(180deg, rgba(20, 24, 36, 0.97) 0%, rgba(10, 14, 24, 0.98) 100%);
    color: #f8fafc;
    border: 1px solid rgba(251, 191, 36, 0.18);
    box-shadow: 0 26px 70px rgba(2, 6, 23, 0.52);
    font: 13px/1.55 'Segoe UI', 'Yu Gothic UI', sans-serif;
  }
  .header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
    margin-bottom: 12px;
  }
  .header-actions {
    display: inline-flex;
    gap: 8px;
  }
  .title {
    font-size: 16px;
    font-weight: 700;
    letter-spacing: 0.03em;
  }
  .subtitle {
    margin-top: 4px;
    color: #cbd5e1;
    font-size: 12px;
  }
  .badge {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 4px 8px;
    border-radius: 999px;
    background: rgba(251, 191, 36, 0.18);
    color: #fde68a;
    font-size: 11px;
    font-weight: 600;
  }
  .panel-tabs {
    display: flex;
    gap: 8px;
    margin-bottom: 12px;
  }
  .panel-tab {
    flex: 1;
    min-width: 0;
    border: 1px solid rgba(148, 163, 184, 0.28);
    border-radius: 999px;
    background: rgba(30, 41, 59, 0.72);
    color: #cbd5e1;
    cursor: pointer;
    font: inherit;
    font-weight: 600;
    letter-spacing: 0.02em;
    padding: 9px 12px;
    transition:
      background-color 120ms ease,
      border-color 120ms ease,
      color 120ms ease,
      box-shadow 120ms ease;
  }
  .panel-tab:hover:not(:disabled) {
    border-color: rgba(250, 204, 21, 0.44);
    color: #f8fafc;
  }
  .panel-tab:focus-visible {
    outline: 2px solid rgba(250, 204, 21, 0.85);
    outline-offset: 2px;
  }
  .panel-tab[aria-selected='true'] {
    background: linear-gradient(180deg, rgba(250, 204, 21, 0.28), rgba(245, 158, 11, 0.18));
    border-color: rgba(250, 204, 21, 0.64);
    box-shadow: inset 0 0 0 1px rgba(250, 204, 21, 0.16);
    color: #fef3c7;
  }
  .panel-tab:disabled {
    cursor: not-allowed;
    opacity: 0.48;
  }
  .panel-tabpanel[hidden] {
    display: none;
  }
  .gemini-empty-state {
    margin-top: 12px;
    padding: 12px 14px;
    border: 1px dashed rgba(148, 163, 184, 0.28);
    border-radius: 14px;
    background: rgba(15, 23, 42, 0.55);
    color: #cbd5e1;
  }
  .close,
  .minimize {
    min-width: 36px;
    height: 36px;
    border: 1px solid rgba(148, 163, 184, 0.18);
    border-radius: 999px;
    background: rgba(15, 23, 42, 0.76);
    color: #cbd5e1;
    cursor: pointer;
    font: inherit;
  }
  .section {
    margin-top: 12px;
  }
  .section:first-of-type {
    margin-top: 0;
  }
  .label {
    margin-bottom: 6px;
    color: #93c5fd;
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 0.08em;
    text-transform: uppercase;
  }
  .banner-box {
    padding: 10px 12px;
    border-radius: 12px;
    background: rgba(245, 158, 11, 0.14);
    border: 1px solid rgba(245, 158, 11, 0.26);
    color: #fde68a;
  }
  .article-card {
    display: grid;
    gap: 10px;
    padding: 12px;
    border-radius: 12px;
    background: rgba(15, 23, 42, 0.5);
    border: 1px solid rgba(148, 163, 184, 0.16);
  }
  .article-header {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: 12px;
  }
  .article-title {
    font-size: 13px;
    font-weight: 700;
    color: #f8fafc;
  }
  .article-subtitle {
    margin-top: 4px;
    font-size: 11px;
    color: #cbd5e1;
  }
  .article-summary {
    color: #e2e8f0;
    font-size: 12px;
    white-space: pre-wrap;
  }
  .article-meta-row {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
  }
  .token-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
    gap: 10px;
  }
  .token-card {
    display: grid;
    gap: 6px;
    padding: 12px;
    border-radius: 12px;
    background: rgba(15, 23, 42, 0.5);
    border: 1px solid rgba(148, 163, 184, 0.16);
  }
  .token-title {
    color: #93c5fd;
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 0.06em;
    text-transform: uppercase;
  }
  .token-value {
    color: #f8fafc;
    font-size: 16px;
    font-weight: 700;
  }
  .token-note {
    color: #cbd5e1;
    font-size: 12px;
    white-space: pre-wrap;
  }
  .token-note--warning {
    color: #fde68a;
  }
  .article-pill {
    display: inline-flex;
    align-items: center;
    gap: 4px;
    padding: 4px 8px;
    border-radius: 999px;
    background: rgba(37, 99, 235, 0.16);
    color: #dbeafe;
    font-size: 11px;
  }
  .box {
    padding: 10px 12px;
    border-radius: 10px;
    background: rgba(15, 23, 42, 0.65);
    border: 1px solid rgba(148, 163, 184, 0.16);
    white-space: pre-wrap;
    word-break: break-word;
  }
  .image {
    display: block;
    width: 100%;
    border-radius: 10px;
    border: 1px solid rgba(148, 163, 184, 0.16);
  }
  .meta {
    margin-top: 10px;
    color: #cbd5e1;
    font-size: 11px;
  }
  .error {
    color: #fecaca;
  }
  .loading {
    color: #fde68a;
  }
  .action-grid {
    display: grid;
    gap: 10px;
  }
  .action-row {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 10px;
  }
  .action-row--single {
    grid-template-columns: 1fr;
  }
  .batch-actions {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
  .input,
  .textarea,
  .action-button {
    box-sizing: border-box;
    width: 100%;
    border-radius: 12px;
    font: inherit;
  }
  .input,
  .textarea {
    border: 1px solid rgba(148, 163, 184, 0.18);
    background: rgba(15, 23, 42, 0.82);
    color: #f8fafc;
    padding: 10px 12px;
  }
  .textarea {
    min-height: 88px;
    resize: vertical;
  }
  .action-button {
    border: 0;
    padding: 10px 12px;
    cursor: pointer;
  }
  .action-button:disabled {
    cursor: not-allowed;
    opacity: 0.55;
  }
  .action-button--primary {
    background: linear-gradient(135deg, #b45309 0%, #ea580c 100%);
    color: #fff7ed;
  }
  .action-button--secondary {
    background: rgba(37, 99, 235, 0.2);
    color: #dbeafe;
  }
  .action-button--accent {
    background: rgba(217, 70, 239, 0.18);
    color: #f5d0fe;
  }
  .action-hint {
    color: #cbd5e1;
    font-size: 12px;
  }
  .batch-counter {
    color: #cbd5e1;
    font-size: 11px;
  }
  .batch-list {
    display: grid;
    gap: 8px;
  }
  .session-item {
    display: grid;
    gap: 6px;
    padding: 10px 12px;
    border-radius: 10px;
    background: rgba(15, 23, 42, 0.65);
    border: 1px solid rgba(148, 163, 184, 0.16);
  }
  .session-item-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 10px;
  }
  .session-item-kind {
    display: inline-flex;
    gap: 8px;
    align-items: center;
    color: #fde68a;
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 0.06em;
    text-transform: uppercase;
  }
  .session-item-text {
    color: #f8fafc;
    font-size: 12px;
    white-space: pre-wrap;
    word-break: break-word;
  }
  .session-item-remove {
    border: 0;
    padding: 6px 10px;
    border-radius: 999px;
    background: rgba(239, 68, 68, 0.18);
    color: #fecaca;
    cursor: pointer;
    font: inherit;
  }
  .batch-hint {
    color: #cbd5e1;
    font-size: 12px;
  }
  .rich-text-box {
    white-space: normal;
  }
  .details {
    border-radius: 12px;
    background: rgba(15, 23, 42, 0.45);
    border: 1px solid rgba(148, 163, 184, 0.16);
    overflow: hidden;
  }
  .details > summary {
    cursor: pointer;
    list-style: none;
    padding: 10px 12px;
    color: #cbd5e1;
    font-weight: 600;
  }
  .details > summary::-webkit-details-marker {
    display: none;
  }
  .details-body {
    padding: 0 12px 12px;
  }
  .session-item-meta {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 10px;
    color: #cbd5e1;
    font-size: 11px;
  }
  .session-item-toggle {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    color: #dbeafe;
  }
  .session-item-toggle input {
    margin: 0;
  }
`;

export const LAUNCHER_STYLE_BLOCK = `
  :host {
    all: initial;
  }
  .launcher {
    position: fixed;
    right: 16px;
    bottom: 16px;
    display: inline-flex;
    align-items: center;
    gap: 8px;
    padding: 10px 12px;
    border-radius: 999px;
    background: rgba(15, 23, 42, 0.95);
    color: #f8fafc;
    border: 1px solid rgba(251, 191, 36, 0.18);
    box-shadow: 0 16px 40px rgba(2, 6, 23, 0.42);
    font: 12px/1.4 'Segoe UI', 'Yu Gothic UI', sans-serif;
  }
  .launcher-button,
  .launcher-close {
    border: 0;
    background: transparent;
    color: inherit;
    cursor: pointer;
    font: inherit;
  }
  .launcher-badge {
    display: inline-flex;
    padding: 4px 8px;
    border-radius: 999px;
    background: rgba(251, 191, 36, 0.16);
    color: #fde68a;
  }
`;
