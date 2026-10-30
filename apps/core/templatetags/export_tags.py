from django import template

register = template.Library()


# Rôle : renvoie l'URL de la page avec export=<format>, en gardant les filtres et en retirant page.
# Liens : tag de templates/partials/export_buttons.html ; ?export= est lu dans apps/core/exports.py.
@register.simple_tag(takes_context=True)
def export_url(context, fmt):
    """Current page URL with export=<fmt>, keeping active filters, dropping page."""
    params = context['request'].GET.copy()
    params.pop('page', None)
    params['export'] = fmt
    return '?' + params.urlencode()
