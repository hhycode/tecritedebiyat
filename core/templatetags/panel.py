from django import template
from django.utils import timezone
from django.utils.formats import date_format

register = template.Library()


@register.filter
def once(zaman):
    """Kisa goreli zaman: "az önce", "5 dk önce", "3 sa önce", "2 gün önce", "3 hf önce", sonra tarih."""
    if not zaman:
        return ""
    saniye = (timezone.now() - zaman).total_seconds()
    if saniye < 60:
        return "az önce"
    dakika = int(saniye // 60)
    if dakika < 60:
        return f"{dakika} dk önce"
    saat = dakika // 60
    if saat < 24:
        return f"{saat} sa önce"
    gun = saat // 24
    if gun < 7:
        return f"{gun} gün önce"
    if gun < 30:
        return f"{gun // 7} hf önce"
    yerel = timezone.localtime(zaman)
    bicim = "j M" if yerel.year == timezone.localtime().year else "j M Y"
    return date_format(yerel, bicim)
