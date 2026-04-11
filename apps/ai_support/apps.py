from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class AiSupportConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.ai_support"
    label = "ai_support"
    verbose_name = _("ИИ-заглушки")
