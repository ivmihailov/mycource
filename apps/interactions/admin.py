from django.contrib import admin

from apps.interactions.models import CourseComment, CourseReview, FavoriteCourse


@admin.register(CourseComment)
class CourseCommentAdmin(admin.ModelAdmin):
    list_display = ("course", "author", "created_at", "is_deleted")
    list_filter = ("is_deleted", "created_at")
    search_fields = ("course__title", "author__username", "body")


@admin.register(CourseReview)
class CourseReviewAdmin(admin.ModelAdmin):
    list_display = ("course", "author", "rating", "updated_at")
    list_filter = ("rating", "updated_at")
    search_fields = ("course__title", "author__username", "body")


@admin.register(FavoriteCourse)
class FavoriteCourseAdmin(admin.ModelAdmin):
    list_display = ("user", "course", "created_at")
    search_fields = ("user__username", "course__title")

# Register your models here.
