from base64 import b64encode
from datetime import datetime, timedelta
from io import BytesIO
from math import asin, cos, isfinite, radians, sin, sqrt

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

import qrcode

from accounts.models import User
from accounts.notification_services import notify_attendance_records
from courses.models import Enrollment

from .models import (
    SESSION_SECTION_COUNT,
    AttendanceAuditLog,
    AttendanceRecord,
    AttendanceStatus,
    AttendanceToken,
    ClassSession,
    SessionSection,
)


def _create_audit_log(*, record, action, old_status, changed_by, recorded_method, note):
    return AttendanceAuditLog.objects.create(
        attendance_record=record,
        student=record.student,
        course=record.course,
        session=record.session,
        section=record.section,
        action=action,
        old_status=old_status,
        new_status=record.status,
        changed_by=changed_by,
        recorded_method=recorded_method,
        note=note,
    )


def _validate_status(status):
    if status not in AttendanceStatus.values:
        raise ValidationError({"status": "Select a valid attendance status."})


def _validate_enrollment(*, student, course):
    if (
        not getattr(student, "pk", None)
        or not getattr(course, "pk", None)
        or not Enrollment.objects.filter(
            student=student,
            course=course,
            is_active=True,
        ).exists()
    ):
        raise ValidationError(
            {"student": "Student must be actively enrolled in the course."}
        )


def _validate_manual_actor(*, student, course, recorded_by):
    if not recorded_by or recorded_by.role != User.Role.CR:
        return
    _validate_enrollment(student=recorded_by, course=course)
    if student.role == User.Role.CR and student.pk != recorded_by.pk:
        raise ValidationError(
            {"student": "A CR cannot change another CR's attendance."}
        )


def _validate_session(*, course, session):
    if (
        not getattr(course, "pk", None)
        or not getattr(session, "pk", None)
        or not ClassSession.objects.filter(pk=session.pk, course=course).exists()
    ):
        raise ValidationError(
            {"session": "Session must belong to the selected course."}
        )


def _validate_section(*, session, section):
    if (
        not getattr(session, "pk", None)
        or not getattr(section, "pk", None)
        or not SessionSection.objects.filter(pk=section.pk, session=session).exists()
    ):
        raise ValidationError(
            {"section": "Section must belong to the selected session."}
        )


def _get_session_sections(session):
    sections = list(session.sections.order_by("section_number"))
    if len(sections) != SESSION_SECTION_COUNT:
        raise ValidationError(
            {"session": f"Session must have exactly {SESSION_SECTION_COUNT} sections."}
        )
    return sections


def _session_start_datetime(session):
    start_datetime = datetime.combine(session.date, session.start_time)
    if timezone.is_naive(start_datetime):
        return timezone.make_aware(start_datetime, timezone.get_current_timezone())
    return start_datetime


def _get_qr_attendance_status(*, session, scanned_at):
    present_until = _session_start_datetime(session) + timedelta(
        minutes=settings.LATE_THRESHOLD_MINUTES
    )
    if scanned_at <= present_until:
        return AttendanceRecord.Status.PRESENT
    return AttendanceRecord.Status.LATE


@transaction.atomic
def create_attendance_token(*, course, session, section=None):
    """Create a short-lived secure attendance token."""
    _validate_session(course=course, session=session)
    if section is not None:
        _validate_section(session=session, section=section)

    active_tokens = AttendanceToken.objects.select_for_update().filter(
        session=session,
        is_active=True,
    )
    list(active_tokens)
    active_tokens.update(is_active=False)

    return AttendanceToken.objects.create(
        course=course,
        session=session,
        section=section,
        expires_at=timezone.now()
        + timedelta(seconds=settings.QR_TOKEN_TTL_SECONDS),
    )


def build_attendance_scan_url(token):
    return f"/attendance/scan/{token.token}/"


def build_qr_code_data_url(value):
    image = qrcode.make(value)
    output = BytesIO()
    image.save(output, format="PNG")
    encoded_image = b64encode(output.getvalue()).decode("ascii")
    return f"data:image/png;base64,{encoded_image}"


def _validate_qr_token(*, token, student, scanned_at):
    if not token.is_active:
        raise ValidationError(
            {
                "token": (
                    "This QR code is no longer active. Please ask your CR or monitor "
                    "for the latest QR code."
                )
            }
        )

    if scanned_at >= token.expires_at:
        raise ValidationError(
            {
                "token": (
                    "This QR code has expired. Please scan the latest code on screen."
                )
            }
        )

    if token.session.status != ClassSession.Status.ACTIVE:
        raise ValidationError(
            {"session": "This attendance session is not accepting QR scans."}
        )

    _validate_enrollment(student=student, course=token.course)


def validate_qr_attendance_token(*, token_value, student, scanned_at=None):
    """Validate a token before displaying the browser location prompt."""
    try:
        token = AttendanceToken.objects.select_related(
            "course", "session", "section"
        ).get(token=token_value)
    except AttendanceToken.DoesNotExist as exc:
        raise ValidationError(
            {"token": "This QR code is invalid. Please scan the latest code on screen."}
        ) from exc

    _validate_qr_token(
        token=token,
        student=student,
        scanned_at=scanned_at or timezone.now(),
    )
    return token


