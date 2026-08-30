from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.conf import settings
from django.core.exceptions import ValidationError
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_http_methods, require_POST

from accounts.decorators import can_access_course, course_manager_required, monitor_required
from accounts.notification_services import notify_students_about_session
from courses.models import Enrollment

from .forms import ManualAttendanceForm, SessionNotificationForm
from .models import AttendanceAuditLog, AttendanceRecord, AttendanceToken, ClassSession
from .services import (
    build_attendance_scan_url,
    build_qr_code_data_url,
    close_session,
    create_attendance_token,
    create_qr_attendance_from_token,
    mark_student_for_section,
    mark_student_for_session,
    validate_qr_attendance_token,
)


def _get_accessible_session(*, session_id, user):
    session = get_object_or_404(
        ClassSession.objects.select_related("course"),
        pk=session_id,
    )
    if not can_access_course(user, session.course):
        from django.core.exceptions import PermissionDenied

        raise PermissionDenied
    return session


def _session_detail_context(*, session, actor, manual_attendance_form=None):
    sections = list(session.sections.all())
    enrollments = list(
        Enrollment.objects.filter(course=session.course, is_active=True)
        .select_related("student")
        .order_by("student__username")
    )
    attendance_records = AttendanceRecord.objects.filter(
        session=session,
        student_id__in=[enrollment.student_id for enrollment in enrollments],
    )
    records_by_student_and_section = {
        (record.student_id, record.section_id): record
        for record in attendance_records
    }
    attendance_rows = []
    for enrollment in enrollments:
        statuses = []
        for section in sections:
            record = records_by_student_and_section.get(
                (enrollment.student_id, section.pk)
            )
            statuses.append(record.get_status_display() if record else "Not recorded")
        attendance_rows.append({"student": enrollment.student, "statuses": statuses})

    return {
        "session": session,
        "sections": sections,
        "attendance_rows": attendance_rows,
        "manual_attendance_form": manual_attendance_form
        or ManualAttendanceForm(session=session, actor=actor),
    }


def _add_service_errors(form, error):
    if hasattr(error, "message_dict"):
        for field, error_messages in error.message_dict.items():
            form_field = field if field in form.fields else None
            for error_message in error_messages:
                form.add_error(form_field, error_message)
        return

    for error_message in error.messages:
        form.add_error(None, error_message)


def _first_validation_error(error):
    if hasattr(error, "message_dict"):
        for error_messages in error.message_dict.values():
            return error_messages[0]
    return error.messages[0]


def _scan_error_response(request, error):
    status_code = 403 if "student" in getattr(error, "message_dict", {}) else 400
    message = (
        "You are not allowed to use this QR code."
        if status_code == 403
        else _first_validation_error(error)
    )
    messages.error(request, message)
    return render(
        request,
        "attendance/scan_error.html",
        {"message": message},
        status=status_code,
    )


@course_manager_required
def session_detail(request, session_id):
    session = _get_accessible_session(session_id=session_id, user=request.user)

    return render(
        request,
        "attendance/session_detail.html",
        _session_detail_context(session=session, actor=request.user),
    )


@course_manager_required
@require_http_methods(["GET", "POST"])
def session_notify(request, session_id):
    session = _get_accessible_session(session_id=session_id, user=request.user)
    form = SessionNotificationForm(request.POST or None, session=session)
    if request.method == "POST" and form.is_valid():
        notifications = notify_students_about_session(
            session=session,
            title=form.cleaned_data["title"],
            message=form.cleaned_data["message"],
        )
        messages.success(
            request,
            f"Class update created for {len(notifications)} enrolled students.",
        )
        return redirect("attendance:session-detail", session_id=session.pk)
    return render(
        request,
        "attendance/session_notify.html",
        {"session": session, "form": form},
    )


