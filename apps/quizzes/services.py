from django.db import transaction
from django.utils import timezone

from apps.quizzes.models import Quiz, QuizAnswer, QuizAttempt, QuizOption, QuizQuestion


def get_or_create_draft_attempt(user, quiz):
    attempt = quiz.attempts.filter(user=user, submitted_at__isnull=True).first()
    if attempt:
        return attempt
    return QuizAttempt.objects.create(user=user, quiz=quiz)


@transaction.atomic
def evaluate_attempt(attempt, cleaned_answers):
    total_score = 0
    quiz = attempt.quiz
    attempt.answers.all().delete()

    for question in quiz.questions.prefetch_related("options"):
        selected_ids = set(cleaned_answers.get(str(question.pk), []))
        selected_options = list(QuizOption.objects.filter(question=question, pk__in=selected_ids))
        correct_ids = set(question.options.filter(is_correct=True).values_list("id", flat=True))
        is_correct = correct_ids == {option.id for option in selected_options}
        awarded_score = question.score if is_correct else 0

        answer = QuizAnswer.objects.create(
            attempt=attempt,
            question=question,
            is_correct=is_correct,
            awarded_score=awarded_score,
        )
        if selected_options:
            answer.selected_options.set(selected_options)
        total_score += awarded_score

    attempt.score = total_score
    attempt.passed = total_score >= quiz.effective_passing_score
    attempt.submitted_at = timezone.now()
    attempt.save(update_fields=["score", "passed", "submitted_at", "updated_at"])
    from apps.learning.services import sync_progress_after_quiz_attempt

    sync_progress_after_quiz_attempt(attempt)
    return attempt


@transaction.atomic
def duplicate_quiz(quiz, lesson_block):
    new_quiz = Quiz.all_objects.get(pk=quiz.pk)
    new_quiz.pk = None
    new_quiz.lesson_block = lesson_block
    new_quiz.save()

    for question in quiz.questions.order_by("position", "id"):
        new_question = QuizQuestion.objects.get(pk=question.pk)
        new_question.pk = None
        new_question.quiz = new_quiz
        new_question.save()

        for option in question.options.order_by("position", "id"):
            new_option = QuizOption.objects.get(pk=option.pk)
            new_option.pk = None
            new_option.question = new_question
            new_option.save()

    new_quiz.update_max_score()
    return new_quiz
