from django.contrib import admin
from django.contrib import messages
from django.contrib.admin.models import ADDITION, CHANGE, DELETION, LogEntry
from django.contrib.auth.models import Group, User
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.tokens import default_token_generator
from django.conf import settings
from django.core.mail import EmailMessage
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Count, F, Prefetch, Q, Sum
from django.db.models.deletion import ProtectedError
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST
from django.urls import NoReverseMatch, reverse, reverse_lazy
from django.utils import timezone
from django.utils.encoding import force_bytes
from django.utils.html import strip_tags
from django.utils.http import url_has_allowed_host_and_scheme, urlsafe_base64_decode, urlsafe_base64_encode
from functools import wraps
import mimetypes
import uuid
import os
import math
from urllib.parse import urlencode

from .dashboard import dashboard_verisi
from .giris_korumasi import giris_kilitli_mi
from .forms import (
    yazarin_gorebildigi_kitaplar,
    ContactForm,
    PanelAlintiForm,
    PanelBlogYazisiForm,
    PanelPasswordForm,
    PanelProfileForm,
    PanelUserForm,
    SifremiUnuttumForm,
    SifreSifirlaForm,
    SuperadminAlintiForm,
    SuperadminKaynakKitapForm,
    SuperadminKaynakYazarForm,
    SuperadminAlintiKategoriForm,
    SuperadminAnaSayfaYayinKartiForm,
    SuperadminBlogKategoriForm,
    SuperadminBlogReklamForm,
    SuperadminBlogUrunForm,
    SuperadminKitapForm,
    SuperadminKitapMaliyetiForm,
    SuperadminKitapMaliyetTuruForm,
    SuperadminKitapTurForm,
    SuperadminKullaniciForm,
    SuperadminKullaniciSifreForm,
    SuperadminSliderForm,
    SuperadminSSSForm,
    SuperadminYazarProfilForm,
)
from .models import (
    ALINTI_SINIRI,
    Alinti,
    AlintiKategori,
    AnaSayfaYayinKarti,
    BlogKategori,
    BlogReklam,
    BlogUrun,
    BlogYazisi,
    Etiket,
    IletisimBasvurusu,
    KaynakKitap,
    KaynakYazar,
    Kitap,
    KitapMaliyetiAyarlari,
    KitapMaliyetiHesaplamaKaydi,
    KitapMaliyetTuru,
    KitapTur,
    Slider,
    SSS,
    YazarProfil,
    YaziMedyasi,
)
from . import medya as medya_kurallari
from .medya import MedyaHatasi


def seo_context(title, description, canonical=""):
    return {
        "page_title": title,
        "meta_description": description[:320],
        "canonical_url": canonical,
    }


def get_client_ip(request):
    forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR", "")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR", "").strip()


CONTENT_MODEL_CONFIG = {
    "anasayfayayinkarti": {
        "model": AnaSayfaYayinKarti,
        "form_class": SuperadminAnaSayfaYayinKartiForm,
        "title": "Ana Sayfa Yayın Kartları",
        "singular": "Ana sayfa yayın kartı",
        "list_headers": ["Başlık", "Aktif", "Sıra", "Bağlantı"],
        "list_values": lambda obj: [obj.baslik, "Evet" if obj.aktif else "Hayır", obj.sira, obj.link or "-"],
        "full_width_fields": {"baslik", "link", "mobil_gorsel", "masaustu_gorsel"},
        "search_fields": ["baslik"],
    },
    "alintikategori": {
        "model": AlintiKategori,
        "form_class": SuperadminAlintiKategoriForm,
        "title": "Alıntı Kategorileri",
        "singular": "Alıntı kategorisi",
        "list_headers": ["Ad", "Kısa ad"],
        "list_values": lambda obj: [obj.ad, obj.slug or "-"],
        "full_width_fields": {"ad", "slug"},
        "search_fields": ["ad", "slug"],
    },
    "sss": {
        "model": SSS,
        "form_class": SuperadminSSSForm,
        "title": "Sık Sorulan Sorular",
        "singular": "SSS",
        "list_headers": ["Soru", "Sıra", "Aktif"],
        "list_values": lambda obj: [obj.soru, obj.sira, "Evet" if obj.aktif else "Hayır"],
        "full_width_fields": {"soru", "cevap"},
        "search_fields": ["soru", "cevap"],
    },
    "alinti": {
        "model": Alinti,
        "form_class": SuperadminAlintiForm,
        "title": "Alıntılar",
        "singular": "Alıntı",
        "list_headers": ["Alıntı", "Kitap", "Durum", "Paylaşan"],
        "list_values": lambda obj: [
            obj.metin[:60] + ("…" if len(obj.metin) > 60 else ""),
            str(obj.kaynak) if obj.kaynak_id else "-",
            obj.get_durum_display(),
            obj.paylasan.get_username() if obj.paylasan_id else "-",
        ],
        "full_width_fields": {"metin", "yorum", "admin_notu", "etiketler_input"},
        "search_fields": ["metin", "kaynak__ad", "kaynak__yazar__ad"],
        "select_related": ["kaynak__yazar", "paylasan"],
    },
    "kaynakkitap": {
        "model": KaynakKitap,
        "form_class": SuperadminKaynakKitapForm,
        "title": "Kaynak kitaplar",
        "singular": "Kaynak kitap",
        "list_headers": ["Kitap", "Yazar", "Yıl", "Onaylı"],
        "list_values": lambda obj: [obj.ad, obj.yazar.ad, obj.basim_yili or "-", "Evet" if obj.onayli else "Hayır"],
        "full_width_fields": {"ad", "kapak"},
        "search_fields": ["ad", "yazar__ad", "isbn"],
        "select_related": ["yazar"],
    },
    "kaynakyazar": {
        "model": KaynakYazar,
        "form_class": SuperadminKaynakYazarForm,
        "title": "Kaynak yazarlar",
        "singular": "Kaynak yazar",
        "list_headers": ["Yazar", "Sitedeki profil"],
        "list_values": lambda obj: [obj.ad, obj.yazar_profili.ad_soyad if obj.yazar_profili_id else "-"],
        "full_width_fields": {"ad"},
        "search_fields": ["ad"],
        "select_related": ["yazar_profili"],
    },
    "blogkategori": {
        "model": BlogKategori,
        "form_class": SuperadminBlogKategoriForm,
        "title": "Blog Kategorileri",
        "singular": "Blog kategorisi",
        "list_headers": ["Ad", "Kısa ad"],
        "list_values": lambda obj: [obj.ad, obj.slug or "-"],
        "full_width_fields": {"ad", "slug"},
        "search_fields": ["ad", "slug"],
    },
    "blogreklam": {
        "model": BlogReklam,
        "form_class": SuperadminBlogReklamForm,
        "title": "Blog Reklamları",
        "singular": "Blog reklamı",
        "list_headers": ["İsim", "Sponsor Etiketi", "Aktif", "Sıra"],
        "list_values": lambda obj: [obj.isim, obj.sponsor_etiketi, "Evet" if obj.aktif else "Hayır", obj.sira],
        "full_width_fields": {"isim", "sponsor_etiketi", "link", "resim"},
        "search_fields": ["isim", "sponsor_etiketi"],
    },
    "blogurun": {
        "model": BlogUrun,
        "form_class": SuperadminBlogUrunForm,
        "title": "Blog Ürünleri",
        "singular": "Blog ürünü",
        "list_headers": ["İsim", "Fiyat", "İndirimli", "Aktif", "Sıra"],
        "list_values": lambda obj: [
            obj.isim,
            f"{obj.fiyat} TL",
            f"{obj.indirimli_fiyat} TL" if obj.indirimli_fiyat else "-",
            "Evet" if obj.aktif else "Hayır",
            obj.sira,
        ],
        "full_width_fields": {"isim", "satis_linki", "resim"},
        "search_fields": ["isim"],
    },
    "blogyazisi": {
        "model": BlogYazisi,
        "form_class": PanelBlogYazisiForm,
        "title": "Blog Yazıları",
        "singular": "Blog yazısı",
        "list_headers": ["Başlık", "Yazar", "Durum", "Yayın Tarihi"],
        "list_values": lambda obj: [obj.baslik, obj.yazar.ad_soyad, obj.get_durum_display(), obj.yayin_tarihi.strftime("%d.%m.%Y") if obj.yayin_tarihi else "-"],
        "full_width_fields": {"baslik", "ozet", "icerik", "gorsel", "meta_title", "meta_description", "seo_keywords"},
        "form_kwargs": lambda request: {"is_superadmin": True},
        "search_fields": ["baslik", "yazar__ad_soyad"],
        "select_related": ["yazar"],
    },
    "kitaptur": {
        "model": KitapTur,
        "form_class": SuperadminKitapTurForm,
        "title": "Kitap Kategorileri",
        "singular": "Kitap kategorisi",
        "list_headers": ["Ad", "Kısa ad"],
        "list_values": lambda obj: [obj.ad, obj.slug or "-"],
        "full_width_fields": {"ad", "slug", "aciklama"},
        "search_fields": ["ad", "slug"],
    },
    "kitapmaliyetturu": {
        "model": KitapMaliyetTuru,
        "form_class": SuperadminKitapMaliyetTuruForm,
        "title": "Kitap Maliyeti Türleri",
        "singular": "Kitap maliyeti türü",
        "list_headers": ["Tür", "Hesaplama", "Sayfa Başı Kelime", "Sıra"],
        "list_values": lambda obj: [
            obj.ad,
            obj.get_hesaplama_yontemi_display(),
            "-" if obj.sayfa_bazli else obj.kelime_yogunlugu,
            obj.sira,
        ],
        "full_width_fields": set(),
        "search_fields": ["ad"],
    },
    "kitap": {
        "model": Kitap,
        "form_class": SuperadminKitapForm,
        "title": "Kitaplar",
        "singular": "Kitap",
        "list_headers": ["Ad", "Yazar", "Yayın Tarihi", "Yayında"],
        "list_values": lambda obj: [obj.ad, obj.yazar_adi, obj.yayin_tarihi.strftime("%d.%m.%Y") if obj.yayin_tarihi else "-", "Evet" if obj.yayinda else "Hayır"],
        "full_width_fields": {"ad", "slug", "aciklama", "kapak_resmi", "meta_title", "meta_description", "kitapyurdu_link", "dr_link", "trendyol_link", "shopier_link", "etiketler_input"},
        "search_fields": ["ad", "yazar__ad_soyad", "ikinci_yazar__ad_soyad"],
        "select_related": ["yazar", "ikinci_yazar"],
    },
    "slider": {
        "model": Slider,
        "form_class": SuperadminSliderForm,
        "title": "Sliderlar",
        "singular": "Slider",
        "list_headers": ["Başlık", "Sıra", "Aktif", "Link"],
        "list_values": lambda obj: [obj.baslik, obj.sira, "Evet" if obj.aktif else "Hayır", obj.link or "-"],
        "full_width_fields": {"baslik", "aciklama", "gorsel", "link"},
        "search_fields": ["baslik"],
    },
    "yazarprofil": {
        "model": YazarProfil,
        "form_class": SuperadminYazarProfilForm,
        "title": "Yazar Profilleri",
        "singular": "Yazar profili",
        "list_headers": ["Ad Soyad", "Rol", "Onaylı", "Kullanıcı"],
        "list_values": lambda obj: [obj.ad_soyad, obj.get_rol_display(), "Evet" if obj.onayli else "Hayır", obj.user.username if obj.user else "-"],
        "full_width_fields": {"ad_soyad", "slug", "biyografi", "fotograf", "instagram", "x_hesabi", "websitesi"},
        "search_fields": ["ad_soyad", "user__username"],
        "select_related": ["user"],
    },
}


def islem_kaydet(request, nesne, eylem, mesaj=""):
    """Panel islemini Django'nun LogEntry tablosuna yazar (kontrol panelindeki "Son aktiviteler" icin)."""
    LogEntry.objects.log_actions(
        user_id=request.user.pk,
        queryset=[nesne],
        action_flag=eylem,
        change_message=mesaj,
        single_object=True,
    )


def degisen_alanlar_mesaji(form):
    etiketler = [str(form.fields[ad].label) for ad in form.changed_data if ad in form.fields]
    return f"Değişen alanlar: {', '.join(etiketler)}" if etiketler else "Değişiklik yok"


def get_content_model_config(model_key):
    return CONTENT_MODEL_CONFIG.get(model_key)


def yazar_kisa_ad(ad_soyad):
    parcalar = [parca for parca in (ad_soyad or "").split() if parca]
    if not parcalar:
        return "T"
    if len(parcalar) == 1:
        return parcalar[0][:1].upper()
    return f"{parcalar[0][:1]}{parcalar[1][:1]}".upper()


def get_or_create_user_profile(user):
    profil, _ = YazarProfil.objects.get_or_create(
        user=user,
        defaults={
            "ad_soyad": user.get_full_name() or user.username,
        },
    )
    return profil


def panel_yoneticisi_mi(user, profil):
    """Yonetici yetkisi: superadmin_required ile ayni kural (rol veya is_superuser)."""
    return user.is_superuser or profil.rol == YazarProfil.RolSecenekleri.SUPERADMIN


def panel_baglami(request, profil, menu, **ekler):
    """Yazar paneli sablonlarinin (templates/panel/base.html) ortak baglami."""
    return {
        "profil": profil,
        "panel_menu": menu,
        "panel_ad": request.user.first_name.strip() or profil.ad_soyad,
        "panel_yonetici": panel_yoneticisi_mi(request.user, profil),
        **ekler,
    }


def superadmin_required(view_func):
    @wraps(view_func)
    @login_required(login_url=reverse_lazy("admin:login"))
    def _wrapped(request, *args, **kwargs):
        profil = get_or_create_user_profile(request.user)
        if not panel_yoneticisi_mi(request.user, profil):
            messages.error(request, "Bu sayfaya yalnızca yöneticiler erişebilir.")
            return redirect("yazar_paneli")

        request.superadmin_profil = profil
        return view_func(request, *args, **kwargs)

    return _wrapped


# Kenar menude hangi ogenin aktif gorunecegi: url adi -> menu anahtari
MENU_URL_ESLESMESI = {
    "superadmin_dashboard": "panel",
    "superadmin_ara": "panel",
    "superadmin_yazilar": "yazilar",
    "superadmin_yazi_detay": "yazilar",
    "superadmin_icerik_yonetimi": "icerik",
    "superadmin_kitaplar": "kitaplar",
    "superadmin_kitap_maliyeti_ayarlari": "maliyet",
    "superadmin_kitap_maliyeti_istatistik_sifirla": "maliyet",
    "superadmin_yazarlar": "yazarlar",
    "superadmin_kullanicilar": "kullanicilar",
    "superadmin_kullanici_yeni": "kullanicilar",
    "superadmin_kullanici_duzenle": "kullanicilar",
    "superadmin_kullanici_sifre": "kullanicilar",
    "superadmin_iletisim": "mesajlar",
    "superadmin_iletisim_detay": "mesajlar",
    "superadmin_iletisim_sil": "mesajlar",
}
# Icerik yonetimi altindaki bazi modellerin kendi menu ogesi var
MENU_MODEL_ESLESMESI = {"blogyazisi": "yazilar", "kitap": "kitaplar", "kitapmaliyetturu": "maliyet", "yazarprofil": "yazarlar"}


