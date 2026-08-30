from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone


class User(AbstractUser):
    class Role(models.TextChoices):
        ADMIN = "ADMIN", "Admin"
        MONITOR = "MONITOR", "Monitor"
        CR = "CR", "CR (Monitor Assistant)"
        STUDENT = "STUDENT", "Student"

    role = models.CharField(
        max_length=10,
        choices=Role.choices,
        default=Role.STUDENT,
    )
    student_code = models.CharField(
        max_length=50,
        unique=True,
        null=True,
        blank=True,
    )
    phone_number = models.CharField(max_length=20, blank=True)
    passport_number = models.CharField(max_length=100, blank=True)
    passport_expiry = models.DateField(blank=True, null=True)
    is_in_dormitory = models.BooleanField(default=False)
    dormitory_room = models.CharField(max_length=100, blank=True)
    wechat_id = models.CharField(max_length=100, blank=True)
    insurance_receipt = models.BooleanField(default=False)
    tuition_receipt = models.BooleanField(default=False)
    dormitory_receipt = models.BooleanField(default=False)

    def clean(self):
        super().clean()

        if self.role in {self.Role.STUDENT, self.Role.CR} and not self.student_code:
            raise ValidationError(
                {"student_code": "Student and CR users must have a student code."}
            )

    def __str__(self):
        return self.username


class Notification(models.Model):
    class Kind(models.TextChoices):
        CLASS_SESSION = "CLASS_SESSION", "Class session"
        ATTENDANCE = "ATTENDANCE", "Attendance status"

    class EmailStatus(models.TextChoices):
        PENDING = "PENDING", "Pending"
        SENT = "SENT", "Sent"
        FAILED = "FAILED", "Failed"
        SKIPPED = "SKIPPED", "Skipped"

    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notifications",
    )
    kind = models.CharField(max_length=20, choices=Kind.choices)
    title = models.CharField(max_length=200)
    message = models.TextField()
    course = models.ForeignKey(
        "courses.Course",
        on_delete=models.CASCADE,
        related_name="notifications",
        blank=True,
        null=True,
    )
    session = models.ForeignKey(
        "attendance.ClassSession",
        on_delete=models.CASCADE,
        related_name="notifications",
        blank=True,
        null=True,
    )
    attendance_record = models.ForeignKey(
        "attendance.AttendanceRecord",
        on_delete=models.SET_NULL,
        related_name="notifications",
        blank=True,
        null=True,
    )
    email_status = models.CharField(
        max_length=10,
        choices=EmailStatus.choices,
        default=EmailStatus.PENDING,
    )
    email_error = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    read_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        ordering = ("-created_at",)

    @property
    def is_read(self):
        return self.read_at is not None

    def mark_read(self):
        if self.read_at is None:
            self.read_at = timezone.now()
            self.save(update_fields=("read_at",))

    def __str__(self):
        return f"{self.title} for {self.recipient}"
