from django import forms
from django.forms import inlineformset_factory
from django.utils.translation import gettext_lazy as _

from apps.core.forms import StyledFormMixin
from apps.quizzes.models import Quiz, QuizOption, QuizQuestion


class QuizForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = Quiz
        fields = ("title", "description", "passing_score")
        widgets = {
            "description": forms.Textarea(attrs={"rows": 4}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.apply_styles()


class QuizQuestionForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = QuizQuestion
        fields = ("question_type", "text", "score", "explanation")
        widgets = {
            "text": forms.Textarea(attrs={"rows": 4}),
            "explanation": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.apply_styles()


QuizOptionFormSet = inlineformset_factory(
    QuizQuestion,
    QuizOption,
    fields=("text", "is_correct", "position"),
    extra=4,
    can_delete=True,
)


class QuizAttemptForm(forms.Form):
    def __init__(self, quiz, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.quiz = quiz
        for question in quiz.questions.prefetch_related("options").order_by("position", "id"):
            choices = [(str(option.pk), option.text) for option in question.options.order_by("position", "id")]
            field_name = str(question.pk)
            common_kwargs = {
                "label": question.text,
                "required": True,
                "help_text": f"Баллов: {question.score}",
                "choices": choices,
            }
            if question.question_type == QuizQuestion.QuestionType.MULTIPLE:
                self.fields[field_name] = forms.MultipleChoiceField(
                    widget=forms.CheckboxSelectMultiple,
                    **common_kwargs,
                )
            else:
                self.fields[field_name] = forms.ChoiceField(
                    widget=forms.RadioSelect,
                    **common_kwargs,
                )

    def get_selected_options(self):
        result = {}
        for field_name, value in self.cleaned_data.items():
            if isinstance(value, str):
                result[field_name] = [value]
            else:
                result[field_name] = value
        return result
