from django import forms


def apply_form_styles(form):
    for field in form.fields.values():
        classes = field.widget.attrs.get("class", "")
        widget = field.widget

        if isinstance(widget, forms.Textarea):
            ui_class = "form-control form-control-textarea"
        elif isinstance(widget, forms.SelectMultiple):
            ui_class = "form-control form-control-multiselect"
        elif isinstance(widget, forms.Select):
            ui_class = "form-control form-control-select"
        elif isinstance(widget, forms.FileInput):
            ui_class = "form-control form-control-file"
        elif isinstance(widget, forms.CheckboxInput):
            ui_class = "form-checkbox"
        elif isinstance(widget, (forms.CheckboxSelectMultiple, forms.RadioSelect)):
            ui_class = "choice-list"
        else:
            ui_class = "form-control"

        field.widget.attrs["class"] = f"{classes} {ui_class}".strip()


class StyledFormMixin:
    def apply_styles(self):
        apply_form_styles(self)
