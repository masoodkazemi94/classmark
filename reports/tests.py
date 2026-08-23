import csv
import io
from datetime import date, time

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from attendance.models import AttendanceRecord, ClassSession
from courses.models import Course, Enrollment

from .services import (
    calculate_attendance_totals,
    get_course_report,
    get_student_report,
)


class ReportServiceTests(TestCase):
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
        cls.second_student = user_model.objects.create_user(
            username="second-student",
            role=user_model.Role.STUDENT,
            student_code="STU-002",
        )
        cls.inactive_student = user_model.objects.create_user(
            username="inactive-student",
            role=user_model.Role.STUDENT,
            student_code="STU-003",
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
        Enrollment.objects.create(course=cls.course, student=cls.second_student)
        Enrollment.objects.create(
            course=cls.course,
            student=cls.inactive_student,
            is_active=False,
        )
        Enrollment.objects.create(course=cls.other_course, student=cls.student)

        cls.sessions = [
            ClassSession.objects.create(
                course=cls.course,
                date=date(2026, 9, day),
                start_time=time(9, 0),
            )
            for day in (1, 2, 3)
        ]
        cls.other_session = ClassSession.objects.create(
            course=cls.other_course,
            date=date(2026, 9, 1),
            start_time=time(13, 0),
        )

        statuses = [
            AttendanceRecord.Status.PRESENT,
            AttendanceRecord.Status.PRESENT,
            AttendanceRecord.Status.LATE,
            AttendanceRecord.Status.LATE,
            AttendanceRecord.Status.LATE,
            AttendanceRecord.Status.LATE,
            AttendanceRecord.Status.ABSENT,
            AttendanceRecord.Status.ABSENT,
            AttendanceRecord.Status.LEAVE,
        ]
        sections = []
        for session in cls.sessions:
            sections.extend(session.sections.order_by("section_number"))

        for section, status in zip(sections, statuses):
            AttendanceRecord.objects.create(
                student=cls.student,
                course=cls.course,
                session=section.session,
                section=section,
                status=status,
                recorded_by=cls.monitor,
            )

        AttendanceRecord.objects.create(
            student=cls.student,
            course=cls.other_course,
            session=cls.other_session,
            section=cls.other_session.sections.get(section_number=1),
            status=AttendanceRecord.Status.ABSENT,
            recorded_by=cls.other_teacher,
        )

    def test_calculate_attendance_totals_uses_integer_report_formula(self):
        totals = calculate_attendance_totals(
            {
                AttendanceRecord.Status.PRESENT: 2,
                AttendanceRecord.Status.LATE: 4,
                AttendanceRecord.Status.ABSENT: 2,
                AttendanceRecord.Status.LEAVE: 1,
            }
        )

        self.assertEqual(
            totals,
            {
                "present_sections": 2,
                "late_sections": 4,
                "absent_sections": 2,
                "leave_sections": 1,
                "absence_hours": 2,
                "late_equivalent_absences": 1,
                "total_absence_equivalent": 3,
            },
        )

    def test_get_course_report_returns_each_active_student_summary(self):
        report_rows = get_course_report(self.course)

        self.assertEqual(
            [row["student"].username for row in report_rows],
            ["second-student", "student"],
        )
        self.assertEqual(
            report_rows[0],
            {
                "student": self.second_student,
                "present_sections": 0,
                "late_sections": 0,
                "absent_sections": 0,
                "leave_sections": 0,
                "absence_hours": 0,
                "late_equivalent_absences": 0,
                "total_absence_equivalent": 0,
            },
        )
        self.assertEqual(report_rows[1]["present_sections"], 2)
        self.assertEqual(report_rows[1]["late_sections"], 4)
        self.assertEqual(report_rows[1]["absent_sections"], 2)
        self.assertEqual(report_rows[1]["leave_sections"], 1)
        self.assertEqual(report_rows[1]["absence_hours"], 2)
        self.assertEqual(report_rows[1]["late_equivalent_absences"], 1)
        self.assertEqual(report_rows[1]["total_absence_equivalent"], 3)

    def test_get_student_report_returns_summary_and_raw_records(self):
        report = get_student_report(self.course, self.student)

        self.assertEqual(report["summary"]["present_sections"], 2)
        self.assertEqual(report["summary"]["late_sections"], 4)
        self.assertEqual(report["summary"]["absent_sections"], 2)
        self.assertEqual(report["summary"]["leave_sections"], 1)
        self.assertEqual(len(report["records"]), 9)
        self.assertEqual(
            [
                (
                    record.session.date,
                    record.section.section_number,
                    record.status,
                )
                for record in report["records"][:3]
            ],
            [
                (date(2026, 9, 1), 1, AttendanceRecord.Status.PRESENT),
                (date(2026, 9, 1), 2, AttendanceRecord.Status.PRESENT),
                (date(2026, 9, 1), 3, AttendanceRecord.Status.LATE),
            ],
        )


class ReportViewTests(TestCase):
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
            first_name="Ada",
            last_name="Lovelace",
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
        cls.session = ClassSession.objects.create(
            course=cls.course,
            date=date(2026, 9, 1),
            start_time=time(9, 0),
        )
        cls.second_session = ClassSession.objects.create(
            course=cls.course,
            date=date(2026, 9, 2),
            start_time=time(9, 0),
        )
        first_session_statuses = {
            1: (AttendanceRecord.Status.LATE, "Arrived after roll call."),
            2: (AttendanceRecord.Status.LATE, ""),
            3: (AttendanceRecord.Status.LATE, ""),
        }
        second_session_statuses = {
            1: (AttendanceRecord.Status.ABSENT, ""),
            2: (AttendanceRecord.Status.LEAVE, "Medical certificate."),
            3: (AttendanceRecord.Status.PRESENT, ""),
        }
        for session, section_statuses in (
            (cls.session, first_session_statuses),
            (cls.second_session, second_session_statuses),
        ):
            for section in session.sections.order_by("section_number"):
                status, note = section_statuses[section.section_number]
                AttendanceRecord.objects.create(
                    student=cls.student,
                    course=cls.course,
                    session=session,
                    section=section,
                    status=status,
                    recorded_by=cls.monitor,
                    note=note,
                )

    def _csv_rows(self, response):
        return list(csv.reader(io.StringIO(response.content.decode())))

    def test_monitor_can_open_report_center(self):
        self.client.force_login(self.monitor)

        response = self.client.get(reverse("reports:report-center"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Generate attendance report")
        self.assertContains(response, self.course.code)
        self.assertContains(response, "View interactive report")

    def test_report_center_routes_each_output_to_existing_report(self):
        self.client.force_login(self.monitor)
        outputs = {
            "VIEW": "reports:course-report",
            "SUMMARY_CSV": "reports:course-report-csv",
            "DETAIL_CSV": "reports:course-attendance-records-csv",
        }

        for output, route in outputs.items():
            with self.subTest(output=output):
                response = self.client.post(
                    reverse("reports:report-center"),
                    {"course": self.course.pk, "output": output},
                )
                self.assertRedirects(
                    response,
                    reverse(route, args=[self.course.pk]),
                    fetch_redirect_response=False,
                )

    def test_cr_cannot_access_report_center(self):
        cr = get_user_model().objects.create_user(
            username="report-cr",
            role=get_user_model().Role.CR,
            student_code="CR-REPORT",
        )
        self.client.force_login(cr)

        response = self.client.get(reverse("reports:report-center"))

        self.assertEqual(response.status_code, 403)

    def test_anonymous_user_is_redirected_from_report_center(self):
        url = reverse("reports:report-center")

        response = self.client.get(url)

        self.assertRedirects(
            response,
            f"/accounts/login/?next={url}",
            fetch_redirect_response=False,
        )

    def test_anonymous_user_is_redirected_from_course_report(self):
        url = reverse("reports:course-report", args=[self.course.pk])

        response = self.client.get(url)

        self.assertRedirects(
            response,
            f"/accounts/login/?next={url}",
            fetch_redirect_response=False,
        )

    def test_student_cannot_access_course_report(self):
        self.client.force_login(self.student)

        response = self.client.get(
            reverse("reports:course-report", args=[self.course.pk])
        )

        self.assertEqual(response.status_code, 403)

    def test_teacher_can_view_owned_course_report(self):
        self.client.force_login(self.monitor)

        response = self.client.get(
            reverse("reports:course-report", args=[self.course.pk])
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Attendance report")
        self.assertContains(response, self.course.code)
        self.assertContains(response, self.student.username)
        self.assertContains(response, "Late-equivalent absences")
        self.assertContains(response, "1")

    def test_other_monitor_can_view_course_report(self):
        self.client.force_login(self.other_teacher)

        response = self.client.get(
            reverse("reports:course-report", args=[self.course.pk])
        )

        self.assertEqual(response.status_code, 200)

    def test_teacher_can_export_course_report_csv(self):
        self.client.force_login(self.monitor)

        response = self.client.get(
            reverse("reports:course-report-csv", args=[self.course.pk])
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "text/csv")
        self.assertEqual(
            response["Content-Disposition"],
            f'attachment; filename="course-{self.course.pk}-attendance-report.csv"',
        )
        self.assertEqual(
            self._csv_rows(response),
            [
                [
                    "Student name",
                    "Student code",
                    "Present sections",
                    "Late sections",
                    "Absent sections",
                    "Leave sections",
                    "Absence hours",
                    "Late-equivalent absences",
                    "Total absence equivalent",
                ],
                ["Ada Lovelace", "STU-001", "1", "3", "1", "1", "1", "1", "2"],
            ],
        )

    def test_teacher_can_export_detailed_attendance_csv(self):
        self.client.force_login(self.monitor)

        response = self.client.get(
            reverse("reports:course-attendance-records-csv", args=[self.course.pk])
        )

        rows = self._csv_rows(response)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "text/csv")
        self.assertEqual(
            response["Content-Disposition"],
            f'attachment; filename="course-{self.course.pk}-attendance-details.csv"',
        )
        self.assertEqual(
            rows[0],
            [
                "Date",
                "Session",
                "Section number",
                "Student",
                "Status",
                "Recorded method",
                "Note",
            ],
        )
        self.assertEqual(
            rows[1],
            [
                "2026-09-01",
                "CS-101 - Introduction to Programming on 2026-09-01",
                "1",
                "Ada Lovelace",
                "LATE",
                "MANUAL",
                "Arrived after roll call.",
            ],
        )
        self.assertEqual(len(rows), 7)

    def test_student_cannot_export_course_report_csv(self):
        self.client.force_login(self.student)

        for url_name in (
            "reports:course-report-csv",
            "reports:course-attendance-records-csv",
        ):
            with self.subTest(url_name=url_name):
                response = self.client.get(reverse(url_name, args=[self.course.pk]))

                self.assertEqual(response.status_code, 403)

    def test_anonymous_user_is_redirected_from_csv_exports(self):
        for url_name in (
            "reports:course-report-csv",
            "reports:course-attendance-records-csv",
        ):
            with self.subTest(url_name=url_name):
                url = reverse(url_name, args=[self.course.pk])

                response = self.client.get(url)

                self.assertRedirects(
                    response,
                    f"/accounts/login/?next={url}",
                    fetch_redirect_response=False,
                )

    def test_other_monitor_can_export_course_report_csv(self):
        self.client.force_login(self.other_teacher)

        for url_name in (
            "reports:course-report-csv",
            "reports:course-attendance-records-csv",
        ):
            with self.subTest(url_name=url_name):
                response = self.client.get(reverse(url_name, args=[self.course.pk]))

                self.assertEqual(response.status_code, 200)

    def test_teacher_can_view_student_report_detail(self):
        self.client.force_login(self.monitor)

        response = self.client.get(
            reverse(
                "reports:student-report-detail",
                args=[self.course.pk, self.student.pk],
            )
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Student attendance detail")
        self.assertContains(response, "Late")
        self.assertContains(response, "Section 1")
        self.assertContains(response, "Arrived after roll call.")

    def test_student_cannot_view_student_report_detail(self):
        self.client.force_login(self.student)

        response = self.client.get(
            reverse(
                "reports:student-report-detail",
                args=[self.course.pk, self.student.pk],
            )
        )

        self.assertEqual(response.status_code, 403)

    def test_teacher_cannot_view_student_detail_for_another_teachers_course(self):
        self.client.force_login(self.monitor)

        response = self.client.get(
            reverse(
                "reports:student-report-detail",
                args=[self.other_course.pk, self.student.pk],
            )
        )

        self.assertEqual(response.status_code, 404)
