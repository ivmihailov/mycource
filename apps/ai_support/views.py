from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import Http404
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_GET, require_POST

from apps.ai_support.catalog import get_model_catalog_service
from apps.ai_support.forms import AIQuestionForm
from apps.ai_support.services import AIModelSelectionService, CourseQnAService, QuizGenerationService, get_ai_advisor
from apps.courses.models import Course
from apps.learning.services import user_can_access_course, user_can_access_lesson
from apps.lessons.builder import render_lesson_builder
from apps.lessons.models import Lesson

AI_QNA_HISTORY_SESSION_KEY = "ai_qna_history"


@login_required
@require_POST
def advice_panel(request):
    context_type = request.POST.get("context_type", "student_hint")
    advisor = get_ai_advisor()
    advice = advisor.get_advice(context_type=context_type, payload=request.POST.dict())
    return render(
        request,
        "ai_support/partials/advice_panel.html",
        {"advice": advice, "context_type": context_type},
    )


@require_POST
def select_model(request):
    catalog_service = get_model_catalog_service()
    selection_service = AIModelSelectionService(catalog_service=catalog_service)
    selected_model = None
    try:
        catalog_service.get_active_options(auto_refresh=True)
        selected_model = selection_service.set_selected_role(request, request.POST.get("role_type"))
        if selected_model:
            messages.success(request, f"Модель ИИ переключена: {selected_model.get_role_type_display()} · {selected_model.display_name}.")
    except Exception as exc:  # noqa: BLE001
        messages.error(request, str(exc))
    return render(
        request,
        "ai_support/partials/model_switcher.html",
        {
            "ai_model_options": selection_service.get_options(),
            "ai_selected_role": selection_service.get_selected_role(request),
            "ai_selected_model": selected_model,
            "ai_enabled": True,
        },
    )


def _get_course_for_ai(request, slug):
    course = get_object_or_404(Course.all_objects.select_related("author", "category"), slug=slug)
    if not user_can_access_course(request.user, course):
        raise Http404
    return course


def _get_history_scope_key(course, lesson=None):
    lesson_part = lesson.pk if lesson else "course"
    return f"{course.pk}:{lesson_part}"


def _get_qna_history(request, course, lesson=None):
    history = request.session.get(AI_QNA_HISTORY_SESSION_KEY, {})
    return history.get(_get_history_scope_key(course, lesson), [])


def _append_qna_history(request, course, *, question, answer, sources, lesson=None):
    history = request.session.get(AI_QNA_HISTORY_SESSION_KEY, {})
    scope_key = _get_history_scope_key(course, lesson)
    entries = history.get(scope_key, [])
    entries.extend(
        [
            {"role": "user", "text": question},
            {"role": "assistant", "text": answer, "sources": sources},
        ]
    )
    history[scope_key] = entries[-8:]
    request.session[AI_QNA_HISTORY_SESSION_KEY] = history
    request.session.modified = True


def _render_qna_panel(request, *, course, lesson=None, form=None, status=200, error=None):
    return render(
        request,
        "ai_support/partials/course_qna_panel.html",
        {
            "ai_question_form": form or AIQuestionForm(),
            "ai_error": error,
            "ai_history": _get_qna_history(request, course, lesson),
            "course": course,
            "lesson": lesson,
        },
        status=status,
    )


@login_required
@require_GET
def course_qna_panel(request, slug):
    course = _get_course_for_ai(request, slug)
    return _render_qna_panel(request, course=course)


@login_required
@require_GET
def lesson_qna_panel(request, course_slug, lesson_slug):
    course = _get_course_for_ai(request, course_slug)
    lesson = get_object_or_404(
        Lesson.all_objects.select_related("course"),
        course=course,
        slug=lesson_slug,
        is_deleted=False,
    )
    if not user_can_access_lesson(request.user, lesson):
        raise Http404
    return _render_qna_panel(request, course=course, lesson=lesson)


@login_required
@require_POST
def ask_course_question(request, slug):
    course = _get_course_for_ai(request, slug)
    form = AIQuestionForm(request.POST)
    if form.is_valid():
        try:
            answer = CourseQnAService().ask(
                request=request,
                course=course,
                question=form.cleaned_data["question"],
            )
            _append_qna_history(
                request,
                course,
                question=form.cleaned_data["question"],
                answer=answer.answer,
                sources=answer.sources,
            )
            return _render_qna_panel(request, course=course)
        except Exception as exc:  # noqa: BLE001
            messages.error(request, str(exc))
            return _render_qna_panel(request, course=course, form=form, status=422, error=str(exc))

    return _render_qna_panel(request, course=course, form=form, status=422)


@login_required
@require_POST
def ask_lesson_question(request, course_slug, lesson_slug):
    course = _get_course_for_ai(request, course_slug)
    lesson = get_object_or_404(
        Lesson.all_objects.select_related("course"),
        course=course,
        slug=lesson_slug,
        is_deleted=False,
    )
    if not user_can_access_lesson(request.user, lesson):
        raise Http404

    form = AIQuestionForm(request.POST)
    if form.is_valid():
        try:
            answer = CourseQnAService().ask(
                request=request,
                course=course,
                lesson=lesson,
                question=form.cleaned_data["question"],
            )
            _append_qna_history(
                request,
                course,
                lesson=lesson,
                question=form.cleaned_data["question"],
                answer=answer.answer,
                sources=answer.sources,
            )
            return _render_qna_panel(request, course=course, lesson=lesson)
        except Exception as exc:  # noqa: BLE001
            messages.error(request, str(exc))
            return _render_qna_panel(request, course=course, lesson=lesson, form=form, status=422, error=str(exc))

    return _render_qna_panel(request, course=course, lesson=lesson, form=form, status=422)


@login_required
@require_POST
def generate_lesson_quiz(request, course_slug, lesson_slug):
    lesson = get_object_or_404(
        Lesson.all_objects.select_related("course", "course__author"),
        course__slug=course_slug,
        slug=lesson_slug,
    )
    if not (request.user.is_staff or lesson.course.author == request.user):
        raise Http404

    try:
        generated = QuizGenerationService().generate_for_lesson(request=request, lesson=lesson)
        messages.success(request, "AI создал черновик теста по текущему содержимому урока.")
        return render_lesson_builder(request, lesson, active_block_id=generated.block.pk)
    except Exception as exc:  # noqa: BLE001
        messages.error(request, str(exc))
        return render_lesson_builder(request, lesson, status=422)