def _coordinate(value, *, field_name, minimum, maximum):
    try:
        coordinate = float(value)
    except (TypeError, ValueError) as exc:
        raise ValidationError(
            {"location": f"Your browser did not provide a valid {field_name}."}
        ) from exc
    if not isfinite(coordinate) or not minimum <= coordinate <= maximum:
        raise ValidationError(
            {"location": f"Your browser provided an invalid {field_name}."}
        )
    return coordinate


def _validate_qr_location(*, course, latitude, longitude, accuracy):
    if not course.require_attendance_location:
        return

    if course.attendance_latitude is None or course.attendance_longitude is None:
        raise ValidationError(
            {"location": "This course's attendance location is not configured."}
        )

    if latitude in (None, "") or longitude in (None, "") or accuracy in (None, ""):
        raise ValidationError(
            {"location": "Location access is required for this course's QR check-in."}
        )

    student_latitude = _coordinate(
        latitude, field_name="latitude", minimum=-90, maximum=90
    )
    student_longitude = _coordinate(
        longitude, field_name="longitude", minimum=-180, maximum=180
    )
    location_accuracy = _coordinate(
        accuracy, field_name="location accuracy", minimum=0, maximum=100000
    )
    allowed_radius = course.attendance_radius_meters
    if location_accuracy > allowed_radius:
        raise ValidationError(
            {
                "location": (
                    f"Location accuracy is too low ({location_accuracy:.0f} m). "
                    "Move near a window, enable precise location, and scan again."
                )
            }
        )

    earth_radius_meters = 6_371_000
    course_latitude = float(course.attendance_latitude)
    course_longitude = float(course.attendance_longitude)
    latitude_delta = radians(course_latitude - student_latitude)
    longitude_delta = radians(course_longitude - student_longitude)
    haversine = sin(latitude_delta / 2) ** 2 + (
        cos(radians(student_latitude))
        * cos(radians(course_latitude))
        * sin(longitude_delta / 2) ** 2
    )
    distance = 2 * earth_radius_meters * asin(sqrt(haversine))
    if distance > allowed_radius:
        raise ValidationError(
            {
                "location": (
                    f"You are about {distance:.0f} m from the class location. "
                    f"You must be within {allowed_radius} m to check in."
                )
            }
        )


@transaction.atomic
def create_qr_attendance_from_token(
    *,
    token_value,
    student,
    scanned_at=None,
    latitude=None,
    longitude=None,
    accuracy=None,
):
    """Create QR attendance records for an enrolled student without overwriting."""
    try:
        token = (
            AttendanceToken.objects.select_for_update()
            .select_related("course", "session", "section")
            .get(token=token_value)
        )
    except AttendanceToken.DoesNotExist as exc:
        raise ValidationError(
            {
                "token": (
                    "This QR code is invalid. Please ask your CR or monitor for a new "
                    "QR code."
                )
            }
        ) from exc

    scanned_at = scanned_at or timezone.now()

    _validate_qr_token(token=token, student=student, scanned_at=scanned_at)
    _validate_qr_location(
        course=token.course,
        latitude=latitude,
        longitude=longitude,
        accuracy=accuracy,
    )
    sections = [token.section] if token.section else _get_session_sections(
        token.session
    )
    status = _get_qr_attendance_status(session=token.session, scanned_at=scanned_at)
    records = []
    created_records = []
    created_count = 0

    for section in sections:
        record, created = AttendanceRecord.objects.select_for_update().get_or_create(
            student=student,
            section=section,
            defaults={
                "course": token.course,
                "session": token.session,
                "status": status,
                "recorded_by": student,
                "recorded_method": AttendanceRecord.RecordedMethod.QR,
            },
        )
        records.append(record)
        if created:
            created_count += 1
            created_records.append(record)
            _create_audit_log(
                record=record,
                action=AttendanceAuditLog.Action.CREATED,
                old_status="",
                changed_by=student,
                recorded_method=AttendanceRecord.RecordedMethod.QR,
                note="",
            )

    if created_records:
        notify_attendance_records(created_records)

    return {
        "token": token,
        "status": status,
        "records": records,
        "created_count": created_count,
        "already_recorded": created_count == 0,
    }


def _mark_attendance(
    *,
    student,
    course,
    session,
    section,
    status,
    recorded_by,
    recorded_method,
    note,
):
    existing = AttendanceRecord.objects.select_for_update().filter(
        student=student,
        section=section,
    ).first()
    old_status = existing.status if existing else ""
    record, created = AttendanceRecord.objects.update_or_create(
        student=student,
        section=section,
        defaults={
            "course": course,
            "session": session,
            "status": status,
            "recorded_by": recorded_by,
            "recorded_method": recorded_method,
            "note": note,
        },
    )
    _create_audit_log(
        record=record,
        action=(
            AttendanceAuditLog.Action.CREATED
            if created
            else AttendanceAuditLog.Action.UPDATED
        ),
        old_status=old_status,
        changed_by=recorded_by,
        recorded_method=recorded_method,
        note=note,
    )
    return record


