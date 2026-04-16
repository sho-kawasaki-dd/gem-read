/**
 * Popup entry は browser action から開かれた Document に UI を mount するだけに留める。
 * 表示ロジックを popup/ 配下へ隔離して、popup 自体の再設計をしやすくする。
 */
import { mountPopup } from './popup/entry';

mountPopup();
