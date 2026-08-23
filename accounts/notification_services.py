from collections import defaultdict

from django.conf import settings
from django.core.mail import send_mail
from django.db import transaction

from courses.models import Enrollment

from .models import Notification


def _deliver_notification(notification_id):
    notification = Notification.objects.select_related("recipient").get(
        pk=notification_id
    )
    if not notification.recipient.email:
        notification.email_status = Notification.EmailStatus.SKIPPED
        notification.email_error = "Recipient has no email address."
    else:
        try:
            send_mail(
                notification.title,
                notification.message,
                settings.DEFAULT_FROM_EMAIL,
                [notification.recipient.email],
                fail_silently=False,
            )
        except Exception as error:  # Email failure must not roll back attendance.
            notification.email_status = Notification.EmailStatus.FAILED
            notification.email_error = str(error)[:2000]
        else:
            notification.email_status = Notification.EmailStatus.SENT
            notification.email_error = ""
    notification.save(update_fields=("email_status", "email_error"))


def create_notification(
    *,
    recipient,
    kind,
    title,
    message,
    course=None,
    session=None,
    attendance_record=None,
):
    notification = Notification.objects.create(
        recipient=recipient,
        kind=kind,
        title=title,
        message=message,
        course=course,
        session=session,
        attendance_record=attendance_record,
    )
    transaction.on_commit(
        lambda notification_id=notification.pk: _deliver_notification(notification_id),
        robust=True,
    )
    return notification


@transaction.atomic
def notify_students_about_session(*, session, title=None, message=None):
    recipients = (
        Enrollment.objects.filter(
            course=session.course,
            is_active=True,
            student__is_active=True,
        )
        .select_related("student")
        .order_by("student_id")
    )
    title = title or f"New class scheduled: {session.course.code}"
    message = message or (
        f"A class for {session.course.code} - {session.course.title} is scheduled "
        f"for {session.date:%Y-%m-%d} at {session.start_time:%H:%M}."
    )
    return [
        create_notification(
            recipient=enrollment.student,
            kind=Notification.Kind.CLASS_SESSION,
            title=title,
            message=message,
            course=session.course,
            session=session,
        )
        for enrollment in recipients
    ]


@transaction.atomic
def notify_attendance_records(records):
    records_by_student = defaultdict(list)
    for record in records:
        records_by_student[record.student_id].append(record)

    notifications = []
    for student_records in records_by_student.values():
        first = student_records[0]
        ordered = sorted(
            student_records,
            key=lambda record: record.section.section_number,
        )
        status_details = ", ".join(
            f"section {record.section.section_number}: {record.get_status_display()}"
            for record in ordered
        )
        notifications.append(
            create_notification(
                recipient=first.student,
                kind=Notification.Kind.ATTENDANCE,
                title=f"Attendance updated: {first.course.code}",
                message=(
                    f"Your attendance for {first.course.code} on "
                    f"{first.session.date:%Y-%m-%d} was updated — {status_details}."
                ),
                course=first.course,
                session=first.session,
                attendance_record=first,
            )
        )
    return notifications
