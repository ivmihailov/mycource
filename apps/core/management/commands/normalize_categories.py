from django.core.management.base import BaseCommand

from apps.courses.services import normalize_categories


class Command(BaseCommand):
    help = "Нормализует категории курсов, скрывает отладочные записи и восстанавливает канонические slug."

    def handle(self, *args, **options):
        categories = normalize_categories()
        self.stdout.write(self.style.SUCCESS("Категории успешно нормализованы."))
        for category in categories.values():
            self.stdout.write(f"- {category.name} ({category.slug})")
