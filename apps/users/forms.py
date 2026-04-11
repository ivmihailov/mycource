from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.utils.translation import gettext_lazy as _

from apps.core.forms import StyledFormMixin
from apps.users.models import User


class RegistrationForm(StyledFormMixin, UserCreationForm):
    email = forms.EmailField(label=_("Email"))
    first_name = forms.CharField(label=_("Имя"), required=False)
    last_name = forms.CharField(label=_("Фамилия"), required=False)

    class Meta:
        model = User
        fields = ("username", "email", "first_name", "last_name", "password1", "password2")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.apply_styles()

    def clean_email(self):
        email = self.cleaned_data["email"].lower()
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError(_("Пользователь с таким email уже существует."))
        return email


class StyledAuthenticationForm(StyledFormMixin, AuthenticationForm):
    username = forms.CharField(label=_("Логин"))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.apply_styles()


class ProfileUpdateForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = User
        fields = ("username", "email", "first_name", "last_name", "avatar", "bio")
        widgets = {
            "bio": forms.Textarea(attrs={"rows": 5}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.apply_styles()

    def clean_email(self):
        email = self.cleaned_data["email"].lower()
        queryset = User.objects.filter(email=email).exclude(pk=self.instance.pk)
        if queryset.exists():
            raise forms.ValidationError(_("Этот email уже используется другим пользователем."))
        return email
