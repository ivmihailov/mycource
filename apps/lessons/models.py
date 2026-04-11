from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from apps.core.models import SoftDeleteModel, TimeStampedModel
from apps.core.utils import generate_unique_slug, upload_to_factory
from apps.core.validators import document_extension_validator, image_extension_validator, validate_file_size


class Lesson(SoftDeleteModel):
    course = models.ForeignKey(
        "courses.Course",
        on_delete=models.CASCADE,
        related_name="lessons",
        verbose_name=_("Курс"),
    )
    title = models.CharField(_("Название"), max_length=255)
    slug = models.SlugField(_("Slug"), max_length=255, blank=True)
    short_description = models.CharField(_("Краткое описание"), max_length=300, blank=True)
    position = models.PositiveIntegerField(_("Позиция"), default=1)
    estimated_duration_minutes = models.PositiveIntegerField(
        _("Оценочная длительность, мин."),
        default=15,
        validators=[MinValueValidator(1)],
    )

    class Meta:
        verbose_name = _("Урок")
        verbose_name_plural = _("Уроки")
        ordering = ("position", "id")
        constraints = [
            models.UniqueConstraint(fields=["course", "slug"], name="unique_lesson_slug_in_course"),
        ]

    def __str__(self):
        return f"{self.course.title}: {self.title}"

    def get_absolute_url(self):
        return reverse(
            "learning:lesson_detail",
            kwargs={"course_slug": self.course.slug, "lesson_slug": self.slug},
        )

    def get_builder_url(self):
        return reverse("lessons:builder", kwargs={"course_slug": self.course.slug, "slug": self.slug})

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = generate_unique_slug(
                self,
                self.title,
                queryset=self.course.lessons.all() if self.course_id else None,
            )
        if not self.position:
            last_position = self.course.lessons.aggregate(models.Max("position"))["position__max"] or 0
            self.position = last_position + 1
        super().save(*args, **kwargs)


class LessonBlock(TimeStampedModel):
    class BlockType(models.TextChoices):
        TEXT = "text", _("Текст")
        IMAGE = "image", _("Изображение")
        CODE = "code", _("Код")
        FILE = "file", _("Файл")
        QUOTE = "quote", _("Цитата/заметка")
        QUIZ = "quiz", _("Тест")

    class NoteStyle(models.TextChoices):
        NOTE = "note", _("Заметка")
        QUOTE = "quote", _("Цитата")

    lesson = models.ForeignKey(
        Lesson,
        on_delete=models.CASCADE,
        related_name="blocks",
        verbose_name=_("Урок"),
    )
    block_type = models.CharField(_("Тип блока"), max_length=20, choices=BlockType.choices)
    title = models.CharField(_("Заголовок"), max_length=255, blank=True)
    position = models.PositiveIntegerField(_("Позиция"), default=1)
    content_markdown = models.TextField(_("Markdown контент"), blank=True)
    image = models.ImageField(
        _("Изображение"),
        upload_to=upload_to_factory("lesson_images"),
        blank=True,
        null=True,
        validators=[validate_file_size, image_extension_validator],
    )
    file = models.FileField(
        _("Файл"),
        upload_to=upload_to_factory("lesson_files"),
        blank=True,
        null=True,
        validators=[validate_file_size, document_extension_validator],
    )
    code_language = models.CharField(_("Язык кода"), max_length=50, blank=True)
    code_content = models.TextField(_("Код"), blank=True)
    note_style = models.CharField(
        _("Стиль заметки"),
        max_length=20,
        choices=NoteStyle.choices,
        blank=True,
        default=NoteStyle.NOTE,
    )
    is_required = models.BooleanField(_("Обязательный блок"), default=True)

    class Meta:
        verbose_name = _("Блок урока")
        verbose_name_plural = _("Блоки уроков")
        ordering = ("position", "id")

    def __str__(self):
        return f"{self.lesson.title}: {self.get_block_type_display()}"

    def clean(self):
        if self.block_type in {self.BlockType.TEXT, self.BlockType.QUOTE} and not self.content_markdown:
            raise ValidationError(_("Для текстового блока нужен markdown-контент."))
        if self.block_type == self.BlockType.IMAGE and not self.image:
            raise ValidationError(_("Для блока изображения нужно загрузить файл."))
        if self.block_type == self.BlockType.FILE and not self.file:
            raise ValidationError(_("Для файлового блока нужно загрузить PDF."))
        if self.block_type == self.BlockType.CODE and not self.code_content:
            raise ValidationError(_("Для кодового блока нужно заполнить код."))

    def save(self, *args, **kwargs):
        if not self.position:
            last_position = self.lesson.blocks.aggregate(models.Max("position"))["position__max"] or 0
            self.position = last_position + 1
        super().save(*args, **kwargs)


class PracticeTask(TimeStampedModel):
    lesson = models.ForeignKey(
        Lesson,
        on_delete=models.CASCADE,
        related_name="practice_tasks",
        verbose_name=_("Урок"),
    )
    title = models.CharField(_("Название"), max_length=255)
    description_markdown = models.TextField(_("Описание"))
    language = models.CharField(_("Язык"), max_length=50, default="python")
    starter_code = models.TextField(_("Стартовый код"), blank=True)
    expected_output_description = models.TextField(_("Ожидаемый результат"), blank=True)
    is_active = models.BooleanField(_("Активно"), default=True)
    is_placeholder = models.BooleanField(_("Заглушка"), default=True)

    class Meta:
        verbose_name = _("Практическое задание")
        verbose_name_plural = _("Практические задания")
        ordering = ("id",)

    def __str__(self):
        return self.title
