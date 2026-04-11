from django.db import transaction

from apps.courses.models import Category, Course
from apps.core.utils import generate_unique_slug


CANONICAL_CATEGORY_DEFINITIONS = {
    "programming": {
        "name": "Программирование",
        "slug": "programming",
        "description": "Курсы по языкам программирования, базовым инженерным практикам и прикладной разработке.",
    },
    "networks": {
        "name": "Сети",
        "slug": "networks",
        "description": "Курсы по интернету, сетевой архитектуре, протоколам и веб-инфраструктуре.",
    },
    "ui_ux": {
        "name": "UI/UX",
        "slug": "ui-ux",
        "description": "Курсы по проектированию интерфейсов, пользовательским сценариям и визуальной структуре продукта.",
    },
    "databases": {
        "name": "Базы данных",
        "slug": "databases",
        "description": "Курсы по SQL, хранению данных и работе с табличными структурами.",
    },
}

LEGACY_CATEGORY_MAP = {
    "Сети и веб": "Сети",
    "UX и дизайн": "UI/UX",
    "Аналитика": "Базы данных",
}


@transaction.atomic
def normalize_categories():
    categories_by_name = {}

    for data in CANONICAL_CATEGORY_DEFINITIONS.values():
        category = Category.objects.filter(name=data["name"]).first() or Category.objects.filter(slug=data["slug"]).first()
        if category is None:
            category = Category.objects.create(
                name=data["name"],
                slug=data["slug"],
                description=data["description"],
                is_active=True,
            )
        else:
            category.name = data["name"]
            category.slug = data["slug"]
            category.description = data["description"]
            category.is_active = True
            category.save()
        categories_by_name[category.name] = category

    fallback_category = categories_by_name["Программирование"]

    for legacy_name, canonical_name in LEGACY_CATEGORY_MAP.items():
        legacy_category = Category.objects.filter(name=legacy_name).first()
        if not legacy_category:
            continue

        target_category = categories_by_name[canonical_name]
        if legacy_category.pk != target_category.pk:
            Course.all_objects.filter(category=legacy_category).update(category=target_category)
            legacy_category.is_active = False
            legacy_category.description = "Скрытая устаревшая категория после нормализации справочника."
            legacy_category.save()

    for category in Category.objects.all():
        if any(category.name.startswith(prefix) for prefix in ("Bug Category", "Manual Category Fix")):
            if Course.all_objects.filter(category=category).exists():
                Course.all_objects.filter(category=category).update(category=fallback_category)
            category.is_active = False
            category.description = "Скрытая отладочная категория."
            category.save()

    return categories_by_name


@transaction.atomic
def duplicate_course(course, author):
    from apps.lessons.services import duplicate_lesson

    copy = Course.all_objects.get(pk=course.pk)
    copy.pk = None
    copy.slug = generate_unique_slug(copy, f"{course.title} копия")
    copy.title = f"{course.title} (копия)"
    copy.status = Course.Status.DRAFT
    copy.published_at = None
    copy.view_count = 0
    copy.average_rating = 0
    copy.reviews_count = 0
    copy.author = author
    copy.save()
    copy.tags.set(course.tags.all())

    for lesson in course.lessons.filter(is_deleted=False).order_by("position", "id"):
        duplicate_lesson(lesson, copy)
    return copy
