from datetime import date, time

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction

from attendance.models import ClassSession
from courses.models import Course, Enrollment


SAMPLE_PASSWORD = "classpulse123"


class Command(BaseCommand):
    help = "Create simple sample data for trying ClassPulse locally."

    @transaction.atomic
    def handle(self, *args, **options):
        user_model = get_user_model()
        teacher = self._get_or_create_teacher(user_model)
        students = self._get_or_create_students(user_model)
        course = self._get_or_create_course(teacher)
        enrollments = self._enroll_students(course, students)
        session = self._get_or_create_session(course)

        self.stdout.write(self.style.SUCCESS("Sample data is ready."))
        self.stdout.write(f"Teacher username: {teacher.username}")
        student_usernames = ", ".join(student.username for student in students)
        self.stdout.write(f"Student usernames: {student_usernames}")
        self.stdout.write(f"Password for sample users: {SAMPLE_PASSWORD}")
        self.stdout.write(f"Course: {course.code} - {course.title}")
        self.stdout.write(f"Active enrollments: {len(enrollments)}")
        self.stdout.write(
            f"Sample session: {session.date} at {session.start_time} "
            f"({session.sections.count()} sections)"
        )

    def _get_or_create_teacher(self, user_model):
        teacher, created = user_model.objects.get_or_create(
            username="sample_teacher",
            defaults={
                "email": "teacher@example.com",
                "first_name": "Sample",
                "last_name": "Teacher",
                "role": user_model.Role.TEACHER,
                "is_staff": True,
            },
        )
        if created:
            teacher.set_password(SAMPLE_PASSWORD)
            teacher.save(update_fields=("password",))
        changed_fields = []
        if teacher.role != user_model.Role.TEACHER:
            teacher.role = user_model.Role.TEACHER
            changed_fields.append("role")
        if not teacher.is_staff:
            teacher.is_staff = True
            changed_fields.append("is_staff")
        if changed_fields:
            teacher.save(update_fields=changed_fields)
        return teacher

    def _get_or_create_students(self, user_model):
        students = []
        sample_students = (
            ("sample_student_1", "STU-DEMO-001", "Ada", "Lovelace"),
            ("sample_student_2", "STU-DEMO-002", "Grace", "Hopper"),
            ("sample_student_3", "STU-DEMO-003", "Katherine", "Johnson"),
        )

        for username, student_code, first_name, last_name in sample_students:
            student, created = user_model.objects.get_or_create(
                username=username,
                defaults={
                    "email": f"{username}@example.com",
                    "first_name": first_name,
                    "last_name": last_name,
                    "role": user_model.Role.STUDENT,
                    "student_code": student_code,
                },
            )
            changed_fields = []
            if created:
                student.set_password(SAMPLE_PASSWORD)
                student.save(update_fields=("password",))
            else:
                if student.role != user_model.Role.STUDENT:
                    student.role = user_model.Role.STUDENT
                    changed_fields.append("role")
                if student.student_code != student_code:
                    student.student_code = student_code
                    changed_fields.append("student_code")
                if changed_fields:
                    student.save(update_fields=changed_fields)
            students.append(student)

        return students

    def _get_or_create_course(self, teacher):
        course, created = Course.objects.get_or_create(
            teacher=teacher,
            code="DEMO-101",
            defaults={
                "title": "Sample Attendance Course",
                "start_date": date(2026, 9, 1),
                "end_date": date(2026, 12, 15),
                "is_active": True,
            },
        )
        if not created and not course.is_active:
            course.is_active = True
            course.save(update_fields=("is_active",))
        return course

    def _enroll_students(self, course, students):
        enrollments = []
        for student in students:
            enrollment, created = Enrollment.objects.get_or_create(
                course=course,
                student=student,
                defaults={"is_active": True},
            )
            if not created and not enrollment.is_active:
                enrollment.is_active = True
                enrollment.save(update_fields=("is_active",))
            enrollments.append(enrollment)
        return enrollments

    def _get_or_create_session(self, course):
        session, _ = ClassSession.objects.get_or_create(
            course=course,
            date=date(2026, 9, 1),
            defaults={
                "start_time": time(9, 0),
                "end_time": time(11, 15),
                "status": ClassSession.Status.ACTIVE,
            },
        )
        return session
