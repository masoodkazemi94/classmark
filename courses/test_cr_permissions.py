from datetime import date, time

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse

from attendance.models import AttendanceRecord, AttendanceToken, ClassSession
from attendance.services import mark_student_for_section
from courses.models import Course, Enrollment


class CRPermissionTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        users = get_user_model()
        cls.monitor = users.objects.create_user(
            username="monitor",
            role=users.Role.MONITOR,
        )
        cls.cr = users.objects.create_user(
            username="cr",
            role=users.Role.CR,
            student_code="CR-001",
        )
        cls.other_cr = users.objects.create_user(
            username="other-cr",
            role=users.Role.CR,
            student_code="CR-002",
        )
        cls.student = users.objects.create_user(
            username="student",
            role=users.Role.STUDENT,
            student_code="STU-001",
        )
        cls.new_student = users.objects.create_user(
            username="new-student",
            role=users.Role.STUDENT,
            student_code="STU-002",
        )
        cls.course = Course.objects.create(
            title="Assigned course",
            code="ASSIGNED",
            monitor=cls.monitor,
            start_date=date(2026, 9, 1),
            end_date=date(2026, 12, 1),
        )
        cls.other_course = Course.objects.create(
            title="Unassigned course",
            code="UNASSIGNED",
            monitor=cls.monitor,
            start_date=date(2026, 9, 1),
            end_date=date(2026, 12, 1),
        )
        Enrollment.objects.create(course=cls.course, student=cls.cr)
        Enrollment.objects.create(course=cls.course, student=cls.other_cr)
        Enrollment.objects.create(course=cls.course, student=cls.student)
        cls.session = ClassSession.objects.create(
            course=cls.course,
            date=date(2026, 9, 1),
            start_time=time(9),
            status=ClassSession.Status.ACTIVE,
        )

    def setUp(self):
        self.client.force_login(self.cr)

    def test_cr_sees_only_assigned_courses(self):
        response = self.client.get(reverse("courses:course-list"))

        self.assertContains(response, self.course.title)
        self.assertNotContains(response, self.other_course.title)

    def test_cr_can_create_session_only_for_assigned_course(self):
        response = self.client.post(
            reverse("courses:session-create", args=[self.course.pk]),
            {"date": "2026-09-02", "start_time": "09:00", "end_time": "11:15"},
        )
        self.assertEqual(response.status_code, 302)

        response = self.client.get(
            reverse("courses:session-create", args=[self.other_course.pk])
        )
        self.assertEqual(response.status_code, 404)

    def test_cr_can_mark_regular_student_and_self(self):
        section = self.session.sections.get(section_number=1)
        url = reverse("attendance:manual-attendance", args=[self.session.pk])

        for student in (self.student, self.cr):
            with self.subTest(student=student.username):
                response = self.client.post(
                    url,
                    {"student": student.pk, "section": section.pk, "status": "PRESENT", "note": ""},
                )
                self.assertEqual(response.status_code, 302)
                self.assertTrue(
                    AttendanceRecord.objects.filter(student=student, section=section).exists()
                )

    def test_cr_cannot_mark_another_cr(self):
        section = self.session.sections.get(section_number=1)
        response = self.client.post(
            reverse("attendance:manual-attendance", args=[self.session.pk]),
            {"student": self.other_cr.pk, "section": section.pk, "status": "ABSENT", "note": ""},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Select a valid choice")
        self.assertFalse(
            AttendanceRecord.objects.filter(student=self.other_cr, section=section).exists()
        )

        with self.assertRaises(ValidationError):
            mark_student_for_section(
                student=self.other_cr,
                course=self.course,
                session=self.session,
                section=section,
                status=AttendanceRecord.Status.ABSENT,
                recorded_by=self.cr,
            )

    def test_cr_can_generate_qr_and_close_session(self):
        response = self.client.post(
            reverse("attendance:session-qr", args=[self.session.pk])
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(AttendanceToken.objects.filter(session=self.session).exists())

        response = self.client.post(
            reverse("attendance:session-close", args=[self.session.pk])
        )
        self.assertEqual(response.status_code, 302)
        self.session.refresh_from_db()
        self.assertEqual(self.session.status, ClassSession.Status.CLOSED)

    def test_cr_cannot_view_reports_or_audit_log(self):
        for url in (
            reverse("reports:course-report", args=[self.course.pk]),
            reverse("attendance:audit-log"),
        ):
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 403)

    def test_cr_can_assign_and_remove_regular_student_but_not_cr(self):
        response = self.client.post(
            reverse("courses:enrollment-add", args=[self.course.pk]),
            {"student": self.new_student.pk},
        )
        self.assertEqual(response.status_code, 302)
        enrollment = Enrollment.objects.get(course=self.course, student=self.new_student)
        self.assertTrue(enrollment.is_active)

        response = self.client.post(
            reverse("courses:enrollment-remove", args=[self.course.pk, enrollment.pk])
        )
        self.assertEqual(response.status_code, 302)
        enrollment.refresh_from_db()
        self.assertFalse(enrollment.is_active)

        other_cr_enrollment = Enrollment.objects.get(
            course=self.course,
            student=self.other_cr,
        )
        self.client.post(
            reverse(
                "courses:enrollment-remove",
                args=[self.course.pk, other_cr_enrollment.pk],
            )
        )
        other_cr_enrollment.refresh_from_db()
        self.assertTrue(other_cr_enrollment.is_active)
