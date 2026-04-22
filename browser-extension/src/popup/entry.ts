import { renderPopup } from './ui/renderPopup';

/**
 * Popup runtime は Phase 1 では設定と疎通確認の起動だけを担う。
 * 操作面の本体は将来的に overlay 側へ寄せる前提なので、ここでは mount の入口だけ公開する。
 */
export function mountPopup(): void {
  // popup は開くたびに Document が作り直されるので、毎回 render から state を再構成する。
  void renderPopup(document);
}
