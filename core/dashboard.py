"""
Kontrol paneli (dashboard) verileri.

Her bolum ayri hesaplanir; bir bolumun sorgusu hata verirse sayfa cokmez,
sadece o kart "yuklenemedi" gosterir. Grafik ve siralama verileri kisa sure
onbellekte tutulur; bekleyen is sayilari her istekte tazedir.
"""
import logging
from datetime import date, timedelta

from django.contrib.admin.models import ADDITION, DELETION, LogEntry
from django.core.cache import cache
from django.db.models import Count, Q
from django.db.models.functions import TruncDate, TruncMonth
from django.urls import reverse
from django.utils import timezone

from .models import Alinti, BlogKategori, BlogYazisi, IletisimBasvurusu, Kitap, YazarProfil

logger = logging.getLogger(__name__)

ONBELLEK_SURESI = 60  # saniye
AY_ADLARI = ["Oca", "Şub", "Mar", "Nis", "May", "Haz", "Tem", "Ağu", "Eyl", "Eki", "Kas", "Ara"]
YAYINDA = BlogYazisi.DurumSecenekleri.YAYINDA
INCELEMEDE = BlogYazisi.DurumSecenekleri.INCELEMEDE


def _guvenli(ad, hesapla):
    """Bolumu hesaplar; hata olursa kaydedip None doner (sablon hata durumunu gosterir)."""
    try:
        return hesapla()
    except Exception:
        logger.exception("Kontrol paneli bolumu hesaplanamadi: %s", ad)
        return None


def _onbellekli(anahtar, hesapla):
    deger = cache.get(anahtar)
    if deger is None:
        deger = hesapla()
        cache.set(anahtar, deger, ONBELLEK_SURESI)
    return deger


def degisim(simdi, onceki):
    """Onceki doneme gore degisim: {'yuzde': 12, 'yon': 'artis'|'azalis'|'sabit'|'yeni'}."""
    if onceki == 0:
        return {"yuzde": None, "yon": "yeni" if simdi else "sabit"}
    yuzde = round((simdi - onceki) * 100 / onceki)
    return {"yuzde": abs(yuzde), "yon": "artis" if yuzde > 0 else "azalis" if yuzde < 0 else "sabit"}


def ozet_kartlari():
    simdi = timezone.now()
    son_30, onceki_30 = simdi - timedelta(days=30), simdi - timedelta(days=60)

    yazi = BlogYazisi.objects.aggregate(
        toplam=Count("id"),
        yayinda=Count("id", filter=Q(durum=YAYINDA)),
        taslak=Count("id", filter=~Q(durum=YAYINDA)),
        incelemede=Count("id", filter=Q(durum=INCELEMEDE)),
        yeni=Count("id", filter=Q(created_at__gte=son_30)),
        onceki=Count("id", filter=Q(created_at__gte=onceki_30, created_at__lt=son_30)),
    )
    yazar = YazarProfil.objects.aggregate(
        toplam=Count("id"),
        yeni=Count("id", filter=Q(created_at__gte=son_30)),
        onay_bekleyen=Count("id", filter=Q(onayli=False)),
    )
    kitap = Kitap.objects.aggregate(
        yeni=Count("id", filter=Q(created_at__gte=son_30)),
        onceki=Count("id", filter=Q(created_at__gte=onceki_30, created_at__lt=son_30)),
    )
    alinti = Alinti.objects.aggregate(
        incelemede=Count("id", filter=Q(durum=INCELEMEDE)),
        yeni=Count("id", filter=Q(created_at__gte=son_30)),
        onceki=Count("id", filter=Q(created_at__gte=onceki_30, created_at__lt=son_30)),
    )
    okunmamis_mesaj = IletisimBasvurusu.objects.filter(incelendi=False).count()

    yeni_icerik = yazi["yeni"] + kitap["yeni"] + alinti["yeni"]
    onceki_icerik = yazi["onceki"] + kitap["onceki"] + alinti["onceki"]
    return {
        "yazi": yazi,
        "yazar": yazar,
        "alinti": alinti,
        "bekleyen_toplam": yazi["incelemede"] + alinti["incelemede"] + okunmamis_mesaj + yazar["onay_bekleyen"],
        "okunmamis_mesaj": okunmamis_mesaj,
        "yeni_icerik": yeni_icerik,
        "yeni_icerik_dagilim": {"yazi": yazi["yeni"], "kitap": kitap["yeni"], "alinti": alinti["yeni"]},
        "yeni_icerik_degisim": degisim(yeni_icerik, onceki_icerik),
        "yazi_degisim": degisim(yazi["yeni"], yazi["onceki"]),
    }


