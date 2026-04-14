from django.core.management.base import BaseCommand, CommandError

from apps.ai_support.catalog import get_model_catalog_service


class Command(BaseCommand):
    help = "Обновляет каталог моделей OpenRouter и сохраняет три активные роли: fast / balanced / strong."

    def handle(self, *args, **options):
        try:
            options_list = get_model_catalog_service().refresh_catalog()
        except Exception as exc:  # noqa: BLE001
            raise CommandError(str(exc)) from exc

        if not options_list:
            self.stdout.write(self.style.WARNING("Каталог обновлен, но подходящие модели не были выбраны."))
            return

        self.stdout.write(self.style.SUCCESS("Каталог AI-моделей обновлен."))
        for option in options_list:
            self.stdout.write(f"- {option.role_type}: {option.display_name} ({option.external_model_id})")
