class MissingModelError(ValueError):
    """Raised when no Gemini model name can be resolved."""


class InvalidImagePayloadError(ValueError):
    """Raised when incoming image payloads cannot be decoded."""