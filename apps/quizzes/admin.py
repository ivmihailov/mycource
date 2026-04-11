from django.contrib import admin

from apps.quizzes.models import Quiz, QuizAnswer, QuizAttempt, QuizOption, QuizQuestion


class QuizOptionInline(admin.TabularInline):
    model = QuizOption
    extra = 0


class QuizQuestionInline(admin.StackedInline):
    model = QuizQuestion
    extra = 0


@admin.register(Quiz)
class QuizAdmin(admin.ModelAdmin):
    list_display = ("title", "lesson_block", "passing_score", "max_score", "is_deleted")
    search_fields = ("title", "lesson_block__lesson__title")
    list_filter = ("is_deleted",)


@admin.register(QuizQuestion)
class QuizQuestionAdmin(admin.ModelAdmin):
    list_display = ("text", "quiz", "question_type", "score", "position")
    list_filter = ("question_type",)
    search_fields = ("text", "quiz__title")
    inlines = [QuizOptionInline]


@admin.register(QuizAttempt)
class QuizAttemptAdmin(admin.ModelAdmin):
    list_display = ("user", "quiz", "score", "passed", "started_at", "submitted_at")
    list_filter = ("passed", "started_at")
    search_fields = ("user__username", "quiz__title")


@admin.register(QuizAnswer)
class QuizAnswerAdmin(admin.ModelAdmin):
    list_display = ("attempt", "question", "is_correct", "awarded_score")
    list_filter = ("is_correct",)

# Register your models here.
