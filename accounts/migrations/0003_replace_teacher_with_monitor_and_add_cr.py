from django.db import migrations, models


def convert_teachers_to_monitors(apps, schema_editor):
    User = apps.get_model("accounts", "User")
    User.objects.filter(role="TEACHER").update(role="MONITOR")
    if not User.objects.filter(username="sample_monitor").exists():
        User.objects.filter(username="sample_teacher").update(
            username="sample_monitor"
        )


class Migration(migrations.Migration):
    dependencies = [("accounts", "0002_user_phone_number_user_role_user_student_code")]

    operations = [
        migrations.AlterField(
            model_name="user",
            name="role",
            field=models.CharField(
                choices=[
                    ("ADMIN", "Admin"),
                    ("MONITOR", "Monitor"),
                    ("CR", "CR (Monitor Assistant)"),
                    ("STUDENT", "Student"),
                ],
                default="STUDENT",
                max_length=10,
            ),
        ),
        migrations.RunPython(
            convert_teachers_to_monitors,
            migrations.RunPython.noop,
        ),
    ]
