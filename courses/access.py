from accounts.models import User

from .models import Course


def courses_for_user(user, *, active_only=False):
    courses = Course.objects.all()
    if active_only:
        courses = courses.filter(is_active=True)
    if user.is_superuser or user.role in {User.Role.ADMIN, User.Role.MONITOR}:
        return courses
    return courses.filter(
        enrollments__student=user,
        enrollments__is_active=True,
    ).distinct()
