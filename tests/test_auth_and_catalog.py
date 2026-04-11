import pytest
from django.core import mail
from django.urls import reverse
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

from apps.interactions.models import FavoriteCourse
from apps.users.tokens import email_verification_token


@pytest.mark.django_db
def test_registration_sends_verification_email(client, settings):
    settings.EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
    response = client.post(
        reverse("users:register"),
        {
            "username": "newuser",
            "email": "newuser@example.com",
            "first_name": "New",
            "last_name": "User",
            "password1": "StrongPass123!",
            "password2": "StrongPass123!",
        },
    )

    assert response.status_code == 302
    assert len(mail.outbox) == 1
    assert "Подтверждение email" in mail.outbox[0].subject


@pytest.mark.django_db
def test_email_confirmation_flow(client, user):
    client.force_login(user)
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = email_verification_token.make_token(user)

    response = client.get(reverse("users:verify_email", kwargs={"uidb64": uid, "token": token}))
    user.refresh_from_db()

    assert response.status_code == 302
    assert user.is_email_verified is True


@pytest.mark.django_db
def test_guest_cannot_open_other_users_draft(client, draft_course):
    response = client.get(reverse("courses:detail", kwargs={"slug": draft_course.slug}))
    assert response.status_code == 404


@pytest.mark.django_db
def test_author_can_create_course(client, author, category):
    client.force_login(author)
    response = client.post(
        reverse("courses:create"),
        {
            "title": "New Course",
            "short_description": "Кратко",
            "full_description": "Описание",
            "category": category.pk,
            "tags": [],
            "level": "beginner",
            "estimated_duration_minutes": 30,
            "order_mode": "free_order",
        },
    )

    assert response.status_code == 302
    assert author.courses.filter(title="New Course").exists()


@pytest.mark.django_db
def test_comment_review_and_favorite_flow(client, user, published_course):
    client.force_login(user)

    client.post(reverse("interactions:add_comment", kwargs={"slug": published_course.slug}), {"body": "Интересный курс"})
    client.post(reverse("interactions:upsert_review", kwargs={"slug": published_course.slug}), {"rating": 5, "body": "Сильный материал"})
    client.post(reverse("interactions:toggle_favorite", kwargs={"slug": published_course.slug}))

    published_course.refresh_from_db()

    assert published_course.comments.count() == 1
    assert published_course.reviews.count() == 1
    assert float(published_course.average_rating) == 5.0
    assert FavoriteCourse.objects.filter(user=user, course=published_course).exists()
