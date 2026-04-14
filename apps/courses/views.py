from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import F
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect
from django.views import View
from django.views.generic import CreateView, DetailView, ListView, TemplateView, UpdateView

from apps.ai_support.forms import AIQuestionForm
from apps.core.mixins import OwnerOrStaffRequiredMixin
from apps.courses.forms import CourseFilterForm, CourseForm
from apps.courses.models import Category, Course
from apps.courses.services import duplicate_course
from apps.interactions.forms import CourseCommentForm, CourseReviewForm
from apps.interactions.models import FavoriteCourse
from apps.learning.models import CourseProgress

User = get_user_model()


def get_visible_course(user, slug):
    queryset = (
        Course.all_objects.visible_for_user(user)
        .select_related("author", "category")
        .prefetch_related("tags", "lessons")
    )
    return get_object_or_404(queryset, slug=slug)


class CourseCatalogView(ListView):
    model = Course
    template_name = "courses/catalog.html"
    context_object_name = "courses"
    paginate_by = 12

    def get_queryset(self):
        queryset = (
            Course.objects.filter(status=Course.Status.PUBLISHED)
            .select_related("author", "category")
            .prefetch_related("tags")
        )
        self.filter_form = CourseFilterForm(self.request.GET or None)
        return self.filter_form.filter_queryset(queryset)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["filter_form"] = self.filter_form
        return context


class CourseDetailView(DetailView):
    model = Course
    template_name = "courses/detail.html"
    context_object_name = "course"

    def get_object(self, queryset=None):
        course = get_visible_course(self.request.user, self.kwargs["slug"])
        if course.status == Course.Status.PUBLISHED:
            Course.all_objects.filter(pk=course.pk).update(view_count=F("view_count") + 1)
            course.refresh_from_db(fields=["view_count"])
        return course

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        course = self.object
        context["comment_form"] = CourseCommentForm()
        review = None
        is_favorite = False

        if self.request.user.is_authenticated:
            review = course.reviews.filter(author=self.request.user).first()
            is_favorite = FavoriteCourse.objects.filter(user=self.request.user, course=course).exists()
            context["course_progress"] = CourseProgress.objects.filter(user=self.request.user, course=course).first()

        context["review_form"] = CourseReviewForm(instance=review)
        context["comments"] = course.comments.select_related("author").order_by("-created_at")
        context["reviews"] = course.reviews.select_related("author").order_by("-updated_at")
        context["is_favorite"] = is_favorite
        context["ai_question_form"] = AIQuestionForm()
        context["can_edit"] = self.request.user.is_authenticated and (
            self.request.user.is_staff or course.author == self.request.user
        )
        return context


class CourseAuthorView(ListView):
    model = Course
    template_name = "courses/author_detail.html"
    context_object_name = "courses"
    paginate_by = 12

    def get_queryset(self):
        self.author = get_object_or_404(User, username=self.kwargs["username"])
        return (
            Course.objects.filter(author=self.author, status=Course.Status.PUBLISHED)
            .select_related("author", "category")
            .prefetch_related("tags")
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["author_profile"] = self.author
        return context


class MyCoursesListView(LoginRequiredMixin, ListView):
    template_name = "courses/my_courses.html"
    context_object_name = "courses"

    def get_queryset(self):
        return (
            Course.all_objects.filter(author=self.request.user, is_deleted=False)
            .exclude(status=Course.Status.DRAFT)
            .select_related("author", "category")
        )


class DraftCourseListView(LoginRequiredMixin, ListView):
    template_name = "courses/drafts.html"
    context_object_name = "courses"

    def get_queryset(self):
        return Course.all_objects.filter(
            author=self.request.user,
            status=Course.Status.DRAFT,
            is_deleted=False,
        ).select_related("author", "category")


class CourseCreateView(LoginRequiredMixin, CreateView):
    model = Course
    form_class = CourseForm
    template_name = "courses/form.html"

    def form_valid(self, form):
        form.instance.author = self.request.user
        messages.success(self.request, "Курс создан как черновик.")
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["course"] = None
        context["lessons"] = []
        return context

    def get_success_url(self):
        return redirect("courses:update", slug=self.object.slug).url


class CourseUpdateView(OwnerOrStaffRequiredMixin, UpdateView):
    model = Course
    form_class = CourseForm
    template_name = "courses/form.html"
    slug_field = "slug"
    slug_url_kwarg = "slug"

    def get_queryset(self):
        return Course.all_objects.filter(is_deleted=False).select_related("author")

    def form_valid(self, form):
        messages.success(self.request, "Курс обновлен.")
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["course"] = self.object
        context["lessons"] = self.object.lessons.filter(is_deleted=False).order_by("position", "id")
        return context


class CoursePreviewView(OwnerOrStaffRequiredMixin, DetailView):
    model = Course
    template_name = "courses/detail.html"
    context_object_name = "course"
    slug_field = "slug"
    slug_url_kwarg = "slug"

    def get_queryset(self):
        return Course.all_objects.select_related("author", "category").prefetch_related("tags", "lessons")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["preview_mode"] = True
        context["comments"] = []
        context["reviews"] = []
        context["comment_form"] = CourseCommentForm()
        context["review_form"] = CourseReviewForm()
        context["is_favorite"] = False
        context["ai_question_form"] = AIQuestionForm()
        context["can_edit"] = True
        return context


class CourseActionMixin(LoginRequiredMixin, View):
    success_message = ""

    def get_course(self):
        course = get_object_or_404(Course.all_objects.select_related("author"), slug=self.kwargs["slug"])
        if not (self.request.user.is_staff or course.author == self.request.user):
            raise Http404
        return course

    def post(self, request, *args, **kwargs):
        course = self.get_course()
        response = self.handle(course)
        if self.success_message:
            messages.success(request, self.success_message)
        return response


class CoursePublishView(CourseActionMixin):
    success_message = "Курс опубликован."

    def handle(self, course):
        course.publish()
        return redirect(course.get_absolute_url())


class CourseArchiveView(CourseActionMixin):
    success_message = "Курс перемещен в архив."

    def handle(self, course):
        course.archive()
        return redirect("courses:my_courses")


class CourseDeleteView(CourseActionMixin):
    success_message = "Курс скрыт из интерфейса."

    def handle(self, course):
        course.soft_delete()
        return redirect("courses:my_courses")


class CourseDuplicateView(CourseActionMixin):
    success_message = "Курс продублирован."

    def handle(self, course):
        duplicated = duplicate_course(course, self.request.user)
        return redirect("courses:update", slug=duplicated.slug)
