/**
 * Background entry は service worker の bootstrap だけに責務を絞る。
 * 実装本体を entry.ts 配下へ寄せることで、Chrome lifecycle 依存と業務ロジックを分離する。
 */
import { registerBackgroundRuntime } from './background/entry';

registerBackgroundRuntime();
