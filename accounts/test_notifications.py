from datetime import date, time
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core import mail
from django.test import TestCase, override_settings
from django.urls import reverse

from attendance.models import AttendanceRecord, ClassSession
from attendance.services import mark_student_for_session
from courses.models import Course, Enrollment

from .models import Notification
from .notification_services import notify_students_about_session


@override_settings(
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    DEFAULT_FROM_EMAIL="ClassPulse <notifications@example.com>",
)
class NotificationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        user_model = get_user_model()
        cls.monitor = user_model.objects.create_user(
            username="monitor",
            password="test-password",
            role=user_model.Role.MONITOR,
        )
        cls.student = user_model.objects.create_user(
            username="student",
            password="test-password",
            role=user_model.Role.STUDENT,
            student_code="STU-001",
            email="student@example.com",
        )
        cls.second_student = user_model.objects.create_user(
            username="second-student",
            password="test-password",
            role=user_model.Role.STUDENT,
            student_code="STU-002",
        )
        cls.cr = user_model.objects.create_user(
            username="cr",
            password="test-password",
            role=user_model.Role.CR,
            student_code="CR-001",
            email="cr@example.com",
        )
        cls.course = Course.objects.create(
            title="Introduction to Programming",
            code="CS-101",
            monitor=cls.monitor,
            start_date=date(2026, 9, 1),
            end_date=date(2026, 12, 15),
        )
        for student in (cls.student, cls.second_student, cls.cr):
            Enrollment.objects.create(course=cls.course, student=student)
        cls.session = ClassSession.objects.create(
            course=cls.course,
            date=date(2026, 9, 1),
            start_time=time(9, 0),
        )

    def test_class_notification_creates_inbox_items_and_sends_email(self):
        with self.captureOnCommitCallbacks(execute=True):
            notifications = notify_students_about_session(session=self.session)

        self.assertEqual(len(notifications), 3)
        self.assertEqual(Notification.objects.count(), 3)
        self.assertEqual(len(mail.outbox), 2)
        notification = Notification.objects.get(recipient=self.student)
        self.assertEqual(notification.kind, Notification.Kind.CLASS_SESSION)
        self.assertEqual(notification.email_status, Notification.EmailStatus.SENT)
        skipped = Notification.objects.get(recipient=self.second_student)
        self.assertEqual(skipped.email_status, Notification.EmailStatus.SKIPPED)

    def test_email_failure_is_recorded_without_losing_notification(self):
        with patch(
            "accounts.notification_services.send_mail",
            side_effect=RuntimeError("SMTP unavailable"),
        ):
            with self.captureOnCommitCallbacks(execute=True):
                notify_students_about_session(session=self.session)

        notification = Notification.objects.get(recipient=self.student)
        self.assertEqual(notification.email_status, Notification.EmailStatus.FAILED)
        self.assertIn("SMTP unavailable", notification.email_error)

    def test_all_section_attendance_creates_one_notification(self):
        with self.captureOnCommitCallbacks(execute=True):
            mark_student_for_session(
                student=self.student,
                course=self.course,
                session=self.session,
                status=AttendanceRecord.Status.LATE,
                recorded_by=self.monitor,
            )

        notification = Notification.objects.get(
            recipient=self.student,
            kind=Notification.Kind.ATTENDANCE,
        )
        self.assertIn("section 1: Late", notification.message)
        self.assertIn("section 3: Late", notification.message)

    def test_student_inbox_only_shows_own_notifications(self):
        notify_students_about_session(session=self.session)
        self.client.force_login(self.student)

        response = self.client.get(reverse("accounts:notification-list"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "New class scheduled: CS-101")
        self.assertEqual(len(response.context["notifications"]), 1)

    def test_student_can_mark_own_notification_read(self):
        notification = notify_students_about_session(session=self.session)[0]
        self.client.force_login(notification.recipient)

        response = self.client.post(
            reverse("accounts:notification-read", args=[notification.pk])
        )

        self.assertRedirects(response, reverse("accounts:notification-list"))
        notification.refresh_from_db()
        self.assertTrue(notification.is_read)

    def test_student_cannot_mark_another_students_notification_read(self):
        notifications = notify_students_about_session(session=self.session)
        another_notification = next(
            item for item in notifications if item.recipient == self.second_student
        )
        self.client.force_login(self.student)

        response = self.client.post(
            reverse("accounts:notification-read", args=[another_notification.pk])
        )

        self.assertEqual(response.status_code, 404)

    def test_monitor_cannot_open_student_notification_inbox(self):
        self.client.force_login(self.monitor)

        response = self.client.get(reverse("accounts:notification-list"))

        self.assertEqual(response.status_code, 403)

    def test_monitor_can_send_custom_session_update(self):
        self.client.force_login(self.monitor)

        response = self.client.post(
            reverse("attendance:session-notify", args=[self.session.pk]),
            {"title": "Room changed", "message": "Meet in room 204."},
        )

        self.assertRedirects(
            response,
            reverse("attendance:session-detail", args=[self.session.pk]),
        )
        self.assertEqual(
            Notification.objects.filter(title="Room changed").count(),
            3,
        )

    def test_session_creation_automatically_notifies_roster(self):
        self.client.force_login(self.monitor)

        response = self.client.post(
            reverse("courses:session-create", args=[self.course.pk]),
            {
                "date": "2026-09-02",
                "start_time": "10:00",
                "end_time": "12:15",
            },
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            Notification.objects.filter(
                kind=Notification.Kind.CLASS_SESSION,
                session__date=date(2026, 9, 2),
            ).count(),
            3,
        )