def aktif_menu(request):
    eslesme = request.resolver_match
    if not eslesme:
        return ""
    model_key = eslesme.kwargs.get("model_key")
    if model_key:
        return MENU_MODEL_ESLESMESI.get(model_key, "icerik")
    return MENU_URL_ESLESMESI.get(eslesme.url_name, "")


def build_superadmin_context(request):
    """Tum admin sayfalarinda gereken baglam: menu durumu ve menu rozetleri."""
    pending_post_count = BlogYazisi.objects.filter(durum=BlogYazisi.DurumSecenekleri.INCELEMEDE).count()
    unread_contact_count = IletisimBasvurusu.objects.filter(incelendi=False).count()
    return {
        "profil": request.superadmin_profil,
        "aktif_menu": aktif_menu(request),
        "admin_pending_post_count": pending_post_count,
        "admin_unread_contact_count": unread_contact_count,
        "admin_notification_count": pending_post_count + unread_contact_count,
    }


def django_admin_modulleri():
    """Icerik Yonetimi sayfasindaki "Sistem (Django Admin)" kartlari."""
    model_groups = [
        ("Kimlik Doğrulama ve Yetkilendirme", [("Gruplar", "auth", "group"), ("Kullanıcılar", "auth", "user")]),
        ("Yönetici Arayüzü", [("Temalar", "admin_interface", "theme")]),
    ]
    admin_modules = []
    for group_name, items in model_groups:
        models = []
        for label, app_label, model_name in items:
            if app_label == "auth" and model_name == "user":
                admin_url = reverse("superadmin_kullanicilar")
                add_url = reverse("superadmin_kullanici_yeni")
            else:
                try:
                    admin_url = reverse(f"admin:{app_label}_{model_name}_changelist")
                except NoReverseMatch:
                    admin_url = ""
                try:
                    add_url = reverse(f"admin:{app_label}_{model_name}_add")
                except NoReverseMatch:
                    add_url = ""
            models.append({"name": label, "model_name": model_name, "admin_url": admin_url, "add_url": add_url})
        admin_modules.append({"name": group_name, "models": models})
    return admin_modules


@superadmin_required
def superadmin_dashboard(request):
    context = build_superadmin_context(request)
    context.update({"page_title": "Kontrol Paneli", "panel": dashboard_verisi()})
    return render(request, "superadmin/dashboard.html", context)


ARAMA_SONUC_LIMITI = 6


@superadmin_required
def superadmin_ara(request):
    """Ust bardaki arama: yazi, kitap, yazar, alinti, kullanici ve mesajlarda arar."""
    arama = request.GET.get("q", "").strip()
    gruplar = []
    if len(arama) >= 2:
        tanimlar = [
            ("Yazılar", "ph-article", BlogYazisi.objects.select_related("yazar"), ["baslik", "yazar__ad_soyad"],
             lambda o: (o.baslik, o.yazar.ad_soyad, reverse("superadmin_yazi_detay", args=[o.pk])),
             reverse("superadmin_yazilar")),
            ("Kitaplar", "ph-books", Kitap.objects.select_related("yazar", "ikinci_yazar"), ["ad", "yazar__ad_soyad", "ikinci_yazar__ad_soyad"],
             lambda o: (o.ad, o.yazar_adi, reverse("superadmin_icerik_model_duzenle", args=["kitap", o.pk])),
             reverse("superadmin_kitaplar")),
            ("Yazarlar", "ph-pen-nib", YazarProfil.objects.select_related("user"), ["ad_soyad", "user__username"],
             lambda o: (o.ad_soyad, o.get_rol_display(), reverse("superadmin_icerik_model_duzenle", args=["yazarprofil", o.pk])),
             reverse("superadmin_yazarlar")),
            ("Alıntılar", "ph-quotes", Alinti.objects.select_related("kaynak__yazar"), ["metin", "kaynak__ad", "kaynak__yazar__ad"],
             lambda o: (o.metin[:90], str(o.kaynak) if o.kaynak_id else "Kaynaksız", reverse("superadmin_icerik_model_duzenle", args=["alinti", o.pk])),
             reverse("superadmin_icerik_model_liste", args=["alinti"])),
            ("Kullanıcılar", "ph-users", User.objects.all(), ["username", "first_name", "last_name", "email"],
             lambda o: (o.username, o.email or "-", reverse("superadmin_kullanici_duzenle", args=[o.pk])),
             reverse("superadmin_kullanicilar")),
            ("Mesajlar", "ph-envelope-simple", IletisimBasvurusu.objects.all(), ["ad", "soyad", "email", "mesaj"],
             lambda o: (f"{o.ad} {o.soyad}", o.get_amac_display(), reverse("superadmin_iletisim_detay", args=[o.pk])),
             reverse("superadmin_iletisim")),
        ]
        for baslik, ikon, queryset, alanlar, satir, liste_url in tanimlar:
            eslesenler = queryset.filter(arama_filtresi(alanlar, arama)).distinct().order_by("-pk")
            sonuclar = list(eslesenler[: ARAMA_SONUC_LIMITI + 1])
            if sonuclar:
                gruplar.append(
                    {
                        "baslik": baslik,
                        "ikon": ikon,
                        "satirlar": [satir(o) for o in sonuclar[:ARAMA_SONUC_LIMITI]],
                        "daha_fazla": len(sonuclar) > ARAMA_SONUC_LIMITI,
                        "liste_url": f"{liste_url}?{urlencode({'q': arama})}",
                    }
                )
    context = build_superadmin_context(request)
    context.update({"page_title": "Arama", "arama": arama, "ust_arama": arama, "gruplar": gruplar})
    return render(request, "superadmin/search.html", context)


@superadmin_required
def superadmin_yazilar(request):
    durum = request.GET.get("durum", "").strip()
    arama = request.GET.get("q", "").strip()
    yazilar = (
        BlogYazisi.objects.select_related("yazar", "kategori", "onaylayan")
        .prefetch_related("kategoriler")
        .order_by("-created_at")
    )
    if durum:
        yazilar = yazilar.filter(durum=durum)
    if arama:
        yazilar = yazilar.filter(arama_filtresi(["baslik", "yazar__ad_soyad"], arama))
    page_obj, sayfa_sorgusu = sayfala(request, yazilar)
    context = build_superadmin_context(request)
    context.update(
        {
            "page_title": "Yazılar",
            "yazilar": page_obj.object_list,
            "page_obj": page_obj,
            "sayfa_sorgusu": sayfa_sorgusu,
            "secili_durum": durum,
            "arama": arama,
            "durumler": BlogYazisi.DurumSecenekleri.choices,
        }
    )
    return render(request, "superadmin/posts.html", context)


@superadmin_required
def superadmin_yazi_detay(request, pk):
    yazi = get_object_or_404(
        BlogYazisi.objects.select_related("yazar", "kategori", "onaylayan").prefetch_related("kategoriler", "medyalar"),
        pk=pk,
    )
    context = build_superadmin_context(request)
    context.update(
        {
            "page_title": yazi.baslik,
            "yazi": yazi,
            "durumler": BlogYazisi.DurumSecenekleri.choices,
        }
    )
    return render(request, "superadmin/post_detail.html", context)


@superadmin_required
def superadmin_yazi_durum_guncelle(request, pk):
    yazi = get_object_or_404(BlogYazisi, pk=pk)
    if request.method == "POST":
        yeni_durum = request.POST.get("durum")
        not_degisti = False
        if "admin_notu" in request.POST:
            yeni_not = request.POST["admin_notu"].strip()[:2000]
            not_degisti = yeni_not != yazi.admin_notu
            yazi.admin_notu = yeni_not
        if yeni_durum in dict(BlogYazisi.DurumSecenekleri.choices):
            durum_degisti = yeni_durum != yazi.durum
            yazi.durum = yeni_durum
            if yeni_durum == BlogYazisi.DurumSecenekleri.YAYINDA:
                yazi.onaylayan = request.user
                if not yazi.yayin_tarihi:
                    yazi.yayin_tarihi = timezone.now()
            else:
                if yeni_durum == BlogYazisi.DurumSecenekleri.INCELEMEDE:
                    yazi.onaylayan = None
                else:
                    yazi.onaylayan = request.user
            yazi.save()
            if durum_degisti:
                islem_kaydet(request, yazi, CHANGE, f"Durum: {yazi.get_durum_display()}")
                messages.success(request, f'"{yazi.baslik}" için durum güncellendi.')
            elif not_degisti:
                islem_kaydet(request, yazi, CHANGE, "Yazara not güncellendi")
                messages.success(request, f'"{yazi.baslik}" için yazara not kaydedildi.')
        if request.POST.get("sonra") == "detay":
            return redirect("superadmin_yazi_detay", pk=yazi.pk)
    return redirect("superadmin_yazilar")


@superadmin_required
def superadmin_iletisim(request):
    durum = request.GET.get("durum", "").strip()
    arama = request.GET.get("q", "").strip()
    basvurular = IletisimBasvurusu.objects.order_by("-created_at")
    if durum == "okunmamis":
        basvurular = basvurular.filter(incelendi=False)
    elif durum == "okunmus":
        basvurular = basvurular.filter(incelendi=True)
    if arama:
        basvurular = basvurular.filter(arama_filtresi(["ad", "soyad", "email", "mesaj"], arama))
    page_obj, sayfa_sorgusu = sayfala(request, basvurular)
    context = build_superadmin_context(request)
    context.update(
        {
            "page_title": "İletişim Başvuruları",
            "basvurular": page_obj.object_list,
            "page_obj": page_obj,
            "sayfa_sorgusu": sayfa_sorgusu,
            "durum_secenekleri": [("okunmamis", "Okunmamış"), ("okunmus", "Okunmuş")],
            "secili_durum": durum,
            "arama": arama,
        }
    )
    return render(request, "superadmin/contacts.html", context)


@superadmin_required
def superadmin_iletisim_detay(request, pk):
    basvuru = get_object_or_404(IletisimBasvurusu, pk=pk)
    if not basvuru.incelendi:
        basvuru.incelendi = True
        basvuru.save(update_fields=["incelendi"])
    context = build_superadmin_context(request)
    context.update(
        {
            "page_title": "İletişim Başvurusu",
            "basvuru": basvuru,
        }
    )
    return render(request, "superadmin/contact_detail.html", context)


@superadmin_required
def superadmin_iletisim_sil(request, pk):
    basvuru = get_object_or_404(IletisimBasvurusu, pk=pk)
    if request.method == "POST":
        try:
            with transaction.atomic():
                islem_kaydet(request, basvuru, DELETION, "İletişim başvurusu silindi")
                basvuru.delete()
            messages.success(request, "İletişim başvurusu silindi.")
            return redirect("superadmin_iletisim")
        except Exception:
            messages.error(request, "Başvuru silinirken beklenmeyen bir hata oluştu.")
            return redirect("superadmin_iletisim_detay", pk=pk)

    context = build_superadmin_context(request)
    context.update(
        {
            "page_title": "İletişim Başvurusunu Sil",
            "onay_ust_etiket": "İletişim Başvurusu",
            "confirm_message": "Bu iletişim başvurusunu kalıcı olarak silmek üzeresin. Bu işlem geri alınamaz.",
            "onay_detaylari": [("Kişi", f"{basvuru.ad} {basvuru.soyad}"), ("E-posta", basvuru.email), ("Tarih", basvuru.created_at.strftime("%d.%m.%Y %H:%M"))],
            "onay_buton": "Kalıcı Olarak Sil",
            "cancel_url": reverse("superadmin_iletisim_detay", args=[basvuru.pk]),
            "geri_url": reverse("superadmin_iletisim"),
        }
    )
    return render(request, "superadmin/confirm.html", context)


@superadmin_required
def superadmin_iletisim_durum_guncelle(request, pk):
    basvuru = get_object_or_404(IletisimBasvurusu, pk=pk)
    if request.method == "POST":
        basvuru.incelendi = request.POST.get("incelendi") == "1"
        basvuru.save(update_fields=["incelendi"])
        islem_kaydet(request, basvuru, CHANGE, "Okundu olarak işaretlendi" if basvuru.incelendi else "Okunmadı olarak işaretlendi")
        messages.success(request, "Başvuru durumu güncellendi.")
    return redirect("superadmin_iletisim")


@superadmin_required
def superadmin_yazarlar(request):
    arama = request.GET.get("q", "").strip()
    yazarlar = YazarProfil.objects.select_related("user").order_by("ad_soyad")
    if arama:
        yazarlar = yazarlar.filter(arama_filtresi(["ad_soyad", "user__username"], arama))
    page_obj, sayfa_sorgusu = sayfala(request, yazarlar)
    context = build_superadmin_context(request)
    context.update(
        {
            "page_title": "Yazarlar",
            "yazarlar": page_obj.object_list,
            "page_obj": page_obj,
            "sayfa_sorgusu": sayfa_sorgusu,
            "arama": arama,
        }
    )
    return render(request, "superadmin/authors.html", context)


@superadmin_required
def superadmin_kitaplar(request):
    arama = request.GET.get("q", "").strip()
    kitaplar = Kitap.objects.select_related("yazar", "ikinci_yazar").order_by("-created_at")
    if arama:
        kitaplar = kitaplar.filter(arama_filtresi(["ad", "yazar__ad_soyad", "ikinci_yazar__ad_soyad"], arama))
    page_obj, sayfa_sorgusu = sayfala(request, kitaplar)
    context = build_superadmin_context(request)
    context.update(
        {
            "page_title": "Kitaplar",
            "kitaplar": page_obj.object_list,
            "page_obj": page_obj,
            "sayfa_sorgusu": sayfa_sorgusu,
            "arama": arama,
        }
    )
    return render(request, "superadmin/books.html", context)


