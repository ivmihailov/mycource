from rest_framework import generics

from apps.api.serializers import CategorySerializer, CourseDetailSerializer, CourseListSerializer, TagSerializer
from apps.courses.models import Category, Course, Tag


class PublishedCourseListAPIView(generics.ListAPIView):
    serializer_class = CourseListSerializer
    queryset = (
        Course.objects.filter(status=Course.Status.PUBLISHED)
        .select_related("author", "category")
        .prefetch_related("tags")
    )


class PublishedCourseDetailAPIView(generics.RetrieveAPIView):
    serializer_class = CourseDetailSerializer
    lookup_field = "slug"
    queryset = (
        Course.objects.filter(status=Course.Status.PUBLISHED)
        .select_related("author", "category")
        .prefetch_related("tags")
    )


class CategoryListAPIView(generics.ListAPIView):
    serializer_class = CategorySerializer
    queryset = Category.objects.for_ui().order_by("name")


class TagListAPIView(generics.ListAPIView):
    serializer_class = TagSerializer
    queryset = Tag.objects.all().order_by("name")
