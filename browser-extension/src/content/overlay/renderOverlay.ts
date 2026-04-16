import type {
  AnalysisAction,
  OverlayPayload,
  RunOverlayActionMessage,
  RunOverlayActionResponse,
} from '../../shared/contracts/messages';

const OVERLAY_HOST_ID = 'gem-read-phase0-overlay-host';
// minimize 状態と draft 入力は再描画を跨いで維持したいので module state に置く。
let isOverlayMinimized = false;
let draftModelName = '';
let draftCustomPrompt = '';

/**
 * Overlay は content script 側で一元管理し、payload から都度 DOM を再構築する。
 * こうしておくと background から渡る状態だけで表示を復元でき、ページ本体の DOM 状態に依存しにくい。
 */
export function renderOverlay(payload: OverlayPayload): void {
  if (payload.modelName !== undefined) {
    draftModelName = payload.modelName;
  }
  if (payload.customPrompt !== undefined) {
    draftCustomPrompt = payload.customPrompt;
  }

  const root = ensureOverlayRoot();
  root.innerHTML = isOverlayMinimized
    ? renderLauncherMarkup(payload)
    : renderPanelMarkup(payload);

  if (isOverlayMinimized) {
    const launcherButton =
      root.querySelector<HTMLButtonElement>('.launcher-button');
    const closeButton =
      root.querySelector<HTMLButtonElement>('.launcher-close');
    launcherButton?.addEventListener('click', () => {
      isOverlayMinimized = false;
      renderOverlay(payload);
    });
    closeButton?.addEventListener('click', disposeOverlay);
    return;
  }

  const selectionBox = root.querySelector<HTMLElement>('.selection-box');
  const previewSection = root.querySelector<HTMLElement>('.preview-section');
  const previewImage = root.querySelector<HTMLImageElement>('.preview-image');
  const resultSection = root.querySelector<HTMLElement>('.result-section');
  const resultLabel = root.querySelector<HTMLElement>('.result-label');
  const resultBox = root.querySelector<HTMLElement>('.result-box');
  const explanationSection = root.querySelector<HTMLElement>(
    '.explanation-section'
  );
  const explanationBox = root.querySelector<HTMLElement>('.explanation-box');
  const rawSection = root.querySelector<HTMLElement>('.raw-section');
  const rawBox = root.querySelector<HTMLElement>('.raw-box');
  const errorSection = root.querySelector<HTMLElement>('.error-section');
  const errorBox = root.querySelector<HTMLElement>('.error-box');
  const metaBox = root.querySelector<HTMLElement>('.meta-box');
  const closeButton = root.querySelector<HTMLButtonElement>('.close');
  const minimizeButton = root.querySelector<HTMLButtonElement>('.minimize');
  const modelInput = root.querySelector<HTMLInputElement>('.model-input');
  const modelDatalist = root.querySelector<HTMLDataListElement>('.model-list');
  const customPromptInput = root.querySelector<HTMLTextAreaElement>(
    '.custom-prompt-input'
  );
  const customButton = root.querySelector<HTMLButtonElement>('.action-custom');
  const translationButton = root.querySelector<HTMLButtonElement>(
    '.action-translation'
  );
  const explanationButton = root.querySelector<HTMLButtonElement>(
    '.action-explanation'
  );
  const actionHint = root.querySelector<HTMLElement>('.action-hint');
  const bannerSection = root.querySelector<HTMLElement>('.banner-section');
  const bannerBox = root.querySelector<HTMLElement>('.banner-box');

  if (
    !selectionBox ||
    !previewSection ||
    !previewImage ||
    !resultSection ||
    !resultLabel ||
    !resultBox ||
    !explanationSection ||
    !explanationBox ||
    !rawSection ||
    !rawBox ||
    !errorSection ||
    !errorBox ||
    !metaBox ||
    !closeButton ||
    !minimizeButton ||
    !modelInput ||
    !modelDatalist ||
    !customPromptInput ||
    !customButton ||
    !translationButton ||
    !explanationButton ||
    !actionHint ||
    !bannerSection ||
    !bannerBox
  ) {
    return;
  }

  selectionBox.textContent =
    payload.selectedText || 'No selection text captured.';

  previewSection.hidden = !payload.previewImageUrl;
  if (payload.previewImageUrl) {
    previewImage.src = payload.previewImageUrl;
  }

  resultSection.hidden = !payload.translatedText;
  resultLabel.textContent = getResultLabel(payload.action);
  resultBox.textContent = payload.translatedText || '';

  explanationSection.hidden = !payload.explanation;
  explanationBox.textContent = payload.explanation || '';

  rawSection.hidden = !payload.rawResponse;
  rawBox.textContent = payload.rawResponse || '';

  errorSection.hidden = !payload.error;
  errorBox.textContent = payload.error || '';

  bannerSection.hidden = !shouldShowBanner(payload);
  bannerBox.textContent = buildBannerText(payload);

  modelInput.value = draftModelName;
  modelDatalist.innerHTML = (payload.modelOptions ?? [])
    .map(
      (model) =>
        `<option value="${escapeHtml(model.modelId)}">${escapeHtml(model.displayName)}</option>`
    )
    .join('');
  customPromptInput.value = draftCustomPrompt;

  // cached session がない段階で action を押しても再利用できる selection がないため、button を閉じておく。
  const actionsEnabled =
    Boolean(payload.sessionReady) && payload.status !== 'loading';
  translationButton.disabled = !actionsEnabled;
  explanationButton.disabled = !actionsEnabled;
  customButton.disabled =
    !actionsEnabled || customPromptInput.value.trim().length === 0;
  actionHint.textContent = actionsEnabled
    ? 'Reuse the captured selection with a different action or model.'
    : 'Select text and run Gem Read once before action buttons become available.';

  metaBox.textContent = buildMetaText(payload);
  metaBox.classList.toggle('loading', payload.status === 'loading');

  modelInput.addEventListener('input', () => {
    draftModelName = modelInput.value.trim();
  });
  customPromptInput.addEventListener('input', () => {
    // 再描画前でも途中入力を失わないよう、draft を module state に戻す。
    draftCustomPrompt = customPromptInput.value;
    customButton.disabled =
      !actionsEnabled || customPromptInput.value.trim().length === 0;
  });

  translationButton.addEventListener('click', () => {
    void runOverlayAction(
      'translation',
      modelInput.value,
      customPromptInput.value,
      errorBox,
      errorSection
    );
  });
  explanationButton.addEventListener('click', () => {
    void runOverlayAction(
      'translation_with_explanation',
      modelInput.value,
      customPromptInput.value,
      errorBox,
      errorSection
    );
  });
  customButton.addEventListener('click', () => {
    void runOverlayAction(
      'custom_prompt',
      modelInput.value,
      customPromptInput.value,
      errorBox,
      errorSection
    );
  });

  minimizeButton.addEventListener('click', () => {
    isOverlayMinimized = true;
    renderOverlay(payload);
  });
  closeButton.addEventListener('click', disposeOverlay);
}

