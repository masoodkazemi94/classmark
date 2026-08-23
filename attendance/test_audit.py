from datetime import date, time

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from courses.models import Course, Enrollment

from .models import AttendanceAuditLog, AttendanceRecord, ClassSession
from .services import mark_student_for_section


class AttendanceAuditTests(TestCase):
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
        cls.course = Course.objects.create(
            title="Course",
            code="AUDIT",
            monitor=cls.monitor,
            start_date=date(2026, 9, 1),
            end_date=date(2026, 12, 1),
        )
        Enrollment.objects.create(course=cls.course, student=cls.student)
        cls.session = ClassSession.objects.create(
            course=cls.course,
            date=date(2026, 9, 1),
            start_time=time(9),
            status=ClassSession.Status.ACTIVE,
        )

    def test_manual_create_and_update_record_old_and_new_statuses(self):
        section = self.session.sections.get(section_number=1)
        values = {
            "student": self.student,
            "course": self.course,
            "session": self.session,
            "section": section,
            "recorded_by": self.monitor,
        }

        mark_student_for_section(status=AttendanceRecord.Status.PRESENT, **values)
        mark_student_for_section(
            status=AttendanceRecord.Status.LATE,
            note="Correction",
            **values,
        )

        logs = list(AttendanceAuditLog.objects.order_by("created_at", "pk"))
        self.assertEqual(len(logs), 2)
        self.assertEqual(logs[0].action, AttendanceAuditLog.Action.CREATED)
        self.assertEqual(logs[0].old_status, "")
        self.assertEqual(logs[0].new_status, AttendanceRecord.Status.PRESENT)
        self.assertEqual(logs[1].action, AttendanceAuditLog.Action.UPDATED)
        self.assertEqual(logs[1].old_status, AttendanceRecord.Status.PRESENT)
        self.assertEqual(logs[1].new_status, AttendanceRecord.Status.LATE)
        self.assertEqual(logs[1].changed_by, self.monitor)
        self.assertEqual(logs[1].note, "Correction")

    def test_monitor_can_view_audit_page(self):
        self.client.force_login(self.monitor)

        response = self.client.get(reverse("attendance:audit-log"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Attendance audit log")
