from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from apps.users.models import User


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (
        ("Дополнительно", {"fields": ("avatar", "bio", "is_email_verified", "created_at", "updated_at")}),
    )
    readonly_fields = ("created_at", "updated_at")
    list_display = (
        "username",
        "email",
        "first_name",
        "last_name",
        "is_staff",
        "is_active",
        "is_email_verified",
    )
    list_filter = ("is_staff", "is_superuser", "is_active", "is_email_verified")
    search_fields = ("username", "email", "first_name", "last_name")
