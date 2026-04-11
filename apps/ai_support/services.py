from dataclasses import dataclass

from django.conf import settings


@dataclass
class AIAdvice:
    title: str
    body: str
    mode: str


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
            body="Сфокусируйтесь на ключевом определении, затем вернитесь к примеру и попробуйте коротко сформулировать вывод своими словами.",
            mode="mock",
        ),
    }

    def get_advice(self, context_type, payload):
        return self.RESPONSES.get(context_type, self.RESPONSES["student_hint"])


def get_ai_advisor():
    # TODO: Позже подключить реального провайдера LLM по настройке AI_PROVIDER.
    # TODO: Добавить аудит запросов к ИИ, лимиты и защиту от небезопасного контента.
    if not settings.AI_ENABLED:
        return MockAIAdvisor()
    return MockAIAdvisor()
