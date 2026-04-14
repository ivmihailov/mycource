import json
from email.header import decode_header

import pytest
from django.urls import reverse

from apps.ai_support.catalog import ModelCatalogService
from apps.ai_support.exceptions import AIUnavailableError
from apps.ai_support.models import AIModelOption, AIUserPreference
from apps.ai_support.prompts import build_course_qna_messages
from apps.ai_support.providers import AICompletionResult, OpenRouterProvider
from apps.ai_support.schemas import validate_generated_quiz_payload
from apps.lessons.models import LessonBlock
from apps.quizzes.models import Quiz


def decode_header_value(value):
    decoded_parts = []
    for chunk, encoding in decode_header(value):
        if isinstance(chunk, bytes):
            decoded_parts.append(chunk.decode(encoding or "utf-8"))
        else:
            decoded_parts.append(chunk)
    return "".join(decoded_parts)


@pytest.fixture
def ai_model_options(db):
    return {
        "fast": AIModelOption.objects.create(
            provider_name="openrouter",
            external_model_id="google/gemini-fast",
            display_name="Gemini Fast",
            role_type=AIModelOption.RoleType.FAST,
            is_active=True,
            context_window=128000,
            supports_structured_output=True,
        ),
        "balanced": AIModelOption.objects.create(
            provider_name="openrouter",
            external_model_id="openai/gpt-balanced",
            display_name="GPT Balanced",
            role_type=AIModelOption.RoleType.BALANCED,
            is_active=True,
            context_window=128000,
            supports_structured_output=True,
        ),
        "strong": AIModelOption.objects.create(
            provider_name="openrouter",
            external_model_id="anthropic/claude-strong",
            display_name="Claude Strong",
            role_type=AIModelOption.RoleType.STRONG,
            is_active=True,
            context_window=200000,
            supports_structured_output=True,
        ),
    }


@pytest.mark.django_db
def test_model_selection_heuristic_prefers_expected_roles():
    service = ModelCatalogService()
    candidates = service._prepare_candidates(
        [
            {
                "id": "google/gemini-2.5-flash-lite",
                "name": "Gemini 2.5 Flash Lite",
                "context_length": 128000,
                "pricing": {"prompt": "0.0000005", "completion": "0.000001"},
                "architecture": {"input_modalities": ["text"], "output_modalities": ["text"]},
                "supported_parameters": ["response_format", "structured_outputs"],
            },
            {
                "id": "openai/gpt-4.1-mini",
                "name": "GPT-4.1 mini",
                "context_length": 128000,
                "pricing": {"prompt": "0.000002", "completion": "0.000008"},
                "architecture": {"input_modalities": ["text"], "output_modalities": ["text"]},
                "supported_parameters": ["response_format"],
            },
            {
                "id": "anthropic/claude-opus-4.1",
                "name": "Claude Opus",
                "context_length": 200000,
                "pricing": {"prompt": "0.00002", "completion": "0.00008"},
                "architecture": {"input_modalities": ["text"], "output_modalities": ["text"]},
                "supported_parameters": ["response_format", "structured_outputs"],
            },
        ]
    )

    selected = service._select_models(candidates, override_ids={})

    assert selected[AIModelOption.RoleType.FAST].model_id == "google/gemini-2.5-flash-lite"
    assert selected[AIModelOption.RoleType.BALANCED].model_id == "openai/gpt-4.1-mini"
    assert selected[AIModelOption.RoleType.STRONG].model_id == "anthropic/claude-opus-4.1"


def test_openrouter_provider_fails_gracefully_without_api_key(settings):
    settings.AI_ENABLED = True
    settings.OPENROUTER_API_KEY = ""

    provider = OpenRouterProvider()
    with pytest.raises(AIUnavailableError):
        provider.list_models()


