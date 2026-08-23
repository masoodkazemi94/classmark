from .models import User


def notification_summary(request):
    if not request.user.is_authenticated or request.user.role not in {
        User.Role.STUDENT,
        User.Role.CR,
    }:
        return {"nav_unread_notification_count": 0}
    return {
        "nav_unread_notification_count": request.user.notifications.filter(
            read_at__isnull=True
        ).count()
    }
