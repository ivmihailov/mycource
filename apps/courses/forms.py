from django import forms
from django.db.models import Q
from django.utils.translation import gettext_lazy as _

from apps.core.forms import StyledFormMixin
from apps.courses.models import Category, Course, Tag


class CourseForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = Course
        fields = (
            "title",
            "short_description",
            "full_description",
            "cover_image",
            "category",
            "tags",
            "level",
            "estimated_duration_minutes",
            "order_mode",
        )
        widgets = {
            "full_description": forms.Textarea(attrs={"rows": 10, "placeholder": _("Markdown-описание курса")}),
            "short_description": forms.Textarea(attrs={"rows": 3}),
            "tags": forms.SelectMultiple(),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["category"].queryset = Category.objects.for_ui()
        self.fields["tags"].queryset = Tag.objects.all()
        self.apply_styles()


class CourseFilterForm(StyledFormMixin, forms.Form):
    SORT_NEW = "new"
    SORT_POPULAR = "popular"
    SORT_TITLE = "title"
    SORT_RATING = "rating"

    q = forms.CharField(label=_("Поиск"), required=False)
    category = forms.ModelChoiceField(label=_("Категория"), queryset=Category.objects.none(), required=False)
    level = forms.ChoiceField(
        label=_("Уровень"),
        required=False,
        choices=[("", "Все")] + list(Course.Level.choices),
    )
    sort = forms.ChoiceField(
        label=_("Сортировка"),
        required=False,
        choices=[
            (SORT_NEW, _("Новые")),
            (SORT_POPULAR, _("Популярные")),
            (SORT_TITLE, _("По названию")),
            (SORT_RATING, _("По рейтингу")),
        ],
        initial=SORT_NEW,
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["category"].queryset = Category.objects.for_ui()
        self.apply_styles()

    def filter_queryset(self, queryset):
        if not self.is_valid():
            return queryset

        query = self.cleaned_data.get("q")
        category = self.cleaned_data.get("category")
        level = self.cleaned_data.get("level")
        sort = self.cleaned_data.get("sort") or self.SORT_NEW

        if query:
            queryset = queryset.filter(title__icontains=query)
        if category:
            queryset = queryset.filter(category=category)
        if level:
            queryset = queryset.filter(level=level)

        ordering_map = {
            self.SORT_NEW: ("-published_at", "-created_at"),
            self.SORT_POPULAR: ("-view_count", "-published_at"),
            self.SORT_TITLE: ("title",),
            self.SORT_RATING: ("-average_rating", "-reviews_count"),
        }
        return queryset.order_by(*ordering_map.get(sort, ordering_map[self.SORT_NEW]))
