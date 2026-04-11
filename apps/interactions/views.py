from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import Http404, HttpResponseRedirect
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.urls import reverse
from django.views.decorators.http import require_POST

from apps.courses.models import Course
from apps.interactions.forms import CourseCommentForm, CourseReviewForm
from apps.interactions.models import CourseComment, CourseReview, FavoriteCourse
from apps.interactions.services import refresh_course_rating


def get_interactive_course(request, slug):
    return get_object_or_404(
        Course.all_objects.visible_for_user(request.user).select_related("author", "category"),
        slug=slug,
    )


@login_required
@require_POST
def toggle_favorite(request, slug):
    course = get_interactive_course(request, slug)
    favorite, created = FavoriteCourse.objects.get_or_create(user=request.user, course=course)
    if not created:
        favorite.delete()
        is_favorite = False
        messages.info(request, "Курс удален из избранного.")
    else:
        is_favorite = True
        messages.success(request, "Курс добавлен в избранное.")

    if request.htmx:
        return render(
            request,
            "interactions/partials/favorite_button.html",
            {"course": course, "is_favorite": is_favorite},
        )
    return redirect(course.get_absolute_url())


@login_required
@require_POST
def add_comment(request, slug):
    course = get_interactive_course(request, slug)
    form = CourseCommentForm(request.POST)
    if form.is_valid():
        comment = form.save(commit=False)
        comment.course = course
        comment.author = request.user
        comment.save()
        messages.success(request, "Комментарий добавлен.")
        form = CourseCommentForm()
    comments = course.comments.select_related("author").order_by("-created_at")
    if request.htmx:
        return render(
            request,
            "interactions/partials/comment_section.html",
            {"course": course, "comment_form": form, "comments": comments},
        )
    return redirect(course.get_absolute_url())


@login_required
@require_POST
def delete_comment(request, pk):
    comment = get_object_or_404(CourseComment.all_objects.select_related("course", "author"), pk=pk)
    if not (request.user.is_staff or comment.author == request.user or comment.course.author == request.user):
        raise Http404
    course = comment.course
    comment.soft_delete()
    messages.info(request, "Комментарий скрыт.")
    return redirect(course.get_absolute_url())


@login_required
@require_POST
def upsert_review(request, slug):
    course = get_interactive_course(request, slug)
    review = CourseReview.objects.filter(course=course, author=request.user).first()
    form = CourseReviewForm(request.POST, instance=review)
    if form.is_valid():
        review = form.save(commit=False)
        review.course = course
        review.author = request.user
        review.save()
        refresh_course_rating(course)
        messages.success(request, "Отзыв сохранен.")
    else:
        messages.error(request, "Не удалось сохранить отзыв.")
    return redirect(course.get_absolute_url())
