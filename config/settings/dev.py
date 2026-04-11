from .base import *  # noqa: F403,F401

DEBUG = True

EMAIL_BACKEND = env(  # type: ignore[name-defined]  # noqa: F405
    "EMAIL_BACKEND",
    "django.core.mail.backends.console.EmailBackend",
)
