import calendar
from datetime import date, datetime

from django.contrib import messages
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from accounts.decorators import course_manager_required, is_monitor, monitor_required
from accounts.models import User
from accounts.notification_services import notify_students_about_session
from attendance.models import ClassSession

from .access import courses_for_user
from .forms import ClassSessionForm, CourseForm, EnrollmentForm
from .models import Course, Enrollment


def _accessible_courses(user):
    return courses_for_user(user)


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
def session_calendar(request):
    today = timezone.localdate()
    try:
        month_start = datetime.strptime(
            request.GET.get("month", ""),
            "%Y-%m",
        ).date().replace(day=1)
    except ValueError:
        month_start = today.replace(day=1)

    if month_start.month == 12:
        next_month = date(month_start.year + 1, 1, 1)
    else:
        next_month = date(month_start.year, month_start.month + 1, 1)
    if month_start.month == 1:
        previous_month = date(month_start.year - 1, 12, 1)
    else:
        previous_month = date(month_start.year, month_start.month - 1, 1)

    courses = _accessible_courses(request.user).order_by("code", "title")
    selected_course = None
    course_id = request.GET.get("course", "").strip()
    if course_id:
        selected_course = get_object_or_404(courses, pk=course_id)

    selected_status = request.GET.get("status", "").strip()
    if selected_status not in ClassSession.Status.values:
        selected_status = ""

    sessions = ClassSession.objects.filter(
        course__in=courses,
        date__gte=month_start,
        date__lt=next_month,
    ).select_related("course")
    if selected_course:
        sessions = sessions.filter(course=selected_course)
    if selected_status:
        sessions = sessions.filter(status=selected_status)

    sessions_by_date = {}
    for session in sessions.order_by("start_time", "course__code"):
        sessions_by_date.setdefault(session.date, []).append(session)

    month_weeks = []
    for week in calendar.Calendar(firstweekday=0).monthdatescalendar(
        month_start.year,
        month_start.month,
    ):
        month_weeks.append(
            [
                {
                    "date": day,
                    "in_month": day.month == month_start.month,
                    "is_today": day == today,
                    "sessions": sessions_by_date.get(day, []),
                }
                for day in week
            ]
        )

    return render(
        request,
        "courses/session_calendar.html",
        {
            "month_start": month_start,
            "previous_month": previous_month.strftime("%Y-%m"),
            "next_month": next_month.strftime("%Y-%m"),
            "today_month": today.strftime("%Y-%m"),
            "month_weeks": month_weeks,
            "courses": courses,
            "selected_course": selected_course,
            "selected_status": selected_status,
            "session_statuses": ClassSession.Status.choices,
        },
    )


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
    initial = {}
    if request.method == "GET" and request.GET.get("date"):
        try:
            initial["date"] = datetime.strptime(request.GET["date"], "%Y-%m-%d").date()
        except ValueError:
            pass
    form = ClassSessionForm(request.POST or None, course=course, initial=initial)

    if request.method == "POST" and form.is_valid():
        session = form.save()
        notifications = notify_students_about_session(session=session)
        messages.success(
            request,
            f"Session created. {len(notifications)} students notified.",
        )
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
