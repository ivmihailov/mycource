from django import forms
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

from apps.core.forms import StyledFormMixin
from apps.lessons.models import Lesson, LessonBlock, PracticeTask


class LessonForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = Lesson
        fields = ("title", "short_description", "estimated_duration_minutes")
        widgets = {
            "short_description": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.apply_styles()


class LessonBlockForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = LessonBlock
        fields = (
            "block_type",
            "title",
            "content_markdown",
            "image",
            "file",
            "code_language",
            "code_content",
            "note_style",
            "is_required",
        )
        widgets = {
            "content_markdown": forms.Textarea(attrs={"rows": 6}),
            "code_content": forms.Textarea(attrs={"rows": 8}),
        }

    def __init__(self, *args, allow_type_edit=True, **kwargs):
        super().__init__(*args, **kwargs)
        self.apply_styles()
        if not allow_type_edit:
            self.fields["block_type"].disabled = True

    def clean(self):
        cleaned_data = super().clean()
        block_type = cleaned_data.get("block_type")
        content_markdown = cleaned_data.get("content_markdown")
        image = cleaned_data.get("image")
        file = cleaned_data.get("file")
        code_content = cleaned_data.get("code_content")

        if block_type in {LessonBlock.BlockType.TEXT, LessonBlock.BlockType.QUOTE} and not content_markdown:
            raise ValidationError(_("Для выбранного типа блока нужен Markdown-контент."))
        if block_type == LessonBlock.BlockType.IMAGE and not (image or self.instance.image):
            raise ValidationError(_("Для блока изображения нужно загрузить файл."))
        if block_type == LessonBlock.BlockType.FILE and not (file or self.instance.file):
            raise ValidationError(_("Для файлового блока нужен PDF-файл."))
        if block_type == LessonBlock.BlockType.CODE and not code_content:
            raise ValidationError(_("Для кодового блока нужно заполнить код."))
        return cleaned_data


class PracticeTaskForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = PracticeTask
        fields = (
            "title",
            "description_markdown",
            "language",
            "starter_code",
            "expected_output_description",
            "is_active",
        )
        widgets = {
            "description_markdown": forms.Textarea(attrs={"rows": 5}),
            "starter_code": forms.Textarea(attrs={"rows": 8}),
            "expected_output_description": forms.Textarea(attrs={"rows": 4}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.apply_styles()
