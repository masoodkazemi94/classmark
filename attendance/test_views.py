from datetime import date, time, timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from courses.models import Course, Enrollment

from .models import AttendanceRecord, AttendanceToken, ClassSession


class TeacherSessionDetailViewTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        user_model = get_user_model()
        cls.monitor = user_model.objects.create_user(
            username="teacher",
            role=user_model.Role.MONITOR,
        )
        cls.other_teacher = user_model.objects.create_user(
            username="other-teacher",
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
        Enrollment.objects.create(course=cls.course, student=cls.student)
        cls.session = ClassSession.objects.create(
            course=cls.course,
            date=date(2026, 9, 1),
            start_time=time(9, 0),
        )
        first_section = cls.session.sections.get(section_number=1)
        AttendanceRecord.objects.create(
            student=cls.student,
            course=cls.course,
            session=cls.session,
            section=first_section,
            status=AttendanceRecord.Status.PRESENT,
            recorded_by=cls.monitor,
        )

    def test_anonymous_user_is_redirected_from_session_detail(self):
        url = reverse("attendance:session-detail", args=[self.session.pk])

        response = self.client.get(url)

        self.assertRedirects(
            response,
            f"/accounts/login/?next={url}",
            fetch_redirect_response=False,
        )

    def test_student_cannot_access_session_detail(self):
        self.client.force_login(self.student)

        response = self.client.get(
            reverse("attendance:session-detail", args=[self.session.pk])
        )

        self.assertEqual(response.status_code, 403)

    def test_owner_can_view_session_sections_students_and_statuses(self):
        self.client.force_login(self.monitor)

        response = self.client.get(
            reverse("attendance:session-detail", args=[self.session.pk])
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "2026-09-01")
        self.assertContains(response, "Section 1")
        self.assertContains(response, "Section 2")
        self.assertContains(response, "Section 3")
        self.assertContains(response, self.student.username)
        self.assertContains(response, "Present")
        self.assertContains(response, "Not recorded", count=2)
        self.assertContains(response, "Mark attendance manually")
        self.assertContains(response, "csrfmiddlewaretoken")

    def test_other_monitor_can_view_session_detail(self):
        self.client.force_login(self.other_teacher)

        response = self.client.get(
            reverse("attendance:session-detail", args=[self.session.pk])
        )

        self.assertEqual(response.status_code, 200)

    def test_owner_can_mark_student_for_all_sections(self):
        self.client.force_login(self.monitor)

        response = self.client.post(
            reverse("attendance:manual-attendance", args=[self.session.pk]),
            {
                "student": self.student.pk,
                "section": "",
                "status": AttendanceRecord.Status.LEAVE,
                "note": "Approved leave.",
            },
            follow=True,
        )

        self.assertRedirects(
            response,
            reverse("attendance:session-detail", args=[self.session.pk]),
        )
        self.assertContains(response, "Attendance updated for student.")
        self.assertEqual(
            list(
                AttendanceRecord.objects.filter(student=self.student)
                .order_by("section__section_number")
                .values_list("status", "note")
            ),
            [
                (AttendanceRecord.Status.LEAVE, "Approved leave."),
                (AttendanceRecord.Status.LEAVE, "Approved leave."),
                (AttendanceRecord.Status.LEAVE, "Approved leave."),
            ],
        )

    def test_owner_can_mark_student_for_one_section(self):
        self.client.force_login(self.monitor)
        second_section = self.session.sections.get(section_number=2)

        response = self.client.post(
            reverse("attendance:manual-attendance", args=[self.session.pk]),
            {
                "student": self.student.pk,
                "section": second_section.pk,
                "status": AttendanceRecord.Status.LATE,
                "note": "",
            },
        )

        self.assertRedirects(
            response,
            reverse("attendance:session-detail", args=[self.session.pk]),
        )
        self.assertEqual(
            AttendanceRecord.objects.get(
                student=self.student,
                section=second_section,
            ).status,
            AttendanceRecord.Status.LATE,
        )
        self.assertFalse(
            AttendanceRecord.objects.filter(
                student=self.student,
                section__section_number=3,
            ).exists()
        )

    def test_manual_attendance_rejects_invalid_student(self):
        user_model = get_user_model()
        unenrolled_student = user_model.objects.create_user(
            username="unenrolled-student",
            role=user_model.Role.STUDENT,
            student_code="STU-002",
        )
        self.client.force_login(self.monitor)

        response = self.client.post(
            reverse("attendance:manual-attendance", args=[self.session.pk]),
            {
                "student": unenrolled_student.pk,
                "section": "",
                "status": AttendanceRecord.Status.PRESENT,
                "note": "",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response,
            "Attendance was not updated. Correct the errors below.",
        )
        self.assertContains(response, "Select a valid choice")
        self.assertFalse(
            AttendanceRecord.objects.filter(student=unenrolled_student).exists()
        )

    def test_other_monitor_can_submit_manual_attendance(self):
        self.client.force_login(self.other_teacher)

        response = self.client.post(
            reverse("attendance:manual-attendance", args=[self.session.pk]),
            {
                "student": self.student.pk,
                "section": "",
                "status": AttendanceRecord.Status.ABSENT,
                "note": "",
            },
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(AttendanceRecord.objects.count(), 3)

    def test_duplicate_manual_submission_updates_existing_record(self):
        first_section = self.session.sections.get(section_number=1)
        existing_record = AttendanceRecord.objects.get(
            student=self.student,
            section=first_section,
        )
        self.client.force_login(self.monitor)

        response = self.client.post(
            reverse("attendance:manual-attendance", args=[self.session.pk]),
            {
                "student": self.student.pk,
                "section": first_section.pk,
                "status": AttendanceRecord.Status.ABSENT,
                "note": "Corrected after roll call.",
            },
        )

        self.assertRedirects(
            response,
            reverse("attendance:session-detail", args=[self.session.pk]),
        )
        existing_record.refresh_from_db()
        self.assertEqual(AttendanceRecord.objects.count(), 1)
        self.assertEqual(existing_record.status, AttendanceRecord.Status.ABSENT)
        self.assertEqual(existing_record.note, "Corrected after roll call.")
        self.assertEqual(
            existing_record.recorded_method,
            AttendanceRecord.RecordedMethod.MANUAL,
        )

    def test_owner_can_close_active_session_and_create_missing_absences(self):
        self.session.status = ClassSession.Status.ACTIVE
        self.session.save(update_fields=("status",))
        self.client.force_login(self.monitor)

        response = self.client.post(
            reverse("attendance:session-close", args=[self.session.pk]),
            follow=True,
        )

        self.assertRedirects(
            response,
            reverse("attendance:session-detail", args=[self.session.pk]),
        )
        self.assertContains(
            response,
            "Session closed and missing records marked absent.",
        )
        self.session.refresh_from_db()
        self.assertEqual(self.session.status, ClassSession.Status.CLOSED)
        self.assertEqual(AttendanceRecord.objects.count(), 3)
        self.assertEqual(
            AttendanceRecord.objects.get(
                student=self.student,
                section__section_number=1,
            ).status,
            AttendanceRecord.Status.PRESENT,
        )
        self.assertEqual(
            AttendanceRecord.objects.filter(
                student=self.student,
                status=AttendanceRecord.Status.ABSENT,
            ).count(),
            2,
        )

    def test_other_monitor_can_close_session(self):
        self.session.status = ClassSession.Status.ACTIVE
        self.session.save(update_fields=("status",))
        self.client.force_login(self.other_teacher)

        response = self.client.post(
            reverse("attendance:session-close", args=[self.session.pk])
        )

        self.assertEqual(response.status_code, 302)
        self.session.refresh_from_db()
        self.assertEqual(self.session.status, ClassSession.Status.CLOSED)
        self.assertEqual(AttendanceRecord.objects.count(), 3)

    def test_close_session_requires_post(self):
        self.session.status = ClassSession.Status.ACTIVE
        self.session.save(update_fields=("status",))
        self.client.force_login(self.monitor)

        response = self.client.get(
            reverse("attendance:session-close", args=[self.session.pk])
        )

        self.assertEqual(response.status_code, 405)
        self.session.refresh_from_db()
        self.assertEqual(self.session.status, ClassSession.Status.ACTIVE)


class TeacherSessionQRCodeViewTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        user_model = get_user_model()
        cls.monitor = user_model.objects.create_user(
            username="teacher",
            role=user_model.Role.MONITOR,
        )
        cls.other_teacher = user_model.objects.create_user(
            username="other-teacher",
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
        Enrollment.objects.create(course=cls.course, student=cls.student)
        cls.session = ClassSession.objects.create(
            course=cls.course,
            date=date(2026, 9, 1),
            start_time=time(9, 0),
            status=ClassSession.Status.ACTIVE,
        )

    def test_anonymous_user_is_redirected_from_qr_page(self):
        url = reverse("attendance:session-qr", args=[self.session.pk])

        response = self.client.get(url)

        self.assertRedirects(
            response,
            f"/accounts/login/?next={url}",
            fetch_redirect_response=False,
        )

    def test_student_cannot_access_qr_page(self):
        self.client.force_login(self.student)

        response = self.client.get(
            reverse("attendance:session-qr", args=[self.session.pk])
        )

        self.assertEqual(response.status_code, 403)

    def test_teacher_can_generate_qr_for_own_session(self):
        self.client.force_login(self.monitor)

        response = self.client.post(
            reverse("attendance:session-qr", args=[self.session.pk]),
            follow=True,
        )

        self.assertRedirects(
            response,
            reverse("attendance:session-qr", args=[self.session.pk]),
        )
        token = AttendanceToken.objects.get(session=self.session)
        self.assertTrue(token.is_active)
        self.assertContains(response, "QR code refreshed.")
        self.assertContains(response, "QR code for student attendance scan")
        self.assertContains(response, "data:image/png;base64,")
        self.assertContains(response, "Refresh now")

    def test_other_monitor_can_generate_qr_for_session(self):
        self.client.force_login(self.other_teacher)

        response = self.client.post(
            reverse("attendance:session-qr", args=[self.session.pk])
        )

        self.assertEqual(response.status_code, 302)
        self.assertTrue(AttendanceToken.objects.exists())

    def test_qr_token_url_is_correct(self):
        self.client.force_login(self.monitor)

        with patch(
            "attendance.models.secrets.token_urlsafe",
            return_value="known-token",
        ):
            response = self.client.post(
                reverse("attendance:session-qr", args=[self.session.pk]),
                follow=True,
            )

        self.assertEqual(
            response.context["scan_url"],
            "http://testserver/attendance/scan/known-token/",
        )

    def test_refresh_qr_deactivates_old_token(self):
        self.client.force_login(self.monitor)

        with patch(
            "attendance.models.secrets.token_urlsafe",
            return_value="first-token",
        ):
            self.client.post(reverse("attendance:session-qr", args=[self.session.pk]))
        first_token = AttendanceToken.objects.get(token="first-token")

        with patch(
            "attendance.models.secrets.token_urlsafe",
            return_value="second-token",
        ):
            self.client.post(reverse("attendance:session-qr", args=[self.session.pk]))

        first_token.refresh_from_db()
        second_token = AttendanceToken.objects.get(token="second-token")
        self.assertFalse(first_token.is_active)
        self.assertTrue(second_token.is_active)

    @override_settings(QR_TOKEN_TTL_SECONDS=5)
    def test_live_refresh_returns_new_qr_and_five_second_expiry(self):
        self.client.force_login(self.monitor)
        before_refresh = timezone.now()

        response = self.client.post(
            reverse("attendance:session-qr-refresh", args=[self.session.pk]),
            HTTP_ACCEPT="application/json",
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["rotation_seconds"], 5)
        self.assertTrue(payload["scan_url"].startswith("http://testserver/attendance/scan/"))
        self.assertTrue(payload["qr_code_data_url"].startswith("data:image/png;base64,"))
        token = AttendanceToken.objects.get(session=self.session)
        self.assertGreaterEqual(token.expires_at, before_refresh + timedelta(seconds=5))
        self.assertLessEqual(token.expires_at, timezone.now() + timedelta(seconds=5))

    def test_qr_page_rejects_non_active_session_with_message(self):
        self.session.status = ClassSession.Status.DRAFT
        self.session.save(update_fields=("status",))
        self.client.force_login(self.monitor)

        response = self.client.get(
            reverse("attendance:session-qr", args=[self.session.pk]),
            follow=True,
        )

        self.assertRedirects(
            response,
            reverse("attendance:session-detail", args=[self.session.pk]),
        )
        self.assertContains(
            response,
            "QR codes are available only for active sessions.",
        )
        self.assertFalse(AttendanceToken.objects.exists())


class StudentAttendanceScanViewTests(TestCase):
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
        Enrollment.objects.create(course=cls.course, student=cls.student)
        session_start = timezone.localtime(timezone.now() - timedelta(minutes=1))
        cls.session = ClassSession.objects.create(
            course=cls.course,
            date=session_start.date(),
            start_time=session_start.time().replace(tzinfo=None, microsecond=0),
            status=ClassSession.Status.ACTIVE,
        )

    def make_token(self, **overrides):
        values = {
            "course": self.course,
            "session": self.session,
            "token": "scan-token",
            "expires_at": timezone.now() + timedelta(seconds=30),
        }
        values.update(overrides)
        return AttendanceToken.objects.create(**values)

    def scan_url(self, token_value="scan-token"):
        return reverse("attendance:scan-attendance", args=[token_value])

    def set_session_started(self, *, minutes_ago):
        session_start = timezone.localtime(
            timezone.now() - timedelta(minutes=minutes_ago)
        )
        self.session.date = session_start.date()
        self.session.start_time = session_start.time().replace(
            tzinfo=None,
            microsecond=0,
        )
        self.session.save(update_fields=("date", "start_time"))

    def test_anonymous_user_is_redirected_from_scan(self):
        url = self.scan_url()

        response = self.client.get(url)

        self.assertRedirects(
            response,
            f"/accounts/login/?next={url}",
            fetch_redirect_response=False,
        )

    def test_valid_scan_records_present_attendance_for_session_sections(self):
        self.make_token()
        self.client.force_login(self.student)

        response = self.client.get(self.scan_url())

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Attendance recorded successfully.")
        self.assertContains(response, "Present")
        self.assertEqual(
            list(
                AttendanceRecord.objects.filter(student=self.student)
                .order_by("section__section_number")
                .values_list("section__section_number", "status", "recorded_method")
            ),
            [
                (
                    1,
                    AttendanceRecord.Status.PRESENT,
                    AttendanceRecord.RecordedMethod.QR,
                ),
                (
                    2,
                    AttendanceRecord.Status.PRESENT,
                    AttendanceRecord.RecordedMethod.QR,
                ),
                (
                    3,
                    AttendanceRecord.Status.PRESENT,
                    AttendanceRecord.RecordedMethod.QR,
                ),
            ],
        )

    def test_expired_token_is_rejected(self):
        self.make_token(expires_at=timezone.now() - timedelta(seconds=1))
        self.client.force_login(self.student)

        response = self.client.get(self.scan_url())

        self.assertContains(response, "This QR code has expired", status_code=400)
        self.assertFalse(AttendanceRecord.objects.exists())

    def test_inactive_token_is_rejected(self):
        self.make_token(is_active=False)
        self.client.force_login(self.student)

        response = self.client.get(self.scan_url())

        self.assertContains(
            response,
            "This QR code is no longer active",
            status_code=400,
        )
        self.assertFalse(AttendanceRecord.objects.exists())

    def test_unenrolled_student_cannot_scan(self):
        self.make_token()
        self.client.force_login(self.unenrolled_student)

        response = self.client.get(self.scan_url())

        self.assertContains(
            response,
            "You are not allowed to use this QR code.",
            status_code=403,
        )
        self.assertNotContains(
            response,
            self.course.title,
            status_code=403,
        )
        self.assertFalse(
            AttendanceRecord.objects.filter(student=self.unenrolled_student).exists()
        )

    def test_duplicate_scan_is_idempotent(self):
        self.make_token(expires_at=timezone.now() + timedelta(minutes=30))
        self.client.force_login(self.student)

        self.client.get(self.scan_url())

        self.set_session_started(minutes_ago=10)
        response = self.client.get(self.scan_url())

        self.assertContains(response, "Your attendance was already recorded")
        self.assertEqual(
            AttendanceRecord.objects.filter(student=self.student).count(),
            3,
        )
        self.assertEqual(
            set(
                AttendanceRecord.objects.filter(student=self.student).values_list(
                    "status",
                    flat=True,
                )
            ),
            {AttendanceRecord.Status.PRESENT},
        )

    @override_settings(LATE_THRESHOLD_MINUTES=5)
    def test_late_scan_records_late_attendance(self):
        self.set_session_started(minutes_ago=10)
        self.make_token()
        self.client.force_login(self.student)

        response = self.client.get(self.scan_url())

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Late")
        self.assertEqual(
            set(
                AttendanceRecord.objects.filter(student=self.student).values_list(
                    "status",
                    flat=True,
                )
            ),
            {AttendanceRecord.Status.LATE},
        )

    def test_closed_session_rejects_scan(self):
        self.session.status = ClassSession.Status.CLOSED
        self.session.save(update_fields=("status",))
        self.make_token()
        self.client.force_login(self.student)

        response = self.client.get(self.scan_url())

        self.assertContains(
            response,
            "This attendance session is not accepting QR scans.",
            status_code=400,
        )
        self.assertFalse(AttendanceRecord.objects.exists())

    def test_qr_scan_is_rejected_after_teacher_closes_session(self):
        self.make_token()
        self.client.force_login(self.monitor)
        self.client.post(reverse("attendance:session-close", args=[self.session.pk]))
        self.client.force_login(self.student)

        response = self.client.get(self.scan_url())

        self.assertContains(
            response,
            "This attendance session is not accepting QR scans.",
            status_code=400,
        )
        self.assertEqual(
            AttendanceRecord.objects.filter(
                recorded_method=AttendanceRecord.RecordedMethod.QR,
            ).count(),
            0,
        )

    def enable_location(self, *, radius=100):
        Course.objects.filter(pk=self.course.pk).update(
            require_attendance_location=True,
            attendance_location_name="Main classroom",
            attendance_latitude="35.689200",
            attendance_longitude="51.389000",
            attendance_radius_meters=radius,
        )

    def test_location_protected_scan_prompts_before_recording(self):
        self.enable_location()
        self.make_token()
        self.client.force_login(self.student)

        response = self.client.get(self.scan_url())

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Confirm your class location")
        self.assertFalse(AttendanceRecord.objects.exists())

    def test_location_protected_scan_accepts_student_inside_radius(self):
        self.enable_location(radius=75)
        self.make_token()
        self.client.force_login(self.student)

        response = self.client.post(
            self.scan_url(),
            {"latitude": "35.689210", "longitude": "51.389010", "accuracy": "8"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Attendance recorded successfully")
        self.assertEqual(AttendanceRecord.objects.count(), 3)

    def test_location_protected_scan_rejects_student_outside_radius(self):
        self.enable_location(radius=50)
        self.make_token()
        self.client.force_login(self.student)

        response = self.client.post(
            self.scan_url(),
            {"latitude": "35.699200", "longitude": "51.389000", "accuracy": "8"},
        )

        self.assertContains(response, "You must be within 50 m", status_code=400)
        self.assertFalse(AttendanceRecord.objects.exists())

    def test_location_protected_scan_rejects_inaccurate_location(self):
        self.enable_location(radius=50)
        self.make_token()
        self.client.force_login(self.student)

        response = self.client.post(
            self.scan_url(),
            {"latitude": "35.689200", "longitude": "51.389000", "accuracy": "80"},
        )

        self.assertContains(response, "Location accuracy is too low", status_code=400)
        self.assertFalse(AttendanceRecord.objects.exists())
