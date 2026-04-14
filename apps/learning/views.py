from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect
from django.views import View
from django.views.generic import ListView, TemplateView

from apps.ai_support.forms import AIQuestionForm
from apps.courses.models import Course
from apps.interactions.models import FavoriteCourse
from apps.learning.models import CourseProgress, LessonProgress
from apps.learning.services import (
    get_accessible_lessons,
    get_next_lesson,
    mark_lesson_completed_manually,
    open_lesson,
    user_can_access_course,
    user_can_access_lesson,
)
from apps.lessons.models import Lesson


class LearningOverviewView(LoginRequiredMixin, TemplateView):
    template_name = "learning/overview.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["in_progress_courses"] = CourseProgress.objects.filter(
            user=self.request.user,
            status=CourseProgress.Status.IN_PROGRESS,
        ).select_related("course", "last_opened_lesson")
        context["completed_courses"] = CourseProgress.objects.filter(
            user=self.request.user,
            status=CourseProgress.Status.COMPLETED,
        ).select_related("course")
        context["favorite_courses"] = FavoriteCourse.objects.filter(user=self.request.user).select_related(
            "course",
            "course__author",
            "course__category",
        )
        return context


class FavoriteCoursesView(LoginRequiredMixin, ListView):
    template_name = "learning/favorites.html"
    context_object_name = "favorite_courses"

    def get_queryset(self):
        return FavoriteCourse.objects.filter(user=self.request.user).select_related("course", "course__author", "course__category")


class CourseStartView(LoginRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        course = get_object_or_404(Course.all_objects.select_related("author"), slug=kwargs["slug"])
        if not user_can_access_course(request.user, course):
            raise Http404

        lessons = get_accessible_lessons(request.user, course)
        if not lessons:
            messages.warning(request, "В этом курсе пока нет доступных уроков.")
            return redirect(course.get_absolute_url())

        progress = CourseProgress.objects.filter(user=request.user, course=course).first()
        target = lessons[0]
        if progress and progress.last_opened_lesson and any(item.pk == progress.last_opened_lesson_id for item in lessons):
            target = progress.last_opened_lesson
        return redirect(target.get_absolute_url())


class LessonDetailView(LoginRequiredMixin, TemplateView):
    template_name = "learning/lesson_detail.html"

    def dispatch(self, request, *args, **kwargs):
        self.course = get_object_or_404(Course.all_objects.select_related("author", "category"), slug=kwargs["course_slug"])
        self.lesson = get_object_or_404(
            Lesson.all_objects.select_related("course"),
            course=self.course,
            slug=kwargs["lesson_slug"],
            is_deleted=False,
        )
        if not user_can_access_course(request.user, self.course):
            raise Http404
        if not user_can_access_lesson(request.user, self.lesson):
            accessible = get_accessible_lessons(request.user, self.course)
            if accessible:
                messages.warning(request, "Следующий урок откроется после завершения предыдущего.")
                return redirect(accessible[-1].get_absolute_url())
            raise Http404
        open_lesson(request.user, self.lesson)
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        accessible_lessons = get_accessible_lessons(self.request.user, self.course)
        accessible_ids = {lesson.pk for lesson in accessible_lessons}
        lesson_progress = LessonProgress.objects.filter(user=self.request.user, lesson=self.lesson).first()
        course_progress = CourseProgress.objects.filter(user=self.request.user, course=self.course).first()
        completed_ids = set(
            LessonProgress.objects.filter(
                user=self.request.user,
                lesson__course=self.course,
                status=LessonProgress.Status.COMPLETED,
            ).values_list("lesson_id", flat=True)
        )
        quiz_blocks = self.lesson.blocks.filter(block_type="quiz").select_related("quiz")

        attempts_by_quiz = {
            block.quiz.pk: block.quiz.attempts.filter(user=self.request.user, submitted_at__isnull=False)[:5]
            for block in quiz_blocks
            if hasattr(block, "quiz")
        }

        context.update(
            {
                "course": self.course,
                "lesson": self.lesson,
                "sidebar_lessons": self.course.lessons.filter(is_deleted=False).order_by("position", "id"),
                "accessible_ids": accessible_ids,
                "completed_ids": completed_ids,
                "lesson_progress": lesson_progress,
                "course_progress": course_progress,
                "quiz_blocks": quiz_blocks,
                "attempts_by_quiz": attempts_by_quiz,
                "next_lesson": get_next_lesson(self.course, self.lesson),
                "practice_tasks": self.lesson.practice_tasks.filter(is_active=True),
                "ai_question_form": AIQuestionForm(),
            }
        )
        return context


class LessonCompleteView(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        lesson = get_object_or_404(
            Lesson.all_objects.select_related("course", "course__author"),
            course__slug=kwargs["course_slug"],
            slug=kwargs["lesson_slug"],
            is_deleted=False,
        )
        if not user_can_access_lesson(request.user, lesson):
            raise Http404
        progress = mark_lesson_completed_manually(request.user, lesson)
        if progress:
            messages.success(request, "Урок отмечен как завершенный.")
        else:
            messages.warning(request, "Этот урок завершается после успешного прохождения теста.")
        return redirect(lesson.get_absolute_url())
