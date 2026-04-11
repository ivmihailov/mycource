from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import render
from django.utils.decorators import method_decorator
from django.views.generic import TemplateView


class HomePageView(TemplateView):
    template_name = "core/home.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        from apps.courses.models import Category, Course
        from apps.interactions.models import FavoriteCourse
        from apps.learning.models import CourseProgress

        published_courses = Course.objects.filter(status=Course.Status.PUBLISHED).select_related("author", "category")
        context["new_courses"] = published_courses.order_by("-published_at", "-created_at")[:3]
        context["popular_courses"] = published_courses.order_by("-view_count", "-published_at")[:3]
        context["categories"] = Category.objects.for_ui()[:6]
        if self.request.user.is_authenticated:
            context["active_courses"] = CourseProgress.objects.filter(
                user=self.request.user,
                status=CourseProgress.Status.IN_PROGRESS,
            ).select_related("course")[:3]
            context["favorite_courses"] = FavoriteCourse.objects.filter(user=self.request.user).select_related("course")[:3]
        return context


class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = "core/dashboard.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        from apps.courses.models import Course
        from apps.interactions.models import FavoriteCourse
        from apps.learning.models import CourseProgress

        context["my_courses_count"] = Course.all_objects.filter(author=self.request.user, is_deleted=False).count()
        context["drafts_count"] = Course.all_objects.filter(
            author=self.request.user,
            status=Course.Status.DRAFT,
            is_deleted=False,
        ).count()
        context["active_learning_count"] = CourseProgress.objects.filter(
            user=self.request.user,
            status=CourseProgress.Status.IN_PROGRESS,
        ).count()
        context["favorites_count"] = FavoriteCourse.objects.filter(user=self.request.user).count()
        return context


@method_decorator(staff_member_required, name="dispatch")
class StaffStatsView(TemplateView):
    template_name = "core/staff_stats.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        from apps.courses.models import Course
        from apps.interactions.models import CourseComment, CourseReview
        from apps.learning.models import CourseProgress
        from apps.users.models import User

        context["stats"] = {
            "users": User.objects.count(),
            "courses": Course.all_objects.count(),
            "published_courses": Course.objects.filter(status=Course.Status.PUBLISHED).count(),
            "course_progress": CourseProgress.objects.count(),
            "comments": CourseComment.all_objects.count(),
            "reviews": CourseReview.objects.count(),
        }
        return context


def custom_page_not_found(request, exception):
    return render(request, "core/404.html", status=404)


def custom_server_error(request):
    return render(request, "core/500.html", status=500)
