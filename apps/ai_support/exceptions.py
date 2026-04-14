class AIError(Exception):
    """Базовая ошибка AI-слоя."""


class AIUnavailableError(AIError):
    """AI временно недоступен или не настроен."""


class AIProviderError(AIError):
    """Ошибка внешнего провайдера моделей."""


class AIValidationError(AIError):
    """Ошибка валидации ответа модели."""
