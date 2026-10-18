"""MemoAi — AI Services package"""


class AIServiceError(RuntimeError):
    """Raised when an AI provider is unavailable or returns an unusable answer.

    MemoAI never substitutes fabricated ("mock") analysis: when the provider
    cannot answer, the caller surfaces a real error state instead.
    """
