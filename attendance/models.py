import secrets

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.db.models import Q
from django.utils import timezone

from courses.models import Course, Enrollment


SESSION_SECTION_COUNT = 3
FIRST_SECTION_NUMBER = 1
SECTION_DURATION_MINUTES = 45
SECTION_COUNTED_HOURS = 1
ATTENDANCE_TOKEN_BYTES = 32


def generate_attendance_token():
    return secrets.token_urlsafe(ATTENDANCE_TOKEN_BYTES)


class AttendanceStatus(models.TextChoices):
    PRESENT = "PRESENT", "Present"
    LATE = "LATE", "Late"
    ABSENT = "ABSENT", "Absent"
    LEAVE = "LEAVE", "Leave"


class AttendanceRecordedMethod(models.TextChoices):
    MANUAL = "MANUAL", "Manual"
    QR = "QR", "QR"
    SYSTEM = "SYSTEM", "System"


class ClassSession(models.Model):
    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Draft"
        ACTIVE = "ACTIVE", "Active"
        CLOSED = "CLOSED", "Closed"

    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name="sessions",
    )
    date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField(blank=True, null=True)
    status = models.CharField(
        max_length=10,
        choices=Status.choices,
        default=Status.DRAFT,
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("course", "date"),
                name="unique_course_session_date",
            ),
        ]

    def clean(self):
        super().clean()

        if self.end_time and self.start_time and self.end_time <= self.start_time:
            raise ValidationError(
                {"end_time": "End time must be after the start time."}
            )

    def save(self, *args, **kwargs):
        is_new = self._state.adding
        original_pk = self.pk
        original_db = self._state.db

        try:
            with transaction.atomic():
                super().save(*args, **kwargs)
                if is_new:
                    SessionSection.objects.bulk_create(
                        [
                            SessionSection(session=self, section_number=section_number)
                            for section_number in range(
                                FIRST_SECTION_NUMBER,
                                SESSION_SECTION_COUNT + FIRST_SECTION_NUMBER,
                            )
                        ]
                    )
        except Exception:
            if is_new:
                self.pk = original_pk
                self._state.adding = True
                self._state.db = original_db
            raise

    def __str__(self):
        return f"{self.course} on {self.date}"


class SessionSection(models.Model):
    session = models.ForeignKey(
        ClassSession,
        on_delete=models.CASCADE,
        related_name="sections",
    )
    section_number = models.PositiveSmallIntegerField()
    duration_minutes = models.PositiveSmallIntegerField(
        default=SECTION_DURATION_MINUTES
    )
    counted_hours = models.PositiveSmallIntegerField(default=SECTION_COUNTED_HOURS)

    class Meta:
        ordering = ("section_number",)
        constraints = [
            models.UniqueConstraint(
                fields=("session", "section_number"),
                name="unique_session_section_number",
            ),
            models.CheckConstraint(
                condition=Q(
                    section_number__gte=FIRST_SECTION_NUMBER,
                    section_number__lte=SESSION_SECTION_COUNT,
                ),
                name="valid_session_section_number",
            ),
            models.CheckConstraint(
                condition=Q(duration_minutes=SECTION_DURATION_MINUTES),
                name="session_section_duration_is_45",
            ),
            models.CheckConstraint(
                condition=Q(counted_hours=SECTION_COUNTED_HOURS),
                name="session_section_counted_hours_is_1",
            ),
        ]

    def __str__(self):
        return f"{self.session} - Section {self.section_number}"


