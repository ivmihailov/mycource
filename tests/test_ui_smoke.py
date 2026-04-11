import json

import pytest
from django.core.management import call_command
from django.urls import reverse

from apps.courses.models import Category, Course
from apps.lessons.models import LessonBlock


@pytest.mark.django_db
def test_public_ui_pages_render_key_sections(client, published_course, course_with_lessons):
    home = client.get(reverse("core:home"))
    catalog = client.get(reverse("courses:catalog"))
    detail = client.get(reverse("courses:detail", kwargs={"slug": published_course.slug}))

    assert home.status_code == 200
    home_html = home.content.decode()
    assert 'data-ui="home-hero"' in home_html
    assert "data-theme-toggle" in home_html
    assert "home-learning.svg" in home_html
    assert "surface-panel" in home_html

    assert catalog.status_code == 200
    catalog_html = catalog.content.decode()
    assert 'data-ui="catalog-filters"' in catalog_html
    assert 'data-ui="course-card"' in catalog_html
    assert "course-card__cover-image" in catalog_html
    assert "filter-panel" in catalog_html

    assert detail.status_code == 200
    html = detail.content.decode()
    assert 'data-ui="course-program"' in html
    assert 'data-ui="course-comments"' in html
    assert 'data-ui="course-reviews"' in html
    assert "surface-panel" in html


@pytest.mark.django_db
def test_debug_categories_are_hidden_from_public_ui_and_author_forms(client, author, published_course):
    Category.objects.create(name="Bug Category", slug="bug-category-manual", is_active=True)
    Category.objects.create(name="Manual Category Fix", slug="manual-category-fix-manual", is_active=True)
    valid_category = Category.objects.create(name="Веб-разработка", slug="web-development", is_active=True)

    home = client.get(reverse("core:home"))
    catalog = client.get(reverse("courses:catalog"))

    client.force_login(author)
    create_page = client.get(reverse("courses:create"))

    assert home.status_code == 200
    assert catalog.status_code == 200
    assert create_page.status_code == 200

    home_html = home.content.decode()
    catalog_html = catalog.content.decode()
    create_html = create_page.content.decode()

    assert "Bug Category" not in home_html
    assert "Manual Category Fix" not in home_html
    assert "Bug Category" not in catalog_html
    assert "Manual Category Fix" not in catalog_html
    assert "Bug Category" not in create_html
    assert "Manual Category Fix" not in create_html
    assert valid_category.name in create_html


@pytest.mark.django_db
def test_authenticated_dashboard_learning_and_profile_pages_render(client, user, course_with_lessons):
    client.force_login(user)

    dashboard = client.get(reverse("core:dashboard"))
    learning = client.get(reverse("learning:overview"))
    profile = client.get(reverse("users:profile"))
    profile_edit = client.get(reverse("users:profile_edit"))
    favorites = client.get(reverse("learning:favorites"))

    assert dashboard.status_code == 200
    dashboard_html = dashboard.content.decode()
    assert 'data-ui="dashboard-grid"' in dashboard_html
    assert "stat-card" in dashboard_html
    assert learning.status_code == 200
    assert "surface-panel" in learning.content.decode()
    assert profile.status_code == 200
    assert profile_edit.status_code == 200
    assert 'data-ui="form-field"' in profile_edit.content.decode()
    assert favorites.status_code == 200


@pytest.mark.django_db
def test_author_course_editor_and_builder_pages_render(client, author, course_with_lessons, category):
    course = course_with_lessons["course"]
    lesson = course_with_lessons["lesson1"]
    client.force_login(author)

    create_page = client.get(reverse("courses:create"))
    edit_page = client.get(reverse("courses:update", kwargs={"slug": course.slug}))
    builder_page = client.get(reverse("lessons:builder", kwargs={"course_slug": course.slug, "slug": lesson.slug}))
    my_courses = client.get(reverse("courses:my_courses"))
    drafts = client.get(reverse("courses:drafts"))

    assert create_page.status_code == 200
    assert 'data-ui="course-form"' in create_page.content.decode()

    assert edit_page.status_code == 200
    assert 'data-ui="course-lessons-panel"' in edit_page.content.decode()

    assert builder_page.status_code == 200
    builder_html = builder_page.content.decode()
    assert 'data-ui="lesson-builder-shell"' in builder_html
    assert 'data-ui="builder-outline"' in builder_html
    assert 'data-ui="builder-block-list"' in builder_html
    assert 'data-ui="builder-block-card"' in builder_html
    assert "surface-elevated" in builder_html
    assert my_courses.status_code == 200
    assert drafts.status_code == 200


