from django.db.models import Count
from django.urls import reverse
from django.utils import timezone

from accounts.models import User
from attendance.models import (
    SESSION_SECTION_COUNT,
    AttendanceRecord,
    AttendanceToken,
    ClassSession,
)
from courses.models import Course, Enrollment
from reports.services import get_course_report


def _admin_url(model, action="changelist", obj=None):
    app_label = model._meta.app_label
    model_name = model._meta.model_name
    if obj is None:
        return reverse(f"admin:{app_label}_{model_name}_{action}")
    return reverse(f"admin:{app_label}_{model_name}_{action}", args=[obj.pk])


def _teacher_courses(user):
    queryset = Course.objects.filter(is_active=True)
    if user.role == User.Role.TEACHER and not user.is_superuser:
        queryset = queryset.filter(teacher=user)
    return queryset.select_related("teacher").order_by("code", "title")


def _stat_cards(courses, sessions, active_tokens, missing_records):
    active_course_count = courses.count()
    active_student_count = (
        Enrollment.objects.filter(course__in=courses, is_active=True)
        .values("student_id")
        .distinct()
        .count()
    )
    return [
        {
            "label": "Active courses",
            "value": active_course_count,
            "icon": "school",
        },
        {
            "label": "Active sessions",
            "value": sessions.filter(status=ClassSession.Status.ACTIVE).count(),
            "icon": "event_available",
        },
        {
            "label": "Enrolled students",
            "value": active_student_count,
            "icon": "groups",
        },
        {
            "label": "Open QR tokens",
            "value": active_tokens.count(),
            "icon": "qr_code_2",
        },
        {
            "label": "Missing attendance",
            "value": missing_records,
            "icon": "assignment_late",
        },
    ]


def _missing_attendance_count(courses, active_sessions):
    enrollments_by_course = {
        item["course_id"]: item["total"]
        for item in Enrollment.objects.filter(course__in=courses, is_active=True)
        .values("course_id")
        .annotate(total=Count("id"))
    }
    expected_records = sum(
        enrollments_by_course.get(session.course_id, 0) * SESSION_SECTION_COUNT
        for session in active_sessions
    )
    recorded_count = AttendanceRecord.objects.filter(
        course__in=courses,
        session__in=active_sessions,
    ).count()
    return max(expected_records - recorded_count, 0)


def _quick_links(user, courses, sessions):
    links = []

    if user.role == User.Role.TEACHER:
        links.append(
            {
                "title": "Teacher courses",
                "description": "Open your teacher course workspace.",
                "icon": "dashboard",
                "url": reverse("courses:course-list"),
            }
        )

    if user.has_perm("courses.view_course"):
        links.append(
            {
                "title": "Admin courses",
                "description": "Review course setup and ownership.",
                "icon": "school",
                "url": _admin_url(Course),
            }
        )
    if user.has_perm("attendance.view_attendancerecord"):
        links.append(
            {
                "title": "Attendance records",
                "description": "Audit manual, QR, and system attendance.",
                "icon": "fact_check",
                "url": _admin_url(AttendanceRecord),
            }
        )
    if user.has_perm("attendance.view_attendancetoken"):
        links.append(
            {
                "title": "QR tokens",
                "description": "Inspect active and expired attendance tokens.",
                "icon": "qr_code_2",
                "url": _admin_url(AttendanceToken),
            }
        )

    first_course = courses.first()
    if first_course and user.role == User.Role.TEACHER:
        links.extend(
            [
                {
                    "title": "Course workspace",
                    "description": f"Open {first_course.code} students and sessions.",
                    "icon": "view_list",
                    "url": reverse("courses:course-detail", args=[first_course.pk]),
                },
                {
                    "title": "Create session",
                    "description": f"Start a class session for {first_course.code}.",
                    "icon": "add_circle",
                    "url": reverse("courses:session-create", args=[first_course.pk]),
                },
                {
                    "title": "Attendance report",
                    "description": f"Open absence totals for {first_course.code}.",
                    "icon": "bar_chart",
                    "url": reverse("reports:course-report", args=[first_course.pk]),
                },
            ]
        )

    first_active_session = sessions.filter(status=ClassSession.Status.ACTIVE).first()
    if first_active_session and user.role == User.Role.TEACHER:
        links.extend(
            [
                {
                    "title": "Show QR code",
                    "description": (
                        f"Open QR check-in for {first_active_session.course.code}."
                    ),
                    "icon": "qr_code_scanner",
                    "url": reverse(
                        "attendance:session-qr",
                        args=[first_active_session.pk],
                    ),
                },
                {
                    "title": "Manual attendance",
                    "description": "Mark or correct section attendance.",
                    "icon": "edit_note",
                    "url": reverse(
                        "attendance:session-detail",
                        args=[first_active_session.pk],
                    ),
                },
            ]
        )

    return links


