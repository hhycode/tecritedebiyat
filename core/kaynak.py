"""Alinti kaynaklari (kitap/yazar) icin Turkce duyarli normallestirme.

"Sabahattin Ali", "SABAHATTİN ALİ" ve "sabahattin  ali." ayni anahtari uretir; ayni kitabin/yazarin
tekrar eklenmesini bu anahtar uzerinden engelleriz.
"""
import re

from django.utils.text import slugify

_HARFLER = str.maketrans({
    "ı": "i", "ş": "s", "ğ": "g", "ü": "u", "ö": "o", "ç": "c",
    "â": "a", "î": "i", "û": "u", "é": "e", "è": "e", "ë": "e", "á": "a", "à": "a", "ä": "a",
})


def turkce_kucuk(metin):
    return (metin or "").replace("I", "ı").replace("İ", "i").lower()


def normal_anahtar(metin):
    """Karsilastirma anahtari: kucuk harf, Turkce harfler sadelesmis, noktalama yok, tek bosluk."""
    sade = turkce_kucuk(metin).translate(_HARFLER)
    sade = re.sub(r"[^\w\s]", " ", sade)
    return re.sub(r"\s+", " ", sade).strip()


def turkce_slug(metin):
    return slugify(normal_anahtar(metin)) or "kaynak"


def isbn_normal(deger):
    """ISBN'den tire ve bosluklari atar; 10 ya da 13 haneli degilse bos dondurur."""
    sade = re.sub(r"[\s-]", "", (deger or "")).upper()
    return sade if re.fullmatch(r"\d{9}[\dX]|\d{13}", sade) else ""
