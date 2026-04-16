export function renderPopup(documentRef: Document): void {
  const appRoot = documentRef.getElementById('app');
  if (!appRoot) {
    return;
  }

  appRoot.innerHTML = `
    <h1>Gem Read</h1>
    <p>Browser extension runtime is loaded.</p>
  `;
}