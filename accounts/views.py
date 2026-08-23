from django.contrib import messages
from django.contrib.auth import logout
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST

from .decorators import monitor_required
from .forms import PromoteCRForm
from .models import User


@require_POST
def logout_view(request):
    logout(request)
    return redirect("home")


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