def _session_rows(user, sessions):
    rows = []
    for session in sessions[:6]:
        row = {
            "course": session.course,
            "date": session.date,
            "time": session.start_time,
            "status": session.get_status_display(),
            "admin_url": _admin_url(ClassSession, "change", session),
            "primary_url": _admin_url(ClassSession, "change", session),
            "detail_url": "",
            "qr_url": "",
            "report_url": "",
        }
        if user.role == User.Role.TEACHER:
            row["detail_url"] = reverse("attendance:session-detail", args=[session.pk])
            row["primary_url"] = row["detail_url"]
            row["report_url"] = reverse(
                "reports:course-report",
                args=[session.course_id],
            )
            if session.status == ClassSession.Status.ACTIVE:
                row["qr_url"] = reverse("attendance:session-qr", args=[session.pk])
        rows.append(row)
    return rows


def _course_rows(user, courses):
    rows = []
    for course in courses[:6]:
        rows.append(
            {
                "course": course,
                "teacher": course.teacher,
                "students": Enrollment.objects.filter(
                    course=course,
                    is_active=True,
                ).count(),
                "sessions": course.sessions.count(),
                "admin_url": _admin_url(Course, "change", course),
                "primary_url": (
                    reverse("courses:course-detail", args=[course.pk])
                    if user.role == User.Role.TEACHER
                    else _admin_url(Course, "change", course)
                ),
                "report_url": (
                    reverse("reports:course-report", args=[course.pk])
                    if user.role == User.Role.TEACHER
                    else ""
                ),
            }
        )
    return rows


def _at_risk_rows(courses):
    rows = []
    for course in courses[:10]:
        for report_row in get_course_report(course):
            total_absences = report_row["total_absence_equivalent"]
            if total_absences <= 0:
                continue
            rows.append(
                {
                    "student": report_row["student"],
                    "course": course,
                    "late_sections": report_row["late_sections"],
                    "absence_hours": report_row["absence_hours"],
                    "total_absence_equivalent": total_absences,
                }
            )
    return sorted(
        rows,
        key=lambda row: (
            row["total_absence_equivalent"],
            row["absence_hours"],
            row["late_sections"],
        ),
        reverse=True,
    )[:5]


def dashboard_callback(request, context):
    user = request.user
    courses = _teacher_courses(user)
    sessions = (
        ClassSession.objects.filter(course__in=courses)
        .select_related("course", "course__teacher")
        .order_by("-date", "-start_time")
    )
    active_sessions = sessions.filter(status=ClassSession.Status.ACTIVE)
    active_tokens = AttendanceToken.objects.filter(
        course__in=courses,
        is_active=True,
        expires_at__gt=timezone.now(),
        session__status=ClassSession.Status.ACTIVE,
    )
    missing_records = _missing_attendance_count(courses, active_sessions)

    context.update(
        {
            "dashboard_title": (
                "Teacher dashboard"
                if user.role == User.Role.TEACHER
                else "Admin dashboard"
            ),
            "dashboard_subtitle": (
                "Quick access to courses, sessions, QR codes, and reports."
            ),
            "stat_cards": _stat_cards(
                courses,
                sessions,
                active_tokens,
                missing_records,
            ),
            "quick_links": _quick_links(user, courses, sessions),
            "course_rows": _course_rows(user, courses),
            "session_rows": _session_rows(user, sessions),
            "at_risk_rows": _at_risk_rows(courses),
        }
    )
    return context
