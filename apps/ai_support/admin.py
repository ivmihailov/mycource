from django.contrib import admin

from apps.ai_support.models import AIInteractionLog, AIModelOption, AIUserPreference


@admin.register(AIModelOption)
class AIModelOptionAdmin(admin.ModelAdmin):
    list_display = ("role_type", "display_name", "external_model_id", "is_active", "supports_structured_output", "updated_at")
    list_filter = ("role_type", "is_active", "supports_structured_output")
    search_fields = ("display_name", "external_model_id")


@admin.register(AIUserPreference)
class AIUserPreferenceAdmin(admin.ModelAdmin):
    list_display = ("user", "selected_role_type", "selected_model_option", "updated_at")
    search_fields = ("user__username", "user__email", "selected_model_option__display_name")
    list_select_related = ("user", "selected_model_option")


@admin.register(AIInteractionLog)
class AIInteractionLogAdmin(admin.ModelAdmin):
    list_display = ("user", "action_type", "status", "selected_model", "course", "lesson", "created_at")
    list_filter = ("action_type", "status", "selected_model")
    search_fields = ("user__username", "course__title", "lesson__title", "selected_model_label", "error_message")
    list_select_related = ("user", "course", "lesson", "selected_model")
