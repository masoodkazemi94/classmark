from django import forms
from django.db import models

from courses.models import Course


class CourseChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, course):
        status = "Active" if course.is_active else "Inactive"
        return f"{course.code} · {course.title} · {status}"


class ReportGenerationForm(forms.Form):
    class Output(models.TextChoices):
        VIEW = "VIEW", "View interactive report"
        SUMMARY_CSV = "SUMMARY_CSV", "Download summary CSV"
        DETAIL_CSV = "DETAIL_CSV", "Download detailed CSV"

    course = CourseChoiceField(
        queryset=Course.objects.none(),
        widget=forms.Select(
            attrs={
                "data-searchable": "true",
                "data-placeholder": "Search courses by code or title…",
                "data-empty-message": "No matching courses",
            }
        ),
    )
    output = forms.ChoiceField(
        choices=Output.choices,
        widget=forms.RadioSelect,
        initial=Output.VIEW,
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["course"].queryset = Course.objects.order_by("code", "title")