@course_manager_required
@require_http_methods(["GET", "POST"])
def session_qr(request, session_id):
    session = _get_accessible_session(session_id=session_id, user=request.user)

    if session.status != ClassSession.Status.ACTIVE:
        messages.error(request, "QR codes are available only for active sessions.")
        return redirect("attendance:session-detail", session_id=session.pk)

    if request.method == "POST":
        create_attendance_token(course=session.course, session=session)
        messages.success(request, "QR code refreshed.")
        return redirect("attendance:session-qr", session_id=session.pk)

    token = (
        AttendanceToken.objects.filter(
            session=session,
            is_active=True,
            expires_at__gt=timezone.now(),
        )
        .order_by("-created_at")
        .first()
    )
    scan_path = build_attendance_scan_url(token) if token else ""
    scan_url = request.build_absolute_uri(scan_path) if scan_path else ""
    qr_code_data_url = build_qr_code_data_url(scan_url) if scan_url else ""

    return render(
        request,
        "attendance/session_qr.html",
        {
            "session": session,
            "token": token,
            "scan_url": scan_url,
            "qr_code_data_url": qr_code_data_url,
            "qr_rotation_seconds": settings.QR_TOKEN_TTL_SECONDS,
        },
    )


@course_manager_required
@require_POST
def session_qr_refresh(request, session_id):
    session = _get_accessible_session(session_id=session_id, user=request.user)
    if session.status != ClassSession.Status.ACTIVE:
        return JsonResponse(
            {"error": "This session is no longer accepting QR scans."},
            status=409,
        )

    token = create_attendance_token(course=session.course, session=session)
    scan_url = request.build_absolute_uri(build_attendance_scan_url(token))
    return JsonResponse(
        {
            "scan_url": scan_url,
            "qr_code_data_url": build_qr_code_data_url(scan_url),
            "expires_at": timezone.localtime(token.expires_at).strftime("%H:%M:%S"),
            "rotation_seconds": settings.QR_TOKEN_TTL_SECONDS,
        }
    )


@login_required
@require_http_methods(["GET", "POST"])
def scan_attendance(request, token):
    if request.method == "GET":
        try:
            attendance_token = validate_qr_attendance_token(
                token_value=token,
                student=request.user,
            )
        except ValidationError as error:
            return _scan_error_response(request, error)

        if attendance_token.course.require_attendance_location:
            return render(
                request,
                "attendance/scan_location.html",
                {"attendance_token": attendance_token},
            )

    try:
        result = create_qr_attendance_from_token(
            token_value=token,
            student=request.user,
            latitude=request.POST.get("latitude"),
            longitude=request.POST.get("longitude"),
            accuracy=request.POST.get("accuracy"),
        )
    except ValidationError as error:
        return _scan_error_response(request, error)

    if result["already_recorded"]:
        message = "Your attendance was already recorded for this QR code."
    else:
        message = "Attendance recorded successfully."

    messages.success(request, message)
    return render(
        request,
        "attendance/scan_confirmation.html",
        {
            "message": message,
            "record_count": len(result["records"]),
            "status": result["status"],
        },
    )


@course_manager_required
@require_POST
def manual_attendance(request, session_id):
    session = _get_accessible_session(session_id=session_id, user=request.user)
    form = ManualAttendanceForm(request.POST, session=session, actor=request.user)

    if form.is_valid():
        attendance_values = {
            "student": form.cleaned_data["student"],
            "course": session.course,
            "session": session,
            "status": form.cleaned_data["status"],
            "recorded_by": request.user,
            "note": form.cleaned_data["note"],
        }

        try:
            section = form.cleaned_data["section"]
            if section:
                mark_student_for_section(section=section, **attendance_values)
            else:
                mark_student_for_session(**attendance_values)
        except ValidationError as error:
            _add_service_errors(form, error)
        else:
            messages.success(
                request,
                f"Attendance updated for {form.cleaned_data['student'].username}.",
            )
            return redirect("attendance:session-detail", session_id=session.pk)

    messages.error(request, "Attendance was not updated. Correct the errors below.")
    return render(
        request,
        "attendance/session_detail.html",
        _session_detail_context(
            session=session,
            actor=request.user,
            manual_attendance_form=form,
        ),
    )


@course_manager_required
@require_POST
def session_close(request, session_id):
    session = _get_accessible_session(session_id=session_id, user=request.user)

    try:
        result = close_session(session=session, closed_by=request.user)
    except ValidationError as error:
        messages.error(request, _first_validation_error(error))
    else:
        if result["already_closed"]:
            messages.info(request, "Session is already closed.")
        else:
            messages.success(
                request,
                "Session closed and missing records marked absent.",
            )

    return redirect("attendance:session-detail", session_id=session.pk)


@monitor_required
def audit_log(request):
    logs = AttendanceAuditLog.objects.select_related(
        "student",
        "course",
        "session",
        "section",
        "changed_by",
    )[:500]
    return render(request, "attendance/audit_log.html", {"audit_logs": logs})
