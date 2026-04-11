from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import LoginView
from django.shortcuts import get_object_or_404, redirect
from django.utils.encoding import force_str
from django.utils.http import urlsafe_base64_decode
from django.views import View
from django.views.generic import CreateView, DetailView, TemplateView, UpdateView

from apps.users.forms import ProfileUpdateForm, RegistrationForm, StyledAuthenticationForm
from apps.users.models import User
from apps.users.services import send_verification_email
from apps.users.tokens import email_verification_token


class UserLoginView(LoginView):
    authentication_form = StyledAuthenticationForm
    template_name = "registration/login.html"


class RegisterView(CreateView):
    model = User
    form_class = RegistrationForm
    template_name = "users/register.html"

    def form_valid(self, form):
        response = super().form_valid(form)
        send_verification_email(self.object, request=self.request)
        messages.success(
            self.request,
            "Аккаунт создан. Мы отправили письмо для подтверждения email.",
        )
        login(self.request, self.object)
        return response

    def get_success_url(self):
        return self.object.get_absolute_url() if hasattr(self.object, "get_absolute_url") else "/accounts/profile/"


class EmailVerificationSentView(TemplateView):
    template_name = "users/email_verification_sent.html"


class VerifyEmailView(View):
    def get(self, request, uidb64, token):
        try:
            uid = force_str(urlsafe_base64_decode(uidb64))
            user = get_object_or_404(User, pk=uid)
        except (TypeError, ValueError, OverflowError):
            user = None

        if user and email_verification_token.check_token(user, token):
            user.is_email_verified = True
            user.save(update_fields=["is_email_verified", "updated_at"])
            messages.success(request, "Email успешно подтвержден.")
        else:
            messages.error(request, "Ссылка подтверждения недействительна или устарела.")
        if request.user.is_authenticated:
            return redirect("users:profile")
        return redirect("users:login")


class ProfileView(LoginRequiredMixin, DetailView):
    model = User
    template_name = "users/profile.html"

    def get_object(self, queryset=None):
        return self.request.user


class ProfileUpdateView(LoginRequiredMixin, UpdateView):
    model = User
    form_class = ProfileUpdateForm
    template_name = "users/profile_form.html"

    def get_object(self, queryset=None):
        return self.request.user

    def form_valid(self, form):
        email_changed = "email" in form.changed_data
        response = super().form_valid(form)
        if email_changed:
            self.object.is_email_verified = False
            self.object.save(update_fields=["is_email_verified", "updated_at"])
            send_verification_email(self.object, request=self.request)
            messages.info(self.request, "Email изменен. Подтвердите новый адрес через письмо.")
        else:
            messages.success(self.request, "Профиль обновлен.")
        return response

    def get_success_url(self):
        return self.object.get_absolute_url() if hasattr(self.object, "get_absolute_url") else "/accounts/profile/"
