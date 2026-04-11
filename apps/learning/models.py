from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.core.models import TimeStampedModel


class CourseProgress(TimeStampedModel):
    class Status(models.TextChoices):
        NOT_STARTED = "not_started", _("Не начат")
        IN_PROGRESS = "in_progress", _("В процессе")
        COMPLETED = "completed", _("Завершен")

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="course_progress_entries",
        verbose_name=_("Пользователь"),
    )
    course = models.ForeignKey(
        "courses.Course",
        on_delete=models.CASCADE,
        related_name="progress_entries",
        verbose_name=_("Курс"),
    )
    started_at = models.DateTimeField(_("Начат"), null=True, blank=True)
    completed_at = models.DateTimeField(_("Завершен"), null=True, blank=True)
    status = models.CharField(_("Статус"), max_length=20, choices=Status.choices, default=Status.NOT_STARTED)
    last_opened_lesson = models.ForeignKey(
        "lessons.Lesson",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
        verbose_name=_("Последний открытый урок"),
    )
    progress_percent = models.PositiveIntegerField(_("Прогресс, %"), default=0)

    class Meta:
        verbose_name = _("Прогресс курса")
        verbose_name_plural = _("Прогресс курсов")
        constraints = [
            models.UniqueConstraint(fields=["user", "course"], name="unique_course_progress"),
        ]


class LessonProgress(TimeStampedModel):
    class Status(models.TextChoices):
        NOT_STARTED = "not_started", _("Не начат")
        IN_PROGRESS = "in_progress", _("В процессе")
        COMPLETED = "completed", _("Завершен")

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="lesson_progress_entries",
        verbose_name=_("Пользователь"),
    )
    lesson = models.ForeignKey(
        "lessons.Lesson",
        on_delete=models.CASCADE,
        related_name="progress_entries",
        verbose_name=_("Урок"),
    )
    started_at = models.DateTimeField(_("Начат"), null=True, blank=True)
    completed_at = models.DateTimeField(_("Завершен"), null=True, blank=True)
    status = models.CharField(_("Статус"), max_length=20, choices=Status.choices, default=Status.NOT_STARTED)
    completed_manually = models.BooleanField(_("Завершен вручную"), default=False)
    best_score = models.PositiveIntegerField(_("Лучший балл"), default=0)

    class Meta:
        verbose_name = _("Прогресс урока")
        verbose_name_plural = _("Прогресс уроков")
        constraints = [
            models.UniqueConstraint(fields=["user", "lesson"], name="unique_lesson_progress"),
        ]
