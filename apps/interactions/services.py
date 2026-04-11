from django.db import models
from django.db.models import Avg


def refresh_course_rating(course):
    stats = course.reviews.aggregate(average=Avg("rating"), count=models.Count("id"))
    course.average_rating = stats["average"] or 0
    course.reviews_count = stats["count"] or 0
    course.save(update_fields=["average_rating", "reviews_count", "updated_at"])
    return course
