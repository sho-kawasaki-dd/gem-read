import type { OverlayPayload } from '../../shared/contracts/messages';

const OVERLAY_HOST_ID = 'gem-read-phase0-overlay-host';

export function renderOverlay(payload: OverlayPayload): void {
  const root = ensureOverlayRoot();
  root.innerHTML = `
    <style>
      :host {
        all: initial;
      }
      .panel {
        position: fixed;
        top: 16px;
        right: 16px;
        width: min(420px, calc(100vw - 32px));
        max-height: calc(100vh - 32px);
        overflow: auto;
        box-sizing: border-box;
        padding: 14px;
        border-radius: 14px;
        background: rgba(18, 24, 38, 0.94);
        color: #f5f7fb;
        border: 1px solid rgba(148, 163, 184, 0.28);
        box-shadow: 0 24px 60px rgba(15, 23, 42, 0.45);
        font: 13px/1.55 'Segoe UI', 'Yu Gothic UI', sans-serif;
      }
      .header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 12px;
        margin-bottom: 12px;
      }
      .title {
        font-size: 14px;
        font-weight: 700;
        letter-spacing: 0.02em;
      }
      .badge {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        padding: 4px 8px;
        border-radius: 999px;
        background: rgba(59, 130, 246, 0.22);
        color: #bfdbfe;
        font-size: 11px;
        font-weight: 600;
      }
      .close {
        border: 0;
        background: transparent;
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
    </style>
    <div class="panel">
      <div class="header">
        <div>
          <div class="title">Gem Read Phase 0</div>
          <div class="badge">${getStatusLabel(payload.status, payload.usedMock)}</div>
        </div>
        <button class="close" type="button">Close</button>
      </div>
      <div class="section">
        <div class="label">Selection</div>
        <div class="box selection-box"></div>
      </div>
      <div class="section preview-section" hidden>
        <div class="label">Crop Preview</div>
        <img class="image preview-image" alt="Selection crop preview" />
      </div>
      <div class="section result-section" hidden>
        <div class="label">Translation</div>
        <div class="box result-box"></div>
      </div>
      <div class="section explanation-section" hidden>
        <div class="label">Explanation</div>
        <div class="box explanation-box"></div>
      </div>
      <div class="section raw-section" hidden>
        <div class="label">Raw Response</div>
        <div class="box raw-box"></div>
      </div>
      <div class="section error-section" hidden>
        <div class="label">Error</div>
        <div class="box error error-box"></div>
      </div>
      <div class="meta meta-box"></div>
    </div>
  `;

  const selectionBox = root.querySelector<HTMLElement>('.selection-box');
  const previewSection = root.querySelector<HTMLElement>('.preview-section');
  const previewImage = root.querySelector<HTMLImageElement>('.preview-image');
  const resultSection = root.querySelector<HTMLElement>('.result-section');
  const resultBox = root.querySelector<HTMLElement>('.result-box');
  const explanationSection = root.querySelector<HTMLElement>('.explanation-section');
  const explanationBox = root.querySelector<HTMLElement>('.explanation-box');
  const rawSection = root.querySelector<HTMLElement>('.raw-section');
  const rawBox = root.querySelector<HTMLElement>('.raw-box');
  const errorSection = root.querySelector<HTMLElement>('.error-section');
  const errorBox = root.querySelector<HTMLElement>('.error-box');
  const metaBox = root.querySelector<HTMLElement>('.meta-box');
  const closeButton = root.querySelector<HTMLButtonElement>('.close');

  if (!selectionBox || !previewSection || !previewImage || !resultSection || !resultBox || !explanationSection || !explanationBox || !rawSection || !rawBox || !errorSection || !errorBox || !metaBox || !closeButton) {
    return;
  }

  selectionBox.textContent = payload.selectedText || 'No selection text captured.';

  previewSection.hidden = !payload.previewImageUrl;
  if (payload.previewImageUrl) {
    previewImage.src = payload.previewImageUrl;
  }

  resultSection.hidden = !payload.translatedText;
  resultBox.textContent = payload.translatedText || '';

  explanationSection.hidden = !payload.explanation;
  explanationBox.textContent = payload.explanation || '';

  rawSection.hidden = !payload.rawResponse;
  rawBox.textContent = payload.rawResponse || '';

  errorSection.hidden = !payload.error;
  errorBox.textContent = payload.error || '';

  metaBox.textContent = buildMetaText(payload);
  if (payload.status === 'loading') {
    metaBox.classList.add('loading');
  } else {
    metaBox.classList.remove('loading');
  }

  closeButton.addEventListener('click', () => {
    const host = document.getElementById(OVERLAY_HOST_ID);
    host?.remove();
  });
}

function buildMetaText(payload: OverlayPayload): string {
  const items: string[] = [];
  if (payload.status === 'loading') {
    items.push('Background workflow is running.');
  }
  if (payload.imageCount !== undefined) {
    items.push(`images=${payload.imageCount}`);
  }
  if (payload.timingMs !== undefined) {
    items.push(`crop=${payload.timingMs.toFixed(1)}ms`);
  }
  if (payload.usedMock) {
    items.push('mock-response');
  }
  return items.join(' | ');
}

function getStatusLabel(status: OverlayPayload['status'], usedMock?: boolean): string {
  if (status === 'loading') {
    return 'Running';
  }
  if (status === 'error') {
    return 'Error';
  }
  return usedMock ? 'Mock Result' : 'Live Result';
}

function ensureOverlayRoot(): ShadowRoot {
  let host = document.getElementById(OVERLAY_HOST_ID);
  if (!host) {
    host = document.createElement('div');
    host.id = OVERLAY_HOST_ID;
    host.style.position = 'fixed';
    host.style.top = '0';
    host.style.left = '0';
    host.style.zIndex = '2147483647';
    document.documentElement.appendChild(host);
  }

  return host.shadowRoot ?? host.attachShadow({ mode: 'open' });
}