@pytest.mark.django_db
def test_lesson_and_quiz_ui_render_for_student(client, user, course_with_lessons):
    course = course_with_lessons["course"]
    lesson1 = course_with_lessons["lesson1"]
    lesson2 = course_with_lessons["lesson2"]
    quiz = course_with_lessons["quiz"]
    client.force_login(user)

    lesson_page = client.get(reverse("learning:lesson_detail", kwargs={"course_slug": course.slug, "lesson_slug": lesson1.slug}))
    client.post(reverse("learning:lesson_complete", kwargs={"course_slug": course.slug, "lesson_slug": lesson1.slug}))
    second_lesson = client.get(reverse("learning:lesson_detail", kwargs={"course_slug": course.slug, "lesson_slug": lesson2.slug}))
    quiz_page = client.get(reverse("quizzes:take", kwargs={"pk": quiz.pk}))

    assert lesson_page.status_code == 200
    lesson_html = lesson_page.content.decode()
    assert 'data-ui="lesson-layout-desktop"' in lesson_html
    assert 'data-ui="lesson-contents-toggle"' in lesson_html
    assert 'data-ui="lesson-sidebar"' in lesson_html
    assert 'data-ui="lesson-nav-item"' in lesson_html
    assert "surface-panel" in lesson_html

    assert second_lesson.status_code == 200
    second_lesson_html = second_lesson.content.decode()
    assert 'data-ui="lesson-content"' in second_lesson_html
    assert 'data-ui="lesson-block"' in second_lesson_html
    assert 'data-ui="quiz-panel"' in second_lesson_html
    assert "Готово" in second_lesson_html

    assert quiz_page.status_code == 200
    quiz_html = quiz_page.content.decode()
    assert 'data-ui="quiz-attempt-form"' in quiz_html
    assert 'data-ui="quiz-card"' in quiz_html
    assert "field-label" in quiz_html


@pytest.mark.django_db
def test_author_can_create_course_then_add_lesson_without_template_error(client, author, category):
    client.force_login(author)

    create_course_response = client.post(
        reverse("courses:create"),
        {
            "title": "Regression Course",
            "short_description": "Курс для регрессионного сценария",
            "full_description": "Полное описание курса для проверки создания урока.",
            "category": category.pk,
            "tags": [],
            "level": "beginner",
            "estimated_duration_minutes": 45,
            "order_mode": "sequential_order",
        },
    )

    assert create_course_response.status_code == 302

    course = Course.all_objects.get(author=author, title="Regression Course")
    lesson_create_url = reverse("lessons:create", kwargs={"course_slug": course.slug})

    lesson_create_page = client.get(lesson_create_url)
    assert lesson_create_page.status_code == 200
    assert 'data-ui="lesson-form"' in lesson_create_page.content.decode()

    lesson_post_response = client.post(
        lesson_create_url,
        {
            "title": "Первый регрессионный урок",
            "short_description": "Описание первого урока",
            "estimated_duration_minutes": 20,
        },
    )

    lesson = course.lessons.get(title="Первый регрессионный урок")

    assert lesson_post_response.status_code == 302
    assert lesson.slug
    assert lesson.position == 1
    assert lesson.course_id == course.id
    assert lesson_post_response.url == reverse("lessons:builder", kwargs={"course_slug": course.slug, "slug": lesson.slug})

    builder_page = client.get(lesson_post_response.url)
    assert builder_page.status_code == 200
    assert "Первый регрессионный урок" in builder_page.content.decode()


