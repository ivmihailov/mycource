import pytest
from django.urls import reverse

from apps.learning.models import CourseProgress, LessonProgress


@pytest.mark.django_db
def test_sequential_access_blocks_next_lesson(client, user, course_with_lessons):
    course = course_with_lessons["course"]
    lesson2 = course_with_lessons["lesson2"]
    client.force_login(user)

    response = client.get(reverse("learning:lesson_detail", kwargs={"course_slug": course.slug, "lesson_slug": lesson2.slug}))

    assert response.status_code == 302
    assert course_with_lessons["lesson1"].slug in response.url


@pytest.mark.django_db
def test_full_learning_progress_flow(client, user, course_with_lessons):
    course = course_with_lessons["course"]
    lesson1 = course_with_lessons["lesson1"]
    lesson2 = course_with_lessons["lesson2"]
    lesson3 = course_with_lessons["lesson3"]
    quiz = course_with_lessons["quiz"]
    question = course_with_lessons["question"]
    correct = course_with_lessons["correct"]
    client.force_login(user)

    client.get(reverse("learning:lesson_detail", kwargs={"course_slug": course.slug, "lesson_slug": lesson1.slug}))
    client.post(reverse("learning:lesson_complete", kwargs={"course_slug": course.slug, "lesson_slug": lesson1.slug}))
    client.get(reverse("learning:lesson_detail", kwargs={"course_slug": course.slug, "lesson_slug": lesson2.slug}))
    client.post(reverse("quizzes:take", kwargs={"pk": quiz.pk}), {str(question.pk): str(correct.pk)})
    client.get(reverse("learning:lesson_detail", kwargs={"course_slug": course.slug, "lesson_slug": lesson3.slug}))
    client.post(reverse("learning:lesson_complete", kwargs={"course_slug": course.slug, "lesson_slug": lesson3.slug}))

    course_progress = CourseProgress.objects.get(user=user, course=course)
    lesson_three_progress = LessonProgress.objects.get(user=user, lesson=lesson3)

    assert lesson_three_progress.status == LessonProgress.Status.COMPLETED
    assert course_progress.status == CourseProgress.Status.COMPLETED
    assert course_progress.progress_percent == 100
