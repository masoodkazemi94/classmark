from django.urls import path

from . import views

app_name = "reports"

urlpatterns = [
    path("", views.report_center, name="report-center"),
    path("courses/<int:course_id>/", views.course_report, name="course-report"),
    path(
        "courses/<int:course_id>/export.csv",
        views.course_report_csv,
        name="course-report-csv",
    ),
    path(
        "courses/<int:course_id>/details.csv",
        views.course_attendance_records_csv,
        name="course-attendance-records-csv",
    ),
    path(
        "courses/<int:course_id>/students/<int:student_id>/",
        views.student_report_detail,
        name="student-report-detail",
    ),
]