@superadmin_required
def superadmin_kitap_maliyeti_ayarlari(request):
    ayarlar = KitapMaliyetiAyarlari.get_ayarlar()
    if request.method == "POST":
        form = SuperadminKitapMaliyetiForm(request.POST, instance=ayarlar)
        if form.is_valid():
            form.save()
            islem_kaydet(request, ayarlar, CHANGE, degisen_alanlar_mesaji(form))
            messages.success(request, "Kitap maliyeti hesaplama ayarları güncellendi.")
            return redirect("superadmin_kitap_maliyeti_ayarlari")
    else:
        form = SuperadminKitapMaliyetiForm(instance=ayarlar)

    ornek_kelime_sayisi = 60000
    ornek_sayfa_sayisi = 100
    turler = []
    for tur in KitapMaliyetTuru.objects.all():
        if tur.sayfa_bazli or not tur.kelime_yogunlugu:
            tahmini_sayfa = ornek_sayfa_sayisi
        else:
            tahmini_sayfa = math.ceil(ornek_kelime_sayisi / tur.kelime_yogunlugu)
        tur_maliyet = (tahmini_sayfa * ayarlar.sayfa_basi_ucret) + ayarlar.sabit_ucret
        turler.append(
            {
                "ad": tur.ad,
                "sayfa_bazli": tur.sayfa_bazli,
                "kelime_yogunlugu": tur.kelime_yogunlugu,
                "tahmini_sayfa": tahmini_sayfa,
                "maliyet_formatli": f"{tur_maliyet:,}".replace(",", "."),
            }
        )

    hesaplama_sayisi = KitapMaliyetiHesaplamaKaydi.objects.count()
    hesaplama_tur_dagilimi = (
        KitapMaliyetiHesaplamaKaydi.objects.values("tur__ad")
        .annotate(adet=Count("id"))
        .order_by("-adet")
    )

    context = build_superadmin_context(request)
    context.update(
        {
            "page_title": "Kitap Maliyeti Hesaplama Ayarları",
            "object": ayarlar,
            "form": form,
            "form_title": "Kitap Maliyeti Hesaplama Ayarları",
            "submit_label": "Değişiklikleri Kaydet",
            "ornek_kelime_sayisi": ornek_kelime_sayisi,
            "ornek_sayfa_sayisi": ornek_sayfa_sayisi,
            "turler": turler,
            "hesaplama_sayisi": hesaplama_sayisi,
            "hesaplama_tur_dagilimi": hesaplama_tur_dagilimi,
        }
    )
    return render(request, "superadmin/kitap_maliyeti_ayarlari.html", context)


@superadmin_required
def superadmin_kitap_maliyeti_istatistik_sifirla(request):
    if request.method == "POST":
        KitapMaliyetiHesaplamaKaydi.objects.all().delete()
        islem_kaydet(request, KitapMaliyetiAyarlari.get_ayarlar(), CHANGE, "Kullanım istatistiği sıfırlandı")
        messages.success(request, "Kullanım istatistiği sıfırlandı.")
        return redirect("superadmin_kitap_maliyeti_ayarlari")

    context = build_superadmin_context(request)
    context.update(
        {
            "page_title": "Kullanım İstatistiğini Sıfırla",
            "onay_ust_etiket": "Kitap Maliyeti Ayarları",
            "confirm_message": (
                "Kitap maliyeti hesaplama aracının toplam kullanım sayısını ve tür dağılımını "
                "kalıcı olarak sıfırlamak üzeresin. Bu işlem geri alınamaz."
            ),
            "onay_detaylari": [("Kayıtlı hesaplama", KitapMaliyetiHesaplamaKaydi.objects.count())],
            "onay_buton": "Evet, Sıfırla",
            "cancel_url": reverse("superadmin_kitap_maliyeti_ayarlari"),
        }
    )
    return render(request, "superadmin/confirm.html", context)


@superadmin_required
def superadmin_icerik_yonetimi(request):
    context = build_superadmin_context(request)
    context.update({"page_title": "İçerik Yönetimi", "app_list": django_admin_modulleri()})
    return render(request, "superadmin/content_management.html", context)


def build_content_form_kwargs(request, config):
    extra = config.get("form_kwargs")
    return extra(request) if callable(extra) else {}


ADMIN_SAYFA_BOYUTU = 25


def sayfala(request, queryset, adet=ADMIN_SAYFA_BOYUTU):
    """Admin listeleri icin sayfa nesnesi ve sayfa linklerinde korunacak sorgu parametreleri."""
    page_obj = Paginator(queryset, adet).get_page(request.GET.get("page"))
    sorgu = request.GET.copy()
    sorgu.pop("page", None)
    return page_obj, sorgu.urlencode()


def turkce_harf_varyantlari(metin):
    """SQLite icontains Turkce harflerde (ş/Ş, ı/I, i/İ) buyuk-kucuk harf ayirt eder; olasi yazimlari uretir."""
    kucuk = metin.replace("I", "ı").replace("İ", "i").lower()
    buyuk = metin.replace("i", "İ").replace("ı", "I").upper()
    bas_buyuk = buyuk[:1] + kucuk[1:]
    return {metin, kucuk, buyuk, bas_buyuk}


def arama_filtresi(alanlar, arama):
    filtre = Q()
    for varyant in turkce_harf_varyantlari(arama):
        for alan in alanlar:
            filtre |= Q(**{f"{alan}__icontains": varyant})
    return filtre


def build_content_rows(objects, config):
    rows = []
    for obj in objects:
        rows.append(
            {
                "pk": obj.pk,
                "title": str(obj),
                "values": config["list_values"](obj),
                "edit_url": reverse("superadmin_icerik_model_duzenle", args=[config["model"]._meta.model_name, obj.pk]),
                "delete_url": reverse("superadmin_icerik_model_sil", args=[config["model"]._meta.model_name, obj.pk]),
            }
        )
    return rows


@superadmin_required
def superadmin_icerik_model_liste(request, model_key):
    config = get_content_model_config(model_key)
    if not config:
        messages.error(request, "Bu içerik türü için özel panel görünümü bulunamadı.")
        return redirect("superadmin_icerik_yonetimi")

    arama = request.GET.get("q", "").strip()
    queryset = config["model"].objects.select_related(*config.get("select_related", [])).order_by("-pk")
    if arama:
        queryset = queryset.filter(arama_filtresi(config["search_fields"], arama)).distinct()
    page_obj, sayfa_sorgusu = sayfala(request, queryset)
    context = build_superadmin_context(request)
    context.update(
        {
            "page_title": config["title"],
            "content_config": config,
            "content_headers": config["list_headers"],
            "content_rows": build_content_rows(page_obj.object_list, config),
            "page_obj": page_obj,
            "sayfa_sorgusu": sayfa_sorgusu,
            "arama": arama,
            "add_url": reverse("superadmin_icerik_model_yeni", args=[model_key]),
        }
    )
    return render(request, "superadmin/content_model_list.html", context)


@superadmin_required
def superadmin_icerik_model_yeni(request, model_key):
    config = get_content_model_config(model_key)
    if not config:
        messages.error(request, "Bu içerik türü için özel panel görünümü bulunamadı.")
        return redirect("superadmin_icerik_yonetimi")

    form_class = config["form_class"]
    form_kwargs = build_content_form_kwargs(request, config)
    if request.method == "POST":
        form = form_class(request.POST, request.FILES, **form_kwargs)
        if form.is_valid():
            nesne = form.save(commit=False)
            if model_key == "blogyazisi":
                nesne.yazar = request.superadmin_profil
                if nesne.durum == BlogYazisi.DurumSecenekleri.YAYINDA and not nesne.onaylayan:
                    nesne.onaylayan = request.user
            nesne.save()
            if hasattr(form, "save_m2m"):
                form.save_m2m()
            islem_kaydet(request, nesne, ADDITION, f"{config['singular']} eklendi")
            messages.success(request, f"{config['singular']} oluşturuldu.")
            return redirect("superadmin_icerik_model_duzenle", model_key=model_key, pk=nesne.pk)
    else:
        form = form_class(**form_kwargs)

    context = build_superadmin_context(request)
    context.update(
        {
            "page_title": f"{config['singular']} ekle",
            "content_config": config,
            "model_key": model_key,
            "form": form,
            "form_title": f"{config['singular']} ekle",
            "submit_label": "Kaydet",
            "back_url": reverse("superadmin_icerik_model_liste", args=[model_key]),
            "full_width_fields": config.get("full_width_fields", set()),
        }
    )
    return render(request, "superadmin/content_model_form.html", context)


@superadmin_required
def superadmin_icerik_model_duzenle(request, model_key, pk):
    config = get_content_model_config(model_key)
    if not config:
        messages.error(request, "Bu içerik türü için özel panel görünümü bulunamadı.")
        return redirect("superadmin_icerik_yonetimi")

    nesne = get_object_or_404(config["model"], pk=pk)
    form_class = config["form_class"]
    form_kwargs = build_content_form_kwargs(request, config)
    if request.method == "POST":
        form = form_class(request.POST, request.FILES, instance=nesne, **form_kwargs)
        if form.is_valid():
            nesne = form.save(commit=False)
            if model_key == "blogyazisi":
                if not nesne.yazar_id:
                    nesne.yazar = request.superadmin_profil
                if nesne.durum == BlogYazisi.DurumSecenekleri.YAYINDA and not nesne.onaylayan:
                    nesne.onaylayan = request.user
                elif nesne.durum != BlogYazisi.DurumSecenekleri.YAYINDA:
                    nesne.onaylayan = None
            nesne.save()
            if hasattr(form, "save_m2m"):
                form.save_m2m()
            islem_kaydet(request, nesne, CHANGE, degisen_alanlar_mesaji(form))
            messages.success(request, f"{config['singular']} güncellendi.")
            return redirect("superadmin_icerik_model_duzenle", model_key=model_key, pk=nesne.pk)
    else:
        form = form_class(instance=nesne, **form_kwargs)

    context = build_superadmin_context(request)
    context.update(
        {
            "page_title": f"{config['singular']} düzenle",
            "content_config": config,
            "model_key": model_key,
            "object": nesne,
            "form": form,
            "form_title": f"{config['singular']} düzenle",
            "submit_label": "Değişiklikleri Kaydet",
            "back_url": reverse("superadmin_icerik_model_liste", args=[model_key]),
            "full_width_fields": config.get("full_width_fields", set()),
        }
    )
    return render(request, "superadmin/content_model_form.html", context)


@superadmin_required
def superadmin_icerik_model_sil(request, model_key, pk):
    config = get_content_model_config(model_key)
    if not config:
        messages.error(request, "Bu içerik türü için özel panel görünümü bulunamadı.")
        return redirect("superadmin_icerik_yonetimi")

    nesne = get_object_or_404(config["model"], pk=pk)
    back_url = reverse("superadmin_icerik_model_liste", args=[model_key])

    if request.method == "POST":
        nesne_etiketi = str(nesne)
        try:
            with transaction.atomic():
                islem_kaydet(request, nesne, DELETION, f"{config['singular']} silindi")
                nesne.delete()
            messages.success(request, f"{config['singular']} silindi: {nesne_etiketi}")
            return redirect(back_url)
        except ProtectedError:
            messages.error(request, "Bu kayıt başka içeriklerle bağlantılı olduğu için silinemiyor.")
        except Exception:
            messages.error(request, "Kayıt silinirken beklenmeyen bir hata oluştu.")
        return redirect("superadmin_icerik_model_duzenle", model_key=model_key, pk=pk)

    context = build_superadmin_context(request)
    context.update(
        {
            "page_title": f"{config['singular']} sil",
            "onay_ust_etiket": "İçerik Yönetimi",
            "confirm_message": f"'{nesne}' kaydını kalıcı olarak silmek üzeresin. Bu işlem geri alınamaz. Silmeden önce içeriğin başka alanlarda kullanılmadığından emin ol.",
            "onay_detaylari": [("İçerik türü", config["title"]), ("Kayıt", str(nesne)), ("Kimlik", f"#{nesne.pk}")],
            "onay_buton": "Kalıcı Olarak Sil",
            "cancel_url": reverse("superadmin_icerik_model_duzenle", args=[model_key, nesne.pk]),
            "geri_url": back_url,
        }
    )
    return render(request, "superadmin/confirm.html", context)


KULLANICI_FORM_TAM_GENISLIK = {"is_active", "is_staff", "is_superuser"}


@superadmin_required
def superadmin_kullanicilar(request):
    arama = request.GET.get("q", "").strip()
    kullanicilar = User.objects.order_by("username")
    if arama:
        kullanicilar = kullanicilar.filter(arama_filtresi(["username", "first_name", "last_name", "email"], arama))
    page_obj, sayfa_sorgusu = sayfala(request, kullanicilar)
    context = build_superadmin_context(request)
    context.update(
        {
            "page_title": "Kullanıcılar",
            "kullanicilar": page_obj.object_list,
            "page_obj": page_obj,
            "sayfa_sorgusu": sayfa_sorgusu,
            "arama": arama,
        }
    )
    return render(request, "superadmin/users.html", context)


def super_kullanici_korumasi(request, kullanici):
    """Super kullanici olmayan panel yoneticisinin super kullanici hesabini degistirmesini engeller."""
    if kullanici.is_superuser and not request.user.is_superuser:
        messages.error(request, "Süper kullanıcı hesaplarını sadece süper kullanıcılar düzenleyebilir.")
        return redirect("superadmin_kullanicilar")
    return None


@superadmin_required
def superadmin_kullanici_yeni(request):
    if request.method == "POST":
        form = SuperadminKullaniciForm(request.POST, duzenleyen=request.user)
        if form.is_valid():
            kullanici = form.save(commit=False)
            kullanici.set_unusable_password()
            kullanici.save()
            islem_kaydet(request, kullanici, ADDITION, "Kullanıcı eklendi")
            messages.success(request, "Kullanıcı oluşturuldu. Şimdi şifresini belirle.")
            return redirect("superadmin_kullanici_sifre", pk=kullanici.pk)
    else:
        form = SuperadminKullaniciForm(duzenleyen=request.user)

    context = build_superadmin_context(request)
    context.update(
        {
            "page_title": "Kullanıcı ekle",
            "form": form,
            "form_title": "Kullanıcı ekle",
            "submit_label": "Kaydet ve şifre belirle",
            "back_url": reverse("superadmin_kullanicilar"),
            "full_width_fields": KULLANICI_FORM_TAM_GENISLIK,
        }
    )
    return render(request, "superadmin/user_form.html", context)


