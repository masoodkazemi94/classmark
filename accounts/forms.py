from django import forms
from django.contrib.auth import get_user_model


class PromoteCRForm(forms.Form):
    student = forms.ModelChoiceField(queryset=get_user_model().objects.none())

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["student"].queryset = get_user_model().objects.filter(
            role=get_user_model().Role.STUDENT,
            is_active=True,
        ).order_by("username")