def test_generated_quiz_schema_validation_accepts_supported_question_types():
    payload = {
        "title": "Черновик теста",
        "description": "Проверка базовых понятий",
        "questions": [
            {
                "question_type": "single_choice",
                "text": "Что такое DNS?",
                "score": 1,
                "explanation": "",
                "options": [
                    {"text": "Система доменных имен", "is_correct": True},
                    {"text": "Веб-браузер", "is_correct": False},
                ],
            },
            {
                "question_type": "multiple_choice",
                "text": "Что относится к веб-запросу?",
                "score": 2,
                "explanation": "",
                "options": [
                    {"text": "DNS lookup", "is_correct": True},
                    {"text": "HTTP request", "is_correct": True},
                    {"text": "Замена MAC на IP", "is_correct": False},
                ],
            },
            {
                "question_type": "true_false",
                "text": "HTTPS использует шифрование.",
                "score": 1,
                "explanation": "",
                "options": [
                    {"text": "True", "is_correct": True},
                    {"text": "False", "is_correct": False},
                ],
            },
        ],
    }

    normalized = validate_generated_quiz_payload(json.dumps(payload, ensure_ascii=False))
    assert normalized["title"] == "Черновик теста"
    assert len(normalized["questions"]) == 3
    assert normalized["questions"][1]["question_type"] == "multiple_choice"


@pytest.mark.django_db
def test_course_qna_prompt_allows_general_explanation_when_course_context_is_missing(course_with_lessons):
    course = course_with_lessons["course"]
    messages = build_course_qna_messages(course=course, question="Что такое интернет?", chunks=[], lesson=None)

    assert "В материалах курса нет прямого ответа" in messages[0]["content"]
    assert "общее пояснение" in messages[1]["content"]


@pytest.mark.django_db
def test_navbar_model_selection_updates_user_preference(client, user, ai_model_options):
    client.force_login(user)

    response = client.post(reverse("ai_support:select_model"), {"role_type": AIModelOption.RoleType.STRONG}, HTTP_HX_REQUEST="true")

    assert response.status_code == 200
    preference = AIUserPreference.objects.get(user=user)
    assert preference.selected_role_type == AIModelOption.RoleType.STRONG
    assert preference.selected_model_option == ai_model_options["strong"]
    assert "Claude Strong" in response.content.decode()
    assert "ui:toast" in decode_header_value(response.headers["HX-Trigger"])


@pytest.mark.django_db
def test_student_can_ask_question_grounded_in_course_content(client, user, course_with_lessons, ai_model_options, monkeypatch):
    client.force_login(user)

    captured = {}

    def fake_chat(self, **kwargs):
        captured["model_id"] = kwargs["model_id"]
        captured["messages"] = kwargs["messages"]
        return AICompletionResult(
            model_id=kwargs["model_id"],
            content="Интернет — это сеть сетей. Опора: Урок «Lesson One», блок «Intro».",
            raw_response={},
        )

    monkeypatch.setattr("apps.ai_support.providers.OpenRouterProvider.chat", fake_chat)

    course = course_with_lessons["course"]
    response = client.post(
        reverse("ai_support:ask_course", kwargs={"slug": course.slug}),
        {"question": "Что такое интернет?"},
        HTTP_HX_REQUEST="true",
    )

    assert response.status_code == 200
    html = response.content.decode()
    assert "сеть сетей" in html
    assert "Урок «Lesson One», блок «Intro»" in html
    assert captured["model_id"] == ai_model_options["balanced"].external_model_id
    assert "Lesson One" in captured["messages"][1]["content"]
    assert 'data-ui="ai-chat-history"' in html


@pytest.mark.django_db
def test_ai_panel_opens_via_dedicated_drawer_endpoint(client, user, course_with_lessons, ai_model_options):
    client.force_login(user)
    course = course_with_lessons["course"]
    lesson = course_with_lessons["lesson1"]

    course_panel = client.get(reverse("ai_support:course_panel", kwargs={"slug": course.slug}), HTTP_HX_REQUEST="true")
    lesson_panel = client.get(
        reverse("ai_support:lesson_panel", kwargs={"course_slug": course.slug, "lesson_slug": lesson.slug}),
        HTTP_HX_REQUEST="true",
    )

    assert course_panel.status_code == 200
    assert lesson_panel.status_code == 200
    assert 'data-ui="ai-drawer-panel"' in course_panel.content.decode()
    assert 'data-ui="ai-chat-form"' in lesson_panel.content.decode()


