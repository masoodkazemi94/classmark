from django.urls import path

from . import views

app_name = "courses"

urlpatterns = [
    path("", views.course_list, name="course-list"),
    path("create/", views.course_create, name="course-create"),
    path("<int:course_id>/", views.course_detail, name="course-detail"),
    path(
        "<int:course_id>/sessions/create/",
        views.session_create,
        name="session-create",
    ),
    path("<int:course_id>/enrollments/add/", views.enrollment_add, name="enrollment-add"),
    path(
        "<int:course_id>/enrollments/<int:enrollment_id>/remove/",
        views.enrollment_remove,
        name="enrollment-remove",
    ),
]
