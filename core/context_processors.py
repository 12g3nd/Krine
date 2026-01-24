
from .views import get_notification_count

def notifications(request):
    return {
        'notification_count': get_notification_count(request)
    }
