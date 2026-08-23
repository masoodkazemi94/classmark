from django.contrib import admin
from django.urls import include, path

from . import views

admin.site.site_header = "ClassPulse Admin"
admin.site.site_title = "ClassPulse Admin"
admin.site.index_title = "ClassPulse Control Center"

urlpatterns = [
    path("", views.home, name="home"),
    path("accounts/", include("accounts.urls")),
    path("admin/", admin.site.urls),
    path("courses/", include("courses.urls")),
    path("attendance/", include("attendance.urls")),
    path("reports/", include("reports.urls")),
]
