from decimal import Decimal

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from apps.core.models import (
    ActiveObjectsManager,
    AllObjectsManager,
    SoftDeleteModel,
    SoftDeleteQuerySet,
    TimeStampedModel,
)
from apps.core.utils import generate_unique_slug, upload_to_factory
from apps.core.validators import image_extension_validator, validate_file_size


DEBUG_CATEGORY_PREFIXES = (
    "Bug Category",
    "Manual Category Fix",
)


class CategoryQuerySet(models.QuerySet):
    def active(self):
        return self.filter(is_active=True)

    def without_debug_categories(self):
        queryset = self
        for prefix in DEBUG_CATEGORY_PREFIXES:
            queryset = queryset.exclude(name__istartswith=prefix)
        return queryset

    def for_ui(self):
        return self.active().without_debug_categories()


class CategoryManager(models.Manager.from_queryset(CategoryQuerySet)):
    pass


class Category(TimeStampedModel):
    name = models.CharField(_("Название"), max_length=120, unique=True)
    slug = models.SlugField(_("Slug"), max_length=150, unique=True, blank=True)
    description = models.TextField(_("Описание"), blank=True)
    is_active = models.BooleanField(_("Активна"), default=True)

    objects = CategoryManager()

    class Meta:
        verbose_name = _("Категория")
        verbose_name_plural = _("Категории")
        ordering = ("name",)

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = generate_unique_slug(self, self.name)
        super().save(*args, **kwargs)


class Tag(TimeStampedModel):
    name = models.CharField(_("Название"), max_length=80, unique=True)
    slug = models.SlugField(_("Slug"), max_length=100, unique=True, blank=True)

    class Meta:
        verbose_name = _("Тег")
        verbose_name_plural = _("Теги")
        ordering = ("name",)

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = generate_unique_slug(self, self.name)
        super().save(*args, **kwargs)


class CourseQuerySet(SoftDeleteQuerySet):
    def published(self):
        return self.filter(status=Course.Status.PUBLISHED, is_deleted=False)

    def visible_for_user(self, user):
        queryset = self.filter(is_deleted=False)
        if user.is_authenticated and user.is_staff:
            return queryset
        if user.is_authenticated:
            return queryset.filter(models.Q(status=Course.Status.PUBLISHED) | models.Q(author=user))
        return queryset.filter(status=Course.Status.PUBLISHED)


class ActiveCourseManager(ActiveObjectsManager.from_queryset(CourseQuerySet)):
    pass


class AllCourseManager(AllObjectsManager.from_queryset(CourseQuerySet)):
    pass


class Course(SoftDeleteModel):
    class Status(models.TextChoices):
        DRAFT = "draft", _("Черновик")
        PUBLISHED = "published", _("Опубликован")
        ARCHIVED = "archived", _("Архив")

    class Level(models.TextChoices):
        BEGINNER = "beginner", _("Начальный")
        INTERMEDIATE = "intermediate", _("Средний")
        ADVANCED = "advanced", _("Продвинутый")

    class OrderMode(models.TextChoices):
        FREE = "free_order", _("Свободный порядок")
        SEQUENTIAL = "sequential_order", _("Последовательный порядок")

    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="courses",
        verbose_name=_("Автор"),
    )
    title = models.CharField(_("Название"), max_length=255)
    slug = models.SlugField(_("Slug"), max_length=255, unique=True, blank=True)
    short_description = models.CharField(_("Краткое описание"), max_length=300)
    full_description = models.TextField(_("Полное описание"))
    cover_image = models.ImageField(
        _("Обложка"),
        upload_to=upload_to_factory("course_covers"),
        blank=True,
        null=True,
        validators=[validate_file_size, image_extension_validator],
    )
    category = models.ForeignKey(
        Category,
        on_delete=models.PROTECT,
        related_name="courses",
        verbose_name=_("Категория"),
    )
    tags = models.ManyToManyField(Tag, blank=True, related_name="courses", verbose_name=_("Теги"))
    status = models.CharField(_("Статус"), max_length=20, choices=Status.choices, default=Status.DRAFT)
    level = models.CharField(_("Уровень"), max_length=20, choices=Level.choices, default=Level.BEGINNER)
    estimated_duration_minutes = models.PositiveIntegerField(
        _("Оценочная длительность, мин."),
        default=60,
        validators=[MinValueValidator(1)],
    )
    order_mode = models.CharField(
        _("Порядок прохождения"),
        max_length=32,
        choices=OrderMode.choices,
        default=OrderMode.FREE,
    )
    published_at = models.DateTimeField(_("Опубликовано"), null=True, blank=True)
    view_count = models.PositiveIntegerField(_("Просмотры"), default=0)
    average_rating = models.DecimalField(
        _("Средний рейтинг"),
        max_digits=3,
        decimal_places=2,
        default=Decimal("0.00"),
    )
    reviews_count = models.PositiveIntegerField(_("Количество отзывов"), default=0)

    objects = ActiveCourseManager()
    all_objects = AllCourseManager()

    class Meta:
        verbose_name = _("Курс")
        verbose_name_plural = _("Курсы")
        ordering = ("-published_at", "-created_at")
        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["slug"]),
            models.Index(fields=["author", "status"]),
            models.Index(fields=["category", "status"]),
        ]

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse("courses:detail", kwargs={"slug": self.slug})

    def get_preview_url(self):
        return reverse("courses:preview", kwargs={"slug": self.slug})

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = generate_unique_slug(self, self.title)
        super().save(*args, **kwargs)

    def publish(self):
        self.status = self.Status.PUBLISHED
        self.published_at = self.published_at or timezone.now()
        self.save(update_fields=["status", "published_at", "updated_at"])

    def archive(self):
        self.status = self.Status.ARCHIVED
        self.save(update_fields=["status", "updated_at"])

    @property
    def active_lessons(self):
        return self.lessons.filter(is_deleted=False).order_by("position", "id")
