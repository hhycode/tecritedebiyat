from django.urls import reverse

# Tam ekran site menusu (templates/partials/site_menu.html): sira burada, tek yerde tanimlidir.
# (etiket, url adi, bu maddeyi aktif yapan url adlari)
SITE_MENUSU = [
    ("Ana Sayfa", "anasayfa", {"anasayfa"}),
    ("Hakkımızda", "hakkimizda", {"hakkimizda"}),
    ("Kitaplar", "kitaplar", {"kitaplar", "kitap_detay"}),
    ("Yazarlar", "yazarlar", {"yazarlar"}),
    ("Teklif Al", "kitap_maliyeti_hesapla", {"kitap_maliyeti_hesapla"}),
    ("Blog", "blog", {"blog", "blog_detay"}),
    ("Alıntılar", "alintilar", {"alintilar", "alinti_kitap", "alinti_yazar"}),
    ("SSS", "sss", {"sss"}),
    ("İletişim", "iletisim", {"iletisim"}),
]


def site_menusu(request):
    eslesme = getattr(request, "resolver_match", None)
    aktif = eslesme.url_name if eslesme else None
    return {
        "site_menusu": [
            {"etiket": etiket, "url": reverse(ad), "aktif": aktif in aktif_adlar}
            for etiket, ad, aktif_adlar in SITE_MENUSU
        ]
    }
