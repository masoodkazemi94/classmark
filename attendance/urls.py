from django.urls import path

from . import views

app_name = "attendance"

urlpatterns = [
    path("audit/", views.audit_log, name="audit-log"),
    path("scan/<str:token>/", views.scan_attendance, name="scan-attendance"),
    path("sessions/<int:session_id>/", views.session_detail, name="session-detail"),
    path(
        "sessions/<int:session_id>/close/",
        views.session_close,
        name="session-close",
    ),
    path("sessions/<int:session_id>/qr/", views.session_qr, name="session-qr"),
    path(
        "sessions/<int:session_id>/manual/",
        views.manual_attendance,
        name="manual-attendance",
    ),
]
