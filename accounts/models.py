from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
from django.db import models


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

    def clean(self):
        super().clean()

        if self.role in {self.Role.STUDENT, self.Role.CR} and not self.student_code:
            raise ValidationError(
                {"student_code": "Student and CR users must have a student code."}
            )

    def __str__(self):
        return self.username
