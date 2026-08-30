from datetime import date

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from courses.models import Course, Enrollment


class ProfileTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        users = get_user_model()
        cls.monitor = users.objects.create_user(
            username="monitor",
            password="old-secure-password",
            role=users.Role.MONITOR,
        )
        cls.admin_user = users.objects.create_user(
            username="profile-admin",
            password="old-secure-password",
            role=users.Role.ADMIN,
        )
        cls.cr = users.objects.create_user(
            username="cr",
            password="old-secure-password",
            role=users.Role.CR,
            student_code="CR-001",
        )
        cls.student = users.objects.create_user(
            username="student",
            password="old-secure-password",
            role=users.Role.STUDENT,
            student_code="STU-001",
            insurance_receipt=True,
        )
        cls.course = Course.objects.create(
            title="Profile course",
            code="PROFILE-101",
            monitor=cls.monitor,
            start_date=date(2026, 9, 1),
            end_date=date(2026, 12, 1),
        )
        Enrollment.objects.create(course=cls.course, student=cls.cr)
        Enrollment.objects.create(course=cls.course, student=cls.student)

    def profile_values(self, **overrides):
        values = {
            "first_name": "Student",
            "last_name": "Example",
            "email": "student@example.com",
            "phone_number": "+98 912 000 0000",
            "passport_number": "P1234567",
            "passport_expiry": "2030-06-30",
            "is_in_dormitory": "on",
            "dormitory_room": "B-204",
            "wechat_id": "student-wechat",
        }
        values.update(overrides)
        return values

    def test_anonymous_user_is_redirected_from_profile(self):
        url = reverse("accounts:profile")

        response = self.client.get(url)

        self.assertRedirects(
            response,
            f"/accounts/login/?next={url}",
            fetch_redirect_response=False,
        )

    def test_every_role_can_open_own_profile(self):
        for user in (self.admin_user, self.monitor, self.cr, self.student):
            with self.subTest(role=user.role):
                self.client.force_login(user)
                response = self.client.get(reverse("accounts:profile"))
                self.assertEqual(response.status_code, 200)
                self.assertContains(response, "Profile")

    def test_user_can_update_optional_profile_and_notification_email(self):
        self.client.force_login(self.student)

        response = self.client.post(
            reverse("accounts:profile"),
            self.profile_values(),
        )

        self.assertRedirects(response, reverse("accounts:profile"))
        self.student.refresh_from_db()
        self.assertEqual(self.student.email, "student@example.com")
        self.assertEqual(self.student.passport_number, "P1234567")
        self.assertEqual(self.student.passport_expiry, date(2030, 6, 30))
        self.assertTrue(self.student.is_in_dormitory)
        self.assertEqual(self.student.dormitory_room, "B-204")
        self.assertEqual(self.student.wechat_id, "student-wechat")

    def test_self_service_cannot_change_administrative_receipts(self):
        self.client.force_login(self.student)
        values = self.profile_values(
            insurance_receipt="on",
            tuition_receipt="on",
        )

        self.client.post(reverse("accounts:profile"), values)

        self.student.refresh_from_db()
        self.assertTrue(self.student.insurance_receipt)
        self.assertFalse(self.student.tuition_receipt)

    def test_user_can_change_password_without_being_logged_out(self):
        self.client.force_login(self.student)

        response = self.client.post(
            reverse("accounts:password-change"),
            {
                "old_password": "old-secure-password",
                "new_password1": "new-even-more-secure-password-42",
                "new_password2": "new-even-more-secure-password-42",
            },
        )

        self.assertRedirects(response, reverse("accounts:profile"))
        self.student.refresh_from_db()
        self.assertTrue(
            self.student.check_password("new-even-more-secure-password-42")
        )
        self.assertEqual(int(self.client.session["_auth_user_id"]), self.student.pk)

    def test_monitor_can_update_student_receipt_statuses(self):
        self.client.force_login(self.monitor)

        response = self.client.post(
            reverse("accounts:student-update", args=[self.student.pk]),
            {
                "username": self.student.username,
                "student_code": self.student.student_code,
                **self.profile_values(),
                "insurance_receipt": "on",
                "tuition_receipt": "on",
                "dormitory_receipt": "on",
            },
        )

        self.assertRedirects(response, reverse("accounts:student-list"))
        self.student.refresh_from_db()
        self.assertTrue(self.student.insurance_receipt)
        self.assertTrue(self.student.tuition_receipt)
        self.assertTrue(self.student.dormitory_receipt)

    def test_cr_cannot_view_or_overpost_student_receipt_fields(self):
        self.client.force_login(self.cr)
        url = reverse("accounts:student-update", args=[self.student.pk])

        get_response = self.client.get(url)
        post_response = self.client.post(
            url,
            {
                "username": self.student.username,
                "student_code": self.student.student_code,
                **self.profile_values(),
                "tuition_receipt": "on",
            },
        )

        self.assertNotContains(get_response, "Insurance receipt")
        self.assertRedirects(post_response, reverse("accounts:student-list"))
        self.student.refresh_from_db()
        self.assertTrue(self.student.insurance_receipt)
        self.assertFalse(self.student.tuition_receipt)
