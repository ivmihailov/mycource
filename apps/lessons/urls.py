from django.urls import path

from apps.lessons.views import (
    BlockCreateView,
    BlockDeleteView,
    BlockDuplicateView,
    BlockSortView,
    BlockUpdateView,
    LessonBuilderView,
    LessonCreateView,
    LessonDeleteView,
    LessonDuplicateView,
    LessonSortView,
    LessonUpdateView,
    PracticeTaskCreateView,
)

app_name = "lessons"

urlpatterns = [
    path("course/<slug:course_slug>/create/", LessonCreateView.as_view(), name="create"),
    path("course/<slug:course_slug>/sort/", LessonSortView.as_view(), name="sort"),
    path("course/<slug:course_slug>/<slug:slug>/edit/", LessonUpdateView.as_view(), name="update"),
    path("course/<slug:course_slug>/<slug:slug>/builder/", LessonBuilderView.as_view(), name="builder"),
    path("course/<slug:course_slug>/<slug:slug>/delete/", LessonDeleteView.as_view(), name="delete"),
    path("course/<slug:course_slug>/<slug:slug>/duplicate/", LessonDuplicateView.as_view(), name="duplicate"),
    path("course/<slug:course_slug>/<slug:slug>/blocks/create/", BlockCreateView.as_view(), name="block_create"),
    path("blocks/<int:pk>/edit/", BlockUpdateView.as_view(), name="block_update"),
    path("blocks/<int:pk>/duplicate/", BlockDuplicateView.as_view(), name="block_duplicate"),
    path("blocks/<int:pk>/delete/", BlockDeleteView.as_view(), name="block_delete"),
    path("course/<slug:course_slug>/<slug:slug>/blocks/sort/", BlockSortView.as_view(), name="block_sort"),
    path("course/<slug:course_slug>/<slug:slug>/practice/create/", PracticeTaskCreateView.as_view(), name="practice_create"),
]
