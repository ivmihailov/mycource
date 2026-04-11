from django.conf import settings
from django.contrib.sites.shortcuts import get_current_site
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

from apps.users.tokens import email_verification_token


def build_verification_url(request, user):
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = email_verification_token.make_token(user)
    path = reverse("users:verify_email", kwargs={"uidb64": uid, "token": token})
    if request is not None:
        return request.build_absolute_uri(path)

    domain = getattr(settings, "SITE_DOMAIN", "127.0.0.1:8000")
    protocol = getattr(settings, "SITE_PROTOCOL", "http")
    return f"{protocol}://{domain}{path}"


def send_verification_email(user, request=None):
    verification_url = build_verification_url(request, user)
    current_site = get_current_site(request).domain if request else settings.SITE_DOMAIN
    subject = "Подтверждение email на платформе «Мой Курс»"
    message = render_to_string(
        "users/email/verify_email.txt",
        {
            "user": user,
            "verification_url": verification_url,
            "site_name": settings.SITE_NAME,
            "current_site": current_site,
        },
    )
    send_mail(
        subject=subject,
        message=message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
        fail_silently=False,
    )
