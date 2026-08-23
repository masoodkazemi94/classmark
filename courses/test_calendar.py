from datetime import date, time

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from attendance.models import ClassSession

from .models import Course, Enrollment


class SessionCalendarTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        users = get_user_model()
        cls.monitor = users.objects.create_user(
            username="monitor",
            role=users.Role.MONITOR,
        )
        cls.cr = users.objects.create_user(
            username="calendar-cr",
            role=users.Role.CR,
            student_code="CR-CAL",
        )
        cls.student = users.objects.create_user(
            username="student",
            role=users.Role.STUDENT,
            student_code="STU-CAL",
        )
        cls.course = Course.objects.create(
            title="Programming",
            code="CAL-101",
            monitor=cls.monitor,
            start_date=date(2026, 8, 1),
            end_date=date(2026, 12, 1),
        )
        cls.other_course = Course.objects.create(
            title="Networks",
            code="NET-101",
            monitor=cls.monitor,
            start_date=date(2026, 8, 1),
            end_date=date(2026, 12, 1),
        )
        Enrollment.objects.create(course=cls.course, student=cls.cr)
        Enrollment.objects.create(course=cls.course, student=cls.student)
        cls.session = ClassSession.objects.create(
            course=cls.course,
            date=date(2026, 8, 24),
            start_time=time(9),
            status=ClassSession.Status.ACTIVE,
        )
        cls.other_session = ClassSession.objects.create(
            course=cls.other_course,
            date=date(2026, 8, 25),
            start_time=time(13),
            status=ClassSession.Status.DRAFT,
        )

    def test_monitor_calendar_shows_sessions_from_all_courses(self):
        self.client.force_login(self.monitor)

        response = self.client.get(
            reverse("courses:session-calendar"),
            {"month": "2026-08"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "August 2026")
        self.assertContains(response, self.course.code)
        self.assertContains(response, self.other_course.code)

    def test_cr_calendar_is_limited_to_assigned_courses(self):
        self.client.force_login(self.cr)

        response = self.client.get(
            reverse("courses:session-calendar"),
            {"month": "2026-08"},
        )

        self.assertContains(response, self.course.code)
        self.assertNotContains(response, self.other_course.code)

    def test_calendar_filters_by_course_and_status(self):
        self.client.force_login(self.monitor)

        response = self.client.get(
            reverse("courses:session-calendar"),
            {
                "month": "2026-08",
                "course": self.course.pk,
                "status": ClassSession.Status.ACTIVE,
            },
        )

        self.assertContains(response, "09:00 · CAL-101")
        self.assertNotContains(response, "13:00 · NET-101")
        self.assertContains(response, "?date=2026-08-27")

    def test_cr_cannot_filter_calendar_to_unassigned_course(self):
        self.client.force_login(self.cr)

        response = self.client.get(
            reverse("courses:session-calendar"),
            {"month": "2026-08", "course": self.other_course.pk},
        )

        self.assertEqual(response.status_code, 404)

    def test_student_cannot_access_management_calendar(self):
        self.client.force_login(self.student)

        response = self.client.get(reverse("courses:session-calendar"))

        self.assertEqual(response.status_code, 403)

    def test_calendar_date_prefills_session_creation_form(self):
        self.client.force_login(self.monitor)

        response = self.client.get(
            reverse("courses:session-create", args=[self.course.pk]),
            {"date": "2026-08-27"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'value="2026-08-27"')
