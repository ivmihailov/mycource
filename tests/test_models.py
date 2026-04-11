import pytest

from apps.courses.models import Course
from apps.interactions.models import CourseReview
from apps.learning.models import LessonProgress
from apps.learning.services import mark_lesson_completed_manually
from apps.quizzes.models import QuizAttempt
from apps.quizzes.services import evaluate_attempt


@pytest.mark.django_db
def test_soft_delete_hides_course(author, category):
    course = Course.objects.create(
        author=author,
        title="Delete Me",
        short_description="desc",
        full_description="body",
        category=category,
        estimated_duration_minutes=10,
    )
    course.soft_delete()

    assert not Course.objects.filter(pk=course.pk).exists()
    assert Course.all_objects.filter(pk=course.pk).exists()


@pytest.mark.django_db
def test_slug_generation_is_unique(author, category):
    first = Course.objects.create(
        author=author,
        title="Python Course",
        short_description="desc",
        full_description="body",
        category=category,
        estimated_duration_minutes=10,
    )
    second = Course.objects.create(
        author=author,
        title="Python Course",
        short_description="desc",
        full_description="body",
        category=category,
        estimated_duration_minutes=10,
    )

    assert first.slug == "python-course"
    assert second.slug.startswith("python-course-")


@pytest.mark.django_db
def test_review_updates_course_rating(user, published_course):
    CourseReview.objects.create(course=published_course, author=user, rating=4, body="Хорошо")
    published_course.refresh_from_db()

    assert float(published_course.average_rating) == 4.0
    assert published_course.reviews_count == 1


@pytest.mark.django_db
def test_manual_lesson_completion_updates_progress(user, course_with_lessons):
    lesson1 = course_with_lessons["lesson1"]
    progress = mark_lesson_completed_manually(user, lesson1)

    assert progress.status == LessonProgress.Status.COMPLETED
    assert progress.completed_manually is True


@pytest.mark.django_db
def test_quiz_attempt_updates_lesson_progress(user, course_with_lessons):
    quiz = course_with_lessons["quiz"]
    question = course_with_lessons["question"]
    correct = course_with_lessons["correct"]
    attempt = QuizAttempt.objects.create(user=user, quiz=quiz)

    evaluate_attempt(attempt, {str(question.pk): [str(correct.pk)]})

    progress = LessonProgress.objects.get(user=user, lesson=quiz.lesson_block.lesson)
    attempt.refresh_from_db()

    assert attempt.passed is True
    assert progress.status == LessonProgress.Status.COMPLETED
    assert progress.best_score == 1