def bekleyen_isler(ozet):
    yazilar = list(
        BlogYazisi.objects.select_related("yazar").filter(durum=INCELEMEDE).order_by("-created_at")[:5]
    )
    mesajlar = list(IletisimBasvurusu.objects.filter(incelendi=False).order_by("-created_at")[:5])
    yazilar_url = reverse("superadmin_yazilar")
    iletisim_url = reverse("superadmin_iletisim")
    return {
        "gruplar": [
            {"ad": "Onay bekleyen yazılar", "ikon": "ph-article", "sayi": ozet["yazi"]["incelemede"],
             "url": f"{yazilar_url}?durum={INCELEMEDE}"},
            {"ad": "Onay bekleyen alıntılar", "ikon": "ph-quotes", "sayi": ozet["alinti"]["incelemede"],
             "url": f"{reverse('superadmin_alintilar')}?durum={INCELEMEDE}"},
            {"ad": "Okunmamış mesajlar", "ikon": "ph-envelope-simple", "sayi": ozet["okunmamis_mesaj"],
             "url": f"{iletisim_url}?durum=okunmamis"},
            {"ad": "Onay bekleyen yazarlar", "ikon": "ph-pen-nib", "sayi": ozet["yazar"]["onay_bekleyen"],
             "url": reverse("superadmin_yazarlar")},
        ],
        "yazilar": [
            {"baslik": y.baslik, "alt": y.yazar.ad_soyad, "zaman": y.created_at,
             "url": reverse("superadmin_yazi_detay", args=[y.pk])}
            for y in yazilar
        ],
        "mesajlar": [
            {"baslik": f"{m.ad} {m.soyad}", "alt": m.get_amac_display(), "zaman": m.created_at,
             "url": reverse("superadmin_iletisim_detay", args=[m.pk])}
            for m in mesajlar
        ],
    }


def _ay_listesi(bugun, adet=12):
    aylar = []
    yil, ay = bugun.year, bugun.month
    for _ in range(adet):
        aylar.append(date(yil, ay, 1))
        ay -= 1
        if ay == 0:
            yil, ay = yil - 1, 12
    return list(reversed(aylar))


def _gunluk_ve_aylik(queryset, alan):
    """Bir icerik turunun son 30 gun (gunluk) ve son 12 ay (aylik) sayilari."""
    yerel = timezone.localtime()
    bugun = yerel.date()
    gun_baslangic = bugun - timedelta(days=29)
    ay_baslangic = _ay_listesi(bugun)[0]

    gunluk = dict(
        queryset.filter(**{f"{alan}__date__gte": gun_baslangic})
        .annotate(gun=TruncDate(alan))
        .values_list("gun")
        .annotate(n=Count("id"))
    )
    aylik = {
        (a.date() if hasattr(a, "date") else a): n
        for a, n in queryset.filter(**{f"{alan}__date__gte": ay_baslangic})
        .annotate(ay=TruncMonth(alan))
        .values_list("ay")
        .annotate(n=Count("id"))
    }
    return gunluk, aylik


def yayin_grafigi():
    bugun = timezone.localtime().date()
    gunler = [bugun - timedelta(days=i) for i in range(29, -1, -1)]
    aylar = _ay_listesi(bugun)
    seriler = [
        ("Blog yazısı", BlogYazisi.objects.filter(durum=YAYINDA), "yayin_tarihi"),
        ("Kitap", Kitap.objects.all(), "created_at"),
        ("Alıntı", Alinti.objects.all(), "created_at"),
    ]
    sonuc = {
        "gun": {"etiketler": [f"{g.day} {AY_ADLARI[g.month - 1]}" for g in gunler], "seriler": []},
        "ay": {"etiketler": [f"{AY_ADLARI[a.month - 1]} {str(a.year)[2:]}" for a in aylar], "seriler": []},
    }
    for ad, queryset, alan in seriler:
        gunluk, aylik = _gunluk_ve_aylik(queryset, alan)
        sonuc["gun"]["seriler"].append({"ad": ad, "veri": [gunluk.get(g, 0) for g in gunler]})
        sonuc["ay"]["seriler"].append({"ad": ad, "veri": [aylik.get(a, 0) for a in aylar]})
    for donem in sonuc.values():
        donem["toplam"] = sum(sum(s["veri"]) for s in donem["seriler"])
        # Grafik yuklenemezse gosterilen tablo icin satirlar
        donem["satirlar"] = [
            {"etiket": etiket, "degerler": [s["veri"][i] for s in donem["seriler"]]}
            for i, etiket in enumerate(donem["etiketler"])
        ]
    return sonuc


def kategori_dagilimi(ilk=7):
    satirlar = list(
        BlogKategori.objects.annotate(
            n=Count("blog_yazilari_coklu", filter=Q(blog_yazilari_coklu__durum=YAYINDA), distinct=True)
        )
        .filter(n__gt=0)
        .order_by("-n", "ad")
        .values_list("ad", "n")
    )
    if len(satirlar) > ilk:
        diger = sum(n for _, n in satirlar[ilk:])
        satirlar = satirlar[:ilk] + [("Diğer", diger)]
    en_buyuk = max((n for _, n in satirlar), default=0)
    return [{"ad": ad, "n": n, "oran": round(n * 100 / en_buyuk) if en_buyuk else 0} for ad, n in satirlar]


