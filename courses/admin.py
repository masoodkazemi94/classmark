from django.contrib import admin
from django.db.models import Count
from django.utils.html import format_html
from unfold.admin import ModelAdmin

from .models import Course, Enrollment


@admin.register(Course)
class CourseAdmin(ModelAdmin):
    list_display = (
        "code",
        "title",
        "monitor",
        "enrolled_students",
        "session_count",
        "start_date",
        "end_date",
        "active_badge",
    )
    list_filter = ("is_active", "start_date", "end_date")
    search_fields = ("code", "title", "monitor__username")
    list_select_related = ("monitor",)
    autocomplete_fields = ("monitor",)
    date_hierarchy = "start_date"
    ordering = ("code",)
    fieldsets = (
        ("Course", {"fields": ("code", "title", "monitor", "is_active")}),
        ("Schedule", {"fields": ("start_date", "end_date")}),
    )

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        return queryset.annotate(
            enrollment_total=Count("enrollments", distinct=True),
            session_total=Count("sessions", distinct=True),
        )

    @admin.display(ordering="enrollment_total", description="Students")
    def enrolled_students(self, obj):
        return obj.enrollment_total

    @admin.display(ordering="session_total", description="Sessions")
    def session_count(self, obj):
        return obj.session_total

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


@admin.register(Enrollment)
class EnrollmentAdmin(ModelAdmin):
    list_display = ("student", "student_code", "course", "active_badge", "created_at")
    list_filter = ("is_active", "created_at", "course")
    search_fields = (
        "student__username",
        "student__student_code",
        "course__code",
        "course__title",
    )
    list_select_related = ("student", "course")
    autocomplete_fields = ("student", "course")
    date_hierarchy = "created_at"
    ordering = ("course__code", "student__username")
    readonly_fields = ("created_at",)

    @admin.display(ordering="student__student_code", description="Student code")
    def student_code(self, obj):
        return obj.student.student_code or "-"

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
