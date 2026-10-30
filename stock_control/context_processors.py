from django.conf import settings


def debug_context(request):
    """Add DEBUG setting to template context for development helpers."""
    return {
        'DEBUG': settings.DEBUG,
    }
