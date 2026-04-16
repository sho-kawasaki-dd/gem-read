import type {
  AnalysisAction,
  ModelOption,
  SelectionCapturePayload,
} from '../../shared/contracts/messages';

export interface SelectionAnalysisSession {
  selection: SelectionCapturePayload;
  previewImageUrl: string;
  cropDurationMs: number;
  modelOptions: ModelOption[];
  lastAction: AnalysisAction;
  lastModelName?: string;
  lastCustomPrompt?: string;
}

// Session は tab 単位で保持し、overlay の再実行で selection/crop を取り直さないようにする。
const sessionStore = new Map<number, SelectionAnalysisSession>();

export function getAnalysisSession(
  tabId: number
): SelectionAnalysisSession | undefined {
  return sessionStore.get(tabId);
}

export function setAnalysisSession(
  tabId: number,
  session: SelectionAnalysisSession
): void {
  sessionStore.set(tabId, session);
}

export function clearAnalysisSession(tabId: number): void {
  sessionStore.delete(tabId);
}
