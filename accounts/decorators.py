from functools import wraps

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied

from courses.models import Enrollment

from .models import User


def is_monitor(user):
    return user.is_authenticated and (
        user.is_superuser or user.role in {User.Role.ADMIN, User.Role.MONITOR}
    )


def is_course_manager(user):
    return user.is_authenticated and (is_monitor(user) or user.role == User.Role.CR)


def can_access_course(user, course):
    if is_monitor(user):
        return True
    return (
        user.is_authenticated
        and user.role == User.Role.CR
        and Enrollment.objects.filter(
            course=course,
            student=user,
            is_active=True,
        ).exists()
    )


def monitor_required(view_func):
    @login_required
    @wraps(view_func)
    def wrapped_view(request, *args, **kwargs):
        if not is_monitor(request.user):
            raise PermissionDenied
        return view_func(request, *args, **kwargs)

    return wrapped_view


def course_manager_required(view_func):
    @login_required
    @wraps(view_func)
    def wrapped_view(request, *args, **kwargs):
        if not is_course_manager(request.user):
            raise PermissionDenied
        return view_func(request, *args, **kwargs)

    return wrapped_view
