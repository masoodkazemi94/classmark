from django.contrib import admin
from django.utils.html import format_html
from unfold.admin import ModelAdmin, TabularInline

from .models import (
    AttendanceAuditLog,
    AttendanceRecord,
    AttendanceToken,
    ClassSession,
    SessionSection,
)


def badge(label, modifier):
    classes = {
        "success": "bg-green-100 text-green-700 dark:bg-green-500/20 dark:text-green-300",
        "info": "bg-sky-100 text-sky-700 dark:bg-sky-500/20 dark:text-sky-300",
        "warning": "bg-amber-100 text-amber-800 dark:bg-amber-500/20 dark:text-amber-300",
        "danger": "bg-red-100 text-red-700 dark:bg-red-500/20 dark:text-red-300",
        "muted": "bg-base-100 text-base-700 dark:bg-base-800 dark:text-base-300",
    }
    return format_html(
        '<span class="rounded-full px-2 py-1 text-xs font-medium {}">{}</span>',
        classes[modifier],
        label,
    )


class SessionSectionInline(TabularInline):
    model = SessionSection
    extra = 0
    can_delete = False
    readonly_fields = ("section_number", "duration_minutes", "counted_hours")


@admin.register(ClassSession)
class ClassSessionAdmin(ModelAdmin):
    list_display = (
        "course",
        "date",
        "start_time",
        "end_time",
        "status_badge",
        "section_count",
    )
    list_filter = ("status", "date", "course")
    search_fields = ("course__code", "course__title")
    list_select_related = ("course",)
    autocomplete_fields = ("course",)
    date_hierarchy = "date"
    ordering = ("-date", "start_time")
    inlines = (SessionSectionInline,)

    @admin.display(ordering="status", description="Status")
    def status_badge(self, obj):
        modifiers = {
            ClassSession.Status.DRAFT: "info",
            ClassSession.Status.ACTIVE: "success",
            ClassSession.Status.CLOSED: "muted",
        }
        return badge(obj.get_status_display(), modifiers[obj.status])

    @admin.display(description="Sections")
    def section_count(self, obj):
        return obj.sections.count()


@admin.register(SessionSection)
class SessionSectionAdmin(ModelAdmin):
    list_display = (
        "session",
        "section_number",
        "duration_minutes",
        "counted_hours",
    )
    list_filter = ("section_number",)
    search_fields = ("session__course__code", "session__course__title")
    list_select_related = ("session", "session__course")
    autocomplete_fields = ("session",)
    readonly_fields = ("session", "section_number", "duration_minutes", "counted_hours")
    ordering = ("session__date", "section_number")

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(AttendanceRecord)
class AttendanceRecordAdmin(ModelAdmin):
    list_display = (
        "student",
        "student_code",
        "course",
        "session_date",
        "section_number",
        "status_badge",
        "method_badge",
        "recorded_by",
        "recorded_at",
    )
    list_filter = ("status", "recorded_method", "course", "session__date")
    search_fields = (
        "student__username",
        "student__student_code",
        "course__code",
        "course__title",
        "note",
    )
    list_select_related = (
        "student",
        "course",
        "session",
        "section",
        "recorded_by",
    )
    autocomplete_fields = ("student", "course", "session", "section", "recorded_by")
    date_hierarchy = "recorded_at"
    ordering = ("-recorded_at",)
    readonly_fields = ("recorded_at",)
    fieldsets = (
        (
            "Attendance",
            {"fields": ("student", "course", "session", "section", "status")},
        ),
        (
            "Recording",
            {"fields": ("recorded_method", "recorded_by", "recorded_at", "note")},
        ),
    )

    @admin.display(ordering="student__student_code", description="Student code")
    def student_code(self, obj):
        return obj.student.student_code or "-"

    @admin.display(ordering="session__date", description="Session date")
    def session_date(self, obj):
        return obj.session.date

    @admin.display(ordering="section__section_number", description="Section")
    def section_number(self, obj):
        return obj.section.section_number

    @admin.display(ordering="status", description="Status")
    def status_badge(self, obj):
        modifiers = {
            AttendanceRecord.Status.PRESENT: "success",
            AttendanceRecord.Status.LATE: "warning",
            AttendanceRecord.Status.ABSENT: "danger",
            AttendanceRecord.Status.LEAVE: "info",
        }
        return badge(obj.get_status_display(), modifiers[obj.status])

    @admin.display(ordering="recorded_method", description="Method")
    def method_badge(self, obj):
        modifiers = {
            AttendanceRecord.RecordedMethod.MANUAL: "info",
            AttendanceRecord.RecordedMethod.QR: "success",
            AttendanceRecord.RecordedMethod.SYSTEM: "muted",
        }
        return badge(obj.get_recorded_method_display(), modifiers[obj.recorded_method])

    def has_delete_permission(self, request, obj=None):
        return False

    def save_model(self, request, obj, form, change):
        old_status = ""
        if change:
            old_status = AttendanceRecord.objects.get(pk=obj.pk).status
        super().save_model(request, obj, form, change)
        AttendanceAuditLog.objects.create(
            attendance_record=obj,
            student=obj.student,
            course=obj.course,
            session=obj.session,
            section=obj.section,
            action=(
                AttendanceAuditLog.Action.UPDATED
                if change
                else AttendanceAuditLog.Action.CREATED
            ),
            old_status=old_status,
            new_status=obj.status,
            changed_by=request.user,
            recorded_method=AttendanceRecord.RecordedMethod.MANUAL,
            note=obj.note,
        )


@admin.register(AttendanceToken)
class AttendanceTokenAdmin(ModelAdmin):
    list_display = (
        "token_preview",
        "course",
        "session",
        "section_label",
        "active_badge",
        "valid_badge",
        "expires_at",
        "created_at",
    )
    list_filter = ("is_active", "expires_at", "course")
    search_fields = ("token", "course__code", "course__title")
    list_select_related = ("course", "session", "section")
    autocomplete_fields = ("course", "session", "section")
    date_hierarchy = "expires_at"
    ordering = ("-created_at",)
    readonly_fields = ("token", "created_at")

    @admin.display(description="Token")
    def token_preview(self, obj):
        return f"{obj.token[:8]}...{obj.token[-6:]}"

    @admin.display(ordering="section__section_number", description="Section")
    def section_label(self, obj):
        if obj.section_id:
            return obj.section.section_number
        return "All sections"

    @admin.display(ordering="is_active", description="Active")
    def active_badge(self, obj):
        return badge("Active", "success") if obj.is_active else badge("Inactive", "muted")

    @admin.display(description="Validity")
    def valid_badge(self, obj):
        return badge("Valid", "success") if obj.is_valid else badge("Invalid", "danger")


@admin.register(AttendanceAuditLog)
class AttendanceAuditLogAdmin(ModelAdmin):
    list_display = (
        "created_at",
        "course",
        "student",
        "section",
        "action",
        "old_status",
        "new_status",
        "changed_by",
        "recorded_method",
    )
    list_filter = ("action", "recorded_method", "old_status", "new_status", "course")
    search_fields = (
        "student__username",
        "student__student_code",
        "changed_by__username",
        "course__code",
        "note",
    )
    list_select_related = ("student", "course", "session", "section", "changed_by")
    ordering = ("-created_at",)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