class AttendanceToken(models.Model):
    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name="attendance_tokens",
    )
    session = models.ForeignKey(
        ClassSession,
        on_delete=models.CASCADE,
        related_name="attendance_tokens",
    )
    section = models.ForeignKey(
        SessionSection,
        on_delete=models.CASCADE,
        related_name="attendance_tokens",
        blank=True,
        null=True,
    )
    token = models.CharField(
        max_length=128,
        unique=True,
        default=generate_attendance_token,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    is_active = models.BooleanField(default=True)

    def clean(self):
        super().clean()

        errors = {}

        if (
            self.course_id
            and self.session_id
            and not ClassSession.objects.filter(
                pk=self.session_id,
                course_id=self.course_id,
            ).exists()
        ):
            errors["session"] = "Session must belong to the selected course."

        if (
            self.session_id
            and self.section_id
            and not SessionSection.objects.filter(
                pk=self.section_id,
                session_id=self.session_id,
            ).exists()
        ):
            errors["section"] = "Section must belong to the selected session."

        if errors:
            raise ValidationError(errors)

    @property
    def is_expired(self):
        return timezone.now() >= self.expires_at

    @property
    def is_valid(self):
        return (
            bool(self.pk)
            and self.is_active
            and not self.is_expired
            and self.session.status == ClassSession.Status.ACTIVE
        )

    def __str__(self):
        return f"Attendance token for {self.session}"


class AttendanceRecord(models.Model):
    Status = AttendanceStatus
    RecordedMethod = AttendanceRecordedMethod

    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="attendance_records",
        limit_choices_to={"role__in": ("STUDENT", "CR")},
    )
    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name="attendance_records",
    )
    session = models.ForeignKey(
        ClassSession,
        on_delete=models.CASCADE,
        related_name="attendance_records",
    )
    section = models.ForeignKey(
        SessionSection,
        on_delete=models.CASCADE,
        related_name="attendance_records",
    )
    status = models.CharField(max_length=10, choices=Status.choices)
    recorded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="recorded_attendance_records",
        blank=True,
        null=True,
    )
    recorded_method = models.CharField(
        max_length=10,
        choices=RecordedMethod.choices,
        default=RecordedMethod.MANUAL,
    )
    recorded_at = models.DateTimeField(auto_now_add=True)
    note = models.TextField(blank=True)

    class Meta:
        ordering = ("-recorded_at",)
        constraints = [
            models.UniqueConstraint(
                fields=("student", "section"),
                name="unique_student_section_attendance",
            ),
            models.CheckConstraint(
                condition=Q(status__in=AttendanceStatus.values),
                name="valid_attendance_status",
            ),
            models.CheckConstraint(
                condition=Q(recorded_method__in=AttendanceRecordedMethod.values),
                name="valid_attendance_recorded_method",
            ),
        ]

    def clean(self):
        super().clean()

        errors = {}

        if (
            self.student_id
            and self.course_id
            and not Enrollment.objects.filter(
                course_id=self.course_id,
                student_id=self.student_id,
                is_active=True,
            ).exists()
        ):
            errors["student"] = "Student must be actively enrolled in the course."

        if (
            self.course_id
            and self.session_id
            and not ClassSession.objects.filter(
                pk=self.session_id,
                course_id=self.course_id,
            ).exists()
        ):
            errors["session"] = "Session must belong to the selected course."

        if (
            self.session_id
            and self.section_id
            and not SessionSection.objects.filter(
                pk=self.section_id,
                session_id=self.session_id,
            ).exists()
        ):
            errors["section"] = "Section must belong to the selected session."

        if errors:
            raise ValidationError(errors)

    def __str__(self):
        return f"{self.student} - {self.section}: {self.get_status_display()}"


class AttendanceAuditLog(models.Model):
    class Action(models.TextChoices):
        CREATED = "CREATED", "Created"
        UPDATED = "UPDATED", "Updated"

    attendance_record = models.ForeignKey(
        AttendanceRecord,
        on_delete=models.SET_NULL,
        related_name="audit_logs",
        blank=True,
        null=True,
    )
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="attendance_audit_logs",
    )
    course = models.ForeignKey(
        Course,
        on_delete=models.PROTECT,
        related_name="attendance_audit_logs",
    )
    session = models.ForeignKey(
        ClassSession,
        on_delete=models.PROTECT,
        related_name="attendance_audit_logs",
    )
    section = models.ForeignKey(
        SessionSection,
        on_delete=models.PROTECT,
        related_name="attendance_audit_logs",
    )
    action = models.CharField(max_length=10, choices=Action.choices)
    old_status = models.CharField(
        max_length=10,
        choices=AttendanceStatus.choices,
        blank=True,
    )
    new_status = models.CharField(max_length=10, choices=AttendanceStatus.choices)
    changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="attendance_changes_made",
        blank=True,
        null=True,
    )
    recorded_method = models.CharField(
        max_length=10,
        choices=AttendanceRecordedMethod.choices,
    )
    note = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-created_at", "-pk")

    def __str__(self):
        return f"{self.student} {self.action} {self.old_status or '-'} -> {self.new_status}"