def en_cok_okunanlar(adet=5):
    return [
        {"baslik": y.baslik, "yazar": y.yazar.ad_soyad, "okunma": y.okunma_sayisi,
         "url": reverse("superadmin_yazi_detay", args=[y.pk])}
        for y in BlogYazisi.objects.select_related("yazar").filter(durum=YAYINDA, okunma_sayisi__gt=0).order_by("-okunma_sayisi")[:adet]
    ]


def uretken_yazarlar(adet=5):
    return list(
        YazarProfil.objects.annotate(n=Count("blog_yazilari", filter=Q(blog_yazilari__durum=YAYINDA)))
        .filter(n__gt=0)
        .order_by("-n", "ad_soyad")
        .values("pk", "ad_soyad", "n")[:adet]
    )


EYLEM_METNI = {ADDITION: "eklendi", 2: "güncellendi", DELETION: "silindi"}
TUR_IKONU = {
    "blogyazisi": "ph-article", "kitap": "ph-books", "alinti": "ph-quotes", "yazarprofil": "ph-pen-nib",
    "user": "ph-user", "iletisimbasvurusu": "ph-envelope-simple", "kitapmaliyetiayarlari": "ph-calculator",
}


def son_aktiviteler(adet=8):
    """Panel kayitlari (LogEntry: kim yapti) + icerik zaman damgalari (yazar panelinden gelenler dahil)."""
    olaylar = []
    for e in LogEntry.objects.select_related("user", "content_type").order_by("-action_time")[:adet]:
        model = e.content_type.model if e.content_type else ""
        tur = e.content_type.name if e.content_type else "Kayıt"
        olaylar.append({
            "zaman": e.action_time,
            "ikon": TUR_IKONU.get(model, "ph-note-pencil"),
            "metin": f"“{e.object_repr}” {EYLEM_METNI.get(e.action_flag, 'değişti')}",
            "detay": e.change_message if e.change_message and not e.change_message.startswith("[") else tur,
            "kisi": (e.user.get_full_name() or e.user.username) if e.user else "",
            "anahtar": (model, e.object_id),
        })
    for y in BlogYazisi.objects.select_related("yazar").order_by("-created_at")[:adet]:
        olaylar.append({"zaman": y.created_at, "ikon": "ph-article", "metin": f"“{y.baslik}” eklendi",
                        "detay": "Blog yazısı", "kisi": y.yazar.ad_soyad, "anahtar": ("blogyazisi", str(y.pk))})
    for k in Kitap.objects.order_by("-created_at")[:adet]:
        olaylar.append({"zaman": k.created_at, "ikon": "ph-books", "metin": f"“{k.ad}” eklendi",
                        "detay": "Kitap", "kisi": "", "anahtar": ("kitap", str(k.pk))})
    for p in YazarProfil.objects.order_by("-created_at")[:adet]:
        olaylar.append({"zaman": p.created_at, "ikon": "ph-pen-nib", "metin": f"{p.ad_soyad} yazar olarak katıldı",
                        "detay": "Yazar profili", "kisi": "", "anahtar": ("yazarprofil", str(p.pk))})

    # Ayni kaydin eklenmesi hem LogEntry'de hem zaman damgasinda varsa tek gosterilir
    gorulen, sonuc = set(), []
    for o in sorted((o for o in olaylar if o["zaman"]), key=lambda o: o["zaman"], reverse=True):
        anahtar = (o["anahtar"], o["metin"].rsplit(" ", 1)[-1])
        if anahtar in gorulen:
            continue
        gorulen.add(anahtar)
        sonuc.append(o)
        if len(sonuc) == adet:
            break
    return sonuc


def dashboard_verisi():
    ozet = _guvenli("ozet", ozet_kartlari)
    return {
        "ozet": ozet,
        "bekleyen": _guvenli("bekleyen", lambda: bekleyen_isler(ozet)) if ozet else None,
        "grafik": _guvenli("grafik", lambda: _onbellekli("dashboard:yayin_grafigi", yayin_grafigi)),
        "kategoriler": _guvenli("kategoriler", lambda: _onbellekli("dashboard:kategoriler", kategori_dagilimi)),
        "okunanlar": _guvenli("okunanlar", lambda: _onbellekli("dashboard:okunanlar", en_cok_okunanlar)),
        "yazarlar": _guvenli("yazarlar", lambda: _onbellekli("dashboard:yazarlar", uretken_yazarlar)),
        "aktiviteler": _guvenli("aktiviteler", son_aktiviteler),
    }
