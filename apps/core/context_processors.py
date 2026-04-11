from django.conf import settings


def site_meta(request):
    return {
        "site_name": settings.SITE_NAME,
        "ai_enabled": settings.AI_ENABLED,
    }
