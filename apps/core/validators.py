from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator
from django.utils.translation import gettext_lazy as _


def validate_file_size(uploaded_file):
    if uploaded_file.size > settings.MAX_UPLOAD_SIZE:
        raise ValidationError(
            _("Размер файла не должен превышать 5 МБ."),
            code="file_too_large",
        )


image_extension_validator = FileExtensionValidator(
    allowed_extensions=settings.IMAGE_EXTENSIONS,
    message=_("Разрешены только JPG, JPEG, PNG и WEBP."),
)

document_extension_validator = FileExtensionValidator(
    allowed_extensions=settings.DOCUMENT_EXTENSIONS,
    message=_("Разрешены только PDF-файлы."),
)