@pytest.mark.django_db
def test_sort_endpoints_keep_editor_logic_working(client, author, course_with_lessons):
    course = course_with_lessons["course"]
    lesson1 = course_with_lessons["lesson1"]
    lesson2 = course_with_lessons["lesson2"]
    lesson3 = course_with_lessons["lesson3"]
    client.force_login(author)

    lesson_sort_response = client.post(
        reverse("lessons:sort", kwargs={"course_slug": course.slug}),
        data=json.dumps({"order": [lesson3.id, lesson1.id, lesson2.id]}),
        content_type="application/json",
    )

    extra_block = LessonBlock.objects.create(
        lesson=lesson1,
        block_type=LessonBlock.BlockType.QUOTE,
        title="Дополнительный блок",
        position=2,
        content_markdown="Тестовый блок для проверки сортировки.",
    )

    block_sort_response = client.post(
        reverse("lessons:block_sort", kwargs={"course_slug": course.slug, "slug": lesson1.slug}),
        data=json.dumps({"order": [extra_block.id, lesson1.blocks.first().id]}),
        content_type="application/json",
    )

    lesson1.refresh_from_db()
    lesson3.refresh_from_db()
    extra_block.refresh_from_db()

    assert lesson_sort_response.status_code == 200
    assert lesson3.position == 1
    assert lesson1.position == 2
    assert block_sort_response.status_code == 200
    assert extra_block.position == 1


@pytest.mark.django_db
def test_author_can_manage_blocks_inline_inside_builder(client, author, course_with_lessons):
    course = course_with_lessons["course"]
    lesson = course_with_lessons["lesson1"]
    existing_block = lesson.blocks.first()
    client.force_login(author)

    shell_response = client.get(
        f"{reverse('lessons:builder', kwargs={'course_slug': course.slug, 'slug': lesson.slug})}?partial=shell&add_after=0",
        HTTP_HX_REQUEST="true",
    )
    assert shell_response.status_code == 200
    assert 'data-ui="builder-add-form"' in shell_response.content.decode()

    create_first_response = client.post(
        reverse("lessons:block_create", kwargs={"course_slug": course.slug, "slug": lesson.slug}),
        {
            "builder_mode": "1",
            "after_id": "0",
            "new-block-block_type": "text",
            "new-block-title": "Вводный inline-блок",
            "new-block-content_markdown": "Текст для inline builder.",
            "new-block-is_required": "on",
        },
        HTTP_HX_REQUEST="true",
    )
    lesson.refresh_from_db()
    created_block = lesson.blocks.get(title="Вводный inline-блок")

    assert create_first_response.status_code == 200
    assert created_block.position == 1
    assert 'data-ui="builder-block-card"' in create_first_response.content.decode()

    create_second_response = client.post(
        reverse("lessons:block_create", kwargs={"course_slug": course.slug, "slug": lesson.slug}),
        {
            "builder_mode": "1",
            "after_id": str(existing_block.pk),
            "new-block-block_type": "quote",
            "new-block-title": "Второй inline-блок",
            "new-block-content_markdown": "Короткая заметка после основного блока.",
            "new-block-note_style": "note",
            "new-block-is_required": "on",
        },
        HTTP_HX_REQUEST="true",
    )
    lesson.refresh_from_db()
    existing_block.refresh_from_db()
    second_block = lesson.blocks.get(title="Второй inline-блок")

    assert create_second_response.status_code == 200
    assert second_block.position == existing_block.position + 1

    delete_response = client.post(
        reverse("lessons:block_delete", kwargs={"pk": second_block.pk}),
        {"builder_mode": "1"},
        HTTP_HX_REQUEST="true",
    )

    assert delete_response.status_code == 200
    assert not lesson.blocks.filter(pk=second_block.pk).exists()


