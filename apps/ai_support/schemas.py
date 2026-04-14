import json

from apps.ai_support.exceptions import AIValidationError
from apps.quizzes.models import QuizQuestion


QUIZ_RESPONSE_SCHEMA = {
    "type": "json_schema",
    "json_schema": {
        "name": "generated_quiz",
        "strict": True,
        "schema": {
            "type": "object",
            "properties": {
                "title": {"type": "string"},
                "description": {"type": "string"},
                "questions": {
                    "type": "array",
                    "minItems": 3,
                    "maxItems": 5,
                    "items": {
                        "type": "object",
                        "properties": {
                            "question_type": {
                                "type": "string",
                                "enum": [
                                    QuizQuestion.QuestionType.SINGLE,
                                    QuizQuestion.QuestionType.MULTIPLE,
                                    QuizQuestion.QuestionType.TRUE_FALSE,
                                ],
                            },
                            "text": {"type": "string"},
                            "score": {"type": "integer", "minimum": 1, "maximum": 10},
                            "explanation": {"type": "string"},
                            "options": {
                                "type": "array",
                                "minItems": 2,
                                "maxItems": 6,
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "text": {"type": "string"},
                                        "is_correct": {"type": "boolean"},
                                    },
                                    "required": ["text", "is_correct"],
                                    "additionalProperties": False,
                                },
                            },
                        },
                        "required": ["question_type", "text", "score", "options"],
                        "additionalProperties": False,
                    },
                },
            },
            "required": ["title", "description", "questions"],
            "additionalProperties": False,
        },
    },
}


def load_json_payload(raw_content):
    if isinstance(raw_content, dict):
        return raw_content
    try:
        return json.loads(raw_content)
    except json.JSONDecodeError as exc:
        raise AIValidationError("Не удалось разобрать JSON-ответ модели.") from exc


def validate_generated_quiz_payload(raw_content):
    payload = load_json_payload(raw_content)
    if not isinstance(payload, dict):
        raise AIValidationError("Ожидался JSON-объект с тестом.")

    title = str(payload.get("title") or "").strip()
    description = str(payload.get("description") or "").strip()
    questions = payload.get("questions")
    if not title or not isinstance(questions, list) or len(questions) < 3:
        raise AIValidationError("Модель вернула неполный тест.")

    normalized_questions = []
    for index, item in enumerate(questions, start=1):
        question_type = str(item.get("question_type") or "").strip()
        if question_type not in {
            QuizQuestion.QuestionType.SINGLE,
            QuizQuestion.QuestionType.MULTIPLE,
            QuizQuestion.QuestionType.TRUE_FALSE,
        }:
            raise AIValidationError("Модель вернула неподдерживаемый тип вопроса.")

        options = item.get("options") or []
        if len(options) < 2:
            raise AIValidationError("У каждого вопроса должно быть минимум два варианта ответа.")
        normalized_options = []
        correct_count = 0
        for option_index, option in enumerate(options, start=1):
            option_text = str(option.get("text") or "").strip()
            is_correct = bool(option.get("is_correct"))
            if not option_text:
                raise AIValidationError("Пустой вариант ответа в AI-тесте.")
            if is_correct:
                correct_count += 1
            normalized_options.append(
                {
                    "text": option_text,
                    "is_correct": is_correct,
                    "position": option_index,
                }
            )

        if question_type == QuizQuestion.QuestionType.SINGLE and correct_count != 1:
            raise AIValidationError("Для single choice нужен ровно один правильный ответ.")
        if question_type == QuizQuestion.QuestionType.MULTIPLE and correct_count < 2:
            raise AIValidationError("Для multiple choice нужно минимум два правильных ответа.")
        if question_type == QuizQuestion.QuestionType.TRUE_FALSE and len(normalized_options) != 2:
            raise AIValidationError("True/False вопрос должен содержать ровно два варианта ответа.")

        normalized_questions.append(
            {
                "question_type": question_type,
                "text": str(item.get("text") or "").strip(),
                "score": int(item.get("score") or 1),
                "explanation": str(item.get("explanation") or "").strip(),
                "position": index,
                "options": normalized_options,
            }
        )

    return {
        "title": title,
        "description": description,
        "questions": normalized_questions,
    }
