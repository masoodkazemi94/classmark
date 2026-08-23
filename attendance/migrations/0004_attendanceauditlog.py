from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0003_replace_teacher_with_monitor_and_add_cr"),
        ("attendance", "0003_attendancetoken"),
        ("courses", "0002_rename_teacher_to_monitor"),
    ]

    operations = [
        migrations.CreateModel(
            name="AttendanceAuditLog",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("action", models.CharField(choices=[("CREATED", "Created"), ("UPDATED", "Updated")], max_length=10)),
                ("old_status", models.CharField(blank=True, choices=[("PRESENT", "Present"), ("LATE", "Late"), ("ABSENT", "Absent"), ("LEAVE", "Leave")], max_length=10)),
                ("new_status", models.CharField(choices=[("PRESENT", "Present"), ("LATE", "Late"), ("ABSENT", "Absent"), ("LEAVE", "Leave")], max_length=10)),
                ("recorded_method", models.CharField(choices=[("MANUAL", "Manual"), ("QR", "QR"), ("SYSTEM", "System")], max_length=10)),
                ("note", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("attendance_record", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="audit_logs", to="attendance.attendancerecord")),
                ("changed_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="attendance_changes_made", to=settings.AUTH_USER_MODEL)),
                ("course", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="attendance_audit_logs", to="courses.course")),
                ("section", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="attendance_audit_logs", to="attendance.sessionsection")),
                ("session", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="attendance_audit_logs", to="attendance.classsession")),
                ("student", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="attendance_audit_logs", to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ("-created_at", "-pk")},
        ),
    ]
