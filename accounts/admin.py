from django.contrib import admin
from django.contrib.auth.admin import GroupAdmin as BaseGroupAdmin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import Group
from django.utils.html import format_html
from unfold.admin import ModelAdmin
from unfold.forms import AdminPasswordChangeForm, UserChangeForm, UserCreationForm

from .models import Notification, User


@admin.register(User)
class CustomUserAdmin(BaseUserAdmin, ModelAdmin):
    form = UserChangeForm
    add_form = UserCreationForm
    change_password_form = AdminPasswordChangeForm
    list_display = (
        "username",
        "email",
        "role_badge",
        "student_code",
        "phone_number",
        "is_staff",
        "active_badge",
    )
    list_filter = BaseUserAdmin.list_filter + ("role",)
    search_fields = BaseUserAdmin.search_fields + ("student_code",)
    ordering = ("username",)
    fieldsets = BaseUserAdmin.fieldsets + (
        (
            "ClassPulse",
            {
                "fields": (
                    "role",
                    "student_code",
                    "phone_number",
                    "passport_number",
                    "passport_expiry",
                    "is_in_dormitory",
                    "dormitory_room",
                    "wechat_id",
                )
            },
        ),
        (
            "Administrative receipts",
            {
                "fields": (
                    "insurance_receipt",
                    "tuition_receipt",
                    "dormitory_receipt",
                )
            },
        ),
    )
    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        (
            "ClassPulse",
            {
                "fields": (
                    "role",
                    "student_code",
                    "phone_number",
                    "passport_number",
                    "passport_expiry",
                    "is_in_dormitory",
                    "dormitory_room",
                    "wechat_id",
                    "insurance_receipt",
                    "tuition_receipt",
                    "dormitory_receipt",
                )
            },
        ),
    )

    @admin.display(ordering="role", description="Role")
    def role_badge(self, obj):
        modifiers = {
            User.Role.ADMIN: "bg-red-100 text-red-700 dark:bg-red-500/20 dark:text-red-300",
            User.Role.MONITOR: "bg-sky-100 text-sky-700 dark:bg-sky-500/20 dark:text-sky-300",
            User.Role.CR: "bg-violet-100 text-violet-700 dark:bg-violet-500/20 dark:text-violet-300",
            User.Role.STUDENT: "bg-green-100 text-green-700 dark:bg-green-500/20 dark:text-green-300",
        }
        return format_html(
            '<span class="rounded-full px-2 py-1 text-xs font-medium {}">{}</span>',
            modifiers.get(
                obj.role,
                "bg-base-100 text-base-700 dark:bg-base-800 dark:text-base-300",
            ),
            obj.get_role_display(),
        )

    @admin.display(ordering="is_active", description="Status")
    def active_badge(self, obj):
        badge_class = (
            "bg-green-100 text-green-700 dark:bg-green-500/20 dark:text-green-300"
            if obj.is_active
            else "bg-base-100 text-base-700 dark:bg-base-800 dark:text-base-300"
        )
        label = "Active" if obj.is_active else "Inactive"
        return format_html(
            '<span class="rounded-full px-2 py-1 text-xs font-medium {}">{}</span>',
            badge_class,
            label,
        )


admin.site.unregister(Group)


@admin.register(Group)
class GroupAdmin(BaseGroupAdmin, ModelAdmin):
    pass


@admin.register(Notification)
class NotificationAdmin(ModelAdmin):
    list_display = (
        "title",
        "recipient",
        "kind",
        "email_status",
        "created_at",
        "read_at",
    )
    list_filter = ("kind", "email_status", "created_at")
    search_fields = ("title", "message", "recipient__username", "recipient__email")
    readonly_fields = (
        "recipient",
        "kind",
        "title",
        "message",
        "course",
        "session",
        "attendance_record",
        "email_status",
        "email_error",
        "created_at",
        "read_at",
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
