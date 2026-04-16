/**
 * 旧 entry から shared 契約へ移行しても import path を壊さないための re-export。
 * 実際の message contract 定義は shared/contracts/messages.ts に集約する。
 */
export * from './shared/config/phase0';
export * from './shared/contracts/messages';
