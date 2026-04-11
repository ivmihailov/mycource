from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.views import View
from django.views.generic import UpdateView

from apps.core.forms import apply_form_styles
from apps.lessons.builder import render_lesson_builder
from apps.quizzes.forms import QuizAttemptForm, QuizForm, QuizOptionFormSet, QuizQuestionForm
from apps.quizzes.models import Quiz, QuizQuestion
from apps.quizzes.services import evaluate_attempt, get_or_create_draft_attempt


def ensure_author_access(user, quiz):
    if not (user.is_staff or quiz.lesson_block.lesson.course.author == user):
        raise Http404


def is_builder_request(request):
    return request.GET.get("builder_mode") == "1" or request.POST.get("builder_mode") == "1"


def style_option_formset(formset):
    for option_form in formset.forms:
        apply_form_styles(option_form)


class QuizUpdateView(LoginRequiredMixin, UpdateView):
    model = Quiz
    form_class = QuizForm
    template_name = "quizzes/quiz_form.html"
    pk_url_kwarg = "pk"

    def dispatch(self, request, *args, **kwargs):
        self.object = self.get_object()
        ensure_author_access(request.user, self.object)
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        if is_builder_request(self.request):
            kwargs["prefix"] = f"quiz-{self.object.pk}"
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["questions"] = self.object.questions.prefetch_related("options").order_by("position", "id")
        return context

    def form_invalid(self, form):
        if is_builder_request(self.request):
            return render_lesson_builder(
                self.request,
                self.object.lesson_block.lesson,
                quiz_forms={self.object.pk: form},
                active_block_id=self.object.lesson_block_id,
                status=422,
            )
        return super().form_invalid(form)

    def form_valid(self, form):
        self.object = form.save()
        messages.success(self.request, "Настройки теста сохранены.")
        if is_builder_request(self.request):
            return render_lesson_builder(
                self.request,
                self.object.lesson_block.lesson,
                active_block_id=self.object.lesson_block_id,
            )
        return redirect(self.get_success_url())

    def get_success_url(self):
        return self.object.lesson_block.lesson.get_builder_url()


class QuizQuestionManageView(LoginRequiredMixin, View):
    template_name = "quizzes/question_form.html"

    def dispatch(self, request, *args, **kwargs):
        self.quiz = get_object_or_404(Quiz.all_objects.select_related("lesson_block__lesson__course"), pk=kwargs["quiz_pk"])
        ensure_author_access(request.user, self.quiz)
        self.question = None
        if "pk" in kwargs:
            self.question = get_object_or_404(QuizQuestion.objects.filter(quiz=self.quiz), pk=kwargs["pk"])
        return super().dispatch(request, *args, **kwargs)

    def render_builder(self, form, formset, *, status=200):
        style_option_formset(formset)
        return render_lesson_builder(
            self.request,
            self.quiz.lesson_block.lesson,
            question_state={
                "quiz_pk": self.quiz.pk,
                "form": form,
                "formset": formset,
                "question": self.question,
            },
            active_block_id=self.quiz.lesson_block_id,
            status=status,
        )

    def get(self, request, *args, **kwargs):
        form = QuizQuestionForm(instance=self.question)
        formset = QuizOptionFormSet(instance=self.question or QuizQuestion(quiz=self.quiz))
        style_option_formset(formset)
        if is_builder_request(request):
            return self.render_builder(form, formset)
        return render(
            request,
            self.template_name,
            {"quiz": self.quiz, "form": form, "formset": formset, "question": self.question},
        )

    def post(self, request, *args, **kwargs):
        form = QuizQuestionForm(request.POST, instance=self.question)
        formset = QuizOptionFormSet(request.POST, instance=self.question or QuizQuestion(quiz=self.quiz))
        if form.is_valid() and formset.is_valid():
            question = form.save(commit=False)
            question.quiz = self.quiz
            if self.question is None:
                question.position = (self.quiz.questions.order_by("-position").values_list("position", flat=True).first() or 0) + 1
            question.save()
            formset.instance = question
            formset.save()
            self.quiz.update_max_score()
            messages.success(request, "Вопрос сохранен.")
            if is_builder_request(request):
                return render_lesson_builder(
                    request,
                    self.quiz.lesson_block.lesson,
                    active_block_id=self.quiz.lesson_block_id,
                )
            return redirect("quizzes:update", pk=self.quiz.pk)

        if is_builder_request(request):
            return self.render_builder(form, formset, status=422)
        style_option_formset(formset)
        return render(
            request,
            self.template_name,
            {"quiz": self.quiz, "form": form, "formset": formset, "question": self.question},
        )


class QuizQuestionDeleteView(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        quiz = get_object_or_404(Quiz.all_objects.select_related("lesson_block__lesson__course"), pk=kwargs["quiz_pk"])
        ensure_author_access(request.user, quiz)
        question = get_object_or_404(QuizQuestion.objects.filter(quiz=quiz), pk=kwargs["pk"])
        question.delete()
        messages.info(request, "Вопрос удален.")
        if is_builder_request(request):
            return render_lesson_builder(
                request,
                quiz.lesson_block.lesson,
                active_block_id=quiz.lesson_block_id,
            )
        return redirect("quizzes:update", pk=quiz.pk)


class QuizTakeView(LoginRequiredMixin, View):
    template_name = "quizzes/take.html"

    def get_quiz(self):
        return get_object_or_404(
            Quiz.objects.select_related("lesson_block__lesson__course").prefetch_related("questions__options"),
            pk=self.kwargs["pk"],
            is_deleted=False,
        )

    def dispatch(self, request, *args, **kwargs):
        self.quiz = self.get_quiz()
        course = self.quiz.lesson_block.lesson.course
        if course.status != course.Status.PUBLISHED and not (request.user.is_staff or request.user == course.author):
            raise Http404
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        attempt = get_or_create_draft_attempt(request.user, self.quiz)
        form = QuizAttemptForm(self.quiz)
        return render(
            request,
            self.template_name,
            {
                "quiz": self.quiz,
                "form": form,
                "attempt": attempt,
                "history": self.quiz.attempts.filter(user=request.user, submitted_at__isnull=False)[:5],
            },
        )

    def post(self, request, *args, **kwargs):
        attempt = get_or_create_draft_attempt(request.user, self.quiz)
        form = QuizAttemptForm(self.quiz, request.POST)
        if form.is_valid():
            evaluate_attempt(attempt, form.get_selected_options())
            messages.success(request, "Тест проверен. Результат сохранен.")
            return redirect("quizzes:result", pk=attempt.pk)
        return render(
            request,
            self.template_name,
            {
                "quiz": self.quiz,
                "form": form,
                "attempt": attempt,
                "history": self.quiz.attempts.filter(user=request.user, submitted_at__isnull=False)[:5],
            },
        )


class QuizResultView(LoginRequiredMixin, View):
    template_name = "quizzes/result.html"

    def get(self, request, *args, **kwargs):
        attempt = get_object_or_404(
            self.request.user.quiz_attempts.select_related("quiz__lesson_block__lesson__course"),
            pk=self.kwargs["pk"],
        )
        return render(request, self.template_name, {"attempt": attempt, "quiz": attempt.quiz})
