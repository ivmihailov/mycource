from django.db import transaction
from django.db.models import F

from apps.core.utils import generate_unique_slug
from apps.lessons.models import Lesson, LessonBlock, PracticeTask


def reindex_lesson_blocks(lesson):
    for index, block in enumerate(lesson.blocks.order_by("position", "id"), start=1):
        if block.position != index:
            block.position = index
            block.save(update_fields=["position", "updated_at"])


@transaction.atomic
def insert_block(lesson, block, after_id=None):
    queryset = lesson.blocks.order_by("position", "id")
    if not queryset.exists():
        block.position = 1
        block.save()
        return block

    if after_id in (None, "", "end"):
        block.position = (queryset.values_list("position", flat=True).last() or 0) + 1
        block.save()
        return block

    if str(after_id) in {"0", "start"}:
        lesson.blocks.filter(position__gte=1).update(position=F("position") + 1)
        block.position = 1
        block.save()
        return block

    reference_block = lesson.blocks.get(pk=after_id)
    lesson.blocks.filter(position__gt=reference_block.position).update(position=F("position") + 1)
    block.position = reference_block.position + 1
    block.save()
    return block


@transaction.atomic
def duplicate_block(block):
    from apps.quizzes.services import duplicate_quiz

    lesson = block.lesson
    lesson.blocks.filter(position__gt=block.position).update(position=F("position") + 1)

    duplicated = LessonBlock.objects.get(pk=block.pk)
    duplicated.pk = None
    duplicated.lesson = lesson
    duplicated.position = block.position + 1
    duplicated.title = f"{block.title or block.get_block_type_display()} (копия)"
    duplicated.save()

    if hasattr(block, "quiz"):
        duplicate_quiz(block.quiz, duplicated)

    reindex_lesson_blocks(lesson)
    return duplicated


@transaction.atomic
def duplicate_lesson(lesson, course=None):
    from apps.quizzes.services import duplicate_quiz

    new_lesson = Lesson.all_objects.get(pk=lesson.pk)
    new_lesson.pk = None
    new_lesson.course = course or lesson.course
    new_lesson.slug = generate_unique_slug(new_lesson, f"{lesson.title} копия", queryset=new_lesson.course.lessons.all())
    new_lesson.title = f"{lesson.title} (копия)"
    new_lesson.save()

    for block in lesson.blocks.order_by("position", "id"):
        new_block = LessonBlock.objects.get(pk=block.pk)
        new_block.pk = None
        new_block.lesson = new_lesson
        new_block.save()

        if hasattr(block, "quiz"):
            duplicate_quiz(block.quiz, new_block)

    for task in lesson.practice_tasks.all():
        new_task = PracticeTask.objects.get(pk=task.pk)
        new_task.pk = None
        new_task.lesson = new_lesson
        new_task.save()
    return new_lesson
