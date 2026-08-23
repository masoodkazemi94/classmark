from django.contrib import messages
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render

from accounts.decorators import course_manager_required, is_monitor, monitor_required
from accounts.models import User

from .forms import ClassSessionForm, CourseForm, EnrollmentForm
from .models import Course, Enrollment


def _accessible_courses(user):
    courses = Course.objects.all()
    if not is_monitor(user):
        courses = courses.filter(
            enrollments__student=user,
            enrollments__is_active=True,
        )
    return courses.distinct()


def _get_accessible_course(user, course_id):
    return get_object_or_404(_accessible_courses(user), pk=course_id)


@course_manager_required
def course_list(request):
    courses = (
        _accessible_courses(request.user)
        .annotate(
            active_student_count=Count(
                "enrollments",
                filter=Q(enrollments__is_active=True),
                distinct=True,
            ),
            session_count=Count("sessions", distinct=True),
        )
        .order_by("code", "title")
    )
    return render(
        request,
        "courses/course_list.html",
        {"courses": courses, "can_create_course": is_monitor(request.user)},
    )


@monitor_required
def course_create(request):
    form = CourseForm(request.POST or None, monitor=request.user)
    if request.method == "POST" and form.is_valid():
        course = form.save()
        messages.success(request, f"{course.code} was created successfully.")
        return redirect("courses:course-detail", course_id=course.pk)
    if request.method == "POST":
        messages.error(request, "Course was not created. Correct the errors below.")
    return render(request, "courses/course_form.html", {"form": form})


@course_manager_required
def course_detail(request, course_id):
    course = _get_accessible_course(request.user, course_id)
    enrollments = course.enrollments.filter(is_active=True).select_related("student")
    sessions = course.sessions.order_by("-date", "-start_time")
    return render(
        request,
        "courses/course_detail.html",
        {
            "course": course,
            "enrollments": enrollments,
            "sessions": sessions,
            "enrollment_form": EnrollmentForm(
                course=course,
                actor=request.user,
            ),
            "can_view_reports": is_monitor(request.user),
        },
    )


@course_manager_required
def session_create(request, course_id):
    course = _get_accessible_course(request.user, course_id)
    form = ClassSessionForm(request.POST or None, course=course)

    if request.method == "POST" and form.is_valid():
        session = form.save()
        messages.success(request, "Session created.")
        return redirect("attendance:session-detail", session_id=session.pk)

    if request.method == "POST":
        messages.error(request, "Session was not created. Correct the errors below.")

    return render(
        request,
        "courses/session_form.html",
        {"course": course, "form": form},
    )


@course_manager_required
def enrollment_add(request, course_id):
    if request.method != "POST":
        return redirect("courses:course-detail", course_id=course_id)
    course = _get_accessible_course(request.user, course_id)
    form = EnrollmentForm(request.POST, course=course, actor=request.user)
    if form.is_valid():
        enrollment, created = Enrollment.objects.get_or_create(
            course=course,
            student=form.cleaned_data["student"],
            defaults={"is_active": True},
        )
        if not created:
            enrollment.is_active = True
            enrollment.save(update_fields=("is_active",))
        messages.success(request, "Student assigned to the course.")
    else:
        messages.error(request, "Student could not be assigned.")
    return redirect("courses:course-detail", course_id=course.pk)


@course_manager_required
def enrollment_remove(request, course_id, enrollment_id):
    if request.method != "POST":
        return redirect("courses:course-detail", course_id=course_id)
    course = _get_accessible_course(request.user, course_id)
    enrollment = get_object_or_404(Enrollment, pk=enrollment_id, course=course)
    if request.user.role == User.Role.CR and enrollment.student.role == User.Role.CR:
        messages.error(request, "A CR cannot remove another CR or themselves.")
    else:
        enrollment.is_active = False
        enrollment.save(update_fields=("is_active",))
        messages.success(request, "Student removed from the course.")
    return redirect("courses:course-detail", course_id=course.pk)