@pytest.mark.django_db
def test_teacher_can_generate_quiz_from_lesson_content(client, author, course_with_lessons, ai_model_options, monkeypatch):
    client.force_login(author)
    lesson = course_with_lessons["lesson1"]
    LessonBlock.objects.create(
        lesson=lesson,
        block_type=LessonBlock.BlockType.TEXT,
        title="Networking Basics",
        position=2,
        content_markdown=(
            "Интернет — это сеть сетей. DNS сопоставляет доменные имена и IP-адреса. "
            "HTTP описывает обмен запросом и ответом между клиентом и сервером. "
            "HTTPS добавляет шифрование через TLS."
        ),
    )

    generated_payload = {
        "title": "AI-тест по уроку",
        "description": "Черновик вопросов по сетевым основам",
        "questions": [
            {
                "question_type": "single_choice",
                "text": "Что делает DNS?",
                "score": 1,
                "explanation": "",
                "options": [
                    {"text": "Сопоставляет домен и IP", "is_correct": True},
                    {"text": "Рендерит HTML", "is_correct": False},
                ],
            },
            {
                "question_type": "multiple_choice",
                "text": "Что участвует в веб-запросе?",
                "score": 2,
                "explanation": "",
                "options": [
                    {"text": "Клиент", "is_correct": True},
                    {"text": "Сервер", "is_correct": True},
                    {"text": "Монитор", "is_correct": False},
                ],
            },
            {
                "question_type": "true_false",
                "text": "HTTPS добавляет шифрование.",
                "score": 1,
                "explanation": "",
                "options": [
                    {"text": "True", "is_correct": True},
                    {"text": "False", "is_correct": False},
                ],
            },
        ],
    }

    def fake_chat(self, **kwargs):
        return AICompletionResult(
            model_id=kwargs["model_id"],
            content=json.dumps(generated_payload, ensure_ascii=False),
            raw_response={},
        )

    monkeypatch.setattr("apps.ai_support.providers.OpenRouterProvider.chat", fake_chat)

    response = client.post(
        reverse("ai_support:generate_quiz", kwargs={"course_slug": lesson.course.slug, "lesson_slug": lesson.slug}),
        HTTP_HX_REQUEST="true",
    )

    lesson.refresh_from_db()
    quiz_block = lesson.blocks.filter(block_type=LessonBlock.BlockType.QUIZ).latest("id")
    quiz = quiz_block.quiz

    assert response.status_code == 200
    assert quiz.is_ai_draft is True
    assert quiz.questions.count() == 3
    assert "AI-черновик" in response.content.decode()


@pytest.mark.django_db
def test_unauthorized_user_cannot_access_protected_ai_endpoints(client, course_with_lessons):
    course = course_with_lessons["course"]
    lesson = course_with_lessons["lesson1"]

    ask_response = client.post(reverse("ai_support:ask_course", kwargs={"slug": course.slug}), {"question": "test"})
    generate_response = client.post(
        reverse("ai_support:generate_quiz", kwargs={"course_slug": course.slug, "lesson_slug": lesson.slug})
    )

    assert ask_response.status_code == 302
    assert generate_response.status_code == 302


@pytest.mark.django_db
def test_builder_starts_without_initial_empty_block_forms(client, author, course_with_lessons, ai_model_options):
    course = course_with_lessons["course"]
    lesson = course_with_lessons["lesson1"]
    client.force_login(author)

    response = client.get(reverse("lessons:builder", kwargs={"course_slug": course.slug, "slug": lesson.slug}))
    html = response.content.decode()

    assert response.status_code == 200
    assert html.count('data-ui="builder-add-form"') == 0

    opened_response = client.get(
        f"{reverse('lessons:builder', kwargs={'course_slug': course.slug, 'slug': lesson.slug})}?partial=shell&add_after=0",
        HTTP_HX_REQUEST="true",
    )
    assert opened_response.status_code == 200
    assert opened_response.content.decode().count('data-ui="builder-add-form"') == 1
