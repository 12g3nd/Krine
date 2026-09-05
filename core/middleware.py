from django.conf import settings
from django.http import HttpResponse


class ArchiveReadOnlyMiddleware:
    """Fail closed on HTTP write methods while Krine is sealed."""

    SAFE_METHODS = {'GET', 'HEAD', 'OPTIONS'}

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if (
            getattr(settings, 'ARCHIVE_MODE', False)
            and request.method.upper() not in self.SAFE_METHODS
        ):
            response = HttpResponse(status=405)
            response['Allow'] = 'GET, HEAD, OPTIONS'
            response['X-Krine-Archive'] = 'read-only'
            return response

        response = self.get_response(request)
        if getattr(settings, 'ARCHIVE_MODE', False):
            response['X-Krine-Archive'] = 'closed-network'
        return response
