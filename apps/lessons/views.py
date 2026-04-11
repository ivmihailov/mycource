import json

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views import View
from django.views.generic import CreateView, DetailView, UpdateView

from apps.courses.models import Course
from apps.lessons.builder import build_lesson_builder_context, render_lesson_builder
from apps.lessons.forms import LessonBlockForm, LessonForm, PracticeTaskForm
from apps.lessons.models import Lesson, LessonBlock
from apps.lessons.services import duplicate_block, duplicate_lesson, insert_block, reindex_lesson_blocks
from apps.quizzes.models import Quiz


def is_htmx_request(request):
    return bool(getattr(request, "htmx", False) or request.headers.get("HX-Request") == "true")


def parse_int_or_none(value, *, default=None):
    if value in (None, ""):
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


class AuthorCourseMixin(LoginRequiredMixin):
    def dispatch(self, request, *args, **kwargs):
        self.course = get_object_or_404(Course.all_objects.select_related("author"), slug=kwargs["course_slug"])
        if not (request.user.is_staff or self.course.author == request.user):
            raise Http404
        return super().dispatch(request, *args, **kwargs)


class AuthorLessonMixin(LoginRequiredMixin):
    def dispatch(self, request, *args, **kwargs):
        self.lesson = get_object_or_404(
            Lesson.all_objects.select_related("course", "course__author"),
            course__slug=kwargs["course_slug"],
            slug=kwargs["slug"],
        )
        if not (request.user.is_staff or self.lesson.course.author == request.user):
            raise Http404
        return super().dispatch(request, *args, **kwargs)


class LessonCreateView(AuthorCourseMixin, CreateView):
    model = Lesson
    form_class = LessonForm
    template_name = "lessons/lesson_form.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["course"] = self.course
        context["lesson"] = None
        return context

    def form_valid(self, form):
        form.instance.course = self.course
        form.instance.position = (
            self.course.lessons.filter(is_deleted=False).order_by("-position").values_list("position", flat=True).first()
            or 0
        ) + 1
        messages.success(self.request, "Урок создан.")
        return super().form_valid(form)

    def get_success_url(self):
        return self.object.get_builder_url()


class LessonUpdateView(AuthorLessonMixin, UpdateView):
    model = Lesson
    form_class = LessonForm
    template_name = "lessons/lesson_form.html"
    slug_url_kwarg = "slug"
    slug_field = "slug"

    def get_queryset(self):
        return Lesson.all_objects.filter(course__slug=self.kwargs["course_slug"])

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        if self.request.POST.get("builder_mode") == "1":
            kwargs["prefix"] = "lesson"
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["course"] = self.object.course
        context["lesson"] = self.object
        return context

    def form_invalid(self, form):
        if self.request.POST.get("builder_mode") == "1" or is_htmx_request(self.request):
            return render_lesson_builder(self.request, self.object, lesson_form=form, status=422)
        return super().form_invalid(form)

    def form_valid(self, form):
        self.object = form.save()
        messages.success(self.request, "Урок обновлен.")
        if self.request.POST.get("builder_mode") == "1" or is_htmx_request(self.request):
            return render_lesson_builder(self.request, self.object)
        return redirect(self.get_success_url())

    def get_success_url(self):
        if self.request.POST.get("return_to") == "course":
            return redirect("courses:update", slug=self.object.course.slug).url
        return self.object.get_builder_url()


class LessonBuilderView(AuthorLessonMixin, DetailView):
    model = Lesson
    template_name = "lessons/builder.html"
    context_object_name = "lesson"
    slug_url_kwarg = "slug"
    slug_field = "slug"

    def get_queryset(self):
        return Lesson.all_objects.select_related("course").prefetch_related("blocks", "practice_tasks")

    def get_object(self, queryset=None):
        return self.lesson

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        add_after_id = parse_int_or_none(self.request.GET.get("add_after"), default=0)
        active_block_id = parse_int_or_none(self.request.GET.get("edit_block"))

        context.update(
            build_lesson_builder_context(
                self.object,
                add_after_id=add_after_id,
                add_block_type=self.request.GET.get("block_type") or LessonBlock.BlockType.TEXT,
                active_block_id=active_block_id,
            )
        )
        return context

    def render_to_response(self, context, **response_kwargs):
        if is_htmx_request(self.request) and self.request.GET.get("partial") == "shell":
            return render(self.request, "lessons/partials/builder_shell.html", context, **response_kwargs)
        return super().render_to_response(context, **response_kwargs)


class LessonDuplicateView(AuthorLessonMixin, View):
    def post(self, request, *args, **kwargs):
        duplicate = duplicate_lesson(self.lesson, self.lesson.course)
        messages.success(request, "Урок продублирован.")
        return redirect("lessons:builder", course_slug=self.lesson.course.slug, slug=duplicate.slug)


class LessonDeleteView(AuthorLessonMixin, View):
    def post(self, request, *args, **kwargs):
        self.lesson.soft_delete()
        messages.info(request, "Урок скрыт.")
        return redirect("courses:update", slug=self.lesson.course.slug)


