"""
URL configuration for config project.
"""
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path


urlpatterns = [
    path('', include('core.urls')),
]

# Archive mode is intentionally public-read-only. Do not leave the Django admin
# mounted when the application is sealed.
if not getattr(settings, 'ARCHIVE_MODE', False):
    urlpatterns.insert(0, path('admin/', admin.site.urls))

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