@superadmin_required
def superadmin_kullanici_duzenle(request, pk):
    kullanici = get_object_or_404(User, pk=pk)
    engel = super_kullanici_korumasi(request, kullanici)
    if engel:
        return engel
    if request.method == "POST":
        # is_valid() formdaki degerleri nesneye yazar; kontrol icin onceki yetkiyi sakla
        super_kullaniciydi = kullanici.is_superuser
        form = SuperadminKullaniciForm(request.POST, instance=kullanici, duzenleyen=request.user)
        if form.is_valid():
            kendi_hesabi = kullanici.pk == request.user.pk
            erisim_kisitlaniyor = (
                not form.cleaned_data["is_active"]
                or not form.cleaned_data["is_staff"]
                or (super_kullaniciydi and not form.cleaned_data.get("is_superuser", True))
            )
            if kendi_hesabi and erisim_kisitlaniyor:
                # Formu sifirlamadan hatayi goster
                form.add_error(None, "Kendi hesabının erişimini bu ekrandan kısıtlayamazsın.")
            else:
                form.save()
                islem_kaydet(request, kullanici, CHANGE, degisen_alanlar_mesaji(form))
                messages.success(request, "Kullanıcı güncellendi.")
                return redirect("superadmin_kullanici_duzenle", pk=pk)
    else:
        form = SuperadminKullaniciForm(instance=kullanici, duzenleyen=request.user)

    context = build_superadmin_context(request)
    context.update(
        {
            "page_title": "Kullanıcı düzenle",
            "object": kullanici,
            "form": form,
            "form_title": f"{kullanici.username} düzenle",
            "submit_label": "Değişiklikleri Kaydet",
            "back_url": reverse("superadmin_kullanicilar"),
            "full_width_fields": KULLANICI_FORM_TAM_GENISLIK,
        }
    )
    return render(request, "superadmin/user_form.html", context)


@superadmin_required
def superadmin_kullanici_sifre(request, pk):
    kullanici = get_object_or_404(User, pk=pk)
    engel = super_kullanici_korumasi(request, kullanici)
    if engel:
        return engel
    if request.method == "POST":
        form = SuperadminKullaniciSifreForm(request.POST)
        if form.is_valid():
            kullanici.set_password(form.cleaned_data["yeni_sifre1"])
            kullanici.save(update_fields=["password"])
            if kullanici.pk == request.user.pk:
                update_session_auth_hash(request, kullanici)
            islem_kaydet(request, kullanici, CHANGE, "Şifre değiştirildi")
            messages.success(request, f"{kullanici.username} için şifre güncellendi.")
            return redirect("superadmin_kullanici_duzenle", pk=pk)
    else:
        form = SuperadminKullaniciSifreForm()

    context = build_superadmin_context(request)
    context.update(
        {
            "page_title": "Şifre belirle",
            "object": kullanici,
            "form": form,
            "back_url": reverse("superadmin_kullanici_duzenle", args=[pk]),
        }
    )
    return render(request, "superadmin/user_password_form.html", context)


# Eski Django admin adresleri (/admin/core/<model>/) icin icerik panelinde karsiligi olmayan modellerin hedefleri
LEGACY_CORE_HEDEFLER = {
    "iletisimbasvurusu": "superadmin_iletisim",
    "theme": "superadmin_icerik_yonetimi",
}


@superadmin_required
def superadmin_legacy_core_model_redirect(request, model_key, pk=None, action=None):
    if model_key in CONTENT_MODEL_CONFIG:
        if action == "add":
            return redirect("superadmin_icerik_model_yeni", model_key=model_key)
        if action == "change" and pk is not None:
            return redirect("superadmin_icerik_model_duzenle", model_key=model_key, pk=pk)
        return redirect("superadmin_icerik_model_liste", model_key=model_key)

    if model_key == "iletisimbasvurusu" and action == "change" and pk is not None:
        return redirect("superadmin_iletisim_detay", pk=pk)
    return redirect(LEGACY_CORE_HEDEFLER.get(model_key, "superadmin_dashboard"))


def anasayfa(request):
    sliderlar = Slider.objects.filter(aktif=True).order_by("sira")
    hero_slider = sliderlar.first()
    marquee_sliderlar = sliderlar
    kitap_siralama = (
        Kitap.objects.select_related("yazar__user")
        .filter(yayinda=True)
        .order_by("-created_at", "-id")
    )
    son_yuklenen_kitap = kitap_siralama.first()
    one_cikan_kitaplar = kitap_siralama.prefetch_related("turler")[1:8]
    son_blog_yazilari = list(
        BlogYazisi.objects.select_related("yazar__user", "kategori")
        .prefetch_related("kategoriler")
        .filter(durum=BlogYazisi.DurumSecenekleri.YAYINDA)
        .order_by("-yayin_tarihi", "-created_at")[:3]
    )
    one_cikan_alintilar = list(yayindaki_alintilar()[:6])
    fallback_alintilar = [
        {"metin": "Bir kitap, içinizdeki donmuş denize indirilmiş bir baltadır.", "yazar": "Franz Kafka"},
        {"metin": "İnsan ancak yüreğiyle baktığı zaman doğruyu görebilir.", "yazar": "Antoine de Saint-Exupéry"},
        {"metin": "Kendini bulmak istiyorsan, kendi başına kal.", "yazar": "Nietzsche"},
        {"metin": "Ya olduğun gibi görün, ya göründüğün gibi ol.", "yazar": "Mevlana"},
        {"metin": "En büyük savaş, kendinle olan savaştır.", "yazar": "Dostoyevski"},
        {"metin": "Şiir, sözcüklerle güzel şeyler yapma sanatıdır.", "yazar": "Cemal Süreya"},
    ]
    alinti_kartlari = [
        {
            "metin": alinti.metin,
            "yazar": alinti.kaynak.yazar.ad,
        }
        for alinti in one_cikan_alintilar
    ]
    if len(alinti_kartlari) < 6:
        alinti_kartlari.extend(fallback_alintilar[: 6 - len(alinti_kartlari)])
    son_yuklenen_kitaplar = kitap_siralama[:6]
    hero_yazarlar = list(YazarProfil.objects.filter(onayli=True).order_by("-created_at", "-id")[:2])
    hero_yazar_kartlari = [
        {
            "ad_soyad": yazar.ad_soyad,
            "fotograf": yazar.fotograf,
            "ilk_harfler": yazar_kisa_ad(yazar.ad_soyad),
        }
        for yazar in hero_yazarlar
    ]
    while len(hero_yazar_kartlari) < 2:
        hero_yazar_kartlari.append(
            {
                "ad_soyad": "Tecrit Edebiyat",
                "fotograf": None,
                "ilk_harfler": "T",
            }
        )
    yayin_kartlari = list(
        AnaSayfaYayinKarti.objects.filter(aktif=True).order_by("sira", "-created_at")[:6]
    )

    context = {
        "sliderlar": sliderlar,
        "hero_slider": hero_slider,
        "marquee_sliderlar": marquee_sliderlar,
        "son_yuklenen_kitap": son_yuklenen_kitap,
        "one_cikan_kitaplar": one_cikan_kitaplar,
        "son_blog_yazilari": son_blog_yazilari,
        "blog_bos_kartlar": range(max(0, 3 - len(son_blog_yazilari))),
        "alinti_ust_satir": alinti_kartlari[:3],
        "alinti_alt_satir": alinti_kartlari[3:6],
        "son_yuklenen_kitaplar": son_yuklenen_kitaplar,
        "hero_yazar_kartlari": hero_yazar_kartlari,
        "yayin_kartlari": yayin_kartlari,
        "kitap_sayisi": Kitap.objects.filter(yayinda=True).count(),
        "yazar_sayisi": YazarProfil.objects.filter(onayli=True).count(),
        "blog_sayisi": BlogYazisi.objects.filter(durum=BlogYazisi.DurumSecenekleri.YAYINDA).count(),
        **seo_context(
            "Tecrit Edebiyat | Kitaplar, Blog Yazilari ve Alintilar",
            "Kitap tanitimlari, yazar profilleri, son blog yazilari ve secilmis alintilarla Turkiye odakli bir edebiyat platformu.",
            request.build_absolute_uri("/"),
        ),
    }
    return render(request, "index.html", context)


def kitaplar(request):
    kategori_slug = request.GET.get("kategori")
    arama = request.GET.get("q", "").strip()

    kitap_listesi = (
        Kitap.objects.select_related("yazar__user", "ikinci_yazar")
        .prefetch_related("turler")
        .filter(yayinda=True)
        .order_by("-yayin_tarihi", "ad")
    )
    secili_kategori = None

    if kategori_slug:
        secili_kategori = get_object_or_404(KitapTur, slug=kategori_slug)
        kitap_listesi = kitap_listesi.filter(turler=secili_kategori)

    if arama:
        kitap_listesi = kitap_listesi.filter(
            Q(ad__icontains=arama)
            | Q(aciklama__icontains=arama)
            | Q(yazar__ad_soyad__icontains=arama)
            | Q(ikinci_yazar__ad_soyad__icontains=arama)
        )

    hero_kitap = kitap_listesi.first()
    marquee_kitaplar = kitap_listesi[:6]

    context = {
        "kitaplar": kitap_listesi,
        "kategoriler": KitapTur.objects.all(),
        "secili_kategori": secili_kategori,
        "arama": arama,
        "hero_kitap": hero_kitap,
        "marquee_kitaplar": marquee_kitaplar,
        **seo_context(
            "Kitaplar | Tecrit Edebiyat",
            "Kategori ve yazar bazinda filtrelenebilen kitap listesi. Kitap detaylari ve satin alma baglantilarina buradan ulasabilirsiniz.",
            request.build_absolute_uri(),
        ),
    }
    return render(request, "kitaplar.html", context)


def kitap_detay(request, slug):
    kitap = get_object_or_404(
        Kitap.objects.select_related("yazar__user", "kaynak").prefetch_related("turler"),
        slug=slug,
        yayinda=True,
    )
    sirali_kitaplar = list(
        Kitap.objects.select_related("yazar__user")
        .filter(yayinda=True)
        .order_by("-yayin_tarihi", "ad")
    )
    onceki_kitap = None
    sonraki_kitap = None
    for index, siradaki_kitap in enumerate(sirali_kitaplar):
        if siradaki_kitap.pk == kitap.pk:
            if index > 0:
                onceki_kitap = sirali_kitaplar[index - 1]
            if index < len(sirali_kitaplar) - 1:
                sonraki_kitap = sirali_kitaplar[index + 1]
            break
    benzer_kitaplar = (
        Kitap.objects.select_related("yazar__user")
        .filter(yayinda=True)
        .exclude(pk=kitap.pk)
        .order_by("-yayin_tarihi")[:3]
    )
    iliskili_bloglar = (
        BlogYazisi.objects.filter(
            durum=BlogYazisi.DurumSecenekleri.YAYINDA,
            yazar=kitap.yazar,
        )
        .order_by("-yayin_tarihi")[:3]
    ) if kitap.yazar else BlogYazisi.objects.none()
    # Bu katalog kitabindan yapilmis yayindaki alintilar (varsa kitabin alinti sayfasina baglanir)
    alinti_kaynagi = getattr(kitap, "kaynak", None)
    alinti_sayisi = yayindaki_alintilar().filter(kaynak=alinti_kaynagi).count() if alinti_kaynagi else 0
    context = {
        "kitap": kitap,
        "alinti_kaynagi": alinti_kaynagi,
        "alinti_sayisi": alinti_sayisi,
        "onceki_kitap": onceki_kitap,
        "sonraki_kitap": sonraki_kitap,
        "benzer_kitaplar": benzer_kitaplar,
        "iliskili_bloglar": iliskili_bloglar,
        **seo_context(
            kitap.meta_title or f"{kitap.ad} | Tecrit Edebiyat",
            kitap.meta_description or kitap.aciklama,
            request.build_absolute_uri(),
        ),
    }
    return render(request, "kitap_detay.html", context)


def yazarlar(request):
    yazar_listesi = (
        YazarProfil.objects.select_related("user", "kaynak_yazar")
        .prefetch_related("kitaplar", "ikinci_yazar_kitaplar", "blog_yazilari")
        .annotate(
            alinti_sayisi=Count(
                "kaynak_yazar__kitaplar__alintilar",
                filter=Q(kaynak_yazar__kitaplar__alintilar__durum=Alinti.DurumSecenekleri.YAYINDA),
            )
        )
        .filter(onayli=True)
        .order_by("ad_soyad")
    )
    return render(
        request,
        "yazarlar.html",
        {
            "yazarlar": yazar_listesi,
            **seo_context(
                "Yazarlar | Tecrit Edebiyat",
                "Platformda yer alan yazarlarin profilleri, kitaplari ve blog yazilari.",
                request.build_absolute_uri(),
            ),
        },
    )


def blog(request):
    kategori_slug = request.GET.get("kategori")
    arama = request.GET.get("q", "").strip()
    blog_yazilari = (
        BlogYazisi.objects.select_related("yazar__user", "kategori")
        .prefetch_related("kategoriler")
        .filter(durum=BlogYazisi.DurumSecenekleri.YAYINDA)
        .order_by("-yayin_tarihi", "-created_at")
    )
    secili_kategori = None
    if kategori_slug:
        secili_kategori = get_object_or_404(BlogKategori, slug=kategori_slug)
        blog_yazilari = blog_yazilari.filter(
            Q(kategori=secili_kategori) | Q(kategoriler=secili_kategori)
        )

    if arama:
        blog_yazilari = blog_yazilari.filter(
            Q(baslik__icontains=arama)
            | Q(ozet__icontains=arama)
            | Q(icerik__icontains=arama)
            | Q(yazar__ad_soyad__icontains=arama)
            | Q(kategori__ad__icontains=arama)
            | Q(kategoriler__ad__icontains=arama)
        )

    blog_yazilari = blog_yazilari.distinct()
    sayfa_nesnesi = Paginator(blog_yazilari, 6).get_page(request.GET.get("sayfa"))
    son_yazilar = blog_yazilari[:4]
    aktif_reklamlar = BlogReklam.objects.filter(aktif=True).order_by("sira", "-created_at")
    urunler = BlogUrun.objects.filter(aktif=True).order_by("-one_cikar", "sira", "-created_at")
    filtreler = {}
    if kategori_slug:
        filtreler["kategori"] = kategori_slug
    if arama:
        filtreler["q"] = arama
    pagination_query = urlencode(filtreler)

    return render(
        request,
        "blog.html",
        {
            "yazilar": sayfa_nesnesi.object_list,
            "kategoriler": BlogKategori.objects.all(),
            "secili_kategori": secili_kategori,
            "arama": arama,
            "son_yazilar": son_yazilar,
            "aktif_reklamlar": aktif_reklamlar,
            "urunler": urunler,
            "sayfa_nesnesi": sayfa_nesnesi,
            "sayfalandirildi_mi": sayfa_nesnesi.paginator.num_pages > 1,
            "pagination_query": pagination_query,
            **seo_context(
                "Blog | Tecrit Edebiyat",
                "Yazarlar tarafindan hazirlanan, editor onayindan gecmis edebiyat yazilari ve incelemeleri.",
                request.build_absolute_uri(),
            ),
        },
    )


BOT_IZLERI = ("bot", "crawl", "spider", "slurp", "preview", "facebookexternalhit", "headless", "curl", "wget", "python-requests")


def okunma_sayilmali_mi(request):
    if request.method != "GET" or request.user.is_staff:
        return False
    tarayici = request.META.get("HTTP_USER_AGENT", "").lower()
    return bool(tarayici) and not any(iz in tarayici for iz in BOT_IZLERI)


