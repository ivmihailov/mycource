from django.db import migrations


CANONICAL_CATEGORY_DEFINITIONS = (
    (
        "Программирование",
        "programming",
        "Курсы по языкам программирования, базовым инженерным практикам и прикладной разработке.",
    ),
    (
        "Сети",
        "networks",
        "Курсы по интернету, сетевой архитектуре, протоколам и веб-инфраструктуре.",
    ),
    (
        "UI/UX",
        "ui-ux",
        "Курсы по проектированию интерфейсов, пользовательским сценариям и визуальной структуре продукта.",
    ),
    (
        "Базы данных",
        "databases",
        "Курсы по SQL, хранению данных и работе с табличными структурами.",
    ),
)

LEGACY_CATEGORY_MAP = {
    "Сети и веб": "Сети",
    "UX и дизайн": "UI/UX",
    "Аналитика": "Базы данных",
}

DEBUG_PREFIXES = (
    "Bug Category",
    "Manual Category Fix",
)


def forwards(apps, schema_editor):
    Category = apps.get_model("courses", "Category")
    Course = apps.get_model("courses", "Course")

    categories_by_name = {}

    for name, slug, description in CANONICAL_CATEGORY_DEFINITIONS:
        category = Category.objects.filter(name=name).first() or Category.objects.filter(slug=slug).first()
        if category is None:
            category = Category.objects.create(
                name=name,
                slug=slug,
                description=description,
                is_active=True,
            )
        else:
            category.name = name
            category.slug = slug
            category.description = description
            category.is_active = True
            category.save()
        categories_by_name[name] = category

    fallback_category = categories_by_name["Программирование"]

    for legacy_name, canonical_name in LEGACY_CATEGORY_MAP.items():
        legacy_category = Category.objects.filter(name=legacy_name).first()
        if not legacy_category:
            continue

        target_category = categories_by_name[canonical_name]
        if legacy_category.pk != target_category.pk:
            Course._base_manager.filter(category=legacy_category).update(category=target_category)
            legacy_category.is_active = False
            legacy_category.description = "Скрытая устаревшая категория после нормализации справочника."
            legacy_category.save()

    for category in Category.objects.all():
        if any(category.name.startswith(prefix) for prefix in DEBUG_PREFIXES):
            if Course._base_manager.filter(category=category).exists():
                Course._base_manager.filter(category=category).update(category=fallback_category)
            category.is_active = False
            category.description = "Скрытая отладочная категория."
            category.save()


class Migration(migrations.Migration):
    dependencies = [
        ("courses", "0002_initial"),
    ]

    operations = [
        migrations.RunPython(forwards, migrations.RunPython.noop),
    ]
