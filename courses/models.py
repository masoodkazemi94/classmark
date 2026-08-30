from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import F, Q


class Course(models.Model):
    title = models.CharField(max_length=200)
    code = models.CharField(max_length=50)
    monitor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="courses_created",
        limit_choices_to={"role__in": ("MONITOR", "ADMIN")},
    )
    start_date = models.DateField()
    end_date = models.DateField()
    is_active = models.BooleanField(default=True)
    attendance_location_name = models.CharField(max_length=200, blank=True)
    attendance_latitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        blank=True,
        null=True,
        validators=[MinValueValidator(-90), MaxValueValidator(90)],
    )
    attendance_longitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        blank=True,
        null=True,
        validators=[MinValueValidator(-180), MaxValueValidator(180)],
    )
    attendance_radius_meters = models.PositiveIntegerField(
        default=100,
        validators=[MinValueValidator(10), MaxValueValidator(5000)],
    )
    require_attendance_location = models.BooleanField(default=False)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=Q(end_date__gte=F("start_date")),
                name="course_end_date_on_or_after_start_date",
            ),
            models.CheckConstraint(
                condition=(
                    Q(attendance_latitude__isnull=True, attendance_longitude__isnull=True)
                    | Q(attendance_latitude__isnull=False, attendance_longitude__isnull=False)
                ),
                name="course_attendance_coordinates_are_paired",
            ),
            models.CheckConstraint(
                condition=Q(
                    attendance_radius_meters__gte=10,
                    attendance_radius_meters__lte=5000,
                ),
                name="course_attendance_radius_between_10_and_5000",
            ),
            models.CheckConstraint(
                condition=(
                    Q(require_attendance_location=False)
                    | Q(
                        attendance_latitude__isnull=False,
                        attendance_longitude__isnull=False,
                    )
                ),
                name="course_required_location_has_coordinates",
            ),
        ]

    def clean(self):
        super().clean()

        if self.monitor_id and self.monitor.role not in {
            self.monitor.Role.MONITOR,
            self.monitor.Role.ADMIN,
        }:
            raise ValidationError(
                {"monitor": "Only Monitor and Admin users can create a course."}
            )

        if self.start_date and self.end_date and self.end_date < self.start_date:
            raise ValidationError(
                {"end_date": "End date must be on or after the start date."}
            )

        coordinates = (self.attendance_latitude, self.attendance_longitude)
        if any(value is not None for value in coordinates) and not all(
            value is not None for value in coordinates
        ):
            raise ValidationError(
                {
                    "attendance_latitude": (
                        "Enter both latitude and longitude for the attendance location."
                    )
                }
            )

        if self.require_attendance_location and not all(
            value is not None for value in coordinates
        ):
            raise ValidationError(
                {
                    "require_attendance_location": (
                        "Set latitude and longitude before requiring location validation."
                    )
                }
            )

    def __str__(self):
        return f"{self.code} - {self.title}"


class Enrollment(models.Model):
    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name="enrollments",
    )
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="course_enrollments",
        limit_choices_to={"role__in": ("STUDENT", "CR")},
    )
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("course", "student"),
                name="unique_course_student_enrollment",
            ),
        ]

    def clean(self):
        super().clean()

        if self.student_id and self.student.role not in {
            self.student.Role.STUDENT,
            self.student.Role.CR,
        }:
            raise ValidationError(
                {"student": "Only students and CR users can be enrolled."}
            )

    def __str__(self):
        return f"{self.student} enrolled in {self.course}"
