from datetime import date, time

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from attendance.models import ClassSession

from .models import Course, Enrollment


class TeacherCourseViewTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        user_model = get_user_model()
        cls.monitor = user_model.objects.create_user(
            username="teacher",
            password="test-password",
            role=user_model.Role.MONITOR,
        )
        cls.other_teacher = user_model.objects.create_user(
            username="other-teacher",
            password="test-password",
            role=user_model.Role.MONITOR,
        )
        cls.student = user_model.objects.create_user(
            username="student",
            password="test-password",
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
        cls.other_course = Course.objects.create(
            title="Data Structures",
            code="CS-102",
            monitor=cls.other_teacher,
            start_date=date(2026, 9, 1),
            end_date=date(2026, 12, 15),
        )
        Enrollment.objects.create(course=cls.course, student=cls.student)

    def test_anonymous_user_is_redirected_from_course_list(self):
        response = self.client.get(reverse("courses:course-list"))

        self.assertRedirects(
            response,
            f"/accounts/login/?next={reverse('courses:course-list')}",
            fetch_redirect_response=False,
        )

    def test_student_cannot_access_teacher_course_list(self):
        self.client.force_login(self.student)

        response = self.client.get(reverse("courses:course-list"))

        self.assertEqual(response.status_code, 403)

    def test_monitor_course_list_shows_all_courses(self):
        self.client.force_login(self.monitor)

        response = self.client.get(reverse("courses:course-list"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.course.title)
        self.assertContains(response, self.other_course.title)

    def test_teacher_can_view_owned_course_detail(self):
        self.client.force_login(self.monitor)

        response = self.client.get(
            reverse("courses:course-detail", args=[self.course.pk])
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.course.title)
        self.assertContains(response, self.student.username)

    def test_monitor_can_create_course(self):
        self.client.force_login(self.monitor)

        response = self.client.post(
            reverse("courses:course-create"),
            {
                "title": "Software Engineering",
                "code": "se-201",
                "start_date": "2026-09-01",
                "end_date": "2026-12-15",
            },
        )

        course = Course.objects.get(code="SE-201")
        self.assertEqual(course.monitor, self.monitor)
        self.assertRedirects(
            response,
            reverse("courses:course-detail", args=[course.pk]),
        )

    def test_student_cannot_create_course(self):
        self.client.force_login(self.student)

        response = self.client.get(reverse("courses:course-create"))

        self.assertEqual(response.status_code, 403)

    def test_monitor_can_view_course_created_by_another_monitor(self):
        self.client.force_login(self.monitor)

        response = self.client.get(
            reverse("courses:course-detail", args=[self.other_course.pk])
        )

        self.assertEqual(response.status_code, 200)

    def test_teacher_can_access_create_session_page_for_owned_course(self):
        self.client.force_login(self.monitor)

        response = self.client.get(
            reverse("courses:session-create", args=[self.course.pk])
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Create session")
        self.assertContains(response, self.course.title)

    def test_teacher_can_create_session_for_owned_course(self):
        self.client.force_login(self.monitor)

        response = self.client.post(
            reverse("courses:session-create", args=[self.course.pk]),
            {
                "date": "2026-09-02",
                "start_time": "09:00",
                "end_time": "11:15",
            },
        )

        session = ClassSession.objects.get(course=self.course, date=date(2026, 9, 2))
        self.assertRedirects(
            response,
            reverse("attendance:session-detail", args=[session.pk]),
        )
        self.assertEqual(session.sections.count(), 3)

    def test_teacher_sees_message_when_session_create_form_is_invalid(self):
        self.client.force_login(self.monitor)

        response = self.client.post(
            reverse("courses:session-create", args=[self.course.pk]),
            {
                "date": "2026-09-01",
                "start_time": "09:00",
                "end_time": "08:30",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response,
            "Session was not created. Correct the errors below.",
        )
        self.assertContains(response, "End time must be after the start time.")

    def test_monitor_can_create_session_for_course_created_by_another_monitor(self):
        self.client.force_login(self.monitor)

        response = self.client.get(
            reverse("courses:session-create", args=[self.other_course.pk])
        )

        self.assertEqual(response.status_code, 200)
