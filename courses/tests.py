from datetime import date
from io import StringIO

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.db import IntegrityError, transaction
from django.test import TestCase

from attendance.models import ClassSession

from .models import Course, Enrollment


class CourseModelTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        user_model = get_user_model()
        cls.monitor = user_model.objects.create_user(
            username="teacher",
            role=user_model.Role.MONITOR,
        )
        cls.student = user_model.objects.create_user(
            username="student",
            role=user_model.Role.STUDENT,
            student_code="STU-001",
        )

    def make_course(self, **overrides):
        values = {
            "title": "Introduction to Programming",
            "code": "CS-101",
            "monitor": self.monitor,
            "start_date": date(2026, 9, 1),
            "end_date": date(2026, 12, 15),
        }
        values.update(overrides)
        return Course(**values)

    def test_teacher_can_own_course(self):
        course = self.make_course()

        course.full_clean()
        course.save()

        self.assertEqual(course.monitor, self.monitor)
        self.assertTrue(course.is_active)

    def test_non_teacher_cannot_own_course(self):
        course = self.make_course(monitor=self.student)

        with self.assertRaises(ValidationError) as context:
            course.full_clean()

        self.assertIn(
            "Only Monitor and Admin users can create a course.",
            context.exception.message_dict["monitor"],
        )

    def test_end_date_cannot_be_before_start_date(self):
        course = self.make_course(end_date=date(2026, 8, 31))

        with self.assertRaises(ValidationError) as context:
            course.full_clean()

        self.assertEqual(
            context.exception.message_dict["end_date"],
            ["End date must be on or after the start date."],
        )

    def test_date_order_is_enforced_by_database_constraint(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            Course.objects.create(
                title="Invalid Course",
                code="INVALID",
                monitor=self.monitor,
                start_date=date(2026, 9, 1),
                end_date=date(2026, 8, 31),
            )

    def test_string_representation_contains_code_and_title(self):
        course = self.make_course()

        self.assertEqual(str(course), "CS-101 - Introduction to Programming")


class EnrollmentModelTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        user_model = get_user_model()
        cls.monitor = user_model.objects.create_user(
            username="teacher",
            role=user_model.Role.MONITOR,
        )
        cls.student = user_model.objects.create_user(
            username="student",
            role=user_model.Role.STUDENT,
            student_code="STU-001",
        )
        cls.course = Course.objects.create(
            title="Introduction to Programming",
            code="CS-101",
            monitor=cls.monitor,
            start_date=date(2026, 9, 1),
            end_date=date(2026, 12, 15),
        )

    def test_student_can_be_enrolled_in_course(self):
        enrollment = Enrollment(course=self.course, student=self.student)

        enrollment.full_clean()
        enrollment.save()

        self.assertEqual(enrollment.course, self.course)
        self.assertEqual(enrollment.student, self.student)
        self.assertTrue(enrollment.is_active)

    def test_cr_can_be_enrolled_in_course(self):
        user_model = get_user_model()
        cr = user_model.objects.create_user(
            username="cr",
            role=user_model.Role.CR,
            student_code="CR-001",
        )
        enrollment = Enrollment(course=self.course, student=cr)

        enrollment.full_clean()
        enrollment.save()

        self.assertEqual(enrollment.student, cr)

    def test_non_student_cannot_be_enrolled(self):
        enrollment = Enrollment(course=self.course, student=self.monitor)

        with self.assertRaises(ValidationError) as context:
            enrollment.full_clean()

        self.assertIn(
            "Only students and CR users can be enrolled.",
            context.exception.message_dict["student"],
        )

    def test_student_cannot_be_enrolled_twice_in_same_course(self):
        Enrollment.objects.create(course=self.course, student=self.student)

        with self.assertRaises(IntegrityError), transaction.atomic():
            Enrollment.objects.create(course=self.course, student=self.student)

    def test_string_representation_identifies_student_and_course(self):
        enrollment = Enrollment(course=self.course, student=self.student)

        self.assertEqual(
            str(enrollment),
            "student enrolled in CS-101 - Introduction to Programming",
        )


class SampleDataCommandTests(TestCase):
    def test_seed_sample_data_creates_demo_teacher_students_course_and_session(self):
        output = StringIO()

        call_command("seed_sample_data", stdout=output)

        user_model = get_user_model()
        teacher = user_model.objects.get(username="sample_monitor")
        students = user_model.objects.filter(username__startswith="sample_student_")
        course = Course.objects.get(code="DEMO-101", monitor=teacher)
        session = ClassSession.objects.get(course=course, date=date(2026, 9, 1))

        self.assertEqual(teacher.role, user_model.Role.MONITOR)
        self.assertTrue(teacher.is_staff)
        self.assertEqual(students.count(), 3)
        self.assertEqual(
            set(students.values_list("role", flat=True)),
            {user_model.Role.STUDENT},
        )
        self.assertEqual(Enrollment.objects.filter(course=course).count(), 3)
        self.assertEqual(session.status, ClassSession.Status.ACTIVE)
        self.assertEqual(session.sections.count(), 3)
        self.assertIn("Sample data is ready.", output.getvalue())

    def test_seed_sample_data_can_run_more_than_once_without_duplicates(self):
        call_command("seed_sample_data", stdout=StringIO())
        call_command("seed_sample_data", stdout=StringIO())

        user_model = get_user_model()
        teacher = user_model.objects.get(username="sample_monitor")
        course = Course.objects.get(code="DEMO-101", monitor=teacher)

        self.assertEqual(user_model.objects.filter(username="sample_monitor").count(), 1)
        self.assertEqual(
            user_model.objects.filter(username__startswith="sample_student_").count(),
            3,
        )
        self.assertEqual(Course.objects.filter(code="DEMO-101").count(), 1)
        self.assertEqual(Enrollment.objects.filter(course=course).count(), 3)
        self.assertEqual(ClassSession.objects.filter(course=course).count(), 1)
