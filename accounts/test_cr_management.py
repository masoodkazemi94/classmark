from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse


class CRManagementTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        users = get_user_model()
        cls.monitor = users.objects.create_user(
            username="monitor",
            role=users.Role.MONITOR,
        )
        cls.student = users.objects.create_user(
            username="student",
            role=users.Role.STUDENT,
            student_code="STU-001",
        )

    def test_monitor_can_promote_student_to_cr(self):
        self.client.force_login(self.monitor)

        response = self.client.post(
            reverse("accounts:cr-management"),
            {"student": self.student.pk},
        )

        self.assertRedirects(response, reverse("accounts:cr-management"))
        self.student.refresh_from_db()
        self.assertEqual(self.student.role, get_user_model().Role.CR)

    def test_student_cannot_open_cr_management(self):
        self.client.force_login(self.student)

        response = self.client.get(reverse("accounts:cr-management"))

        self.assertEqual(response.status_code, 403)
