"""アプリケーション全体のデフォルト設定値を定義するモジュール。

秘匿情報は含めず、レイアウトやデフォルト倍率など
コード上で共有するパラメータをここに集約する。
実行時に変更される設定は別途管理し、ここは初期値のみ扱う。
"""

# --- ウィンドウ ---
DEFAULT_WINDOW_WIDTH = 1280
DEFAULT_WINDOW_HEIGHT = 800
SPLITTER_RATIO = (70, 30)

# --- レンダリング ---
DEFAULT_DPI = 144

# --- ズーム ---
ZOOM_MIN = 0.25
ZOOM_MAX = 4.0
ZOOM_STEP = 0.25

# --- ドキュメント表示 ---
PAGE_GAP = 10               # ページ間の余白 (ピクセル)
VIEWPORT_BUFFER_PAGES = 2   # ビューポート前後に先読みするページ数

# --- 最近のファイル ---
MAX_RECENT_FILES = 10

# --- 環境変数名 ---
ENV_GEMINI_API_KEY = "GEMINI_API_KEY"