def blog_detay(request, slug):
    yazi = get_object_or_404(
        BlogYazisi.objects.select_related("yazar__user", "kategori").prefetch_related(
            "kategoriler",
            "medyalar",
            Prefetch(
                "alintilar",
                queryset=Alinti.objects.filter(durum=Alinti.DurumSecenekleri.YAYINDA, kaynak__isnull=False).select_related("kaynak__yazar", "paylasan__profil"),
                to_attr="yayindaki_alintilar",
            ),
        ),
        slug=slug,
        durum=BlogYazisi.DurumSecenekleri.YAYINDA,
    )
    if okunma_sayilmali_mi(request):
        # save() cagirmadan atomik artis: updated_at ve icerik temizligi etkilenmez
        BlogYazisi.objects.filter(pk=yazi.pk).update(okunma_sayisi=F("okunma_sayisi") + 1)
    sirali_yazilar = list(
        BlogYazisi.objects.select_related("yazar__user", "kategori")
        .prefetch_related("kategoriler")
        .filter(durum=BlogYazisi.DurumSecenekleri.YAYINDA)
        .order_by("-yayin_tarihi", "-created_at")
    )
    onceki_yazi = None
    sonraki_yazi = None
    for index, siradaki_yazi in enumerate(sirali_yazilar):
        if siradaki_yazi.pk == yazi.pk:
            if index > 0:
                onceki_yazi = sirali_yazilar[index - 1]
            if index < len(sirali_yazilar) - 1:
                sonraki_yazi = sirali_yazilar[index + 1]
            break

    kelime_sayisi = len(strip_tags(yazi.icerik or "").split())
    okuma_suresi = max(1, math.ceil(kelime_sayisi / 200)) if kelime_sayisi else 1
    benzer_yazilar = (
        BlogYazisi.objects.select_related("yazar__user", "kategori")
        .prefetch_related("kategoriler")
        .filter(durum=BlogYazisi.DurumSecenekleri.YAYINDA)
        .exclude(pk=yazi.pk)
        .order_by("-yayin_tarihi")[:3]
    )
    son_yazilar = (
        BlogYazisi.objects.select_related("yazar__user", "kategori")
        .prefetch_related("kategoriler")
        .filter(durum=BlogYazisi.DurumSecenekleri.YAYINDA)
        .exclude(pk=yazi.pk)
        .order_by("-yayin_tarihi", "-created_at")[:4]
    )
    return render(
        request,
        "blog_detay.html",
        {
            "yazi": yazi,
            "onceki_yazi": onceki_yazi,
            "sonraki_yazi": sonraki_yazi,
            "okuma_suresi": okuma_suresi,
            "benzer_yazilar": benzer_yazilar,
            "son_yazilar": son_yazilar,
            "kategoriler": BlogKategori.objects.all(),
            **seo_context(
                yazi.meta_title or f"{yazi.baslik} | Tecrit Edebiyat",
                yazi.meta_description or yazi.ozet or yazi.icerik,
                request.build_absolute_uri(),
            ),
        },
    )


def yayindaki_alintilar():
    """Sitede gosterilen alintilar: yayinda ve kaynagi belli olanlar."""
    return (
        Alinti.objects.select_related("kaynak__yazar", "kategori", "paylasan__profil")
        .filter(durum=Alinti.DurumSecenekleri.YAYINDA, kaynak__isnull=False)
        .order_by("-yayin_tarihi", "-created_at")
    )


def alintilar(request):
    alinti_listesi = yayindaki_alintilar()
    sayfa_nesnesi = Paginator(alinti_listesi, 12).get_page(request.GET.get("sayfa"))

    return render(
        request,
        "alintilar.html",
        {
            "alintilar": alinti_listesi,
            "sayfa_nesnesi": sayfa_nesnesi,
            "sayfalandirildi_mi": sayfa_nesnesi.paginator.num_pages > 1,
            **seo_context(
                "Alıntılar | Tecrit Edebiyat",
                "Kitaplardan seçilmiş, paylaşılmaya değer alıntılar ve kaynak eser bilgileri.",
                request.build_absolute_uri(),
            ),
        },
    )


def alinti_kitap(request, slug):
    kitap = get_object_or_404(KaynakKitap.objects.select_related("yazar", "katalog_kitabi"), slug=slug)
    alinti_listesi = yayindaki_alintilar().filter(kaynak=kitap)
    if not kitap.onayli and not alinti_listesi.exists():
        raise Http404("Kitap bulunamadı")
    sayfa_nesnesi = Paginator(alinti_listesi, 12).get_page(request.GET.get("sayfa"))
    kunye = " · ".join(str(p) for p in [kitap.yayinevi, kitap.basim_yili] if p)
    return render(
        request,
        "alintilar_kitap.html",
        {
            "kitap": kitap,
            "kunye": kunye,
            "sayfa_nesnesi": sayfa_nesnesi,
            "sayfalandirildi_mi": sayfa_nesnesi.paginator.num_pages > 1,
            **seo_context(
                f"{kitap.ad} – Alıntılar | Tecrit Edebiyat",
                f"{kitap.yazar.ad} imzalı {kitap.ad} kitabından okurlarımızın paylaştığı alıntılar.",
                request.build_absolute_uri(),
            ),
        },
    )


def alinti_yazar(request, slug):
    yazar = get_object_or_404(KaynakYazar.objects.select_related("yazar_profili"), slug=slug)
    alinti_listesi = yayindaki_alintilar().filter(kaynak__yazar=yazar)
    kitaplar = list(
        yazar.kitaplar.annotate(
            yayindaki=Count("alintilar", filter=Q(alintilar__durum=Alinti.DurumSecenekleri.YAYINDA))
        ).filter(Q(onayli=True) | Q(yayindaki__gt=0)).order_by("-yayindaki", "ad")
    )
    if not kitaplar:
        raise Http404("Yazar bulunamadı")
    sayfa_nesnesi = Paginator(alinti_listesi, 12).get_page(request.GET.get("sayfa"))
    return render(
        request,
        "alintilar_yazar.html",
        {
            "yazar": yazar,
            "kitaplar": kitaplar,
            "sayfa_nesnesi": sayfa_nesnesi,
            "sayfalandirildi_mi": sayfa_nesnesi.paginator.num_pages > 1,
            **seo_context(
                f"{yazar.ad} – Alıntılar | Tecrit Edebiyat",
                f"{yazar.ad} kitaplarından okurlarımızın paylaştığı alıntılar.",
                request.build_absolute_uri(),
            ),
        },
    )


def sss(request):
    sorular = SSS.objects.filter(aktif=True).order_by("sira", "-eklenme_tarihi")
    return render(
        request,
        "sss.html",
        {
            "sorular": sorular,
            **seo_context(
                "Sik Sorulan Sorular | Tecrit Edebiyat",
                "Tecrit Edebiyat hakkinda sik sorulan sorular ve cevaplari.",
                request.build_absolute_uri(),
            ),
        },
    )


def gizlilik_politikasi(request):
    politika_maddeleri = [
        {
            "baslik": "1. Genel Bilgilendirme",
            "icerik": [
                "Bu web sitesi, kullanıcıların kendi içeriklerini (yazı, yorum vb.) paylaşabildiği bir platformdur. Siteyi kullanan her kullanıcı, aşağıda belirtilen şartları kabul etmiş sayılır.",
            ],
        },
        {
            "baslik": "2. Kişisel Verilerin Toplanması ve Kullanımı",
            "icerik": [
                "Platform, kullanıcı deneyimini geliştirmek amacıyla bazı kişisel verileri (örneğin kullanıcı adı, e-posta adresi, IP bilgisi vb.) toplayabilir.",
                "Toplanan veriler:",
                "Hesap oluşturma ve yönetme",
                "İçerik paylaşımını sağlama",
                "Güvenlik ve kötüye kullanımın önlenmesi",
                "amacıyla kullanılır.",
                "Bu veriler, üçüncü kişilerle kullanıcının açık rızası olmadan paylaşılmaz (yasal zorunluluklar hariç).",
            ],
        },
        {
            "baslik": "3. Çerezler (Cookies)",
            "icerik": [
                "Web sitesi, kullanıcı deneyimini iyileştirmek amacıyla çerezler kullanabilir. Kullanıcılar, tarayıcı ayarları üzerinden çerez kullanımını sınırlayabilir veya devre dışı bırakabilir.",
            ],
        },
        {
            "baslik": "4. Kullanıcı İçerikleri ve Sorumluluk",
            "icerik": [
                "Bu platformda paylaşılan tüm içeriklerin (yazılar, yorumlar, görseller vb.) sorumluluğu tamamen içeriği paylaşan kullanıcıya aittir.",
                "Platform:",
                "Kullanıcılar tarafından paylaşılan içeriklerin doğruluğunu garanti etmez",
                "İçeriklerden doğabilecek herhangi bir hukuki sorumluluğu kabul etmez",
                "Kullanıcı, paylaştığı içeriklerin:",
                "Yasalara uygun olduğunu",
                "Üçüncü kişilerin haklarını ihlal etmediğini",
                "Telif hakkı, kişilik hakları ve diğer tüm yasal yükümlülüklere uygun olduğunu",
                "kabul eder.",
            ],
        },
        {
            "baslik": "5. İçerik Kaldırma Hakkı",
            "icerik": [
                "Platform, gerekli gördüğü durumlarda herhangi bir içeriği:",
                "Düzenleme",
                "Kaldırma",
                "Yayından kaldırma",
                "hakkını saklı tutar.",
            ],
        },
        {
            "baslik": "6. Üçüncü Taraf Bağlantılar",
            "icerik": [
                "Platform, üçüncü taraf sitelere bağlantılar içerebilir. Bu sitelerin gizlilik politikalarından ve içeriklerinden platform sorumlu değildir.",
            ],
        },
        {
            "baslik": "7. Güvenlik",
            "icerik": [
                "Kullanıcı verilerinin korunması için gerekli teknik önlemler alınmaktadır. Ancak internet ortamında %100 güvenlik garanti edilemez.",
            ],
        },
        {
            "baslik": "8. Değişiklikler",
            "icerik": [
                "Platform, bu gizlilik politikasını dilediği zaman güncelleme hakkını saklı tutar. Güncellemeler yayınlandığı anda yürürlüğe girer.",
            ],
        },
        {
            "baslik": "9. Kabul",
            "icerik": [
                "Bu siteyi kullanan her kullanıcı, bu gizlilik politikası ve sorumluluk reddi metnini okuduğunu ve kabul ettiğini beyan eder.",
            ],
        },
    ]
    return render(
        request,
        "gizlilik_politikasi.html",
        {
            "politika_maddeleri": politika_maddeleri,
            **seo_context(
                "Gizlilik Politikasi ve Sorumluluk Reddi | Tecrit Edebiyat",
                "Tecrit Edebiyat gizlilik politikasi, cerez kullanimi, kullanici icerikleri ve sorumluluk reddi metni.",
                request.build_absolute_uri(),
            ),
        },
    )


def kullanim_sartlari(request):
    sart_maddeleri = [
        {
            "baslik": "1. Taraflar ve Kapsam",
            "icerik": [
                'Bu web sitesi ("Platform"), kullanıcıların içerik paylaşabildiği bir blog hizmeti sunmaktadır. Platformu kullanan herkes ("Kullanıcı"), aşağıdaki kullanım şartlarını kabul etmiş sayılır.',
            ],
        },
        {
            "baslik": "2. Hizmet Tanımı",
            "icerik": [
                "Platform, kullanıcıların yazı, yorum ve benzeri içerikler paylaşmasına olanak sağlayan bir içerik paylaşım alanıdır. Platform, yalnızca bir aracıdır ve kullanıcılar tarafından oluşturulan içerikler üzerinde editoryal sorumluluk üstlenmez.",
            ],
        },
        {
            "baslik": "3. Üyelik ve Hesap Sorumluluğu",
            "icerik": [
                "Kullanıcı:",
                "Doğru ve güncel bilgiler sağlamakla yükümlüdür",
                "Hesap bilgilerinin gizliliğinden kendisi sorumludur",
                "Hesabı üzerinden gerçekleştirilen tüm işlemleri kabul eder",
            ],
        },
        {
            "baslik": "4. Kullanıcı İçerikleri",
            "icerik": [
                "Platformda paylaşılan tüm içeriklerin sorumluluğu tamamen kullanıcıya aittir.",
                "Kullanıcı, paylaştığı içeriklerin:",
                "Yasalara uygun olduğunu",
                "Telif hakkı ihlali içermediğini",
                "Başkalarının haklarını ihlal etmediğini",
                "kabul eder.",
                "Platform:",
                "Kullanıcı içeriklerini önceden kontrol etmek zorunda değildir",
                "İçeriklerin doğruluğunu garanti etmez",
                "Kullanıcı içeriklerinden doğabilecek hiçbir hukuki sorumluluğu kabul etmez",
            ],
        },
        {
            "baslik": "5. Yasaklı Kullanımlar",
            "icerik": [
                "Kullanıcı aşağıdaki eylemlerde bulunamaz:",
                "Hukuka aykırı içerik paylaşmak",
                "Hakaret, tehdit veya nefret söylemi içeren içerikler yayınlamak",
                "Başkalarının kişisel verilerini izinsiz paylaşmak",
                "Spam, yanıltıcı veya zararlı içerik üretmek",
                "Bu kurallara aykırı davranan kullanıcıların hesapları askıya alınabilir veya tamamen silinebilir.",
            ],
        },
        {
            "baslik": "6. İçerik Üzerindeki Haklar",
            "icerik": [
                "Kullanıcı, paylaştığı içeriklerin tüm haklarına sahiptir. Ancak kullanıcı, Platforma bu içerikleri yayınlama, çoğaltma ve görüntüleme konusunda sınırlı, ücretsiz ve devredilebilir bir kullanım hakkı verdiğini kabul eder.",
            ],
        },
        {
            "baslik": "7. İçerik Kaldırma ve Hesap Sonlandırma",
            "icerik": [
                "Platform:",
                "Herhangi bir içeriği kaldırma",
                "Kullanıcı hesabını askıya alma veya sonlandırma",
                "hakkını önceden bildirim yapmaksızın saklı tutar.",
            ],
        },
        {
            "baslik": "8. Sorumluluğun Sınırlandırılması",
            "icerik": [
                "Platform:",
                "Kullanıcı içeriklerinden doğan doğrudan veya dolaylı zararlardan sorumlu değildir",
                "Hizmetin kesintisiz veya hatasız olacağını garanti etmez",
            ],
        },
        {
            "baslik": "9. Değişiklikler",
            "icerik": [
                "Platform, bu kullanım şartlarını dilediği zaman güncelleme hakkını saklı tutar. Güncellemeler yayınlandığı anda yürürlüğe girer.",
            ],
        },
        {
            "baslik": "10. Uygulanacak Hukuk",
            "icerik": [
                "Bu kullanım şartları Türkiye Cumhuriyeti kanunlarına tabidir. Taraflar arasında doğabilecek uyuşmazlıklarda ilgili mahkemeler ve icra daireleri yetkilidir.",
            ],
        },
        {
            "baslik": "11. Kabul",
            "icerik": [
                "Platformu kullanan her kullanıcı, bu kullanım şartlarını okuduğunu, anladığını ve kabul ettiğini beyan eder.",
            ],
        },
    ]
    return render(
        request,
        "kullanim_sartlari.html",
        {
            "sart_maddeleri": sart_maddeleri,
            **seo_context(
                "Kullanim Sartlari | Tecrit Edebiyat",
                "Tecrit Edebiyat kullanim sartlari, hesap sorumluluklari, yasakli kullanimlar ve hukuki sinirlar.",
                request.build_absolute_uri(),
            ),
        },
    )