@pytest.mark.django_db
def test_block_editor_closes_after_save_and_can_be_reopened(client, author, course_with_lessons):
    course = course_with_lessons["course"]
    lesson = course_with_lessons["lesson1"]
    block = lesson.blocks.first()
    client.force_login(author)

    open_response = client.get(
        f"{reverse('lessons:builder', kwargs={'course_slug': course.slug, 'slug': lesson.slug})}?partial=shell&edit_block={block.pk}",
        HTTP_HX_REQUEST="true",
    )
    assert open_response.status_code == 200
    open_html = open_response.content.decode()
    assert reverse("lessons:block_update", kwargs={"pk": block.pk}) in open_html
    assert "Сохранить блок" in open_html

    save_response = client.post(
        reverse("lessons:block_update", kwargs={"pk": block.pk}),
        {
            "builder_mode": "1",
            f"block-{block.pk}-title": "Обновленный блок",
            f"block-{block.pk}-content_markdown": "Новый текст для проверки сворачивания.",
            f"block-{block.pk}-is_required": "on",
        },
        HTTP_HX_REQUEST="true",
    )

    assert save_response.status_code == 200
    save_html = save_response.content.decode()
    assert reverse("lessons:block_update", kwargs={"pk": block.pk}) not in save_html
    assert f"edit_block={block.pk}" in save_html
    assert "Редактировать" in save_html


@pytest.mark.django_db
def test_quiz_block_shows_inline_question_actions_after_creation(client, author, course_with_lessons):
    course = course_with_lessons["course"]
    lesson = course_with_lessons["lesson1"]
    client.force_login(author)

    create_quiz_block = client.post(
        reverse("lessons:block_create", kwargs={"course_slug": course.slug, "slug": lesson.slug}),
        {
            "builder_mode": "1",
            "after_id": "0",
            "new-block-block_type": "quiz",
            "new-block-title": "Тестовый блок для вопросов",
            "new-block-is_required": "on",
        },
        HTTP_HX_REQUEST="true",
    )

    assert create_quiz_block.status_code == 200
    block = lesson.blocks.get(title="Тестовый блок для вопросов")
    html = create_quiz_block.content.decode()
    assert reverse("quizzes:update", kwargs={"pk": block.quiz.pk}) in html
    assert reverse("quizzes:question_create", kwargs={"quiz_pk": block.quiz.pk}) in html
    assert f"edit_block={block.pk}" in html
    assert "Добавить вопрос" in html


@pytest.mark.django_db
def test_builder_uses_course_scoped_lesson_lookup_for_repeated_slugs(client, author, category):
    first_course = Course.objects.create(
        author=author,
        title="Русский курс один",
        short_description="Первый курс",
        full_description="Описание первого курса",
        category=category,
        status=Course.Status.DRAFT,
        estimated_duration_minutes=30,
    )
    second_course = Course.objects.create(
        author=author,
        title="Русский курс два",
        short_description="Второй курс",
        full_description="Описание второго курса",
        category=category,
        status=Course.Status.DRAFT,
        estimated_duration_minutes=30,
    )

    lesson_one = first_course.lessons.create(title="Урок", short_description="Первый урок", position=1)
    lesson_two = second_course.lessons.create(title="Урок", short_description="Второй урок", position=1)

    client.force_login(author)
    response = client.get(reverse("lessons:builder", kwargs={"course_slug": second_course.slug, "slug": lesson_two.slug}))

    assert lesson_one.slug == lesson_two.slug
    assert response.status_code == 200
    assert second_course.title in response.content.decode()


@pytest.mark.django_db
def test_seed_demo_creates_featured_internet_course(client):
    call_command("seed_demo")

    course = Course.objects.get(title="Введение в устройство интернета")
    detail = client.get(reverse("courses:detail", kwargs={"slug": course.slug}))

    assert course.lessons.filter(is_deleted=False).count() == 3
    assert detail.status_code == 200
    html = detail.content.decode()
    assert "DNS, доменные имена и путь запроса" in html
    assert "HTTP, HTTPS, страницы, ресурсы" in html
    assert "course-internet.svg" in html
