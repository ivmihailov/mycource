from django.shortcuts import render

from apps.lessons.forms import LessonBlockForm, LessonForm
from apps.lessons.models import LessonBlock
from apps.quizzes.forms import QuizForm


def build_lesson_builder_context(
    lesson,
    *,
    lesson_form=None,
    block_forms=None,
    quiz_forms=None,
    add_form=None,
    add_after_id=None,
    add_block_type=None,
    question_state=None,
    active_block_id=None,
):
    block_forms = block_forms or {}
    quiz_forms = quiz_forms or {}
    question_state = question_state or {}

    if lesson_form is None:
        lesson_form = LessonForm(instance=lesson, prefix="lesson")

    if add_after_id is not None and add_form is None:
        add_form = LessonBlockForm(
            prefix="new-block",
            initial={
                "block_type": add_block_type or LessonBlock.BlockType.TEXT,
                "note_style": LessonBlock.NoteStyle.NOTE,
                "is_required": True,
            },
        )

    blocks = list(
        lesson.blocks.select_related("quiz")
        .prefetch_related("quiz__questions__options")
        .order_by("position", "id")
    )

    block_cards = []
    for block in blocks:
        block_form = block_forms.get(block.pk) or LessonBlockForm(
            instance=block,
            prefix=f"block-{block.pk}",
            allow_type_edit=False,
        )
        card = {
            "block": block,
            "form": block_form,
            "quiz": getattr(block, "quiz", None),
            "quiz_form": None,
            "question_state": None,
        }
        if card["quiz"] is not None:
            card["quiz_form"] = quiz_forms.get(card["quiz"].pk) or QuizForm(
                instance=card["quiz"],
                prefix=f"quiz-{card['quiz'].pk}",
            )
            if question_state.get("quiz_pk") == card["quiz"].pk:
                card["question_state"] = question_state
        block_cards.append(card)

    return {
        "course": lesson.course,
        "lesson": lesson,
        "lesson_form": lesson_form,
        "block_cards": block_cards,
        "blocks": blocks,
        "practice_tasks": lesson.practice_tasks.filter(is_active=True),
        "add_form": add_form,
        "add_after_id": add_after_id,
        "add_block_type": add_block_type or LessonBlock.BlockType.TEXT,
        "active_block_id": active_block_id,
    }


def render_lesson_builder(
    request,
    lesson,
    *,
    lesson_form=None,
    block_forms=None,
    quiz_forms=None,
    add_form=None,
    add_after_id=None,
    add_block_type=None,
    question_state=None,
    active_block_id=None,
    status=200,
):
    context = build_lesson_builder_context(
        lesson,
        lesson_form=lesson_form,
        block_forms=block_forms,
        quiz_forms=quiz_forms,
        add_form=add_form,
        add_after_id=add_after_id,
        add_block_type=add_block_type,
        question_state=question_state,
        active_block_id=active_block_id,
    )
    return render(request, "lessons/partials/builder_shell.html", context, status=status)
