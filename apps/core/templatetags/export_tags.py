from django import template

register = template.Library()


@register.simple_tag(takes_context=True)
def export_url(context, fmt):
    """Current page URL with export=<fmt>, keeping active filters, dropping page."""
    params = context['request'].GET.copy()
    params.pop('page', None)
    params['export'] = fmt
    return '?' + params.urlencode()