def iletisim(request):
    if request.method == "POST":
        contact_form = ContactForm(request.POST, request.FILES)
        if contact_form.is_valid():
            basvuru = IletisimBasvurusu.objects.create(
                ad=contact_form.cleaned_data["name"],
                soyad=contact_form.cleaned_data["surname"],
                email=contact_form.cleaned_data["email"],
                telefon=contact_form.cleaned_data["phone"],
                amac=contact_form.cleaned_data["purpose"],
                mesaj=contact_form.cleaned_data["message"],
                dosya=contact_form.cleaned_data.get("attachment"),
            )

            konu = f"[Tecrit Edebiyat] {basvuru.get_amac_display()} - {basvuru.ad} {basvuru.soyad}"
            icerik = (
                f"İletişim amacı: {basvuru.get_amac_display()}\n"
                f"Ad Soyad: {basvuru.ad} {basvuru.soyad}\n"
                f"E-posta: {basvuru.email}\n"
                f"Telefon: {basvuru.telefon}\n"
                f"Başvuru tarihi: {basvuru.created_at.strftime('%d.%m.%Y %H:%M')}\n\n"
                f"Mesaj:\n{basvuru.mesaj}"
            )

            try:
                email = EmailMessage(
                    subject=konu,
                    body=icerik,
                    from_email=getattr(settings, "DEFAULT_FROM_EMAIL", None) or basvuru.email,
                    to=[settings.CONTACT_EMAIL, "iletisim@tecritedebiyat.com"],
                    reply_to=[basvuru.email],
                )

                if basvuru.dosya:
                    mime_type, _ = mimetypes.guess_type(basvuru.dosya.name)
                    with basvuru.dosya.open("rb") as dosya_icerigi:
                        email.attach(
                            os.path.basename(basvuru.dosya.name),
                            dosya_icerigi.read(),
                            mime_type or "application/octet-stream",
                        )

                email.send(fail_silently=False)
                messages.success(request, "Mesajınız alındı ve e-posta olarak iletildi. En kısa sürede size dönüş yapacağız.")
            except Exception:
                messages.warning(
                    request,
                    "Başvurunuz kaydedildi ancak e-posta gönderiminde bir sorun oluştu. Admin panelinden mesajınıza yine ulaşabilirsiniz.",
                )

            return redirect("iletisim")
    else:
        contact_form = ContactForm()

    return render(
        request,
        "iletisim.html",
        {
            "contact_form": contact_form,
            **seo_context(
                "Iletisim | Tecrit Edebiyat",
                "Tecrit Edebiyat ile iletisime gecmek, is birligi yapmak veya yazi gondermek icin iletisim sayfasi.",
                request.build_absolute_uri(),
            ),
        }
    )


def hakkimizda(request):
    marquee_kitaplar = list(
        Kitap.objects.select_related("yazar__user")
        .filter(yayinda=True, kapak_resmi__isnull=False)
        .exclude(kapak_resmi="")
        .order_by("-created_at", "-id")[:4]
    )

    if marquee_kitaplar:
        while len(marquee_kitaplar) < 4:
            marquee_kitaplar.extend(marquee_kitaplar[: 4 - len(marquee_kitaplar)])
        marquee_kitaplar = marquee_kitaplar[:4]

    return render(
        request,
        "hakkimizda.html",
        {
            "marquee_kitaplar": marquee_kitaplar,
            "kitap_sayisi": Kitap.objects.filter(yayinda=True).count(),
            "yazar_sayisi": YazarProfil.objects.filter(onayli=True).count(),
            "blog_sayisi": BlogYazisi.objects.filter(durum=BlogYazisi.DurumSecenekleri.YAYINDA).count(),
            **seo_context(
                "Hakkimizda | Tecrit Edebiyat",
                "Tecrit Edebiyat'in amaci, yayin cizgisi ve yazar odakli icerik ekosistemi hakkinda bilgi.",
                request.build_absolute_uri(),
            ),
        },
    )


def kitap_maliyeti_hesapla(request):
    ayarlar = KitapMaliyetiAyarlari.get_ayarlar()
    sayfa_basi_ucret = ayarlar.sayfa_basi_ucret
    sabit_ucret = ayarlar.sabit_ucret
    turler = list(KitapMaliyetTuru.objects.all())

    kelime_sayisi = ""
    sayfa_sayisi = ""
    secili_tur_id = ""
    toplam_ucret = None
    formatli_toplam_ucret = ""
    hesaplama_detayi = ""
    form_hatasi = ""

    if turler and not secili_tur_id:
        secili_tur_id = str(turler[0].id)

    if request.method == "POST":
        kelime_sayisi = request.POST.get("kelime_sayisi", "").strip()
        sayfa_sayisi = request.POST.get("sayfa_sayisi", "").strip()
        secili_tur_id = request.POST.get("tur", "").strip()
        secili_tur = next((t for t in turler if str(t.id) == secili_tur_id), None)

        if secili_tur is None:
            form_hatasi = "Lütfen kitap türünü seçin."
        else:
            sayfa_bazli = secili_tur.sayfa_bazli or not secili_tur.kelime_yogunlugu
            girilen = sayfa_sayisi if sayfa_bazli else kelime_sayisi
            try:
                girilen_int = int(girilen)
                if girilen_int <= 0:
                    raise ValueError
            except ValueError:
                form_hatasi = (
                    "Lütfen 1 veya daha büyük bir sayfa sayısı girin."
                    if sayfa_bazli
                    else "Lütfen 1 veya daha büyük bir kelime sayısı girin."
                )
            else:
                if sayfa_bazli:
                    tahmini_sayfa = girilen_int
                    hesaplama_detayi = f"{tahmini_sayfa} sayfa × {sayfa_basi_ucret} + {sabit_ucret:,}".replace(",", ".")
                else:
                    tahmini_sayfa = math.ceil(girilen_int / secili_tur.kelime_yogunlugu)
                    hesaplama_detayi = (
                        f"({girilen_int} kelime ÷ {secili_tur.kelime_yogunlugu} kelime/sayfa ≈ {tahmini_sayfa} sayfa) "
                        f"× {sayfa_basi_ucret} + {sabit_ucret:,}".replace(",", ".")
                    )
                toplam_ucret = (tahmini_sayfa * sayfa_basi_ucret) + sabit_ucret
                formatli_toplam_ucret = f"{toplam_ucret:,}".replace(",", ".")
                KitapMaliyetiHesaplamaKaydi.objects.create(
                    tur=secili_tur,
                    kelime_sayisi=None if sayfa_bazli else girilen_int,
                    sayfa_sayisi=girilen_int if sayfa_bazli else None,
                    toplam_ucret=toplam_ucret,
                )

    ornek_kelime_sayisi = 60000
    ornek_tur = next((t for t in turler if not t.sayfa_bazli and t.kelime_yogunlugu), None)
    if ornek_tur:
        ornek_tahmini_sayfa = math.ceil(ornek_kelime_sayisi / ornek_tur.kelime_yogunlugu)
        ornek_maliyet = (ornek_tahmini_sayfa * sayfa_basi_ucret) + sabit_ucret
    else:
        ornek_maliyet = sabit_ucret

    return render(
        request,
        "kitap_maliyeti_hesapla.html",
        {
            "kelime_sayisi": kelime_sayisi,
            "sayfa_sayisi": sayfa_sayisi,
            "turler": turler,
            "secili_tur_id": secili_tur_id,
            "sayfa_basi_ucret": sayfa_basi_ucret,
            "sabit_ucret": sabit_ucret,
            "sabit_ucret_formatli": f"{sabit_ucret:,}".replace(",", "."),
            "toplam_ucret": toplam_ucret,
            "formatli_toplam_ucret": formatli_toplam_ucret,
            "hesaplama_detayi": hesaplama_detayi,
            "form_hatasi": form_hatasi,
            "ornek_kelime_sayisi": ornek_kelime_sayisi,
            "ornek_tur_adi": ornek_tur.ad if ornek_tur else "",
            "ornek_maliyet_formatli": f"{ornek_maliyet:,}".replace(",", "."),
            **seo_context(
                "Kitap Basim Maliyeti Hesaplama | Tecrit Edebiyat",
                f"Kitap kelime sayinizi ve turunuzu girin, baski maliyetini hesaplayin. Formul: (tahmini sayfa sayisi x {sayfa_basi_ucret} TL) + {sabit_ucret} TL.",
                request.build_absolute_uri(),
            ),
        },
    )


def kayit(request):
    if request.method == "POST":
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            YazarProfil.objects.get_or_create(user=user)
            login(request, user)
            messages.success(request, "Hesabınız oluşturuldu. Yazar panelinize hoş geldiniz!")
            return redirect("yazar_paneli")
    else:
        form = UserCreationForm()
    return render(request, "kayit.html", {"form": form, **seo_context("Kayıt Ol", "Tecrit Edebiyat yazar veya okur hesabı oluşturma sayfası.")})


def giris(request):
    if request.method == "POST":
        username = request.POST.get("username", "")
        password = request.POST.get("password", "")
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            # Oturum gerektiren bir sayfadan gelindiyse oraya donulur (yalnizca site ici adresler)
            hedef = request.GET.get("next", "")
            if hedef and url_has_allowed_host_and_scheme(hedef, allowed_hosts={request.get_host()}, require_https=request.is_secure()):
                return redirect(hedef)
            return redirect("yazar_paneli")
        if giris_kilitli_mi(request, username):
            messages.error(request, "Çok fazla hatalı deneme yapıldı. Lütfen 15 dakika sonra tekrar deneyin.")
        else:
            messages.error(request, "Kullanıcı adı veya şifre hatalı.")
    return render(request, "giris.html", seo_context("Giriş Yap", "Tecrit Edebiyat hesabına giriş yapma sayfası."))


def sifremi_unuttum(request):
    if request.method == "POST":
        form = SifremiUnuttumForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data["email"]
            kullanicilar = User.objects.filter(email__iexact=email, is_active=True)
            for kullanici in kullanicilar:
                if not kullanici.has_usable_password():
                    continue
                uid = urlsafe_base64_encode(force_bytes(kullanici.pk))
                token = default_token_generator.make_token(kullanici)
                sifirlama_linki = request.build_absolute_uri(
                    reverse("sifre_sifirla", kwargs={"uidb64": uid, "token": token})
                )
                konu = "Tecrit Edebiyat - Şifre Sıfırlama"
                icerik = (
                    f"Merhaba {kullanici.get_full_name() or kullanici.username},\n\n"
                    "Tecrit Edebiyat hesabın için şifre sıfırlama talebinde bulundun.\n"
                    "Yeni şifreni belirlemek için aşağıdaki bağlantıya tıklayabilirsin:\n\n"
                    f"{sifirlama_linki}\n\n"
                    "Bu talebi sen yapmadıysan bu e-postayı görmezden gelebilirsin, "
                    "hesabında herhangi bir değişiklik yapılmayacaktır."
                )
                try:
                    email_message = EmailMessage(
                        subject=konu,
                        body=icerik,
                        from_email=getattr(settings, "DEFAULT_FROM_EMAIL", None) or settings.CONTACT_EMAIL,
                        to=[kullanici.email],
                    )
                    email_message.send(fail_silently=False)
                except Exception:
                    pass
            return redirect("sifremi_unuttum_gonderildi")
    else:
        form = SifremiUnuttumForm()
    return render(
        request,
        "sifremi_unuttum.html",
        {"form": form, **seo_context("Şifremi Unuttum", "Tecrit Edebiyat hesap şifresi sıfırlama talebi sayfası.")},
    )


def sifremi_unuttum_gonderildi(request):
    return render(
        request,
        "sifremi_unuttum_gonderildi.html",
        seo_context("E-posta Gönderildi", "Şifre sıfırlama bağlantısı e-posta adresine gönderildi."),
    )


def sifre_sifirla(request, uidb64, token):
    try:
        uid = urlsafe_base64_decode(uidb64).decode()
        kullanici = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        kullanici = None

    token_gecerli = kullanici is not None and default_token_generator.check_token(kullanici, token)

    form = None
    if token_gecerli:
        if request.method == "POST":
            form = SifreSifirlaForm(kullanici, request.POST)
            if form.is_valid():
                form.save()
                messages.success(request, "Şifren başarıyla güncellendi. Şimdi giriş yapabilirsin.")
                return redirect("giris")
        else:
            form = SifreSifirlaForm(kullanici)

    return render(
        request,
        "sifre_sifirla.html",
        {
            "form": form,
            "token_gecerli": token_gecerli,
            **seo_context("Şifre Sıfırla", "Tecrit Edebiyat hesabın için yeni şifre belirleme sayfası."),
        },
    )


def cikis(request):
    logout(request)
    return redirect("anasayfa")


# Yazar panelinde durum filtresi -> veritabani durumlari. "duzeltme" editorun geri cevirdigi yazilardir.
PANEL_DURUM_FILTRELERI = {
    "taslak": [BlogYazisi.DurumSecenekleri.TASLAK],
    "incelemede": [BlogYazisi.DurumSecenekleri.INCELEMEDE],
    "yayinda": [BlogYazisi.DurumSecenekleri.YAYINDA],
    "duzeltme": [BlogYazisi.DurumSecenekleri.DUZELTME, BlogYazisi.DurumSecenekleri.REDDEDILDI],
}
PANEL_SAYFA_BOYUTU = 10


def yazar_panel_ozeti(profil):
    """Yazarin yazi sayilari ve okunma toplami (tek sorgu)."""
    D = BlogYazisi.DurumSecenekleri
    sayilar = BlogYazisi.objects.filter(yazar=profil).aggregate(
        toplam=Count("id"),
        yayinda=Count("id", filter=Q(durum=D.YAYINDA)),
        taslak=Count("id", filter=Q(durum=D.TASLAK)),
        incelemede=Count("id", filter=Q(durum=D.INCELEMEDE)),
        duzeltme=Count("id", filter=Q(durum__in=PANEL_DURUM_FILTRELERI["duzeltme"])),
        okunma=Sum("okunma_sayisi", filter=Q(durum=D.YAYINDA)),
    )
    sayilar["okunma"] = sayilar["okunma"] or 0
    return sayilar


