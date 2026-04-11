from rest_framework import serializers

from apps.courses.models import Category, Course, Tag


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ("id", "name", "slug", "description")


class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = ("id", "name", "slug")


class CourseListSerializer(serializers.ModelSerializer):
    author = serializers.CharField(source="author.username")
    category = serializers.CharField(source="category.name")

    class Meta:
        model = Course
        fields = (
            "id",
            "title",
            "slug",
            "short_description",
            "level",
            "estimated_duration_minutes",
            "author",
            "category",
            "average_rating",
            "reviews_count",
            "published_at",
        )


class CourseDetailSerializer(serializers.ModelSerializer):
    author = serializers.CharField(source="author.username")
    category = CategorySerializer()
    tags = TagSerializer(many=True)

    class Meta:
        model = Course
        fields = (
            "id",
            "title",
            "slug",
            "short_description",
            "full_description",
            "level",
            "estimated_duration_minutes",
            "order_mode",
            "author",
            "category",
            "tags",
            "average_rating",
            "reviews_count",
            "published_at",
        )
