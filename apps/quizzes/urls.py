from django.urls import path

from apps.quizzes.views import QuizQuestionDeleteView, QuizQuestionManageView, QuizResultView, QuizTakeView, QuizUpdateView

app_name = "quizzes"

urlpatterns = [
    path("<int:pk>/edit/", QuizUpdateView.as_view(), name="update"),
    path("<int:quiz_pk>/questions/create/", QuizQuestionManageView.as_view(), name="question_create"),
    path("<int:quiz_pk>/questions/<int:pk>/edit/", QuizQuestionManageView.as_view(), name="question_update"),
    path("<int:quiz_pk>/questions/<int:pk>/delete/", QuizQuestionDeleteView.as_view(), name="question_delete"),
    path("<int:pk>/take/", QuizTakeView.as_view(), name="take"),
    path("attempts/<int:pk>/result/", QuizResultView.as_view(), name="result"),
]
