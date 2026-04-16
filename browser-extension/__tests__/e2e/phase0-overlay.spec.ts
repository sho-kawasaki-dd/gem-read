import { chromium, expect, test, type BrowserContext, type Page, type Worker } from '@playwright/test';
import { promises as fs } from 'node:fs';
import http, { type Server } from 'node:http';
import os from 'node:os';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const extensionPath = path.resolve(__dirname, '..', '..', 'dist');
const fixturePath = path.resolve(__dirname, 'fixtures', 'selection-page.html');
const expectedSelectionText =
  'Gem Read validates browser selection smoke tests with a stable paragraph so the extension can capture text coordinates and render its overlay deterministically.';

type SelectionResponse = {
  ok: boolean;
  payload?: {
    text: string;
  };
  error?: string;
};

async function startFixtureServer(): Promise<{ server: Server; url: string }> {
  const html = await fs.readFile(fixturePath, 'utf8');

  return new Promise((resolve, reject) => {
    const server = http.createServer((_request, response) => {
      response.writeHead(200, { 'Content-Type': 'text/html; charset=utf-8' });
      response.end(html);
    });

    server.once('error', reject);
    server.listen(0, '127.0.0.1', () => {
      const address = server.address();
      if (!address || typeof address === 'string') {
        reject(new Error('Failed to bind fixture server.'));
        return;
      }

      resolve({
        server,
        url: `http://127.0.0.1:${address.port}`,
      });
    });
  });
}

async function closeServer(server: Server): Promise<void> {
  await new Promise<void>((resolve, reject) => {
    server.close((error) => {
      if (error) {
        reject(error);
        return;
      }
      resolve();
    });
  });
}

async function getServiceWorker(context: BrowserContext): Promise<Worker> {
  const existingWorker = context.serviceWorkers()[0];
  if (existingWorker) {
    return existingWorker;
  }

  return context.waitForEvent('serviceworker');
}

async function selectFixtureText(page: Page): Promise<void> {
  await page.locator('#target').waitFor();
  await page.evaluate(() => {
    const paragraph = document.querySelector('#target');
    if (!(paragraph?.firstChild instanceof Text)) {
      throw new Error('Fixture paragraph text node is missing.');
    }

    const range = document.createRange();
    range.setStart(paragraph.firstChild, 0);
    range.setEnd(paragraph.firstChild, paragraph.firstChild.textContent?.length ?? 0);

    const selection = window.getSelection();
    if (!selection) {
      throw new Error('Selection API is unavailable.');
    }

    selection.removeAllRanges();
    selection.addRange(range);
    document.dispatchEvent(new Event('selectionchange'));
  });
}

async function collectSelection(worker: Worker): Promise<SelectionResponse> {
  return worker.evaluate(async () => {
    const [tab] = await chrome.tabs.query({ active: true, lastFocusedWindow: true });
    if (!tab?.id) {
      return {
        ok: false,
        error: 'No active tab found.',
      };
    }

    return chrome.tabs.sendMessage(tab.id, {
      type: 'phase0.collectSelection',
      fallbackText: '',
    });
  });
}

async function renderErrorOverlay(worker: Worker, text: string): Promise<void> {
  await worker.evaluate(async (selectedText) => {
    const [tab] = await chrome.tabs.query({ active: true, lastFocusedWindow: true });
    if (!tab?.id) {
      throw new Error('No active tab found.');
    }

    await chrome.tabs.sendMessage(tab.id, {
      type: 'phase0.renderOverlay',
      payload: {
        status: 'error',
        selectedText,
        error: 'Playwright smoke stub',
      },
    });
  }, text);
}

async function readShadowText(page: Page, selector: string): Promise<string | null> {
  return page.locator('#gem-read-phase0-overlay-host').evaluate((host, targetSelector) => {
    return host.shadowRoot?.querySelector(targetSelector)?.textContent ?? null;
  }, selector);
}

test('captures selection and renders the overlay in Chromium', async () => {
  const userDataDir = await fs.mkdtemp(path.join(os.tmpdir(), 'gem-read-extension-'));
  const { server, url } = await startFixtureServer();
  let context: BrowserContext | undefined;

  try {
    context = await chromium.launchPersistentContext(userDataDir, {
      channel: 'chromium',
      headless: true,
      args: [
        `--disable-extensions-except=${extensionPath}`,
        `--load-extension=${extensionPath}`,
      ],
    });

    const worker = await getServiceWorker(context);
    const page = await context.newPage();
    await page.goto(url, { waitUntil: 'domcontentloaded' });
    await expect(page.locator('#target')).toContainText('Gem Read validates browser selection smoke tests');
    await selectFixtureText(page);

    await expect.poll(async () => {
      const response = await collectSelection(worker);
      return response.ok ? response.payload?.text ?? '' : '';
    }).toBe(expectedSelectionText);

    const response = await collectSelection(worker);
    expect(response).toMatchObject({
      ok: true,
      payload: {
        text: expectedSelectionText,
      },
    });

    await renderErrorOverlay(worker, response.payload?.text ?? expectedSelectionText);

    await expect.poll(async () => readShadowText(page, '.selection-box')).toBe(expectedSelectionText);
    await expect.poll(async () => readShadowText(page, '.error-box')).toBe('Playwright smoke stub');
  } finally {
    await context?.close();
    await closeServer(server);
    await fs.rm(userDataDir, { recursive: true, force: true });
  }
});