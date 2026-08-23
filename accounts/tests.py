from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase


class UserModelTests(TestCase):
    def test_teacher_user_can_be_created(self):
        user_model = get_user_model()

        teacher = user_model.objects.create_user(
            username="teacher",
            password="test-password",
            role=user_model.Role.MONITOR,
        )

        self.assertEqual(teacher.role, user_model.Role.MONITOR)
        self.assertIsNone(teacher.student_code)
        self.assertEqual(teacher.phone_number, "")
        self.assertTrue(teacher.check_password("test-password"))

    def test_student_user_can_be_created(self):
        user_model = get_user_model()

        student = user_model.objects.create_user(
            username="student",
            password="test-password",
            role=user_model.Role.STUDENT,
            student_code="STU-001",
            phone_number="+1-555-0100",
        )

        self.assertEqual(student.role, user_model.Role.STUDENT)
        self.assertEqual(student.student_code, "STU-001")
        self.assertEqual(student.phone_number, "+1-555-0100")
        self.assertTrue(student.check_password("test-password"))

    def test_role_must_be_a_supported_value(self):
        user_model = get_user_model()
        user = user_model(username="invalid-role", role="INVALID")

        with self.assertRaises(ValidationError) as context:
            user.full_clean()

        self.assertIn("role", context.exception.message_dict)

    def test_student_role_requires_student_code(self):
        user_model = get_user_model()
        student = user_model(username="student", role=user_model.Role.STUDENT)

        with self.assertRaises(ValidationError) as context:
            student.full_clean()

        self.assertEqual(
            context.exception.message_dict["student_code"],
            ["Student and CR users must have a student code."],
        )

    def test_string_representation_is_username(self):
        user_model = get_user_model()
        teacher = user_model(username="teacher", role=user_model.Role.MONITOR)

        self.assertEqual(str(teacher), "teacher")
