from datetime import date, time, timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.utils import timezone

from courses.models import Course, Enrollment

from .models import (
    SECTION_COUNTED_HOURS,
    SECTION_DURATION_MINUTES,
    SESSION_SECTION_COUNT,
    AttendanceRecord,
    AttendanceToken,
    ClassSession,
    SessionSection,
)


class ClassSessionModelTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        user_model = get_user_model()
        cls.monitor = user_model.objects.create_user(
            username="teacher",
            role=user_model.Role.MONITOR,
        )
        cls.course = Course.objects.create(
            title="Introduction to Programming",
            code="CS-101",
            monitor=cls.monitor,
            start_date=date(2026, 9, 1),
            end_date=date(2026, 12, 15),
        )

    def make_session(self, **overrides):
        values = {
            "course": self.course,
            "date": date(2026, 9, 1),
            "start_time": time(9, 0),
        }
        values.update(overrides)
        return ClassSession(**values)

    def test_creating_session_automatically_creates_three_sections(self):
        session = self.make_session()

        session.save()

        self.assertEqual(session.sections.count(), SESSION_SECTION_COUNT)
        self.assertEqual(
            list(
                session.sections.values_list(
                    "section_number",
                    "duration_minutes",
                    "counted_hours",
                )
            ),
            [
                (1, SECTION_DURATION_MINUTES, SECTION_COUNTED_HOURS),
                (2, SECTION_DURATION_MINUTES, SECTION_COUNTED_HOURS),
                (3, SECTION_DURATION_MINUTES, SECTION_COUNTED_HOURS),
            ],
        )

    def test_new_session_defaults_to_draft_with_optional_end_time(self):
        session = self.make_session()

        session.save()

        self.assertEqual(session.status, ClassSession.Status.DRAFT)
        self.assertIsNone(session.end_time)

    def test_updating_session_does_not_create_more_sections(self):
        session = self.make_session()
        session.save()

        session.start_time = time(10, 0)
        session.save()

        self.assertEqual(session.sections.count(), SESSION_SECTION_COUNT)

    def test_duplicate_course_session_date_is_rejected(self):
        self.make_session().save()

        with self.assertRaises(IntegrityError), transaction.atomic():
            self.make_session(start_time=time(13, 0)).save()

    def test_same_date_is_allowed_for_different_course(self):
        other_course = Course.objects.create(
            title="Data Structures",
            code="CS-102",
            monitor=self.monitor,
            start_date=date(2026, 9, 1),
            end_date=date(2026, 12, 15),
        )

        self.make_session().save()
        other_session = self.make_session(course=other_course)
        other_session.save()

        self.assertEqual(ClassSession.objects.count(), 2)

    def test_end_time_must_be_after_start_time(self):
        session = self.make_session(end_time=time(8, 59))

        with self.assertRaises(ValidationError) as context:
            session.full_clean()

        self.assertEqual(
            context.exception.message_dict["end_time"],
            ["End time must be after the start time."],
        )

    def test_session_and_sections_are_created_atomically(self):
        session = self.make_session()

        with patch.object(
            SessionSection.objects,
            "bulk_create",
            side_effect=IntegrityError("Section creation failed."),
        ):
            with self.assertRaises(IntegrityError):
                session.save()

        self.assertFalse(ClassSession.objects.filter(course=self.course).exists())
        self.assertIsNone(session.pk)

        session.save()

        self.assertEqual(session.sections.count(), SESSION_SECTION_COUNT)


class SessionSectionModelTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        user_model = get_user_model()
        teacher = user_model.objects.create_user(
            username="teacher",
            role=user_model.Role.MONITOR,
        )
        course = Course.objects.create(
            title="Introduction to Programming",
            code="CS-101",
            monitor=teacher,
            start_date=date(2026, 9, 1),
            end_date=date(2026, 12, 15),
        )
        cls.session = ClassSession.objects.create(
            course=course,
            date=date(2026, 9, 1),
            start_time=time(9, 0),
        )

    def test_duplicate_section_number_is_rejected(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            SessionSection.objects.create(session=self.session, section_number=1)

    def test_section_number_outside_one_to_three_is_rejected(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            SessionSection.objects.create(session=self.session, section_number=4)

    def test_duration_and_counted_hours_cannot_change(self):
        section = self.session.sections.get(section_number=1)
        section.duration_minutes = SECTION_DURATION_MINUTES + 1
        section.counted_hours = SECTION_COUNTED_HOURS + 1

        with self.assertRaises(ValidationError) as context:
            section.full_clean()

        self.assertIn(
            "Constraint “session_section_duration_is_45” is violated.",
            context.exception.messages,
        )
        self.assertIn(
            "Constraint “session_section_counted_hours_is_1” is violated.",
            context.exception.messages,
        )


class AttendanceTokenModelTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        user_model = get_user_model()
        teacher = user_model.objects.create_user(
            username="teacher",
            role=user_model.Role.MONITOR,
        )
        cls.course = Course.objects.create(
            title="Introduction to Programming",
            code="CS-101",
            monitor=teacher,
            start_date=date(2026, 9, 1),
            end_date=date(2026, 12, 15),
        )
        cls.other_course = Course.objects.create(
            title="Data Structures",
            code="CS-102",
            monitor=teacher,
            start_date=date(2026, 9, 1),
            end_date=date(2026, 12, 15),
        )
        cls.session = ClassSession.objects.create(
            course=cls.course,
            date=date(2026, 9, 1),
            start_time=time(9, 0),
            status=ClassSession.Status.ACTIVE,
        )
        cls.other_session = ClassSession.objects.create(
            course=cls.other_course,
            date=date(2026, 9, 1),
            start_time=time(13, 0),
            status=ClassSession.Status.ACTIVE,
        )

    def make_token(self, **overrides):
        values = {
            "course": self.course,
            "session": self.session,
            "expires_at": timezone.now() + timedelta(seconds=30),
        }
        values.update(overrides)
        return AttendanceToken.objects.create(**values)

    def test_expired_token_is_invalid(self):
        token = self.make_token(expires_at=timezone.now() - timedelta(seconds=1))

        self.assertTrue(token.is_expired)
        self.assertFalse(token.is_valid)

    def test_inactive_token_is_invalid(self):
        token = self.make_token(is_active=False)

        self.assertFalse(token.is_expired)
        self.assertFalse(token.is_valid)

    def test_token_is_valid_only_while_session_is_active(self):
        token = self.make_token()

        self.assertTrue(token.is_valid)

        self.session.status = ClassSession.Status.CLOSED
        self.session.save(update_fields=("status",))

        self.assertFalse(token.is_valid)

    def test_unsaved_token_is_invalid(self):
        token = AttendanceToken(
            course=self.course,
            session=self.session,
            expires_at=timezone.now() + timedelta(seconds=30),
        )

        self.assertFalse(token.is_valid)

    def test_token_value_must_be_unique(self):
        token = self.make_token()

        with self.assertRaises(IntegrityError), transaction.atomic():
            self.make_token(token=token.token)

    def test_token_relationships_must_match(self):
        token = AttendanceToken(
            course=self.course,
            session=self.other_session,
            section=self.session.sections.get(section_number=1),
            expires_at=timezone.now() + timedelta(seconds=30),
        )

        with self.assertRaises(ValidationError) as context:
            token.full_clean()

        self.assertEqual(
            context.exception.message_dict["session"],
            ["Session must belong to the selected course."],
        )
        self.assertEqual(
            context.exception.message_dict["section"],
            ["Section must belong to the selected session."],
        )


class AttendanceRecordModelTests(TestCase):
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
        cls.unenrolled_student = user_model.objects.create_user(
            username="unenrolled-student",
            role=user_model.Role.STUDENT,
            student_code="STU-002",
        )
        cls.course = Course.objects.create(
            title="Introduction to Programming",
            code="CS-101",
            monitor=cls.monitor,
            start_date=date(2026, 9, 1),
            end_date=date(2026, 12, 15),
        )
        cls.other_course = Course.objects.create(
            title="Data Structures",
            code="CS-102",
            monitor=cls.monitor,
            start_date=date(2026, 9, 1),
            end_date=date(2026, 12, 15),
        )
        cls.enrollment = Enrollment.objects.create(
            course=cls.course,
            student=cls.student,
        )
        cls.session = ClassSession.objects.create(
            course=cls.course,
            date=date(2026, 9, 1),
            start_time=time(9, 0),
        )
        cls.other_session = ClassSession.objects.create(
            course=cls.other_course,
            date=date(2026, 9, 1),
            start_time=time(13, 0),
        )
        cls.section = cls.session.sections.get(section_number=1)

    def make_record(self, **overrides):
        values = {
            "student": self.student,
            "course": self.course,
            "session": self.session,
            "section": self.section,
            "status": AttendanceRecord.Status.PRESENT,
            "recorded_by": self.monitor,
        }
        values.update(overrides)
        return AttendanceRecord(**values)

    def test_manual_attendance_record_can_be_created(self):
        record = self.make_record(note="Marked during roll call.")

        record.full_clean()
        record.save()

        self.assertEqual(record.recorded_method, AttendanceRecord.RecordedMethod.MANUAL)
        self.assertEqual(record.recorded_by, self.monitor)
        self.assertEqual(record.note, "Marked during roll call.")
        self.assertIsNotNone(record.recorded_at)

    def test_student_can_have_only_one_record_per_section(self):
        AttendanceRecord.objects.create(
            student=self.student,
            course=self.course,
            session=self.session,
            section=self.section,
            status=AttendanceRecord.Status.PRESENT,
            recorded_by=self.monitor,
        )

        with self.assertRaises(IntegrityError), transaction.atomic():
            AttendanceRecord.objects.create(
                student=self.student,
                course=self.course,
                session=self.session,
                section=self.section,
                status=AttendanceRecord.Status.LATE,
                recorded_by=self.monitor,
            )

    def test_invalid_status_is_rejected(self):
        record = self.make_record(status="INVALID")

        with self.assertRaises(ValidationError) as context:
            record.full_clean()

        self.assertIn("status", context.exception.message_dict)

    def test_status_choices_are_enforced_by_database_constraint(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            AttendanceRecord.objects.create(
                student=self.student,
                course=self.course,
                session=self.session,
                section=self.section,
                status="INVALID",
                recorded_by=self.monitor,
            )

    def test_student_must_have_active_course_enrollment(self):
        record = self.make_record(student=self.unenrolled_student)

        with self.assertRaises(ValidationError) as context:
            record.full_clean()

        self.assertEqual(
            context.exception.message_dict["student"],
            ["Student must be actively enrolled in the course."],
        )

    def test_inactive_enrollment_is_not_valid_for_attendance(self):
        self.enrollment.is_active = False
        self.enrollment.save()
        record = self.make_record()

        with self.assertRaises(ValidationError) as context:
            record.full_clean()

        self.assertEqual(
            context.exception.message_dict["student"],
            ["Student must be actively enrolled in the course."],
        )

    def test_session_must_belong_to_selected_course(self):
        record = self.make_record(session=self.other_session)

        with self.assertRaises(ValidationError) as context:
            record.full_clean()

        self.assertEqual(
            context.exception.message_dict["session"],
            ["Session must belong to the selected course."],
        )

    def test_section_must_belong_to_selected_session(self):
        other_section = self.other_session.sections.get(section_number=1)
        record = self.make_record(section=other_section)

        with self.assertRaises(ValidationError) as context:
            record.full_clean()

        self.assertEqual(
            context.exception.message_dict["section"],
            ["Section must belong to the selected session."],
        )
