from django.contrib.auth.models import AbstractUser
from django.db import models
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from apps.core.models import TimeStampedModel
from apps.core.utils import upload_to_factory
from apps.core.validators import image_extension_validator, validate_file_size


class User(AbstractUser, TimeStampedModel):
    email = models.EmailField(_("Email"), unique=True)
    avatar = models.ImageField(
        _("Аватар"),
        upload_to=upload_to_factory("avatars"),
        blank=True,
        null=True,
        validators=[validate_file_size, image_extension_validator],
    )
    bio = models.TextField(_("О себе"), blank=True)
    is_email_verified = models.BooleanField(_("Email подтвержден"), default=False)

    REQUIRED_FIELDS = ["email"]

    class Meta:
        verbose_name = _("Пользователь")
        verbose_name_plural = _("Пользователи")
        ordering = ("username",)

    def __str__(self):
        return self.username

    def get_display_name(self):
        return self.get_full_name() or self.username

    def get_absolute_url(self):
        return reverse("users:profile")