def yazar_alinti_ozeti(user):
    """Kullanicinin paylastigi alintilarin durum sayilari (tek sorgu)."""
    D = Alinti.DurumSecenekleri
    return Alinti.objects.filter(paylasan=user).aggregate(
        toplam=Count("id"),
        yayinda=Count("id", filter=Q(durum=D.YAYINDA)),
        taslak=Count("id", filter=Q(durum=D.TASLAK)),
        incelemede=Count("id", filter=Q(durum=D.INCELEMEDE)),
        duzeltme=Count("id", filter=Q(durum__in=PANEL_DURUM_FILTRELERI["duzeltme"])),
    )


def yazar_panel_karsilama(sayilar, kitap_sayisi, alinti_sayilari=None):
    """Karsilama alanindaki kisa durum ozeti; yalnizca gercek sayilardan cumle kurar."""
    alinti_sayilari = alinti_sayilari or {"toplam": 0, "duzeltme": 0, "incelemede": 0}
    if not sayilar["toplam"] and not alinti_sayilari["toplam"]:
        return ["Panelinize hoş geldiniz. İlk yazınızı ya da bir kitaptan alıntınızı gönderdiğinizde durumunu buradan takip edebilirsiniz."]
    cumleler = []
    if sayilar["duzeltme"]:
        cumleler.append(f"{sayilar['duzeltme']} yazınız için editörden geri bildirim var.")
    if alinti_sayilari["duzeltme"]:
        cumleler.append(f"{alinti_sayilari['duzeltme']} alıntınız için editörden geri bildirim var.")
    if alinti_sayilari["incelemede"]:
        cumleler.append(f"{alinti_sayilari['incelemede']} alıntınız editör incelemesinde.")
    if sayilar["incelemede"]:
        cumleler.append(f"{sayilar['incelemede']} yazınız editör incelemesinde.")
    if sayilar["taslak"]:
        cumleler.append(f"{sayilar['taslak']} taslağınız sizi bekliyor.")
    if not cumleler:
        cumleler.append("Bekleyen bir işiniz yok; gönderdikleriniz yayında.")
    if sayilar["okunma"]:
        cumleler.append(f"Yayındaki yazılarınız 15 Ekim 2026'dan bu yana {sayilar['okunma']} kez okundu.")
    if kitap_sayisi:
        cumleler.append(f"Yayınevimizde {kitap_sayisi} kitabınız yayında.")
    return cumleler


# Editorun durum degisikligi kaydi (islem_kaydet: "Durum: <ad>") -> yazara gosterilen metin, renk, ikon
GERI_BILDIRIM_METINLERI = {
    "Yayında": ("Yayına alındı", "success", "ph-check-circle"),
    "Düzeltme istendi": ("Düzeltme istendi", "danger", "ph-arrow-u-up-left"),
    "Reddedildi": ("Reddedildi", "danger", "ph-x-circle"),
    "İncelemede": ("İncelemeye alındı", "", "ph-hourglass-medium"),
    "Taslak": ("Taslağa çevrildi", "", "ph-note-pencil"),
}


def yazar_geri_bildirimleri(request, profil, adet=6):
    """Yazarin yazilari ve alintilari uzerinde baskalarinin (editorlerin) yaptigi islemler; LogEntry'den okunur."""
    kayitli = {}
    for y in BlogYazisi.objects.filter(yazar=profil).values("pk", "baslik", "durum", "admin_notu"):
        kayitli[("blogyazisi", str(y["pk"]))] = {
            **y, "url": reverse("yazar_panel_yazi_duzenle", args=[y["pk"]]), "tur": "Yazı",
        }
    for a in Alinti.objects.filter(paylasan=request.user).values("pk", "metin", "durum", "admin_notu", "kaynak__ad"):
        kayitli[("alinti", str(a["pk"]))] = {
            "pk": a["pk"], "baslik": a["kaynak__ad"] or a["metin"][:40], "durum": a["durum"], "admin_notu": a["admin_notu"],
            "url": reverse("yazar_panel_alinti_duzenle", args=[a["pk"]]), "tur": "Alıntı",
        }
    if not kayitli:
        return []
    kosul = Q()
    for model in ("blogyazisi", "alinti"):
        kimlikler = [k[1] for k in kayitli if k[0] == model]
        if kimlikler:
            kosul |= Q(content_type__model=model, object_id__in=kimlikler)
    kayitlar = (
        LogEntry.objects.filter(kosul, content_type__app_label="core", action_flag=CHANGE)
        .exclude(user=request.user)
        .select_related("content_type")
        .order_by("-action_time")[:adet]
    )
    sonuc = []
    gosterilen_not = set()
    for kayit in kayitlar:
        oge = kayitli[(kayit.content_type.model, kayit.object_id)]
        mesaj = kayit.get_change_message()
        if mesaj.startswith("Durum: "):
            metin, renk, ikon = GERI_BILDIRIM_METINLERI.get(mesaj[7:], (mesaj[7:], "", "ph-info"))
        elif mesaj == "Yazara not güncellendi":
            metin, renk, ikon = "Editör not bıraktı", "warning", "ph-chat-circle-text"
        else:
            metin, renk, ikon = f"Editör {oge['tur'].lower()}nızı düzenledi", "", "ph-pencil-simple"
        # Not, yalnizca icerik hala duzeltme/ret durumundaysa ve en yeni kaydinda gosterilir
        not_metni = ""
        anahtar = (kayit.content_type.model, oge["pk"])
        if (
            oge["admin_notu"]
            and oge["durum"] in PANEL_DURUM_FILTRELERI["duzeltme"]
            and renk in ("warning", "danger")
            and anahtar not in gosterilen_not
        ):
            not_metni = oge["admin_notu"]
            gosterilen_not.add(anahtar)
        sonuc.append({"oge": oge, "metin": metin, "renk": renk, "ikon": ikon, "zaman": kayit.action_time, "not": not_metni})
    return sonuc


@login_required(login_url="giris")
def yazar_paneli(request):
    profil = get_or_create_user_profile(request.user)
    sayilar = yazar_panel_ozeti(profil)
    kitap_sayisi = Kitap.objects.filter(Q(yazar=profil) | Q(ikinci_yazar=profil), yayinda=True).count()

    alinti_sayilari = yazar_alinti_ozeti(request.user)
    liste = "alintilar" if request.GET.get("liste") == "alintilar" else "yazilar"
    durum = request.GET.get("durum", "")
    if durum not in PANEL_DURUM_FILTRELERI:
        durum = ""
    if liste == "alintilar":
        kayitlar = (
            Alinti.objects.filter(paylasan=request.user)
            .select_related("kaynak__yazar")
            .order_by(F("updated_at").desc(nulls_last=True), "-id")
        )
        liste_sayilari = alinti_sayilari
    else:
        kayitlar = (
            BlogYazisi.objects.filter(yazar=profil)
            .select_related("kategori")
            .only("baslik", "slug", "durum", "kategori__ad", "okunma_sayisi", "admin_notu", "yayin_tarihi", "created_at", "updated_at")
            .order_by(F("updated_at").desc(nulls_last=True), "-id")
        )
        liste_sayilari = sayilar
    if durum:
        kayitlar = kayitlar.filter(durum__in=PANEL_DURUM_FILTRELERI[durum])
    page_obj, sayfa_sorgusu = sayfala(request, kayitlar, PANEL_SAYFA_BOYUTU)

    profil_eksikleri = [ad for ad, dolu in (("fotoğraf", profil.fotograf), ("biyografi", profil.biyografi.strip())) if not dolu]

    return render(
        request,
        "panel/dashboard.html",
        panel_baglami(
            request,
            profil,
            "panel",
            sayilar=liste_sayilari,
            yazi_toplam=sayilar["toplam"],
            alinti_toplam=alinti_sayilari["toplam"],
            liste=liste,
            liste_sorgusu="liste=alintilar&" if liste == "alintilar" else "",
            karsilama=yazar_panel_karsilama(sayilar, kitap_sayisi, alinti_sayilari),
            durum=durum,
            durum_sekmeleri=[
                ("", "Tümü", liste_sayilari["toplam"]),
                ("taslak", "Taslak", liste_sayilari["taslak"]),
                ("incelemede", "İncelemede", liste_sayilari["incelemede"]),
                ("yayinda", "Yayında", liste_sayilari["yayinda"]),
                ("duzeltme", "Düzeltme / ret", liste_sayilari["duzeltme"]),
            ],
            page_obj=page_obj,
            sayfa_sorgusu=sayfa_sorgusu,
            profil_eksikleri=profil_eksikleri,
            geri_bildirimler=yazar_geri_bildirimleri(request, profil),
        ),
    )


@login_required(login_url="giris")
def yazar_panel_profil(request):
    profil = get_or_create_user_profile(request.user)
    if request.method == "POST":
        eski_fotograf = profil.fotograf.name if profil.fotograf else ""
        user_form = PanelUserForm(request.POST, instance=request.user)
        profile_form = PanelProfileForm(request.POST, request.FILES, instance=profil)
        if user_form.is_valid() and profile_form.is_valid():
            user = user_form.save()
            profil_nesnesi = profile_form.save(commit=False)
            ad_soyad = " ".join(parca for parca in [user.first_name.strip(), user.last_name.strip()] if parca)
            profil_nesnesi.ad_soyad = ad_soyad or user.username
            profil_nesnesi.save()
            # Kaldirilan ya da degistirilen eski fotograf diskte yetim kalmasin
            yeni_fotograf = profil_nesnesi.fotograf.name if profil_nesnesi.fotograf else ""
            if eski_fotograf and eski_fotograf != yeni_fotograf:
                profil_nesnesi.fotograf.storage.delete(eski_fotograf)
            messages.success(request, "Profil bilgileriniz güncellendi.")
            return redirect("yazar_panel_profil")
        messages.error(request, "Profiliniz kaydedilmedi. Lütfen işaretli alanları düzeltin.")
        profil.refresh_from_db()
        request.user.refresh_from_db()
    else:
        user_form = PanelUserForm(instance=request.user)
        profile_form = PanelProfileForm(instance=profil)

    return render(
        request,
        "panel/profil.html",
        panel_baglami(request, profil, "profil", user_form=user_form, profile_form=profile_form),
    )


@login_required(login_url="giris")
def yazar_panel_sifre(request):
    profil = get_or_create_user_profile(request.user)
    if request.method == "POST":
        form = PanelPasswordForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)
            messages.success(request, "Şifreniz güncellendi.")
            return redirect("yazar_panel_sifre")
        messages.error(request, "Şifreniz değiştirilmedi. Lütfen işaretli alanları düzeltin.")
    else:
        form = PanelPasswordForm(request.user)

    return render(request, "panel/sifre.html", panel_baglami(request, profil, "guvenlik", form=form))


def medya_ozeti(medya):
    """Panelde medya karti icin JSON."""
    return {
        "id": medya.pk,
        "tur": medya.tur,
        "kaynak": medya.kaynak,
        "ad": str(medya),
        "boyut": medya.boyut_metni,
        "url": medya.dosya.url if medya.dosya else "",
        "mime": medya.mime,
        "saglayici": medya.get_saglayici_display() if medya.saglayici else "",
        "gomme": medya.gomme_adresi,
        "yukseklik": medya.gomme_yuksekligi,
    }


def medya_json_hatasi(mesaj, durum=400):
    return JsonResponse({"hata": mesaj}, status=durum)


# Yaziya baglanmamis yuklemeler icin ust sinir (toplu otomatik isteklere karsi; boyutu kota sinirlar)
BEKLEYEN_MEDYA_SINIRI = 30


def bekleyen_medya_siniri_asildi(user):
    return YaziMedyasi.objects.filter(yukleyen=user, yazi__isnull=True).count() >= BEKLEYEN_MEDYA_SINIRI


@login_required(login_url="giris")
@require_POST
def yazar_panel_medya_yukle(request):
    dosya = request.FILES.get("dosya")
    if not dosya:
        return medya_json_hatasi("Dosya alınamadı. Lütfen yeniden deneyin.")
    if bekleyen_medya_siniri_asildi(request.user):
        return medya_json_hatasi("Kaydedilmemiş çok fazla yükleme var. Önce yazınızı kaydedin.")
    try:
        tur, uzanti, mime = medya_kurallari.dosyayi_dogrula(dosya, request.POST.get("tur", ""))
    except MedyaHatasi as hata:
        return medya_json_hatasi(str(hata))
    kullanilan = YaziMedyasi.objects.filter(yukleyen=request.user).aggregate(t=Sum("boyut"))["t"] or 0
    if kullanilan + dosya.size > medya_kurallari.KULLANICI_KOTASI:
        return medya_json_hatasi(
            f"Yükleme alanınız doldu: toplam {medya_kurallari.KULLANICI_KOTASI // medya_kurallari.MB} MB'ın "
            f"{medya_kurallari.boyut_metni(kullanilan)} kadarını kullanıyorsunuz. Eski yazılarınızdan medya kaldırabilirsiniz."
        )
    medya = YaziMedyasi(
        yukleyen=request.user,
        tur=tur,
        kaynak=YaziMedyasi.Kaynak.DOSYA,
        orijinal_ad=os.path.basename(dosya.name)[:255],
        mime=mime,
        boyut=dosya.size,
    )
    # Diskteki ad sunucuda uretilir; kullanicinin dosya adi yalnizca gosterim icin saklanir
    medya.dosya.save(f"{uuid.uuid4().hex}.{uzanti}", dosya, save=False)
    medya.save()
    return JsonResponse(medya_ozeti(medya), status=201)


@login_required(login_url="giris")
@require_POST
def yazar_panel_medya_baglanti(request):
    if bekleyen_medya_siniri_asildi(request.user):
        return medya_json_hatasi("Kaydedilmemiş çok fazla medya var. Önce yazınızı kaydedin.")
    adres = request.POST.get("adres", "").strip()[:500]
    try:
        bilgi = medya_kurallari.baglantiyi_coz(adres)
    except MedyaHatasi as hata:
        return medya_json_hatasi(str(hata))
    medya = YaziMedyasi.objects.create(
        yukleyen=request.user,
        tur=bilgi["tur"],
        kaynak=YaziMedyasi.Kaynak.BAGLANTI,
        saglayici=bilgi["saglayici"],
        gomme_kimligi=bilgi["kimlik"],
        baglanti=medya_kurallari.kaynak_adresi(bilgi["saglayici"], bilgi["kimlik"]),
    )
    return JsonResponse(medya_ozeti(medya), status=201)


