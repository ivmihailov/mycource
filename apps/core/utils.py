import secrets
from pathlib import Path

import bleach
import markdown
from django.utils.deconstruct import deconstructible
from django.utils.html import mark_safe
from django.utils.text import slugify

BLEACH_ALLOWED_TAGS = sorted(
    set(bleach.sanitizer.ALLOWED_TAGS).union(
        {
            "p",
            "pre",
            "code",
            "h1",
            "h2",
            "h3",
            "h4",
            "blockquote",
            "ul",
            "ol",
            "li",
            "hr",
            "br",
            "strong",
            "em",
        }
    )
)

BLEACH_ALLOWED_ATTRIBUTES = {
    "a": ["href", "title", "target", "rel"],
    "img": ["src", "alt", "title"],
}


def generate_unique_slug(instance, source_value, slug_field_name="slug", queryset=None):
    model_class = instance.__class__
    slug = slugify(source_value)[:200] or "item"
    candidate = slug

    if queryset is None:
        manager = getattr(model_class, "all_objects", model_class._default_manager)
        queryset = manager.all()

    if instance.pk:
        queryset = queryset.exclude(pk=instance.pk)

    counter = 2
    while queryset.filter(**{slug_field_name: candidate}).exists():
        candidate = f"{slug[:190]}-{counter}"
        counter += 1
    return candidate


def timezone_path():
    from django.utils import timezone

    now = timezone.localtime()
    return f"{now.year}/{now.month:02d}"


@deconstructible
class UploadToPath:
    def __init__(self, prefix):
        self.prefix = prefix

    def __call__(self, instance, filename):
        extension = Path(filename).suffix.lower()
        token = secrets.token_hex(8)
        return f"{self.prefix}/{timezone_path()}/{token}{extension}"


def upload_to_factory(prefix):
    return UploadToPath(prefix)


def render_markdown(markdown_text):
    if not markdown_text:
        return ""

    html = markdown.markdown(
        markdown_text,
        extensions=["extra", "sane_lists", "fenced_code", "tables"],
    )
    cleaned = bleach.clean(
        html,
        tags=BLEACH_ALLOWED_TAGS,
        attributes=BLEACH_ALLOWED_ATTRIBUTES,
        strip=True,
    )
    return mark_safe(cleaned)
