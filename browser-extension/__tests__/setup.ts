import { afterEach, beforeEach, vi } from 'vitest';

import { createChromeMock } from './mocks/chrome';

beforeEach(() => {
  vi.restoreAllMocks();
  document.head.innerHTML = '';
  document.body.innerHTML = '';
  document.title = '';
  vi.stubGlobal('chrome', createChromeMock());
  window.history.replaceState({}, '', 'http://localhost:3000/');
  Object.defineProperty(window, 'innerWidth', {
    configurable: true,
    value: 1280,
  });
  Object.defineProperty(window, 'innerHeight', {
    configurable: true,
    value: 720,
  });
  Object.defineProperty(window, 'devicePixelRatio', {
    configurable: true,
    value: 2,
  });
});

afterEach(() => {
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
  document.head.innerHTML = '';
  document.body.innerHTML = '';
  document.title = '';
  window.history.replaceState({}, '', 'http://localhost:3000/');
});