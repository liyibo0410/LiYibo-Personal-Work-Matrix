"""Exception types for the LLM gateway."""


class LLMNotConfiguredError(RuntimeError):
    """Raised when the gateway has no usable base_url / api_key / model."""


class LLMResponseError(RuntimeError):
    """Raised when the upstream LLM returns an error or unparseable response."""
