from django.db import migrations


def backfill_audit_baseline(apps, schema_editor):
    User = apps.get_model("accounts", "User")
    AttendanceRecord = apps.get_model("attendance", "AttendanceRecord")
    AttendanceAuditLog = apps.get_model("attendance", "AttendanceAuditLog")

    User.objects.filter(is_superuser=True).update(role="ADMIN")

    logs = []
    for record in AttendanceRecord.objects.all().iterator():
        logs.append(
            AttendanceAuditLog(
                attendance_record_id=record.pk,
                student_id=record.student_id,
                course_id=record.course_id,
                session_id=record.session_id,
                section_id=record.section_id,
                action="CREATED",
                old_status="",
                new_status=record.status,
                changed_by_id=record.recorded_by_id,
                recorded_method=record.recorded_method,
                note=record.note,
            )
        )
    AttendanceAuditLog.objects.bulk_create(logs)


class Migration(migrations.Migration):
    dependencies = [("attendance", "0004_attendanceauditlog")]

    operations = [
        migrations.RunPython(
            backfill_audit_baseline,
            migrations.RunPython.noop,
        )
    ]
