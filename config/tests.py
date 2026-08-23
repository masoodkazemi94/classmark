from datetime import date, time

from django.apps import apps
from django.conf import settings
from django.contrib import admin
from django.contrib.auth import get_user_model
from django.test import SimpleTestCase
from django.test import TestCase
from django.urls import reverse
from unfold.admin import ModelAdmin

from attendance.models import AttendanceToken
from attendance.models import ClassSession
from config.settings import base
from courses.models import Course


class ProjectBootTests(SimpleTestCase):
    def test_home_page_loads(self):
        response = self.client.get(reverse("home"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "ClassPulse")

    def test_expected_apps_are_installed(self):
        for app_name in ("unfold", "accounts", "courses", "attendance", "reports"):
            with self.subTest(app_name=app_name):
                self.assertTrue(apps.is_installed(app_name))

    def test_unfold_is_loaded_before_django_admin(self):
        self.assertLess(
            settings.INSTALLED_APPS.index("unfold"),
            settings.INSTALLED_APPS.index("django.contrib.admin"),
        )

    def test_custom_user_model_is_configured(self):
        self.assertEqual(settings.AUTH_USER_MODEL, "accounts.User")

    def test_database_settings_use_postgresql_outside_tests(self):
        self.assertEqual(
            base.DATABASES["default"]["ENGINE"],
            "django.db.backends.postgresql",
        )

    def test_test_command_uses_isolated_sqlite_database(self):
        self.assertEqual(
            settings.DATABASES["default"]["ENGINE"],
            "django.db.backends.sqlite3",
        )


class AdminCustomizationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        user_model = get_user_model()
        cls.admin_user = user_model.objects.create_user(
            username="admin",
            password="test-password",
            role=user_model.Role.ADMIN,
            is_staff=True,
            is_superuser=True,
        )

    def test_admin_index_uses_classpulse_branding_and_styles(self):
        self.client.force_login(self.admin_user)

        response = self.client.get(reverse("admin:index"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "ClassPulse")
        self.assertContains(response, "Attendance operations")

    def test_attendance_tokens_are_registered_in_admin(self):
        self.assertIn(AttendanceToken, admin.site._registry)
        self.assertIsInstance(admin.site._registry[AttendanceToken], ModelAdmin)

    def test_teacher_admin_dashboard_shows_owned_course_shortcuts(self):
        user_model = get_user_model()
        teacher = user_model.objects.create_user(
            username="teacher-admin",
            password="test-password",
            role=user_model.Role.MONITOR,
            is_staff=True,
        )
        other_teacher = user_model.objects.create_user(
            username="other-teacher",
            role=user_model.Role.MONITOR,
        )
        owned_course = Course.objects.create(
            title="Owned Attendance",
            code="OWN-101",
            monitor=teacher,
            start_date=date(2026, 9, 1),
            end_date=date(2026, 12, 15),
        )
        Course.objects.create(
            title="Other Attendance",
            code="OTHER-101",
            monitor=other_teacher,
            start_date=date(2026, 9, 1),
            end_date=date(2026, 12, 15),
        )
        ClassSession.objects.create(
            course=owned_course,
            date=date(2026, 9, 1),
            start_time=time(9, 0),
            status=ClassSession.Status.ACTIVE,
        )
        self.client.force_login(teacher)

        response = self.client.get(reverse("admin:index"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Monitor dashboard")
        self.assertContains(response, "Quick access")
        self.assertContains(response, "OWN-101")
        self.assertContains(response, "Course workspace")
        self.assertContains(response, "Show QR code")
        self.assertContains(response, "Attendance report")
        self.assertNotContains(response, "Admin courses")
        self.assertContains(response, "OTHER-101")