@transaction.atomic
def mark_student_for_section(
    *,
    student,
    course,
    session,
    section,
    status,
    recorded_by=None,
    note="",
):
    """Create or update one student's manual attendance for one section."""
    _validate_status(status)
    _validate_enrollment(student=student, course=course)
    _validate_manual_actor(
        student=student,
        course=course,
        recorded_by=recorded_by,
    )
    _validate_session(course=course, session=session)
    _validate_section(session=session, section=section)

    record = _mark_attendance(
        student=student,
        course=course,
        session=session,
        section=section,
        status=status,
        recorded_by=recorded_by,
        recorded_method=AttendanceRecord.RecordedMethod.MANUAL,
        note=note,
    )
    notify_attendance_records([record])
    return record


@transaction.atomic
def mark_student_for_session(
    *,
    student,
    course,
    session,
    status,
    recorded_by=None,
    note="",
):
    """Create or update one student's manual attendance for all three sections."""
    _validate_status(status)
    _validate_enrollment(student=student, course=course)
    _validate_manual_actor(
        student=student,
        course=course,
        recorded_by=recorded_by,
    )
    _validate_session(course=course, session=session)
    sections = _get_session_sections(session)

    records = [
        _mark_attendance(
            student=student,
            course=course,
            session=session,
            section=section,
            status=status,
            recorded_by=recorded_by,
            recorded_method=AttendanceRecord.RecordedMethod.MANUAL,
            note=note,
        )
        for section in sections
    ]
    notify_attendance_records(records)
    return records


@transaction.atomic
def bulk_mark_missing_students_absent(*, course, session, recorded_by=None):
    """Mark missing records absent for actively enrolled students."""
    _validate_session(course=course, session=session)
    sections = _get_session_sections(session)
    enrollments = Enrollment.objects.filter(course=course, is_active=True).select_related(
        "student"
    )
    created_records = []

    for enrollment in enrollments:
        for section in sections:
            record, created = AttendanceRecord.objects.get_or_create(
                student=enrollment.student,
                section=section,
                defaults={
                    "course": course,
                    "session": session,
                    "status": AttendanceRecord.Status.ABSENT,
                    "recorded_by": recorded_by,
                    "recorded_method": AttendanceRecord.RecordedMethod.SYSTEM,
                },
            )
            if created:
                created_records.append(record)
                _create_audit_log(
                    record=record,
                    action=AttendanceAuditLog.Action.CREATED,
                    old_status="",
                    changed_by=recorded_by,
                    recorded_method=AttendanceRecord.RecordedMethod.SYSTEM,
                    note="Session closed; missing attendance marked absent.",
                )

    if created_records:
        notify_attendance_records(created_records)

    return created_records


@transaction.atomic
def close_session(*, session, closed_by=None):
    """Close an active session and fill missing attendance records."""
    if not getattr(session, "pk", None):
        raise ValidationError({"session": "Session must already exist."})

    try:
        session = (
            ClassSession.objects.select_for_update()
            .select_related("course")
            .get(pk=session.pk)
        )
    except ClassSession.DoesNotExist as exc:
        raise ValidationError({"session": "Session must already exist."}) from exc

    if session.status == ClassSession.Status.CLOSED:
        return {
            "session": session,
            "created_records": [],
            "already_closed": True,
        }

    if session.status != ClassSession.Status.ACTIVE:
        raise ValidationError({"status": "Only active sessions can be closed."})

    created_records = bulk_mark_missing_students_absent(
        course=session.course,
        session=session,
        recorded_by=closed_by,
    )
    session.status = ClassSession.Status.CLOSED
    session.save(update_fields=("status",))

    return {
        "session": session,
        "created_records": created_records,
        "already_closed": False,
    }


@transaction.atomic
def change_attendance_record_manually(
    *,
    record,
    status,
    recorded_by=None,
    note=None,
):
    """Safely change an existing attendance record as a manual correction."""
    _validate_status(status)

    if not record.pk:
        raise ValidationError({"record": "Attendance record must already exist."})

    try:
        record = AttendanceRecord.objects.select_for_update().get(pk=record.pk)
    except AttendanceRecord.DoesNotExist as exc:
        raise ValidationError(
            {"record": "Attendance record must already exist."}
        ) from exc

    _validate_enrollment(student=record.student, course=record.course)
    _validate_session(course=record.course, session=record.session)
    _validate_section(session=record.session, section=record.section)

    _validate_manual_actor(
        student=record.student,
        course=record.course,
        recorded_by=recorded_by,
    )
    old_status = record.status
    record.status = status
    record.recorded_by = recorded_by
    record.recorded_method = AttendanceRecord.RecordedMethod.MANUAL
    if note is not None:
        record.note = note

    record.full_clean()
    record.save(
        update_fields=("status", "recorded_by", "recorded_method", "note")
    )
    _create_audit_log(
        record=record,
        action=AttendanceAuditLog.Action.UPDATED,
        old_status=old_status,
        changed_by=recorded_by,
        recorded_method=AttendanceRecord.RecordedMethod.MANUAL,
        note=record.note,
    )
    notify_attendance_records([record])
    return record
