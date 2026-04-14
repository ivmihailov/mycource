from django.urls import path

from apps.ai_support.views import (
    advice_panel,
    course_qna_panel,
    ask_course_question,
    ask_lesson_question,
    generate_lesson_quiz,
    lesson_qna_panel,
    select_model,
)

app_name = "ai_support"

urlpatterns = [
    path("advice/", advice_panel, name="advice"),
    path("select-model/", select_model, name="select_model"),
    path("courses/<slug:slug>/panel/", course_qna_panel, name="course_panel"),
    path("courses/<slug:slug>/ask/", ask_course_question, name="ask_course"),
    path("courses/<slug:course_slug>/lessons/<slug:lesson_slug>/panel/", lesson_qna_panel, name="lesson_panel"),
    path("courses/<slug:course_slug>/lessons/<slug:lesson_slug>/ask/", ask_lesson_question, name="ask_lesson"),
    path("courses/<slug:course_slug>/lessons/<slug:lesson_slug>/generate-quiz/", generate_lesson_quiz, name="generate_quiz"),
]
