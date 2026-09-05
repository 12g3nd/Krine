from datetime import date

from django.conf import settings
from django.db.models import Count, Min, Max, Q
from django.utils import timezone

from .models import Post, Comment, Reaction
from .views import get_notification_count


def notifications(request):
    if getattr(settings, 'ARCHIVE_MODE', False):
        return {'notification_count': 0}
    return {'notification_count': get_notification_count(request)}


def analytics(request):
    if getattr(settings, 'ARCHIVE_MODE', False):
        return {'GOOGLE_ANALYTICS_ID': ''}
    return {'GOOGLE_ANALYTICS_ID': getattr(settings, 'GOOGLE_ANALYTICS_ID', '')}


def _configured_date(name):
    raw = getattr(settings, name, '')
    if not raw:
        return None
    try:
        return date.fromisoformat(raw)
    except ValueError:
        return None


def archive_state(request):
    archive_mode = getattr(settings, 'ARCHIVE_MODE', False)
    if not archive_mode:
        return {'ARCHIVE_MODE': False, 'ARCHIVE': None}

    public_posts = Post.objects.filter(is_flagged=False, is_analyzed=True)
    post_stats = public_posts.aggregate(
        post_count=Count('id'),
        first_entry=Min('created_at'),
        last_entry=Max('created_at'),
    )

    post_count = post_stats['post_count'] or 0
    first_entry = post_stats['first_entry']
    last_entry = post_stats['last_entry']

    opened_date = _configured_date('ARCHIVE_OPENED_DATE')
    if not opened_date and first_entry:
        opened_date = timezone.localtime(first_entry).date()

    closed_date = _configured_date('ARCHIVE_CLOSED_DATE') or timezone.localdate()

    comment_count = Comment.objects.filter(
        post__is_flagged=False,
        post__is_analyzed=True,
    ).count()

    like_count = Reaction.objects.filter(
        post__is_flagged=False,
        post__is_analyzed=True,
        reaction_type=Reaction.LIKE,
    ).count()

    record_id = (
        f"KRN-{opened_date.strftime('%Y%m%d') if opened_date else 'UNKNOWN'}-"
        f"{closed_date.strftime('%Y%m%d')}-{post_count:04d}"
    )

    return {
        'ARCHIVE_MODE': True,
        'ARCHIVE': {
            'status': 'CLOSED',
            'post_count': post_count,
            'comment_count': comment_count,
            'like_count': like_count,
            'first_entry': first_entry,
            'last_entry': last_entry,
            'opened_date': opened_date,
            'closed_date': closed_date,
            'record_id': record_id,
            'site_url': getattr(settings, 'ARCHIVE_SITE_URL', 'https://krine.ca'),
        },
    }
