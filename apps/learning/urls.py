from django.urls import path

from apps.learning.views import CourseStartView, FavoriteCoursesView, LearningOverviewView, LessonCompleteView, LessonDetailView

app_name = "learning"

urlpatterns = [
    path("", LearningOverviewView.as_view(), name="overview"),
    path("favorites/", FavoriteCoursesView.as_view(), name="favorites"),
    path("courses/<slug:slug>/start/", CourseStartView.as_view(), name="start_course"),
    path(
        "courses/<slug:course_slug>/lessons/<slug:lesson_slug>/",
        LessonDetailView.as_view(),
        name="lesson_detail",
    ),
    path(
        "courses/<slug:course_slug>/lessons/<slug:lesson_slug>/complete/",
        LessonCompleteView.as_view(),
        name="lesson_complete",
    ),
]
