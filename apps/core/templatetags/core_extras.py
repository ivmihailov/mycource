from django import template

from apps.core.utils import render_markdown

register = template.Library()


@register.filter
def markdownify(value):
    return render_markdown(value)


@register.filter
def filename(value):
    if not value:
        return ""
    return str(value).split("/")[-1]


@register.filter
def get_item(mapping, key):
    if not mapping:
        return []
    return mapping.get(key, [])


@register.filter
def widget_type(bound_field):
    return bound_field.field.widget.__class__.__name__


@register.filter
def course_illustration(course):
    title = (getattr(course, "title", "") or "").lower()
    slug = (getattr(course, "slug", "") or "").lower()
    category = getattr(getattr(course, "category", None), "name", "") or ""
    haystack = f"{title} {slug} {category}".lower()

    mapping = (
        (("internet", "dns", "http", "брауз", "сет", "web"), "images/illustrations/course-internet.svg"),
        (("python", "django", "код", "программ"), "images/illustrations/course-python.svg"),
        (("ux", "design", "дизайн", "интерфейс"), "images/illustrations/course-ux.svg"),
        (("sql", "аналит", "данн"), "images/illustrations/course-sql.svg"),
    )

    for keywords, asset in mapping:
        if any(keyword in haystack for keyword in keywords):
            return asset
    return "images/illustrations/course-web.svg"


@register.filter
def can_manage_course(user, course):
    if not getattr(user, "is_authenticated", False):
        return False
    return bool(user.is_staff or getattr(course, "author_id", None) == user.id)
