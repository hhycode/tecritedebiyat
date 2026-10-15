from django import template
from django.utils.safestring import mark_safe

from core.html_temizleme import temiz_html as _temiz_html

register = template.Library()


@register.filter
def temiz_html(value):
    """Kullanici HTML'ini guvenli etiketlere indirip isaretler (|safe yerine kullanilir)."""
    return mark_safe(_temiz_html(value))
