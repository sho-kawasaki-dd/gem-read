class MissingModelError(ValueError):
    """Raised when no Gemini model name can be resolved."""


class InvalidImagePayloadError(ValueError):
    """Raised when incoming image payloads cannot be decoded."""


class UnsupportedCacheModelError(ValueError):
    """Raised when a requested model cannot create Gemini explicit caches."""