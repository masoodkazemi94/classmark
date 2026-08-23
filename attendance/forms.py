from django import forms
from django.contrib.auth import get_user_model
from django.db.models import Q

from accounts.forms import StudentChoiceField

from .models import AttendanceStatus, SessionSection


class SessionSectionChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, section):
        return f"Section {section.section_number}"


class ManualAttendanceForm(forms.Form):
    student = StudentChoiceField(queryset=get_user_model().objects.none())
    section = SessionSectionChoiceField(
        queryset=SessionSection.objects.none(),
        required=False,
        empty_label="All 3 sections",
        label="Apply to",
    )
    status = forms.ChoiceField(choices=AttendanceStatus.choices)
    note = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={"rows": 2}),
    )

    def __init__(self, *args, session, actor=None, **kwargs):
        super().__init__(*args, **kwargs)
        students = (
            get_user_model()
            .objects.filter(
                course_enrollments__course=session.course,
                course_enrollments__is_active=True,
            )
        )
        if actor and actor.role == get_user_model().Role.CR:
            students = students.filter(
                Q(role=get_user_model().Role.STUDENT) | Q(pk=actor.pk)
            )
        self.fields["student"].queryset = students.order_by("username")
        self.fields["student"].widget.attrs.update(
            {
                "data-searchable": "true",
                "data-placeholder": "Search enrolled students…",
            }
        )
        self.fields["section"].queryset = session.sections.order_by("section_number")
