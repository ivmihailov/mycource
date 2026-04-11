from django.urls import path

from apps.courses.views import (
    CourseArchiveView,
    CourseAuthorView,
    CourseCatalogView,
    CourseCreateView,
    CourseDeleteView,
    CourseDetailView,
    CourseDuplicateView,
    CoursePreviewView,
    CoursePublishView,
    CourseUpdateView,
    DraftCourseListView,
    MyCoursesListView,
)

app_name = "courses"

urlpatterns = [
    path("", CourseCatalogView.as_view(), name="catalog"),
    path("create/", CourseCreateView.as_view(), name="create"),
    path("mine/", MyCoursesListView.as_view(), name="my_courses"),
    path("drafts/", DraftCourseListView.as_view(), name="drafts"),
    path("authors/<str:username>/", CourseAuthorView.as_view(), name="author_detail"),
    path("<slug:slug>/", CourseDetailView.as_view(), name="detail"),
    path("<slug:slug>/edit/", CourseUpdateView.as_view(), name="update"),
    path("<slug:slug>/preview/", CoursePreviewView.as_view(), name="preview"),
    path("<slug:slug>/publish/", CoursePublishView.as_view(), name="publish"),
    path("<slug:slug>/archive/", CourseArchiveView.as_view(), name="archive"),
    path("<slug:slug>/delete/", CourseDeleteView.as_view(), name="delete"),
    path("<slug:slug>/duplicate/", CourseDuplicateView.as_view(), name="duplicate"),
]
