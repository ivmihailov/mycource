from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.core.models import TimeStampedModel


class AIModelOption(TimeStampedModel):
    class RoleType(models.TextChoices):
        FAST = "fast", _("Быстрая")
        BALANCED = "balanced", _("Сбалансированная")
        STRONG = "strong", _("Сильная")

    provider_name = models.CharField(_("Провайдер"), max_length=50, default="openrouter")
    external_model_id = models.CharField(_("Внешний model id"), max_length=255)
    display_name = models.CharField(_("Отображаемое имя"), max_length=255)
    role_type = models.CharField(_("Роль"), max_length=20, choices=RoleType.choices)
    is_active = models.BooleanField(_("Активна"), default=True)
    context_window = models.PositiveIntegerField(_("Размер контекста"), default=0)
    supports_structured_output = models.BooleanField(_("Поддерживает structured output"), default=False)
    metadata_json = models.JSONField(_("Метаданные"), default=dict, blank=True)

    class Meta:
        verbose_name = _("AI-модель")
        verbose_name_plural = _("AI-модели")
        ordering = ("role_type", "display_name")
        constraints = [
            models.UniqueConstraint(
                fields=["provider_name", "external_model_id"],
                name="unique_ai_model_per_provider",
            ),
        ]

    def __str__(self):
        return f"{self.get_role_type_display()}: {self.display_name}"


class AIUserPreference(TimeStampedModel):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="ai_preference",
        verbose_name=_("Пользователь"),
    )
    selected_role_type = models.CharField(
        _("Выбранная роль модели"),
        max_length=20,
        choices=AIModelOption.RoleType.choices,
        default=AIModelOption.RoleType.BALANCED,
    )
    selected_model_option = models.ForeignKey(
        AIModelOption,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="user_preferences",
        verbose_name=_("Выбранная модель"),
    )

    class Meta:
        verbose_name = _("Настройка AI-пользователя")
        verbose_name_plural = _("Настройки AI-пользователей")

    def __str__(self):
        return f"{self.user} -> {self.get_selected_role_type_display()}"


class AIInteractionLog(TimeStampedModel):
    class ActionType(models.TextChoices):
        QNA = "qa", _("Вопрос по курсу")
        QUIZ_GENERATION = "quiz_generation", _("Генерация теста")
        MODEL_SELECTION = "model_selection", _("Выбор модели")

    class Status(models.TextChoices):
        SUCCESS = "success", _("Успешно")
        FAILED = "failed", _("Ошибка")

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="ai_logs",
        verbose_name=_("Пользователь"),
    )
    course = models.ForeignKey(
        "courses.Course",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="ai_logs",
        verbose_name=_("Курс"),
    )
    lesson = models.ForeignKey(
        "lessons.Lesson",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="ai_logs",
        verbose_name=_("Урок"),
    )
    action_type = models.CharField(_("Тип действия"), max_length=30, choices=ActionType.choices)
    selected_model = models.ForeignKey(
        AIModelOption,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="interaction_logs",
        verbose_name=_("Модель"),
    )
    selected_model_label = models.CharField(_("Снимок model id"), max_length=255, blank=True)
    status = models.CharField(_("Статус"), max_length=20, choices=Status.choices, default=Status.SUCCESS)
    error_message = models.TextField(_("Текст ошибки"), blank=True)

    class Meta:
        verbose_name = _("Лог AI-взаимодействия")
        verbose_name_plural = _("Логи AI-взаимодействий")
        ordering = ("-created_at",)

    def __str__(self):
        return f"{self.user} / {self.action_type} / {self.status}"
