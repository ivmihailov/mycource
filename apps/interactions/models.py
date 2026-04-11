from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.core.models import SoftDeleteModel, TimeStampedModel


class CourseComment(SoftDeleteModel):
    course = models.ForeignKey(
        "courses.Course",
        on_delete=models.CASCADE,
        related_name="comments",
        verbose_name=_("Курс"),
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="course_comments",
        verbose_name=_("Автор"),
    )
    body = models.TextField(_("Комментарий"))

    class Meta:
        verbose_name = _("Комментарий к курсу")
        verbose_name_plural = _("Комментарии к курсам")
        ordering = ("-created_at",)


class CourseReview(TimeStampedModel):
    course = models.ForeignKey(
        "courses.Course",
        on_delete=models.CASCADE,
        related_name="reviews",
        verbose_name=_("Курс"),
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="course_reviews",
        verbose_name=_("Автор"),
    )
    rating = models.PositiveSmallIntegerField(
        _("Оценка"),
        validators=[MinValueValidator(1), MaxValueValidator(5)],
    )
    body = models.TextField(_("Отзыв"), blank=True)

    class Meta:
        verbose_name = _("Отзыв")
        verbose_name_plural = _("Отзывы")
        ordering = ("-updated_at",)
        constraints = [
            models.UniqueConstraint(fields=["course", "author"], name="unique_review_per_course_author"),
        ]

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        from apps.interactions.services import refresh_course_rating

        refresh_course_rating(self.course)

    def delete(self, using=None, keep_parents=False):
        course = self.course
        response = super().delete(using=using, keep_parents=keep_parents)
        from apps.interactions.services import refresh_course_rating

        refresh_course_rating(course)
        return response


class FavoriteCourse(TimeStampedModel):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="favorite_courses",
        verbose_name=_("Пользователь"),
    )
    course = models.ForeignKey(
        "courses.Course",
        on_delete=models.CASCADE,
        related_name="favorited_by",
        verbose_name=_("Курс"),
    )

    class Meta:
        verbose_name = _("Избранный курс")
        verbose_name_plural = _("Избранные курсы")
        constraints = [
            models.UniqueConstraint(fields=["user", "course"], name="unique_favorite_course"),
        ]
