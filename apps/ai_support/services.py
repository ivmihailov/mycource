import logging
from dataclasses import dataclass
from decimal import Decimal

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import transaction

from apps.ai_support.catalog import get_model_catalog_service
from apps.ai_support.exceptions import AIProviderError, AIUnavailableError, AIValidationError
from apps.ai_support.models import AIInteractionLog, AIModelOption, AIUserPreference
from apps.ai_support.prompts import build_course_qna_messages, build_quiz_generation_messages
from apps.ai_support.providers import OpenRouterProvider
from apps.ai_support.retrieval import CourseContentRetriever
from apps.ai_support.schemas import QUIZ_RESPONSE_SCHEMA, validate_generated_quiz_payload
from apps.lessons.models import LessonBlock
from apps.lessons.services import insert_block
from apps.quizzes.models import Quiz, QuizOption, QuizQuestion

logger = logging.getLogger(__name__)
User = get_user_model()

SESSION_ROLE_KEY = "selected_ai_role_type"


@dataclass
class AIAdvice:
    title: str
    body: str
    mode: str


@dataclass
class CourseAnswer:
    answer: str
    sources: list[str]
    model_option: AIModelOption | None


@dataclass
class GeneratedQuizDraft:
    block: LessonBlock
    quiz: Quiz
    model_option: AIModelOption | None


class BaseAIAdvisor:
    def get_advice(self, context_type, payload):
        raise NotImplementedError


class MockAIAdvisor(BaseAIAdvisor):
    RESPONSES = {
        "course_creation": AIAdvice(
            title="Mock-совет ИИ для автора",
            body="Попробуйте уточнить учебную цель курса, добавить ожидаемый результат и разбить материал на короткие логические уроки.",
            mode="mock",
        ),
        "lesson_help": AIAdvice(
            title="Mock-подсказка по уроку",
            body="Сделайте вступление короче, а проверку знаний свяжите с конкретным практическим результатом урока.",
            mode="mock",
        ),
        "student_hint": AIAdvice(
            title="Mock-подсказка для ученика",
            body="Сфокусируйтесь на ключевом определении, затем вернитесь к примеру и попробуйте кратко сформулировать вывод своими словами.",
            mode="mock",
        ),
    }

    def get_advice(self, context_type, payload):
        return self.RESPONSES.get(context_type, self.RESPONSES["student_hint"])


def get_ai_advisor():
    return MockAIAdvisor()


class AIModelSelectionService:
    def __init__(self, catalog_service=None):
        self.catalog_service = catalog_service or get_model_catalog_service()

    def get_options(self, *, auto_refresh=False):
        return self.catalog_service.get_active_options(auto_refresh=auto_refresh)

    def get_selected_role(self, request):
        if request.user.is_authenticated:
            preference = getattr(request.user, "ai_preference", None)
            if preference and preference.selected_role_type:
                return preference.selected_role_type
        return request.session.get(SESSION_ROLE_KEY, AIModelOption.RoleType.BALANCED)

    def get_selected_model(self, request):
        selected_role = self.get_selected_role(request)
        options = {option.role_type: option for option in self.get_options()}
        return options.get(selected_role) or options.get(AIModelOption.RoleType.BALANCED)

    def set_selected_role(self, request, role_type):
        role_type = role_type or AIModelOption.RoleType.BALANCED
        options = {option.role_type: option for option in self.get_options()}
        selected_model = options.get(role_type)
        request.session[SESSION_ROLE_KEY] = role_type
        if request.user.is_authenticated:
            preference, _ = AIUserPreference.objects.get_or_create(user=request.user)
            preference.selected_role_type = role_type
            preference.selected_model_option = selected_model
            preference.save(update_fields=["selected_role_type", "selected_model_option", "updated_at"])
            AIInteractionLog.objects.create(
                user=request.user,
                action_type=AIInteractionLog.ActionType.MODEL_SELECTION,
                selected_model=selected_model,
                selected_model_label=selected_model.external_model_id if selected_model else "",
                status=AIInteractionLog.Status.SUCCESS,
            )
        return selected_model


class CourseQnAService:
    def __init__(self, provider=None, retriever=None, selection_service=None):
        self.provider = provider or OpenRouterProvider()
        self.retriever = retriever or CourseContentRetriever()
        self.selection_service = selection_service or AIModelSelectionService()

    def ask(self, *, request, course, question, lesson=None):
        question = (question or "").strip()
        if len(question) < 6:
            raise AIValidationError("Сформулируйте вопрос чуть подробнее.")
        if len(question) > 500:
            raise AIValidationError("Вопрос слишком длинный. Сократите его до 500 символов.")

        model_option = self.selection_service.get_selected_model(request)
        if model_option is None:
            raise AIUnavailableError("Каталог моделей ИИ пока не подготовлен.")

        chunks = self.retriever.select_relevant_chunks(course=course, question=question, lesson=lesson)
        messages = build_course_qna_messages(course=course, question=question, chunks=chunks, lesson=lesson)

        try:
            result = self.provider.chat(
                model_id=model_option.external_model_id,
                messages=messages,
                temperature=0.2,
                max_tokens=900,
            )
            AIInteractionLog.objects.create(
                user=request.user,
                course=course,
                lesson=lesson,
                action_type=AIInteractionLog.ActionType.QNA,
                selected_model=model_option,
                selected_model_label=model_option.external_model_id,
                status=AIInteractionLog.Status.SUCCESS,
            )
        except (AIProviderError, AIUnavailableError) as exc:
            logger.warning("AI course Q&A failed", exc_info=exc)
            AIInteractionLog.objects.create(
                user=request.user,
                course=course,
                lesson=lesson,
                action_type=AIInteractionLog.ActionType.QNA,
                selected_model=model_option,
                selected_model_label=model_option.external_model_id,
                status=AIInteractionLog.Status.FAILED,
                error_message=str(exc),
            )
            raise

        return CourseAnswer(
            answer=result.content,
            sources=[chunk.source_label for chunk in chunks],
            model_option=model_option,
        )


