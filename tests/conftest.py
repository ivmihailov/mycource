import pytest
from django.contrib.auth import get_user_model

from apps.courses.models import Category, Course
from apps.lessons.models import Lesson, LessonBlock
from apps.quizzes.models import Quiz, QuizOption, QuizQuestion

User = get_user_model()


@pytest.fixture(autouse=True)
def disable_ai_auto_refresh(settings):
    settings.AI_AUTO_REFRESH_MODELS = False


@pytest.fixture
def user(db):
    return User.objects.create_user(
        username="user1",
        email="user1@example.com",
        password="StrongPass123!",
        is_email_verified=True,
    )


@pytest.fixture
def author(db):
    return User.objects.create_user(
        username="author1",
        email="author1@example.com",
        password="StrongPass123!",
        is_email_verified=True,
    )


@pytest.fixture
def category(db):
    return Category.objects.create(name="Backend")


@pytest.fixture
def published_course(author, category):
    return Course.objects.create(
        author=author,
        title="Django Basics",
        short_description="Курс по Django",
        full_description="Описание",
        category=category,
        status=Course.Status.PUBLISHED,
        estimated_duration_minutes=120,
        order_mode=Course.OrderMode.SEQUENTIAL,
    )


@pytest.fixture
def draft_course(author, category):
    return Course.all_objects.create(
        author=author,
        title="Draft Course",
        short_description="Черновик",
        full_description="Описание",
        category=category,
        status=Course.Status.DRAFT,
        estimated_duration_minutes=60,
    )


@pytest.fixture
def course_with_lessons(published_course):
    lesson1 = Lesson.objects.create(
        course=published_course,
        title="Lesson One",
        short_description="Первый урок",
        position=1,
    )
    LessonBlock.objects.create(
        lesson=lesson1,
        block_type=LessonBlock.BlockType.TEXT,
        title="Intro",
        position=1,
        content_markdown="Содержимое первого урока",
    )

    lesson2 = Lesson.objects.create(
        course=published_course,
        title="Lesson Two",
        short_description="Второй урок",
        position=2,
    )
    quiz_block = LessonBlock.objects.create(
        lesson=lesson2,
        block_type=LessonBlock.BlockType.QUIZ,
        title="Quiz",
        position=1,
    )
    quiz = Quiz.objects.create(lesson_block=quiz_block, title="Lesson Quiz", passing_score=1)
    question = QuizQuestion.objects.create(
        quiz=quiz,
        question_type=QuizQuestion.QuestionType.SINGLE,
        text="Правильный вариант?",
        score=1,
        position=1,
    )
    correct = QuizOption.objects.create(question=question, text="Да", is_correct=True, position=1)
    QuizOption.objects.create(question=question, text="Нет", is_correct=False, position=2)
    quiz.update_max_score()

    lesson3 = Lesson.objects.create(
        course=published_course,
        title="Lesson Three",
        short_description="Третий урок",
        position=3,
    )
    LessonBlock.objects.create(
        lesson=lesson3,
        block_type=LessonBlock.BlockType.TEXT,
        title="Outro",
        position=1,
        content_markdown="Финальный урок",
    )
    return {
        "course": published_course,
        "lesson1": lesson1,
        "lesson2": lesson2,
        "lesson3": lesson3,
        "quiz": quiz,
        "question": question,
        "correct": correct,
    }
