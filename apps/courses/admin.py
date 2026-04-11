from django.contrib import admin, messages
from django.utils import timezone

from apps.courses.models import Category, Course, Tag


@admin.action(description="Опубликовать выбранные курсы")
def publish_courses(modeladmin, request, queryset):
    updated = queryset.update(status=Course.Status.PUBLISHED, published_at=timezone.now())
    modeladmin.message_user(request, f"Опубликовано курсов: {updated}", messages.SUCCESS)


@admin.action(description="Архивировать выбранные курсы")
def archive_courses(modeladmin, request, queryset):
    updated = queryset.update(status=Course.Status.ARCHIVED)
    modeladmin.message_user(request, f"Архивировано курсов: {updated}", messages.SUCCESS)


@admin.action(description="Мягко удалить выбранные курсы")
def soft_delete_courses(modeladmin, request, queryset):
    for course in queryset:
        course.soft_delete()
    modeladmin.message_user(request, "Выбранные курсы скрыты.", messages.SUCCESS)


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "is_active")
    list_filter = ("is_active",)
    search_fields = ("name", "description")
    prepopulated_fields = {"slug": ("name",)}


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "created_at")
    search_fields = ("name",)
    prepopulated_fields = {"slug": ("name",)}


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ("title", "author", "status", "level", "category", "average_rating", "reviews_count")
    list_filter = ("status", "level", "category")
    search_fields = ("title", "short_description", "author__username")
    readonly_fields = ("published_at", "view_count", "average_rating", "reviews_count", "created_at", "updated_at")
    actions = (publish_courses, archive_courses, soft_delete_courses)

# Register your models here.
