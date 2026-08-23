from datetime import date

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from courses.models import Course, Enrollment


class StudentManagementTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        users = get_user_model()
        cls.monitor = users.objects.create_user(
            username="monitor",
            password="test-password",
            role=users.Role.MONITOR,
        )
        cls.cr = users.objects.create_user(
            username="course-cr",
            password="test-password",
            role=users.Role.CR,
            student_code="CR-001",
        )
        cls.student = users.objects.create_user(
            username="ada",
            password="test-password",
            role=users.Role.STUDENT,
            student_code="STU-001",
            first_name="Ada",
            last_name="Lovelace",
        )
        cls.unassigned_student = users.objects.create_user(
            username="outside",
            password="test-password",
            role=users.Role.STUDENT,
            student_code="STU-OUT",
        )
        cls.course = Course.objects.create(
            title="Programming",
            code="CS-101",
            monitor=cls.monitor,
            start_date=date(2026, 9, 1),
            end_date=date(2026, 12, 1),
        )
        Enrollment.objects.create(course=cls.course, student=cls.student)
        Enrollment.objects.create(course=cls.course, student=cls.cr)

    def test_monitor_can_search_student_directory(self):
        self.client.force_login(self.monitor)

        response = self.client.get(reverse("accounts:student-list"), {"q": "STU-001"})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Ada Lovelace")
        self.assertNotContains(response, self.cr.username)

    def test_monitor_can_create_student(self):
        self.client.force_login(self.monitor)

        response = self.client.post(
            reverse("accounts:student-create"),
            {
                "username": "grace",
                "first_name": "Grace",
                "last_name": "Hopper",
                "email": "grace@example.com",
                "student_code": "STU-002",
                "phone_number": "12345",
                "password1": "A-secure-demo-password-42",
                "password2": "A-secure-demo-password-42",
            },
        )

        self.assertRedirects(response, reverse("accounts:student-list"))
        student = get_user_model().objects.get(username="grace")
        self.assertEqual(student.role, get_user_model().Role.STUDENT)
        self.assertTrue(student.check_password("A-secure-demo-password-42"))

    def test_monitor_can_update_student(self):
        self.client.force_login(self.monitor)

        response = self.client.post(
            reverse("accounts:student-update", args=[self.student.pk]),
            {
                "username": "ada",
                "first_name": "Ada",
                "last_name": "Byron",
                "email": "ada@example.com",
                "student_code": "STU-001",
                "phone_number": "555",
            },
        )

        self.assertRedirects(response, reverse("accounts:student-list"))
        self.student.refresh_from_db()
        self.assertEqual(self.student.last_name, "Byron")
        self.assertEqual(self.student.phone_number, "555")

    def test_deactivate_preserves_student_and_deactivates_enrollments(self):
        self.client.force_login(self.monitor)

        response = self.client.post(
            reverse("accounts:student-deactivate", args=[self.student.pk])
        )

        self.assertRedirects(response, reverse("accounts:student-list"))
        self.student.refresh_from_db()
        self.assertFalse(self.student.is_active)
        self.assertTrue(get_user_model().objects.filter(pk=self.student.pk).exists())
        self.assertFalse(
            Enrollment.objects.get(course=self.course, student=self.student).is_active
        )

    def test_monitor_can_restore_student(self):
        self.student.is_active = False
        self.student.save(update_fields=("is_active",))
        self.client.force_login(self.monitor)

        response = self.client.post(
            reverse("accounts:student-restore", args=[self.student.pk])
        )

        self.assertRedirects(response, reverse("accounts:student-list"))
        self.student.refresh_from_db()
        self.assertTrue(self.student.is_active)

    def test_cr_sees_only_ordinary_students_in_assigned_courses(self):
        self.client.force_login(self.cr)

        response = self.client.get(reverse("accounts:student-list"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Ada Lovelace")
        self.assertNotContains(response, self.unassigned_student.username)

    def test_cr_can_create_student_in_assigned_course(self):
        self.client.force_login(self.cr)

        response = self.client.post(
            reverse("accounts:student-create"),
            {
                "username": "new-class-student",
                "first_name": "New",
                "last_name": "Student",
                "email": "",
                "student_code": "STU-NEW",
                "phone_number": "",
                "course": self.course.pk,
                "password1": "A-secure-demo-password-42",
                "password2": "A-secure-demo-password-42",
            },
        )

        self.assertRedirects(response, reverse("accounts:student-list"))
        student = get_user_model().objects.get(username="new-class-student")
        self.assertTrue(
            Enrollment.objects.filter(
                course=self.course,
                student=student,
                is_active=True,
            ).exists()
        )

    def test_cr_can_update_assigned_student_but_not_other_cr_or_unassigned_student(self):
        self.client.force_login(self.cr)
        response = self.client.post(
            reverse("accounts:student-update", args=[self.student.pk]),
            {
                "username": "ada",
                "first_name": "Ada",
                "last_name": "Lovelace",
                "email": "ada@course.example",
                "student_code": "STU-001",
                "phone_number": "",
            },
        )
        self.assertRedirects(response, reverse("accounts:student-list"))
        self.student.refresh_from_db()
        self.assertEqual(self.student.email, "ada@course.example")

        for student in (self.cr, self.unassigned_student):
            with self.subTest(student=student.username):
                response = self.client.get(
                    reverse("accounts:student-update", args=[student.pk])
                )
                self.assertEqual(response.status_code, 404)

    def test_cr_cannot_globally_deactivate_student(self):
        self.client.force_login(self.cr)

        response = self.client.post(
            reverse("accounts:student-deactivate", args=[self.student.pk])
        )

        self.assertEqual(response.status_code, 403)
        self.student.refresh_from_db()
        self.assertTrue(self.student.is_active)
