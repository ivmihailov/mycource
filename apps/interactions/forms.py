from django import forms
from django.utils.translation import gettext_lazy as _

from apps.core.forms import StyledFormMixin
from apps.interactions.models import CourseComment, CourseReview


class CourseCommentForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = CourseComment
        fields = ("body",)
        widgets = {
            "body": forms.Textarea(attrs={"rows": 4, "placeholder": _("Напишите комментарий...")}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.apply_styles()


class CourseReviewForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = CourseReview
        fields = ("rating", "body")
        widgets = {
            "rating": forms.Select(
                choices=[(1, "1"), (2, "2"), (3, "3"), (4, "4"), (5, "5")],
            ),
            "body": forms.Textarea(attrs={"rows": 4, "placeholder": _("Поделитесь впечатлением о курсе...")}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.apply_styles()
