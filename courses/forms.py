from django import forms
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError

from accounts.forms import StudentChoiceField
from attendance.models import ClassSession

from .models import Course, Enrollment


class CourseForm(forms.ModelForm):
    class Meta:
        model = Course
        fields = ("title", "code", "start_date", "end_date")
        widgets = {
            "start_date": forms.DateInput(attrs={"type": "date"}),
            "end_date": forms.DateInput(attrs={"type": "date"}),
        }

    def __init__(self, *args, monitor, **kwargs):
        super().__init__(*args, **kwargs)
        self.monitor = monitor
        self.instance.monitor = monitor

    def clean_code(self):
        code = self.cleaned_data["code"].strip().upper()
        if Course.objects.filter(code__iexact=code).exists():
            raise ValidationError("A course with this code already exists.")
        return code

    def save(self, commit=True):
        course = super().save(commit=False)
        course.monitor = self.monitor
        if commit:
            course.save()
        return course


class ClassSessionForm(forms.ModelForm):
    class Meta:
        model = ClassSession
        fields = ("date", "start_time", "end_time")
        widgets = {
            "date": forms.DateInput(attrs={"type": "date"}),
            "start_time": forms.TimeInput(attrs={"type": "time"}),
            "end_time": forms.TimeInput(attrs={"type": "time"}),
        }

    def __init__(self, *args, course, **kwargs):
        super().__init__(*args, **kwargs)
        self.course = course

    def clean_date(self):
        session_date = self.cleaned_data["date"]
        if ClassSession.objects.filter(
            course=self.course,
            date=session_date,
        ).exists():
            raise ValidationError("A session already exists for this course and date.")
        return session_date

    def save(self, commit=True):
        session = super().save(commit=False)
        session.course = self.course
        if commit:
            session.save()
        return session


class EnrollmentForm(forms.Form):
    student = StudentChoiceField(queryset=get_user_model().objects.none())

    def __init__(self, *args, course, actor, **kwargs):
        super().__init__(*args, **kwargs)
        roles = [get_user_model().Role.STUDENT]
        if actor.role != get_user_model().Role.CR:
            roles.append(get_user_model().Role.CR)
        enrolled_ids = Enrollment.objects.filter(
            course=course,
            is_active=True,
        ).values_list("student_id", flat=True)
        self.fields["student"].queryset = (
            get_user_model()
            .objects.filter(role__in=roles, is_active=True)
            .exclude(pk__in=enrolled_ids)
            .order_by("username")
        )
        self.fields["student"].widget.attrs.update(
            {
                "data-searchable": "true",
                "data-placeholder": "Search students by name or code…",
            }
        )
