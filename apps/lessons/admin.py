from django.contrib import admin

from apps.lessons.models import Lesson, LessonBlock, PracticeTask


@admin.register(Lesson)
class LessonAdmin(admin.ModelAdmin):
    list_display = ("title", "course", "position", "estimated_duration_minutes", "is_deleted")
    list_filter = ("course", "is_deleted")
    search_fields = ("title", "course__title")


@admin.register(LessonBlock)
class LessonBlockAdmin(admin.ModelAdmin):
    list_display = ("lesson", "block_type", "position", "is_required")
    list_filter = ("block_type", "is_required")
    search_fields = ("lesson__title", "title", "content_markdown")


@admin.register(PracticeTask)
class PracticeTaskAdmin(admin.ModelAdmin):
    list_display = ("title", "lesson", "language", "is_active", "is_placeholder")
    list_filter = ("language", "is_active", "is_placeholder")
    search_fields = ("title", "lesson__title")

# Register your models here.
