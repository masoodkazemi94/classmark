from django.contrib.auth.views import LoginView
from django.urls import path

from . import views

app_name = "accounts"

urlpatterns = [
    path("login/", LoginView.as_view(template_name="accounts/login.html"), name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("crs/", views.cr_management, name="cr-management"),
]
