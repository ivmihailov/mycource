from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.core.models import SoftDeleteModel, TimeStampedModel


class Quiz(SoftDeleteModel):
    lesson_block = models.OneToOneField(
        "lessons.LessonBlock",
        on_delete=models.CASCADE,
        related_name="quiz",
        verbose_name=_("Блок урока"),
    )
    title = models.CharField(_("Название"), max_length=255)
    description = models.TextField(_("Описание"), blank=True)
    passing_score = models.PositiveIntegerField(_("Проходной балл"), null=True, blank=True)
    max_score = models.PositiveIntegerField(_("Максимальный балл"), default=0)
    is_ai_draft = models.BooleanField(_("AI-черновик"), default=False)

    class Meta:
        verbose_name = _("Тест")
        verbose_name_plural = _("Тесты")
        ordering = ("created_at",)

    def __str__(self):
        return self.title

    def update_max_score(self):
        self.max_score = self.questions.aggregate(models.Sum("score"))["score__sum"] or 0
        self.save(update_fields=["max_score", "updated_at"])

    @property
    def effective_passing_score(self):
        return self.passing_score if self.passing_score is not None else self.max_score


class QuizQuestion(TimeStampedModel):
    class QuestionType(models.TextChoices):
        SINGLE = "single_choice", _("Один правильный")
        MULTIPLE = "multiple_choice", _("Несколько правильных")
        TRUE_FALSE = "true_false", _("True / False")

    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name="questions", verbose_name=_("Тест"))
    question_type = models.CharField(_("Тип вопроса"), max_length=32, choices=QuestionType.choices)
    text = models.TextField(_("Текст вопроса"))
    position = models.PositiveIntegerField(_("Позиция"), default=1)
    score = models.PositiveIntegerField(_("Баллы"), default=1, validators=[MinValueValidator(1), MaxValueValidator(100)])
    explanation = models.TextField(_("Пояснение"), blank=True)

    class Meta:
        verbose_name = _("Вопрос")
        verbose_name_plural = _("Вопросы")
        ordering = ("position", "id")

    def __str__(self):
        return self.text[:80]

    def save(self, *args, **kwargs):
        if not self.position:
            last_position = self.quiz.questions.aggregate(models.Max("position"))["position__max"] or 0
            self.position = last_position + 1
        super().save(*args, **kwargs)
        self.quiz.update_max_score()

    def delete(self, using=None, keep_parents=False):
        quiz = self.quiz
        response = super().delete(using=using, keep_parents=keep_parents)
        quiz.update_max_score()
        return response


class QuizOption(TimeStampedModel):
    question = models.ForeignKey(
        QuizQuestion,
        on_delete=models.CASCADE,
        related_name="options",
        verbose_name=_("Вопрос"),
    )
    text = models.CharField(_("Текст варианта"), max_length=255)
    is_correct = models.BooleanField(_("Правильный"), default=False)
    position = models.PositiveIntegerField(_("Позиция"), default=1)

    class Meta:
        verbose_name = _("Вариант ответа")
        verbose_name_plural = _("Варианты ответов")
        ordering = ("position", "id")

    def __str__(self):
        return self.text

    def save(self, *args, **kwargs):
        if not self.position:
            last_position = self.question.options.aggregate(models.Max("position"))["position__max"] or 0
            self.position = last_position + 1
        super().save(*args, **kwargs)


class QuizAttempt(TimeStampedModel):
    user = models.ForeignKey("users.User", on_delete=models.CASCADE, related_name="quiz_attempts", verbose_name=_("Пользователь"))
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name="attempts", verbose_name=_("Тест"))
    started_at = models.DateTimeField(_("Начато"), auto_now_add=True)
    submitted_at = models.DateTimeField(_("Отправлено"), null=True, blank=True)
    score = models.PositiveIntegerField(_("Балл"), default=0)
    passed = models.BooleanField(_("Пройден"), default=False)

    class Meta:
        verbose_name = _("Попытка теста")
        verbose_name_plural = _("Попытки тестов")
        ordering = ("-started_at",)


class QuizAnswer(TimeStampedModel):
    attempt = models.ForeignKey(QuizAttempt, on_delete=models.CASCADE, related_name="answers", verbose_name=_("Попытка"))
    question = models.ForeignKey(QuizQuestion, on_delete=models.CASCADE, related_name="answers", verbose_name=_("Вопрос"))
    selected_options = models.ManyToManyField(QuizOption, blank=True, related_name="answers", verbose_name=_("Выбранные варианты"))
    is_correct = models.BooleanField(_("Правильный ответ"), default=False)
    awarded_score = models.PositiveIntegerField(_("Начислено баллов"), default=0)

    class Meta:
        verbose_name = _("Ответ пользователя")
        verbose_name_plural = _("Ответы пользователей")
