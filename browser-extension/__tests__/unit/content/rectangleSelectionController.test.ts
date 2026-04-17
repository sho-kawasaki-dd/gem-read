import { describe, expect, it } from 'vitest';

import { startRectangleSelection } from '../../../src/content/selection/rectangleSelectionController';

describe('rectangleSelectionController', () => {
  it('mounts the rectangle overlay above the main overlay host', async () => {
    const mainOverlayHost = document.createElement('div');
    mainOverlayHost.id = 'gem-read-phase0-overlay-host';
    mainOverlayHost.style.position = 'fixed';
    mainOverlayHost.style.zIndex = '2147483647';
    document.documentElement.appendChild(mainOverlayHost);

    const selectionPromise = startRectangleSelection('overlay');

    const rectangleHost = document.getElementById('gem-read-phase2-rectangle-overlay');
    expect(rectangleHost).not.toBeNull();
    expect(rectangleHost?.style.zIndex).toBe('2147483647');
    expect(mainOverlayHost.compareDocumentPosition(rectangleHost as Node)).toBe(
      Node.DOCUMENT_POSITION_FOLLOWING
    );

    window.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape' }));
    const result = await selectionPromise;

    expect(result).toEqual({
      ok: false,
      error: 'Rectangle selection was cancelled.',
    });
    expect(document.getElementById('gem-read-phase2-rectangle-overlay')).toBeNull();
  });
});import { describe, expect, it } from 'vitest';

import {
  isRectangleSelectionActive,
  startRectangleSelection,
} from '../../../src/content/selection/rectangleSelectionController';

describe('rectangleSelectionController', () => {
  it('captures a viewport rectangle and returns an image-only selection payload', async () => {
    const promise = startRectangleSelection('overlay');

    const host = document.getElementById('gem-read-phase2-rectangle-overlay');
    if (!host) {
      throw new Error('Rectangle overlay host was not rendered.');
    }

    host.dispatchEvent(
      new MouseEvent('mousedown', {
        bubbles: true,
        button: 0,
        clientX: 10,
        clientY: 20,
      })
    );
    window.dispatchEvent(
      new MouseEvent('mousemove', {
        bubbles: true,
        clientX: 60,
        clientY: 90,
      })
    );
    window.dispatchEvent(
      new MouseEvent('mouseup', {
        bubbles: true,
        clientX: 60,
        clientY: 90,
      })
    );

    const result = await promise;

    expect(result.ok).toBe(true);
    expect(result.payload?.text).toBe('');
    expect(result.payload?.rect).toEqual({
      left: 10,
      top: 20,
      width: 50,
      height: 70,
    });
    expect(isRectangleSelectionActive()).toBe(false);
  });

  it('cancels rectangle selection on Escape', async () => {
    const promise = startRectangleSelection('command');

    window.dispatchEvent(
      new KeyboardEvent('keydown', {
        key: 'Escape',
        bubbles: true,
      })
    );

    const result = await promise;

    expect(result).toEqual({
      ok: false,
      error: 'Rectangle selection was cancelled.',
    });
    expect(isRectangleSelectionActive()).toBe(false);
  });
});