from django.urls import path

from apps.api.views import CategoryListAPIView, PublishedCourseDetailAPIView, PublishedCourseListAPIView, TagListAPIView

app_name = "api"

urlpatterns = [
    path("courses/", PublishedCourseListAPIView.as_view(), name="course_list"),
    path("courses/<slug:slug>/", PublishedCourseDetailAPIView.as_view(), name="course_detail"),
    path("categories/", CategoryListAPIView.as_view(), name="category_list"),
    path("tags/", TagListAPIView.as_view(), name="tag_list"),
]
