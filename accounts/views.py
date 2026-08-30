from django.contrib import messages
from django.contrib.auth import logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordChangeForm
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from .decorators import course_manager_required, is_monitor, monitor_required
from .forms import ProfileForm, PromoteCRForm, StudentCreateForm, StudentUpdateForm
from .models import Notification, User

from courses.models import Course, Enrollment


@require_POST
def logout_view(request):
    logout(request)
    return redirect("home")


@login_required
def profile(request):
    form = ProfileForm(request.POST or None, instance=request.user)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Your profile was updated.")
        return redirect("accounts:profile")
    if request.method == "POST":
        messages.error(request, "Your profile was not updated. Correct the errors below.")
    return render(
        request,
        "accounts/profile.html",
        {"form": form, "profile_user": request.user},
    )


@login_required
def password_change(request):
    form = PasswordChangeForm(request.user, request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        update_session_auth_hash(request, user)
        messages.success(request, "Your password was changed successfully.")
        return redirect("accounts:profile")
    if request.method == "POST":
        messages.error(request, "Your password was not changed. Correct the errors below.")
    return render(request, "accounts/password_change.html", {"form": form})


@monitor_required
def cr_management(request):
    form = PromoteCRForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        student = form.cleaned_data["student"]
        student.role = User.Role.CR
        student.save(update_fields=("role",))
        messages.success(request, f"{student.username} promoted to CR.")
        return redirect("accounts:cr-management")
    return render(
        request,
        "accounts/cr_management.html",
        {
            "form": form,
            "cr_users": User.objects.filter(role=User.Role.CR).order_by("username"),
        },
    )


def _cr_courses(user):
    return Course.objects.filter(
        enrollments__student=user,
        enrollments__is_active=True,
    ).distinct()


def _managed_students(user):
    students = User.objects.filter(role__in=(User.Role.STUDENT, User.Role.CR))
    if not is_monitor(user):
        students = students.filter(
            role=User.Role.STUDENT,
            course_enrollments__course__in=_cr_courses(user),
            course_enrollments__is_active=True,
        )
    return students.distinct()


@course_manager_required
def student_list(request):
    query = request.GET.get("q", "").strip()
    students = _managed_students(request.user)
    if query:
        students = students.filter(
            Q(username__icontains=query)
            | Q(first_name__icontains=query)
            | Q(last_name__icontains=query)
            | Q(student_code__icontains=query)
            | Q(email__icontains=query)
        )
    enrollment_filter = Q(course_enrollments__is_active=True)
    if not is_monitor(request.user):
        enrollment_filter &= Q(course_enrollments__course__in=_cr_courses(request.user))
    students = students.annotate(
        active_course_count=Count(
            "course_enrollments",
            filter=enrollment_filter,
            distinct=True,
        )
    ).order_by("username")
    return render(
        request,
        "accounts/student_list.html",
        {
            "students": students,
            "query": query,
            "can_global_manage": is_monitor(request.user),
        },
    )


@course_manager_required
@transaction.atomic
def student_create(request):
    form = StudentCreateForm(request.POST or None, actor=request.user)
    if request.method == "POST" and form.is_valid():
        student = form.save()
        course = form.cleaned_data.get("course")
        if course:
            Enrollment.objects.create(course=course, student=student)
        messages.success(request, f"Student {student.username} was created.")
        return redirect("accounts:student-list")
    if request.method == "POST":
        messages.error(request, "Student was not created. Correct the errors below.")
    return render(
        request,
        "accounts/student_form.html",
        {
            "form": form,
            "page_title": "Create student",
            "student": None,
            "can_global_manage": is_monitor(request.user),
        },
    )


@course_manager_required
def student_update(request, student_id):
    student = get_object_or_404(
        _managed_students(request.user),
        pk=student_id,
    )
    form = StudentUpdateForm(
        request.POST or None,
        instance=student,
        actor=request.user,
    )
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, f"{student.username} was updated.")
        return redirect("accounts:student-list")
    if request.method == "POST":
        messages.error(request, "Student was not updated. Correct the errors below.")
    return render(
        request,
        "accounts/student_form.html",
        {
            "form": form,
            "page_title": "Edit student",
            "student": student,
            "can_global_manage": is_monitor(request.user),
        },
    )


@monitor_required
@require_POST
@transaction.atomic
def student_deactivate(request, student_id):
    student = get_object_or_404(
        User,
        pk=student_id,
        role__in=(User.Role.STUDENT, User.Role.CR),
    )
    student.is_active = False
    student.save(update_fields=("is_active",))
    student.course_enrollments.filter(is_active=True).update(is_active=False)
    messages.success(
        request,
        f"{student.username} was deactivated. Attendance history was preserved.",
    )
    return redirect("accounts:student-list")


@monitor_required
@require_POST
def student_restore(request, student_id):
    student = get_object_or_404(
        User,
        pk=student_id,
        role__in=(User.Role.STUDENT, User.Role.CR),
    )
    student.is_active = True
    student.save(update_fields=("is_active",))
    messages.success(request, f"{student.username} was restored. Assign courses as needed.")
    return redirect("accounts:student-list")


def _require_notification_recipient(user):
    if user.role not in {User.Role.STUDENT, User.Role.CR}:
        raise PermissionDenied


@login_required
def notification_list(request):
    _require_notification_recipient(request.user)
    notifications = request.user.notifications.select_related(
        "course",
        "session",
        "attendance_record",
    )
    return render(
        request,
        "accounts/notification_list.html",
        {
            "notifications": notifications,
            "unread_count": notifications.filter(read_at__isnull=True).count(),
        },
    )


@login_required
@require_POST
def notification_mark_read(request, notification_id):
    _require_notification_recipient(request.user)
    notification = get_object_or_404(
        Notification,
        pk=notification_id,
        recipient=request.user,
    )
    notification.mark_read()
    return redirect("accounts:notification-list")


@login_required
@require_POST
def notifications_mark_all_read(request):
    _require_notification_recipient(request.user)
    request.user.notifications.filter(read_at__isnull=True).update(
        read_at=timezone.now()
    )
    messages.success(request, "All notifications marked as read.")
    return redirect("accounts:notification-list")
