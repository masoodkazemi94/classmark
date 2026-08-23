from django.contrib.auth.views import LoginView
from django.urls import path

from . import views

app_name = "accounts"

urlpatterns = [
    path("login/", LoginView.as_view(template_name="accounts/login.html"), name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("notifications/", views.notification_list, name="notification-list"),
    path(
        "notifications/read-all/",
        views.notifications_mark_all_read,
        name="notifications-read-all",
    ),
    path(
        "notifications/<int:notification_id>/read/",
        views.notification_mark_read,
        name="notification-read",
    ),
    path("crs/", views.cr_management, name="cr-management"),
    path("students/", views.student_list, name="student-list"),
    path("students/create/", views.student_create, name="student-create"),
    path("students/<int:student_id>/edit/", views.student_update, name="student-update"),
    path(
        "students/<int:student_id>/deactivate/",
        views.student_deactivate,
        name="student-deactivate",
    ),
    path(
        "students/<int:student_id>/restore/",
        views.student_restore,
        name="student-restore",
    ),
]