@login_required(login_url="giris")
@require_POST
def yazar_panel_medya_sil(request, pk):
    # Yalnizca henuz yaziya baglanmamis kendi yuklemesi; bagli medya yazi kaydedilirken kaldirilir
    medya = get_object_or_404(YaziMedyasi, pk=pk, yukleyen=request.user, yazi__isnull=True)
    medya.delete()
    return JsonResponse({"silindi": pk})


def yazi_medya_secimi(request, yazi):
    """Formdan gelen medya siralamasi: kullanicinin bekleyen yuklemeleri + bu yazinin mevcut medyasi."""
    kimlikler = []
    for deger in request.POST.getlist("medya"):
        if deger.isdigit() and int(deger) not in kimlikler:
            kimlikler.append(int(deger))
    uygun = Q(yazi__isnull=True, yukleyen=request.user)
    if yazi is not None and yazi.pk:
        uygun |= Q(yazi=yazi)
    bulunan = {m.pk: m for m in YaziMedyasi.objects.filter(uygun, pk__in=kimlikler)}
    secili = [bulunan[k] for k in kimlikler if k in bulunan]
    for medya in secili:
        medya.aciklama = request.POST.get(f"medya_aciklama_{medya.pk}", "").strip()[: medya_kurallari.ACIKLAMA_SINIRI]
    return secili


def yazi_medyasini_kaydet(yazi, secili):
    with transaction.atomic():
        for sira, medya in enumerate(secili):
            medya.yazi = yazi
            medya.sira = sira
            medya.save(update_fields=["yazi", "sira", "aciklama"])
        for kaldirilan in yazi.medyalar.exclude(pk__in=[m.pk for m in secili]):
            kaldirilan.delete()


YAZI_BASINA_ALINTI = 10


def yazi_alinti_secimi(request, yazi):
    """Formda isaretlenen alintilar: yalnizca kullanicinin kendi alintilari (+ yazida zaten bulunanlar)."""
    kimlikler = {int(d) for d in request.POST.getlist("alintilar") if d.isdigit()}
    uygun = Q(paylasan=request.user)
    if yazi is not None and yazi.pk:
        uygun |= Q(yazilar=yazi)
    return list(Alinti.objects.filter(uygun, pk__in=kimlikler).distinct())


def yazar_alinti_secenekleri(request, yazi):
    """Yazi formunda iliştirilebilecek alintilar: kullanicinin reddedilmemis alintilari ve yazida bulunanlar."""
    uygun = Q(paylasan=request.user) & ~Q(durum=Alinti.DurumSecenekleri.REDDEDILDI)
    if yazi is not None and yazi.pk:
        uygun |= Q(yazilar=yazi)
    return list(
        Alinti.objects.filter(uygun).select_related("kaynak__yazar").distinct().order_by(F("updated_at").desc(nulls_last=True), "-id")[:60]
    )


def yazar_yazi_formu(request, profil, yazi=None):
    """Yeni yazi ve duzenleme ortak akisi.

    Yazar: "Taslak olarak kaydet" (islem=taslak) ya da "Incelemeye gonder"; yazi hicbir zaman dogrudan
    yayina cikmaz. Yayindaki bir yazi duzenlenirse yeniden incelemeye gider ama ilk yayin tarihi korunur.
    Yonetici: durumu formdan secer.
    """
    D = BlogYazisi.DurumSecenekleri
    is_superadmin = panel_yoneticisi_mi(request.user, profil)
    yeni_mi = yazi is None
    onceki_durum = None if yeni_mi else yazi.durum

    if request.method == "POST":
        mevcut_gorsel = yazi.gorsel if yazi and yazi.gorsel else None
        gorsel_temizle = request.POST.get("gorsel-clear") == "on"
        yeni_gorsel = request.FILES.get("gorsel")
        post_data = request.POST.copy()
        taslak_mi = request.POST.get("islem") == "taslak"
        if not is_superadmin:
            post_data["durum"] = D.TASLAK if taslak_mi else D.INCELEMEDE

        form = PanelBlogYazisiForm(post_data, request.FILES, instance=yazi, is_superadmin=is_superadmin, panel_gorunumu=True)
        medya_listesi = yazi_medya_secimi(request, yazi)
        alinti_listesi = yazi_alinti_secimi(request, yazi)
        gecerli = form.is_valid()
        if len(alinti_listesi) > YAZI_BASINA_ALINTI:
            form.add_error(None, f"Bir yazıya en fazla {YAZI_BASINA_ALINTI} alıntı ekleyebilirsiniz.")
            gecerli = False
        if len(medya_listesi) > medya_kurallari.YAZI_BASINA_MEDYA:
            form.add_error(None, f"Bir yazıya en fazla {medya_kurallari.YAZI_BASINA_MEDYA} ses ya da video ekleyebilirsiniz.")
            gecerli = False
        if gecerli:
            yazi = form.save(commit=False)
            if gorsel_temizle and not yeni_gorsel:
                if mevcut_gorsel:
                    mevcut_gorsel.delete(save=False)
                yazi.gorsel = None
            elif yeni_gorsel and mevcut_gorsel and mevcut_gorsel.name != yazi.gorsel.name:
                mevcut_gorsel.delete(save=False)

            yazi.yazar = profil
            if is_superadmin:
                if yazi.durum == D.YAYINDA and not yazi.onaylayan:
                    yazi.onaylayan = request.user
            else:
                yazi.durum = D.TASLAK if taslak_mi else D.INCELEMEDE
                yazi.onaylayan = None
            yazi.save()
            form.save_m2m()
            yazi_medyasini_kaydet(yazi, medya_listesi)
            yazi.alintilar.set(alinti_listesi)
            islem_kaydet(
                request,
                yazi,
                ADDITION if yeni_mi else CHANGE,
                f"Yazar panelinden {'eklendi' if yeni_mi else 'güncellendi'} ({yazi.get_durum_display()})",
            )

            if is_superadmin:
                messages.success(request, "Yazınız yayında." if yazi.durum == D.YAYINDA else "Yazınız kaydedildi.")
                return redirect("yazar_paneli")
            if taslak_mi:
                messages.success(request, "Taslağınız kaydedildi. Hazır olduğunuzda incelemeye gönderebilirsiniz.")
                return redirect("yazar_panel_yazi_duzenle", pk=yazi.pk)
            if onceki_durum == D.YAYINDA:
                messages.success(request, "Değişiklikleriniz kaydedildi. Yazınız editör onayından sonra yeniden yayımlanacak.")
            else:
                messages.success(request, "Yazınız editör onayına gönderildi. Sonucu panelinizden takip edebilirsiniz.")
            return redirect("yazar_paneli")
        messages.error(request, "Yazınız kaydedilmedi. Lütfen işaretli alanları düzeltin.")
    else:
        form = PanelBlogYazisiForm(instance=yazi, is_superadmin=is_superadmin, panel_gorunumu=True)
        medya_listesi = list(yazi.medyalar.all()) if yazi else []
        alinti_listesi = list(yazi.alintilar.all()) if yazi else []

    if yazi is not None and request.method == "POST":
        # Gecersiz gonderimde form, nesneyi kaydedilmemis degerlerle doldurur; sayfada kayitli hali gosterilir
        yazi = BlogYazisi.objects.get(pk=yazi.pk)

    return render(
        request,
        "panel/yazi_form.html",
        panel_baglami(
            request,
            profil,
            "yazi" if yeni_mi else "panel",
            form=form,
            yazi=yazi,
            onceki_durum=onceki_durum,
            is_superadmin=is_superadmin,
            medya_listesi=medya_listesi,
            medya_kurallari=medya_kurallari,
            alinti_secenekleri=yazar_alinti_secenekleri(request, yazi),
            secili_alintilar={a.pk for a in alinti_listesi},
            yazi_basina_alinti=YAZI_BASINA_ALINTI,
        ),
    )


@login_required(login_url="giris")
def yazar_panel_yeni_yazi(request):
    return yazar_yazi_formu(request, get_or_create_user_profile(request.user))


@login_required(login_url="giris")
def yazar_panel_yazi_duzenle(request, pk):
    profil = get_or_create_user_profile(request.user)
    yazi = get_object_or_404(BlogYazisi, pk=pk, yazar=profil)
    return yazar_yazi_formu(request, profil, yazi)


@login_required(login_url="giris")
def yazar_panel_yazi_sil(request, pk):
    profil = get_or_create_user_profile(request.user)
    yazi = get_object_or_404(BlogYazisi, pk=pk, yazar=profil)

    if request.method == "POST":
        yazi_baslik = yazi.baslik
        with transaction.atomic():
            islem_kaydet(request, yazi, DELETION, "Yazar panelinden silindi")
            yazi.delete()
        messages.success(request, f"“{yazi_baslik}” yazınız silindi.")
        return redirect("yazar_paneli")

    return redirect("yazar_panel_yazi_duzenle", pk=pk)


# ---------- Yazar paneli: alintilar ----------

@login_required(login_url="giris")
def yazar_panel_kitap_ara(request):
    """Alinti formundaki kitap/yazar onerileri (JSON). Yalnizca onayli kitaplar ve kullanicinin ekledikleri."""
    from .kaynak import normal_anahtar

    sorgu = normal_anahtar(request.GET.get("q", ""))[:100]
    if len(sorgu) < 2:
        return JsonResponse({"kitaplar": [], "yazarlar": []})
    if request.GET.get("tur") == "yazar":
        yazarlar = (
            KaynakYazar.objects.filter(ad_normal__contains=sorgu)
            .filter(Q(kitaplar__onayli=True) | Q(kitaplar__ekleyen=request.user))
            .distinct()
            .order_by("ad")[:20]
        )
        sirali = sorted(yazarlar, key=lambda y: (not y.ad_normal.startswith(sorgu), y.ad_normal))[:8]
        return JsonResponse({"kitaplar": [], "yazarlar": [{"ad": y.ad} for y in sirali]})
    adaylar = (
        yazarin_gorebildigi_kitaplar(request.user)
        .filter(Q(ad_normal__contains=sorgu) | Q(yazar__ad_normal__contains=sorgu))
        .select_related("yazar", "katalog_kitabi")
        .order_by("ad")[:30]
    )
    sirali = sorted(adaylar, key=lambda k: (not k.ad_normal.startswith(sorgu), not k.yazar.ad_normal.startswith(sorgu), k.ad_normal))[:8]
    return JsonResponse(
        {
            "kitaplar": [
                {
                    "id": k.pk,
                    "ad": k.ad,
                    "yazar": k.yazar.ad,
                    "kunye": " · ".join(str(p) for p in [k.yayinevi, k.basim_yili] if p),
                    "kapak": k.kapak_url,
                    "onay_bekliyor": not k.onayli,
                }
                for k in sirali
            ],
            "yazarlar": [],
        }
    )


def yazar_alinti_formu(request, profil, alinti=None):
    """Yeni alinti ve duzenleme. Yazar: taslak ya da incelemeye gonder; yonetici dogrudan yayinlayabilir."""
    D = Alinti.DurumSecenekleri
    yonetici = panel_yoneticisi_mi(request.user, profil)
    yeni_mi = alinti is None
    onceki_durum = None if yeni_mi else alinti.durum

    if request.method == "POST":
        form = PanelAlintiForm(request.POST, request.FILES, instance=alinti, user=request.user)
        if form.is_valid():
            islem = request.POST.get("islem")
            with transaction.atomic():
                kaynak = form.kaynak_kitabi_hazirla()
                alinti = form.save(commit=False)
                alinti.kaynak = kaynak
                alinti.paylasan = request.user
                if islem == "taslak":
                    alinti.durum = D.TASLAK
                elif yonetici and islem == "yayinla":
                    alinti.durum = D.YAYINDA
                    alinti.onaylayan = request.user
                else:
                    alinti.durum = D.INCELEMEDE
                if alinti.durum != D.YAYINDA:
                    alinti.onaylayan = None
                alinti.save()
                form.save_m2m()
                islem_kaydet(
                    request, alinti, ADDITION if yeni_mi else CHANGE,
                    f"Yazar panelinden {'eklendi' if yeni_mi else 'güncellendi'} ({alinti.get_durum_display()})",
                )
            if form.mevcut_kitap_kullanildi:
                messages.info(request, f"“{kaynak}” zaten kayıtlıydı; alıntınız bu kitaba eklendi.")
            if alinti.durum == D.TASLAK:
                messages.success(request, "Alıntınız taslak olarak kaydedildi.")
                return redirect("yazar_panel_alinti_duzenle", pk=alinti.pk)
            if alinti.durum == D.YAYINDA:
                messages.success(request, "Alıntınız yayında.")
            elif onceki_durum == D.YAYINDA:
                messages.success(request, "Değişiklikleriniz kaydedildi. Alıntınız editör onayından sonra yeniden yayımlanacak.")
            else:
                messages.success(request, "Alıntınız editör onayına gönderildi.")
            return redirect(f"{reverse('yazar_paneli')}?liste=alintilar#yazilarim")
        messages.error(request, "Alıntınız kaydedilmedi. Lütfen işaretli alanları düzeltin.")
        if alinti is not None:
            alinti = Alinti.objects.select_related("kaynak__yazar").get(pk=alinti.pk)
    else:
        form = PanelAlintiForm(instance=alinti, user=request.user)

    # Formda gosterilecek secili kitap (gecersiz gonderimde de korunur)
    secili_kitap = None
    kaynak_id = form["kaynak_id"].value()
    if kaynak_id and str(kaynak_id).isdigit():
        secili_kitap = yazarin_gorebildigi_kitaplar(request.user).select_related("yazar").filter(pk=int(kaynak_id)).first()

    return render(
        request,
        "panel/alinti_form.html",
        panel_baglami(
            request,
            profil,
            "alinti" if yeni_mi else "panel",
            form=form,
            alinti=alinti,
            secili_kitap=secili_kitap,
            yonetici=yonetici,
            alinti_siniri=ALINTI_SINIRI,
        ),
    )


@login_required(login_url="giris")
def yazar_panel_yeni_alinti(request):
    return yazar_alinti_formu(request, get_or_create_user_profile(request.user))


@login_required(login_url="giris")
def yazar_panel_alinti_duzenle(request, pk):
    alinti = get_object_or_404(Alinti.objects.select_related("kaynak__yazar"), pk=pk, paylasan=request.user)
    return yazar_alinti_formu(request, get_or_create_user_profile(request.user), alinti)


@login_required(login_url="giris")
@require_POST
def yazar_panel_alinti_sil(request, pk):
    alinti = get_object_or_404(Alinti, pk=pk, paylasan=request.user)
    with transaction.atomic():
        islem_kaydet(request, alinti, DELETION, "Yazar panelinden silindi")
        alinti.delete()
    messages.success(request, "Alıntınız silindi.")
    return redirect(f"{reverse('yazar_paneli')}?liste=alintilar#yazilarim")
