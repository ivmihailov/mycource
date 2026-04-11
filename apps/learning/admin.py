from django.contrib import admin

from apps.learning.models import CourseProgress, LessonProgress


@admin.register(CourseProgress)
class CourseProgressAdmin(admin.ModelAdmin):
    list_display = ("user", "course", "status", "progress_percent", "started_at", "completed_at")
    list_filter = ("status",)
    search_fields = ("user__username", "course__title")


@admin.register(LessonProgress)
class LessonProgressAdmin(admin.ModelAdmin):
    list_display = ("user", "lesson", "status", "best_score", "completed_manually")
    list_filter = ("status", "completed_manually")
    search_fields = ("user__username", "lesson__title")

# Register your models here.
