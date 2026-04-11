from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from apps.learning.models import CourseProgress, LessonProgress


def get_or_create_course_progress(user, course):
    progress, _ = CourseProgress.objects.get_or_create(user=user, course=course)
    return progress


def get_or_create_lesson_progress(user, lesson):
    progress, _ = LessonProgress.objects.get_or_create(user=user, lesson=lesson)
    return progress


def user_can_access_course(user, course):
    if course.is_deleted:
        return False
    if course.status == course.Status.PUBLISHED:
        return True
    return user.is_authenticated and (user == course.author or user.is_staff)


def get_accessible_lessons(user, course):
    lessons = list(course.lessons.filter(is_deleted=False).order_by("position", "id"))
    if course.order_mode == course.OrderMode.FREE or user == course.author or user.is_staff:
        return lessons

    accessible = []
    for lesson in lessons:
        if not accessible:
            accessible.append(lesson)
            continue
        previous_lesson = accessible[-1]
        previous_progress = LessonProgress.objects.filter(user=user, lesson=previous_lesson).first()
        if previous_progress and previous_progress.status == LessonProgress.Status.COMPLETED:
            accessible.append(lesson)
        else:
            break
    return accessible


def user_can_access_lesson(user, lesson):
    if not user_can_access_course(user, lesson.course):
        return False
    lessons = get_accessible_lessons(user, lesson.course)
    return any(item.pk == lesson.pk for item in lessons)


@transaction.atomic
def open_lesson(user, lesson):
    course_progress = get_or_create_course_progress(user, lesson.course)
    lesson_progress = get_or_create_lesson_progress(user, lesson)

    now = timezone.now()
    if course_progress.status == CourseProgress.Status.NOT_STARTED:
        course_progress.status = CourseProgress.Status.IN_PROGRESS
        course_progress.started_at = now

    course_progress.last_opened_lesson = lesson
    course_progress.save(update_fields=["status", "started_at", "last_opened_lesson", "updated_at"])

    if lesson_progress.status == LessonProgress.Status.NOT_STARTED:
        lesson_progress.status = LessonProgress.Status.IN_PROGRESS
        lesson_progress.started_at = now
        lesson_progress.save(update_fields=["status", "started_at", "updated_at"])

    recalculate_course_progress(user, lesson.course)
    return lesson_progress


def lesson_requires_quiz(lesson):
    return lesson.blocks.filter(block_type="quiz").exists()


@transaction.atomic
def mark_lesson_completed_manually(user, lesson):
    if lesson_requires_quiz(lesson):
        return None

    lesson_progress = get_or_create_lesson_progress(user, lesson)
    lesson_progress.status = LessonProgress.Status.COMPLETED
    lesson_progress.completed_at = lesson_progress.completed_at or timezone.now()
    lesson_progress.completed_manually = True
    if not lesson_progress.started_at:
        lesson_progress.started_at = timezone.now()
    lesson_progress.save()
    recalculate_course_progress(user, lesson.course)
    return lesson_progress


@transaction.atomic
def sync_progress_after_quiz_attempt(attempt):
    lesson = attempt.quiz.lesson_block.lesson
    lesson_progress = get_or_create_lesson_progress(attempt.user, lesson)
    lesson_progress.status = LessonProgress.Status.IN_PROGRESS
    lesson_progress.started_at = lesson_progress.started_at or attempt.started_at
    lesson_progress.best_score = max(lesson_progress.best_score, attempt.score)

    if attempt.passed:
        lesson_progress.status = LessonProgress.Status.COMPLETED
        lesson_progress.completed_at = timezone.now()

    lesson_progress.save()
    recalculate_course_progress(attempt.user, lesson.course)
    return lesson_progress


@transaction.atomic
def recalculate_course_progress(user, course):
    course_progress = get_or_create_course_progress(user, course)
    lessons = list(course.lessons.filter(is_deleted=False))
    total_lessons = len(lessons)
    completed_count = LessonProgress.objects.filter(
        user=user,
        lesson__course=course,
        status=LessonProgress.Status.COMPLETED,
        lesson__is_deleted=False,
    ).count()
    progress_percent = int((completed_count / total_lessons) * 100) if total_lessons else 0
    course_progress.progress_percent = progress_percent

    if completed_count == 0 and not CourseProgress.objects.filter(user=user, course=course).filter(
        Q(started_at__isnull=False) | Q(last_opened_lesson__isnull=False)
    ).exists():
        course_progress.status = CourseProgress.Status.NOT_STARTED
    elif total_lessons and completed_count >= total_lessons:
        course_progress.status = CourseProgress.Status.COMPLETED
        course_progress.completed_at = course_progress.completed_at or timezone.now()
        course_progress.started_at = course_progress.started_at or timezone.now()
    else:
        course_progress.status = CourseProgress.Status.IN_PROGRESS
        course_progress.started_at = course_progress.started_at or timezone.now()
        course_progress.completed_at = None

    course_progress.save()
    return course_progress


def get_next_lesson(course, current_lesson):
    lessons = list(course.lessons.filter(is_deleted=False).order_by("position", "id"))
    for index, lesson in enumerate(lessons):
        if lesson.pk == current_lesson.pk and index + 1 < len(lessons):
            return lessons[index + 1]
    return None
