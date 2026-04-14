from django.conf import settings
from django.db.utils import OperationalError, ProgrammingError

from apps.ai_support.services import AIModelSelectionService


def site_meta(request):
    context = {
        "site_name": settings.SITE_NAME,
        "ai_enabled": settings.AI_ENABLED,
        "ai_model_options": [],
        "ai_selected_role": None,
        "ai_selected_model": None,
    }
    try:
        selection_service = AIModelSelectionService()
        context["ai_model_options"] = selection_service.get_options(auto_refresh=settings.AI_AUTO_REFRESH_MODELS)
        context["ai_selected_role"] = selection_service.get_selected_role(request)
        context["ai_selected_model"] = selection_service.get_selected_model(request)
    except (OperationalError, ProgrammingError):
        # Во время первых миграций таблицы AI-настроек могут еще не существовать.
        return context
    except Exception:
        return context
    return context
