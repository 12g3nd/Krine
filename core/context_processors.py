from django.conf import settings

from .views import get_notification_count


def notifications(request):
    return {'notification_count': get_notification_count(request)}


def analytics(request):
    return {'GOOGLE_ANALYTICS_ID': getattr(settings, 'GOOGLE_ANALYTICS_ID', '')}