function renderPanelMarkup(payload: OverlayPayload): string {
  return `
    <style>
      :host {
        all: initial;
      }
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
    </style>
    <div class="panel">
      <div class="header">
        <div>
          <div class="title">Gem Read Overlay</div>
          <div class="subtitle">Selection actions stay on-page while the background keeps the API flow.</div>
          <div class="badge">${getStatusLabel(payload.status, payload.usedMock)}</div>
        </div>
        <div class="header-actions">
          <button class="minimize" type="button" aria-label="Minimize overlay">_</button>
          <button class="close" type="button" aria-label="Close overlay">X</button>
        </div>
      </div>
      <div class="section banner-section" hidden>
        <div class="label">Runtime</div>
        <div class="banner-box"></div>
      </div>
      <div class="section">
        <div class="label">Actions</div>
        <div class="action-grid">
          <input class="input model-input" type="text" list="gem-read-model-list" placeholder="Optional model override" />
          <datalist class="model-list" id="gem-read-model-list"></datalist>
          <div class="action-row">
            <button class="action-button action-button--primary action-translation" type="button">Translate</button>
            <button class="action-button action-button--secondary action-explanation" type="button">Translate + Explain</button>
          </div>
          <textarea class="textarea custom-prompt-input" placeholder="Custom prompt for the current selection"></textarea>
          <div class="action-row action-row--single">
            <button class="action-button action-button--accent action-custom" type="button">Run Custom Prompt</button>
          </div>
          <div class="action-hint"></div>
        </div>
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
        <div class="label result-label">Translation</div>
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
}

function renderLauncherMarkup(payload: OverlayPayload): string {
  return `
    <style>
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
    </style>
    <div class="launcher">
      <button class="launcher-button" type="button">Gem Read</button>
      <span class="launcher-badge">${getStatusLabel(payload.status, payload.usedMock)}</span>
      <button class="launcher-close" type="button" aria-label="Close overlay">X</button>
    </div>
  `;
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
  if (payload.availability) {
    items.push(`availability=${payload.availability}`);
  }
  if (payload.degradedReason) {
    items.push(`reason=${payload.degradedReason}`);
  }
  if (payload.action) {
    items.push(`action=${payload.action}`);
  }
  return items.join(' | ');
}

function getStatusLabel(
  status: OverlayPayload['status'],
  usedMock?: boolean
): string {
  if (status === 'loading') {
    return 'Running';
  }
  if (status === 'error') {
    return 'Error';
  }
  return usedMock ? 'Mock Result' : 'Live Result';
}

function getResultLabel(action: OverlayPayload['action']): string {
  if (action === 'custom_prompt') {
    return 'Custom Prompt Result';
  }
  if (action === 'translation_with_explanation') {
    return 'Translation';
  }
  return 'Translation';
}

function shouldShowBanner(payload: OverlayPayload): boolean {
  return (
    !payload.sessionReady || payload.usedMock || Boolean(payload.degradedReason)
  );
}

function buildBannerText(payload: OverlayPayload): string {
  if (!payload.sessionReady) {
    return 'No cached selection session is ready yet. Select text on the page and run Gem Read once before using overlay actions.';
  }
  if (payload.usedMock) {
    return 'Mock mode is active. The Local API is reachable, but Gemini credentials are not configured.';
  }
  if (payload.degradedReason) {
    return `Runtime is degraded: ${payload.degradedReason}.`;
  }
  return '';
}

async function runOverlayAction(
  action: AnalysisAction,
  modelName: string,
  customPrompt: string,
  errorBox: HTMLElement,
  errorSection: HTMLElement
): Promise<void> {
  if (action === 'custom_prompt' && customPrompt.trim().length === 0) {
    errorBox.textContent = 'Custom prompt cannot be empty.';
    errorSection.hidden = false;
    return;
  }

  const message: RunOverlayActionMessage = {
    type: 'phase1.runOverlayAction',
    payload: {
      action,
      modelName: modelName.trim() || undefined,
      customPrompt:
        action === 'custom_prompt' ? customPrompt.trim() : undefined,
    },
  };

  // Overlay は privileged 処理を持たず、実行そのものは background に委譲する。
  const response = (await chrome.runtime.sendMessage(message)) as
    | RunOverlayActionResponse
    | undefined;
  if (response && !response.ok) {
    errorBox.textContent = response.error ?? 'Overlay action failed.';
    errorSection.hidden = false;
    return;
  }

  errorBox.textContent = '';
  errorSection.hidden = true;
}

function disposeOverlay(): void {
  const host = document.getElementById(OVERLAY_HOST_ID);
  host?.remove();
  isOverlayMinimized = false;
}

function escapeHtml(value: string): string {
  return value
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#39;');
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

  // Shadow DOM に閉じ込めて、対象ページの CSS と overlay の見た目が干渉しないようにする。
  return host.shadowRoot ?? host.attachShadow({ mode: 'open' });
}
