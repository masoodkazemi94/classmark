from datetime import date, time

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from attendance.models import AttendanceRecord, ClassSession
from attendance.services import mark_student_for_section
from courses.models import Course, Enrollment


class RoleDashboardTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        users = get_user_model()
        cls.monitor = users.objects.create_user(
            username="monitor",
            role=users.Role.MONITOR,
        )
        cls.cr = users.objects.create_user(
            username="dashboard-cr",
            role=users.Role.CR,
            student_code="CR-DASH",
        )
        cls.student = users.objects.create_user(
            username="dashboard-student",
            role=users.Role.STUDENT,
            student_code="STU-DASH",
        )
        cls.other_student = users.objects.create_user(
            username="other-student",
            role=users.Role.STUDENT,
            student_code="STU-OTHER",
        )
        today = timezone.localdate()
        cls.course = Course.objects.create(
            title="Dashboard Programming",
            code="DASH-101",
            monitor=cls.monitor,
            start_date=today,
            end_date=date(today.year + 1, today.month, 1),
        )
        cls.other_course = Course.objects.create(
            title="Dashboard Networks",
            code="DASH-202",
            monitor=cls.monitor,
            start_date=today,
            end_date=date(today.year + 1, today.month, 1),
        )
        Enrollment.objects.create(course=cls.course, student=cls.cr)
        Enrollment.objects.create(course=cls.course, student=cls.student)
        Enrollment.objects.create(course=cls.other_course, student=cls.other_student)
        cls.session = ClassSession.objects.create(
            course=cls.course,
            date=today,
            start_time=time(9),
            status=ClassSession.Status.ACTIVE,
        )
        cls.other_session = ClassSession.objects.create(
            course=cls.other_course,
            date=today,
            start_time=time(13),
            status=ClassSession.Status.ACTIVE,
        )
        mark_student_for_section(
            student=cls.student,
            course=cls.course,
            session=cls.session,
            section=cls.session.sections.get(section_number=1),
            status=AttendanceRecord.Status.PRESENT,
            recorded_by=cls.monitor,
        )

    def test_monitor_dashboard_shows_all_course_operations(self):
        self.client.force_login(self.monitor)

        response = self.client.get(reverse("home"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Welcome back")
        self.assertContains(response, self.course.code)
        self.assertContains(response, self.other_course.code)
        self.assertContains(response, "Needs attention")
        self.assertContains(response, "Recent attendance activity")

    def test_cr_dashboard_only_shows_assigned_course(self):
        self.client.force_login(self.cr)

        response = self.client.get(reverse("home"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.course.code)
        self.assertNotContains(response, self.other_course.code)
        self.assertNotContains(response, "Recent attendance activity")

    def test_student_dashboard_shows_personal_courses_and_attendance(self):
        self.client.force_login(self.student)

        response = self.client.get(reverse("home"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Your courses, upcoming classes")
        self.assertContains(response, self.course.code)
        self.assertNotContains(response, self.other_course.code)
        self.assertContains(response, "Present sections")
        self.assertContains(response, "Recent attendance")
