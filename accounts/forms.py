from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm

from courses.models import Course


PERSONAL_PROFILE_FIELDS = (
    "first_name",
    "last_name",
    "email",
    "phone_number",
    "passport_number",
    "passport_expiry",
    "is_in_dormitory",
    "dormitory_room",
    "wechat_id",
)
ADMINISTRATIVE_RECEIPT_FIELDS = (
    "insurance_receipt",
    "tuition_receipt",
    "dormitory_receipt",
)


def _can_edit_receipts(actor):
    user_model = get_user_model()
    return actor.is_superuser or actor.role in {
        user_model.Role.ADMIN,
        user_model.Role.MONITOR,
    }


class ProfileForm(forms.ModelForm):
    class Meta:
        model = get_user_model()
        fields = PERSONAL_PROFILE_FIELDS
        widgets = {
            "passport_expiry": forms.DateInput(attrs={"type": "date"}),
        }
        help_texts = {
            "email": "Class and attendance notifications are sent to this address.",
            "dormitory_room": "Leave blank if you do not live in the dormitory.",
        }


class StudentChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, student):
        name = student.get_full_name() or student.username
        role = " · CR" if student.role == student.Role.CR else ""
        return f"{name} (@{student.username}) · {student.student_code}{role}"


class PromoteCRForm(forms.Form):
    student = StudentChoiceField(queryset=get_user_model().objects.none())

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["student"].queryset = get_user_model().objects.filter(
            role=get_user_model().Role.STUDENT,
            is_active=True,
        ).order_by("username")
        self.fields["student"].widget.attrs.update(
            {
                "data-searchable": "true",
                "data-placeholder": "Search students by name or code…",
            }
        )


class StudentCreateForm(UserCreationForm):
    course = forms.ModelChoiceField(
        queryset=Course.objects.none(),
        required=False,
        help_text="The student will be actively assigned to this course.",
    )

    class Meta(UserCreationForm.Meta):
        model = get_user_model()
        fields = (
            "username",
            "student_code",
            *PERSONAL_PROFILE_FIELDS,
            *ADMINISTRATIVE_RECEIPT_FIELDS,
        )
        widgets = {
            "passport_expiry": forms.DateInput(attrs={"type": "date"}),
        }

    def __init__(self, *args, actor, **kwargs):
        super().__init__(*args, **kwargs)
        if not _can_edit_receipts(actor):
            for field_name in ADMINISTRATIVE_RECEIPT_FIELDS:
                self.fields.pop(field_name)
        courses = Course.objects.filter(is_active=True)
        if actor.role == get_user_model().Role.CR:
            courses = courses.filter(
                enrollments__student=actor,
                enrollments__is_active=True,
            )
            self.fields["course"].required = True
            self.fields["course"].help_text = (
                "Required. Choose one of your assigned courses."
            )
        self.fields["course"].queryset = courses.distinct().order_by("code", "title")
        self.order_fields(
            [
                "username",
                "student_code",
                "first_name",
                "last_name",
                "email",
                "phone_number",
                "passport_number",
                "passport_expiry",
                "is_in_dormitory",
                "dormitory_room",
                "wechat_id",
                *ADMINISTRATIVE_RECEIPT_FIELDS,
                "course",
                "password1",
                "password2",
            ]
        )

    def save(self, commit=True):
        student = super().save(commit=False)
        student.role = get_user_model().Role.STUDENT
        if commit:
            student.save()
        return student


class StudentUpdateForm(forms.ModelForm):
    class Meta:
        model = get_user_model()
        fields = (
            "username",
            "student_code",
            *PERSONAL_PROFILE_FIELDS,
            *ADMINISTRATIVE_RECEIPT_FIELDS,
        )
        widgets = {
            "passport_expiry": forms.DateInput(attrs={"type": "date"}),
        }

    def __init__(self, *args, actor, **kwargs):
        super().__init__(*args, **kwargs)
        if not _can_edit_receipts(actor):
            for field_name in ADMINISTRATIVE_RECEIPT_FIELDS:
                self.fields.pop(field_name)
