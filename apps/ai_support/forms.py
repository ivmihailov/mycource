from django import forms

from apps.ai_support.models import AIModelOption
from apps.core.forms import StyledFormMixin


class AIQuestionForm(StyledFormMixin, forms.Form):
    question = forms.CharField(
        label="Ваш вопрос",
        max_length=500,
        widget=forms.Textarea(
            attrs={
                "rows": 3,
                "placeholder": "Сформулируйте вопрос по текущему курсу или уроку.",
            }
        ),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.apply_styles()


class AIModelSelectionForm(StyledFormMixin, forms.Form):
    role_type = forms.ChoiceField(label="Модель ИИ", choices=AIModelOption.RoleType.choices)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.apply_styles()
