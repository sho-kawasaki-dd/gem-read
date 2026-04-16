/**
 * Content script entry はページ注入時の起動点だけを担う。
 * DOM 操作や overlay 制御は content/ 以下に閉じ込め、entry を薄く保つ。
 */
import { registerContentRuntime } from './content/entry';

registerContentRuntime();
