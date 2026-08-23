from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0003_replace_teacher_with_monitor_and_add_cr"),
        ("courses", "0001_initial"),
    ]

    operations = [
        migrations.RenameField(
            model_name="course",
            old_name="teacher",
            new_name="monitor",
        ),
        migrations.AlterField(
            model_name="course",
            name="monitor",
            field=models.ForeignKey(
                limit_choices_to={"role": "MONITOR"},
                on_delete=django.db.models.deletion.CASCADE,
                related_name="courses_created",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AlterField(
            model_name="enrollment",
            name="student",
            field=models.ForeignKey(
                limit_choices_to={"role__in": ("STUDENT", "CR")},
                on_delete=django.db.models.deletion.CASCADE,
                related_name="course_enrollments",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
    ]
