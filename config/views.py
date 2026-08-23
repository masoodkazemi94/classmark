from collections import Counter

from django.db.models import Count, Q
from django.shortcuts import render
from django.utils import timezone

from accounts.decorators import is_course_manager, is_monitor
from accounts.models import Notification
from attendance.models import (
    SESSION_SECTION_COUNT,
    AttendanceAuditLog,
    AttendanceRecord,
    ClassSession,
)
from courses.access import courses_for_user
from courses.models import Enrollment
from reports.services import calculate_attendance_totals


def _session_queryset(courses):
    return (
        ClassSession.objects.filter(course__in=courses)
        .select_related("course")
        .annotate(
            active_enrollment_count=Count(
                "course__enrollments",
                filter=Q(
                    course__enrollments__is_active=True,
                    course__enrollments__student__is_active=True,
                ),
                distinct=True,
            ),
            attendance_record_count=Count("attendance_records", distinct=True),
        )
    )


def _missing_count(session):
    expected = session.active_enrollment_count * SESSION_SECTION_COUNT
    return max(expected - session.attendance_record_count, 0)


def _management_dashboard_context(user):
    today = timezone.localdate()
    courses = courses_for_user(user, active_only=True)
    sessions = _session_queryset(courses)
    today_sessions = list(sessions.filter(date=today).order_by("start_time"))
    upcoming_sessions = list(
        sessions.filter(date__gte=today)
        .exclude(status=ClassSession.Status.CLOSED)
        .order_by("date", "start_time")[:8]
    )
    attention_sessions = []
    active_sessions = list(
        sessions.filter(status=ClassSession.Status.ACTIVE).order_by("date", "start_time")
    )
    for session in active_sessions:
        session.missing_count = _missing_count(session)
        if session.missing_count:
            attention_sessions.append(session)

    context = {
        "dashboard_mode": "management",
        "is_monitor_dashboard": is_monitor(user),
        "today": today,
        "course_count": courses.count(),
        "student_count": Enrollment.objects.filter(
            course__in=courses,
            is_active=True,
            student__is_active=True,
        )
        .values("student_id")
        .distinct()
        .count(),
        "today_sessions": today_sessions,
        "upcoming_sessions": upcoming_sessions,
        "attention_sessions": attention_sessions[:6],
        "missing_attendance_count": sum(
            session.missing_count for session in active_sessions
        ),
    }
    if is_monitor(user):
        context["recent_audit_logs"] = AttendanceAuditLog.objects.select_related(
            "student",
            "course",
            "changed_by",
            "section",
        )[:6]
    return context


def _student_dashboard_context(user):
    today = timezone.localdate()
    courses = courses_for_user(user, active_only=True)
    sessions = (
        ClassSession.objects.filter(course__in=courses, date__gte=today)
        .select_related("course")
        .order_by("date", "start_time")[:8]
    )
    records = AttendanceRecord.objects.filter(student=user).select_related(
        "course",
        "session",
        "section",
    )
    totals = calculate_attendance_totals(Counter(records.values_list("status", flat=True)))
    return {
        "dashboard_mode": "student",
        "today": today,
        "student_courses": courses.order_by("code", "title"),
        "upcoming_sessions": sessions,
        "recent_records": records.order_by("-recorded_at")[:8],
        "student_totals": totals,
        "recent_notifications": Notification.objects.filter(recipient=user)[:4],
        "unread_notification_count": Notification.objects.filter(
            recipient=user,
            read_at__isnull=True,
        ).count(),
    }


def home(request):
    context = {"dashboard_mode": "public"}
    if request.user.is_authenticated:
        if is_course_manager(request.user):
            context = _management_dashboard_context(request.user)
        else:
            context = _student_dashboard_context(request.user)
    return render(request, "home.html", context)