class QuizGenerationService:
    MIN_LESSON_TEXT = 280

    def __init__(self, provider=None, retriever=None, selection_service=None):
        self.provider = provider or OpenRouterProvider()
        self.retriever = retriever or CourseContentRetriever()
        self.selection_service = selection_service or AIModelSelectionService()

    def generate_for_lesson(self, *, request, lesson):
        lesson_text = self.retriever.collect_lesson_text(lesson)
        if len(lesson_text.strip()) < self.MIN_LESSON_TEXT:
            raise AIValidationError("Для качественной генерации теста в уроке пока недостаточно содержательного текста.")

        model_option = self.selection_service.get_selected_model(request)
        if model_option is None:
            raise AIUnavailableError("Каталог моделей ИИ пока не подготовлен.")

        messages = build_quiz_generation_messages(lesson=lesson, lesson_text=lesson_text)
        attempt_errors = []
        parsed_payload = None

        for attempt in range(2):
            try:
                result = self.provider.chat(
                    model_id=model_option.external_model_id,
                    messages=messages,
                    response_format=QUIZ_RESPONSE_SCHEMA if model_option.supports_structured_output else None,
                    require_parameters=model_option.supports_structured_output,
                    temperature=0.2,
                    max_tokens=1800,
                )
                parsed_payload = validate_generated_quiz_payload(result.content)
                break
            except AIValidationError as exc:
                attempt_errors.append(str(exc))
                messages = messages + [
                    {
                        "role": "user",
                        "content": "Повтори ответ и верни только валидный JSON по схеме. Без пояснений и markdown.",
                    }
                ]
            except (AIProviderError, AIUnavailableError) as exc:
                logger.warning("AI quiz generation failed", exc_info=exc)
                AIInteractionLog.objects.create(
                    user=request.user,
                    course=lesson.course,
                    lesson=lesson,
                    action_type=AIInteractionLog.ActionType.QUIZ_GENERATION,
                    selected_model=model_option,
                    selected_model_label=model_option.external_model_id,
                    status=AIInteractionLog.Status.FAILED,
                    error_message=str(exc),
                )
                raise

        if parsed_payload is None:
            raise AIValidationError(attempt_errors[-1] if attempt_errors else "Не удалось разобрать AI-тест.")

        draft = self._create_draft_quiz(lesson=lesson, payload=parsed_payload)
        AIInteractionLog.objects.create(
            user=request.user,
            course=lesson.course,
            lesson=lesson,
            action_type=AIInteractionLog.ActionType.QUIZ_GENERATION,
            selected_model=model_option,
            selected_model_label=model_option.external_model_id,
            status=AIInteractionLog.Status.SUCCESS,
        )
        return GeneratedQuizDraft(block=draft.lesson_block, quiz=draft, model_option=model_option)

    @transaction.atomic
    def _create_draft_quiz(self, *, lesson, payload):
        quiz_block = LessonBlock(
            lesson=lesson,
            block_type=LessonBlock.BlockType.QUIZ,
            title=payload["title"],
            position=0,
            is_required=True,
        )
        insert_block(lesson, quiz_block, after_id=lesson.blocks.order_by("-position").values_list("id", flat=True).first())
        quiz = Quiz.objects.create(
            lesson_block=quiz_block,
            title=payload["title"],
            description=payload["description"],
            is_ai_draft=True,
        )
        for question_payload in payload["questions"]:
            question = QuizQuestion.objects.create(
                quiz=quiz,
                question_type=question_payload["question_type"],
                text=question_payload["text"],
                position=question_payload["position"],
                score=question_payload["score"],
                explanation=question_payload["explanation"],
            )
            for option_payload in question_payload["options"]:
                QuizOption.objects.create(
                    question=question,
                    text=option_payload["text"],
                    is_correct=option_payload["is_correct"],
                    position=option_payload["position"],
                )
        quiz.update_max_score()
        if quiz.max_score:
            quiz.passing_score = max(1, round(quiz.max_score * Decimal("0.7")))
            quiz.save(update_fields=["passing_score", "updated_at"])
        return quiz
