from django.urls import path

from apps.ai_support.views import advice_panel

app_name = "ai_support"

urlpatterns = [
    path("advice/", advice_panel, name="advice"),
]
