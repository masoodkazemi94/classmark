import csv

from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render

from accounts.decorators import monitor_required
from courses.models import Course, Enrollment

from .forms import ReportGenerationForm
from .services import (
    get_course_attendance_records,
    get_course_report,
    get_student_report,
)


SUMMARY_CSV_HEADERS = [
    "Student name",
    "Student code",
    "Present sections",
    "Late sections",
    "Absent sections",
    "Leave sections",
    "Absence hours",
    "Late-equivalent absences",
    "Total absence equivalent",
]

DETAIL_CSV_HEADERS = [
    "Date",
    "Session",
    "Section number",
    "Student",
    "Status",
    "Recorded method",
    "Note",
]


def _student_name(student):
    return student.get_full_name() or student.username


def _csv_response(filename):
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response


@monitor_required
def report_center(request):
    form = ReportGenerationForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        course = form.cleaned_data["course"]
        output = form.cleaned_data["output"]
        route = {
            ReportGenerationForm.Output.VIEW: "reports:course-report",
            ReportGenerationForm.Output.SUMMARY_CSV: "reports:course-report-csv",
            ReportGenerationForm.Output.DETAIL_CSV: (
                "reports:course-attendance-records-csv"
            ),
        }[output]
        return redirect(route, course_id=course.pk)

    return render(request, "reports/report_center.html", {"form": form})


@monitor_required
def course_report(request, course_id):
    course = get_object_or_404(Course, pk=course_id)

    return render(
        request,
        "reports/course_report.html",
        {
            "course": course,
            "report_rows": get_course_report(course),
        },
    )


@monitor_required
def course_report_csv(request, course_id):
    course = get_object_or_404(Course, pk=course_id)
    response = _csv_response(f"course-{course.pk}-attendance-report.csv")
    writer = csv.writer(response)

    writer.writerow(SUMMARY_CSV_HEADERS)
    for row in get_course_report(course):
        student = row["student"]
        writer.writerow(
            [
                _student_name(student),
                student.student_code,
                row["present_sections"],
                row["late_sections"],
                row["absent_sections"],
                row["leave_sections"],
                row["absence_hours"],
                row["late_equivalent_absences"],
                row["total_absence_equivalent"],
            ]
        )

    return response


@monitor_required
def course_attendance_records_csv(request, course_id):
    course = get_object_or_404(Course, pk=course_id)
    response = _csv_response(f"course-{course.pk}-attendance-details.csv")
    writer = csv.writer(response)

    writer.writerow(DETAIL_CSV_HEADERS)
    for record in get_course_attendance_records(course):
        writer.writerow(
            [
                record.session.date.isoformat(),
                str(record.session),
                record.section.section_number,
                _student_name(record.student),
                record.status,
                record.recorded_method,
                record.note,
            ]
        )

    return response


@monitor_required
def student_report_detail(request, course_id, student_id):
    course = get_object_or_404(Course, pk=course_id)
    enrollment = get_object_or_404(
        Enrollment.objects.select_related("student"),
        course=course,
        student_id=student_id,
        is_active=True,
    )

    return render(
        request,
        "reports/student_report_detail.html",
        {
            "course": course,
            "student": enrollment.student,
            "report": get_student_report(course, enrollment.student),
        },
    )