class LessonSortView(AuthorCourseMixin, View):
    def post(self, request, *args, **kwargs):
        payload = json.loads(request.body or "{}")
        order = payload.get("order", [])
        lessons = {str(lesson.id): lesson for lesson in self.course.lessons.filter(is_deleted=False)}
        for index, lesson_id in enumerate(order, start=1):
            lesson = lessons.get(str(lesson_id))
            if lesson:
                lesson.position = index
                lesson.save(update_fields=["position", "updated_at"])
        return JsonResponse({"ok": True})


class BlockCreateView(AuthorLessonMixin, CreateView):
    model = LessonBlock
    form_class = LessonBlockForm
    template_name = "lessons/block_form.html"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        if self.request.POST.get("builder_mode") == "1":
            kwargs["prefix"] = "new-block"
        return kwargs

    def form_invalid(self, form):
        if self.request.POST.get("builder_mode") == "1" or is_htmx_request(self.request):
            add_after_id = parse_int_or_none(self.request.POST.get("after_id"), default=0)
            return render_lesson_builder(
                self.request,
                self.lesson,
                add_form=form,
                add_after_id=add_after_id,
                add_block_type=self.request.POST.get("new-block-block_type"),
                status=422,
            )
        return super().form_invalid(form)

    def form_valid(self, form):
        form.instance.lesson = self.lesson
        response_after_id = self.request.POST.get("after_id")
        block = form.save(commit=False)
        block.lesson = self.lesson
        block.position = 0
        insert_block(self.lesson, block, after_id=response_after_id)
        self.object = block
        if self.object.block_type == LessonBlock.BlockType.QUIZ and not hasattr(self.object, "quiz"):
            Quiz.objects.create(
                lesson_block=self.object,
                title=self.object.title or f"Тест к уроку «{self.lesson.title}»",
            )
        messages.success(self.request, "Блок добавлен.")
        if self.request.POST.get("builder_mode") == "1" or is_htmx_request(self.request):
            return render_lesson_builder(self.request, self.lesson, active_block_id=self.object.pk)
        return redirect(self.get_success_url())

    def get_success_url(self):
        return self.lesson.get_builder_url()


class BlockUpdateView(LoginRequiredMixin, UpdateView):
    model = LessonBlock
    form_class = LessonBlockForm
    template_name = "lessons/block_form.html"
    pk_url_kwarg = "pk"

    def dispatch(self, request, *args, **kwargs):
        self.object = self.get_object()
        if not (request.user.is_staff or self.object.lesson.course.author == request.user):
            raise Http404
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["allow_type_edit"] = False
        if self.request.POST.get("builder_mode") == "1":
            kwargs["prefix"] = f"block-{self.object.pk}"
        return kwargs

    def form_invalid(self, form):
        if self.request.POST.get("builder_mode") == "1" or is_htmx_request(self.request):
            return render_lesson_builder(
                self.request,
                self.object.lesson,
                block_forms={self.object.pk: form},
                active_block_id=self.object.pk,
                status=422,
            )
        return super().form_invalid(form)

    def form_valid(self, form):
        self.object = form.save()
        messages.success(self.request, "Блок обновлен.")
        if self.request.POST.get("builder_mode") == "1" or is_htmx_request(self.request):
            return render_lesson_builder(self.request, self.object.lesson)
        return redirect(self.get_success_url())

    def get_success_url(self):
        return self.object.lesson.get_builder_url()


class BlockDuplicateView(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        block = get_object_or_404(LessonBlock.objects.select_related("lesson", "lesson__course"), pk=kwargs["pk"])
        if not (request.user.is_staff or block.lesson.course.author == request.user):
            raise Http404

        duplicated = duplicate_block(block)
        messages.success(request, "Блок продублирован.")
        if is_htmx_request(request):
            return render_lesson_builder(request, duplicated.lesson)
        return redirect(duplicated.lesson.get_builder_url())


class BlockDeleteView(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        block = get_object_or_404(LessonBlock.objects.select_related("lesson", "lesson__course"), pk=kwargs["pk"])
        if not (request.user.is_staff or block.lesson.course.author == request.user):
            raise Http404
        lesson = block.lesson
        block.delete()
        reindex_lesson_blocks(lesson)
        messages.info(request, "Блок удален.")
        if is_htmx_request(request):
            return render_lesson_builder(request, lesson)
        return redirect(lesson.get_builder_url())


class BlockSortView(AuthorLessonMixin, View):
    def post(self, request, *args, **kwargs):
        payload = json.loads(request.body or "{}")
        order = payload.get("order", [])
        blocks = {str(block.id): block for block in self.lesson.blocks.all()}
        for index, block_id in enumerate(order, start=1):
            block = blocks.get(str(block_id))
            if block:
                block.position = index
                block.save(update_fields=["position", "updated_at"])
        return JsonResponse({"ok": True})


class PracticeTaskCreateView(AuthorLessonMixin, CreateView):
    form_class = PracticeTaskForm
    template_name = "lessons/practice_form.html"

    def form_valid(self, form):
        form.instance.lesson = self.lesson
        form.instance.is_placeholder = True
        messages.success(self.request, "Практическое задание добавлено как заглушка.")
        return super().form_valid(form)

    def get_success_url(self):
        return self.lesson.get_builder_url()
