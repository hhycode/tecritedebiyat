from django.contrib import admin
from django.contrib import messages
from django.contrib.admin.models import LogEntry
from django.contrib.auth.models import Group, User
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.tokens import default_token_generator
from django.conf import settings
from django.core.mail import EmailMessage
from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.db.models.deletion import ProtectedError
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import NoReverseMatch, reverse, reverse_lazy
from django.utils import timezone
from django.utils.encoding import force_bytes
from django.utils.html import strip_tags
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from functools import wraps
import mimetypes
import os
import math
from urllib.parse import urlencode

from .forms import (
    ContactForm,
    PanelBlogYazisiForm,
    PanelPasswordForm,
    PanelProfileForm,
    PanelUserForm,
    SifremiUnuttumForm,
    SifreSifirlaForm,
    SuperadminAlintiForm,
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
    Alinti,
    AlintiKategori,
    AnaSayfaYayinKarti,
    BlogKategori,
    BlogReklam,
    BlogUrun,
    BlogYazisi,
    Etiket,
    IletisimBasvurusu,
    Kitap,
    KitapMaliyetiAyarlari,
    KitapMaliyetiHesaplamaKaydi,
    KitapMaliyetTuru,
    KitapTur,
    Slider,
    SSS,
    YazarProfil,
)


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
    },
    "alintikategori": {
        "model": AlintiKategori,
        "form_class": SuperadminAlintiKategoriForm,
        "title": "Alıntı Kategorileri",
        "singular": "Alıntı kategorisi",
        "list_headers": ["Ad", "Slug"],
        "list_values": lambda obj: [obj.ad, obj.slug or "-"],
        "full_width_fields": {"ad", "slug"},
    },
    "sss": {
        "model": SSS,
        "form_class": SuperadminSSSForm,
        "title": "Sık Sorulan Sorular",
        "singular": "SSS",
        "list_headers": ["Soru", "Sıra", "Aktif"],
        "list_values": lambda obj: [obj.soru, obj.sira, "Evet" if obj.aktif else "Hayır"],
        "full_width_fields": {"soru", "cevap"},
    },
    "alinti": {
        "model": Alinti,
        "form_class": SuperadminAlintiForm,
        "title": "Alıntılar",
        "singular": "Alıntı",
        "list_headers": ["Kitap", "Kategori", "Sayfa", "Yayında"],
        "list_values": lambda obj: [obj.kitap.ad, obj.kategori.ad if obj.kategori else "-", obj.sayfa_no or "-", "Evet" if obj.yayinda else "Hayır"],
        "full_width_fields": {"metin", "etiketler_input"},
    },
    "blogkategori": {
        "model": BlogKategori,
        "form_class": SuperadminBlogKategoriForm,
        "title": "Blog Kategorileri",
        "singular": "Blog kategorisi",
        "list_headers": ["Ad", "Slug"],
        "list_values": lambda obj: [obj.ad, obj.slug or "-"],
        "full_width_fields": {"ad", "slug"},
    },
    "blogreklam": {
        "model": BlogReklam,
        "form_class": SuperadminBlogReklamForm,
        "title": "Blog Reklamları",
        "singular": "Blog reklamı",
        "list_headers": ["İsim", "Sponsor Etiketi", "Aktif", "Sıra"],
        "list_values": lambda obj: [obj.isim, obj.sponsor_etiketi, "Evet" if obj.aktif else "Hayır", obj.sira],
        "full_width_fields": {"isim", "sponsor_etiketi", "link", "resim"},
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
    },
    "kitaptur": {
        "model": KitapTur,
        "form_class": SuperadminKitapTurForm,
        "title": "Kitap Kategorileri",
        "singular": "Kitap kategorisi",
        "list_headers": ["Ad", "Slug"],
        "list_values": lambda obj: [obj.ad, obj.slug or "-"],
        "full_width_fields": {"ad", "slug", "aciklama"},
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
    },
    "kitap": {
        "model": Kitap,
        "form_class": SuperadminKitapForm,
        "title": "Kitaplar",
        "singular": "Kitap",
        "list_headers": ["Ad", "Yazar", "Yayın Tarihi", "Yayında"],
        "list_values": lambda obj: [obj.ad, obj.yazar_adi, obj.yayin_tarihi.strftime("%d.%m.%Y") if obj.yayin_tarihi else "-", "Evet" if obj.yayinda else "Hayır"],
        "full_width_fields": {"ad", "slug", "aciklama", "kapak_resmi", "meta_title", "meta_description", "kitapyurdu_link", "dr_link", "trendyol_link", "shopier_link", "etiketler_input"},
    },
    "slider": {
        "model": Slider,
        "form_class": SuperadminSliderForm,
        "title": "Sliderlar",
        "singular": "Slider",
        "list_headers": ["Başlık", "Sıra", "Aktif", "Link"],
        "list_values": lambda obj: [obj.baslik, obj.sira, "Evet" if obj.aktif else "Hayır", obj.link or "-"],
        "full_width_fields": {"baslik", "aciklama", "gorsel", "link"},
    },
    "yazarprofil": {
        "model": YazarProfil,
        "form_class": SuperadminYazarProfilForm,
        "title": "Yazar Profilleri",
        "singular": "Yazar profili",
        "list_headers": ["Ad Soyad", "Rol", "Onaylı", "Kullanıcı"],
        "list_values": lambda obj: [obj.ad_soyad, obj.get_rol_display(), "Evet" if obj.onayli else "Hayır", obj.user.username if obj.user else "-"],
        "full_width_fields": {"ad_soyad", "slug", "biyografi", "fotograf", "instagram", "x_hesabi", "websitesi"},
    },
}


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


def superadmin_required(view_func):
    @wraps(view_func)
    @login_required(login_url=reverse_lazy("admin:login"))
    def _wrapped(request, *args, **kwargs):
        profil = get_or_create_user_profile(request.user)
        if not (request.user.is_superuser or profil.rol == YazarProfil.RolSecenekleri.SUPERADMIN):
            messages.error(request, "Bu alana sadece süper admin erişebilir.")
            return redirect("yazar_paneli")

        request.superadmin_profil = profil
        return view_func(request, *args, **kwargs)

    return _wrapped


def build_superadmin_context(request):
    pending_posts = list(
        BlogYazisi.objects.select_related("yazar", "kategori")
        .prefetch_related("kategoriler")
        .filter(durum=BlogYazisi.DurumSecenekleri.INCELEMEDE)
        .order_by("-created_at")[:6]
    )
    unread_contacts = list(
        IletisimBasvurusu.objects.filter(incelendi=False).order_by("-created_at")[:6]
    )
    recent_logs = list(
        LogEntry.objects.select_related("content_type", "user").order_by("-action_time")[:8]
    )
    model_groups = [
        (
            "Kimlik Doğrulama ve Yetkilendirme",
            [
                ("Gruplar", "auth", "group"),
                ("Kullanıcılar", "auth", "user"),
            ],
        ),
        (
            "Yönetici Arayüzü",
            [
                ("Temalar", "admin_interface", "theme"),
            ],
        ),
    ]
    admin_modules = []
    for group_name, items in model_groups:
        models = []
        for label, app_label, model_name in items:
            if app_label == "core" and model_name in CONTENT_MODEL_CONFIG:
                admin_url = reverse("superadmin_icerik_model_liste", args=[model_name])
                add_url = reverse("superadmin_icerik_model_yeni", args=[model_name])
            elif app_label == "core" and model_name == "iletisimbasvurusu":
                admin_url = reverse("superadmin_iletisim")
                add_url = ""
            elif app_label == "auth" and model_name == "user":
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
            models.append(
                {
                    "name": label,
                    "model_name": model_name,
                    "admin_url": admin_url,
                    "add_url": add_url,
                }
            )
        admin_modules.append({"name": group_name, "models": models})
    pending_post_count = BlogYazisi.objects.filter(durum=BlogYazisi.DurumSecenekleri.INCELEMEDE).count()
    unread_contact_count = IletisimBasvurusu.objects.filter(incelendi=False).count()
    return {
        "profil": request.superadmin_profil,
        "app_list": admin_modules,
        "admin_pending_posts": pending_posts,
        "admin_unread_contacts": unread_contacts,
        "admin_recent_logs": recent_logs,
        "admin_pending_post_count": pending_post_count,
        "admin_unread_contact_count": unread_contact_count,
        "admin_notification_count": pending_post_count + unread_contact_count,
        "admin_total_books": Kitap.objects.count(),
        "admin_total_quotes": Alinti.objects.count(),
        "admin_total_authors": YazarProfil.objects.count(),
        "admin_total_posts": BlogYazisi.objects.count(),
    }


@superadmin_required
def superadmin_dashboard(request):
    context = build_superadmin_context(request)
    context["page_title"] = "Kontrol Paneli"
    return render(request, "superadmin/dashboard.html", context)


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
        yazilar = yazilar.filter(Q(baslik__icontains=arama) | Q(yazar__ad_soyad__icontains=arama))
    context = build_superadmin_context(request)
    context.update(
        {
            "page_title": "Yazılar",
            "yazilar": yazilar[:50],
            "secili_durum": durum,
            "arama": arama,
            "durumler": BlogYazisi.DurumSecenekleri.choices,
        }
    )
    return render(request, "superadmin/posts.html", context)


@superadmin_required
def superadmin_yazi_detay(request, pk):
    yazi = get_object_or_404(
        BlogYazisi.objects.select_related("yazar", "kategori", "onaylayan").prefetch_related("kategoriler"),
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
        if yeni_durum in dict(BlogYazisi.DurumSecenekleri.choices):
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
            messages.success(request, f'"{yazi.baslik}" için durum güncellendi.')
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
        basvurular = basvurular.filter(
            Q(ad__icontains=arama)
            | Q(soyad__icontains=arama)
            | Q(email__icontains=arama)
            | Q(mesaj__icontains=arama)
        )
    context = build_superadmin_context(request)
    context.update(
        {
            "page_title": "İletişim Başvuruları",
            "basvurular": basvurular[:50],
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
            "item_title": f"{basvuru.ad} {basvuru.soyad}",
            "cancel_url": reverse("superadmin_iletisim_detay", args=[basvuru.pk]),
            "confirm_message": "Bu iletişim başvurusunu kalıcı olarak silmek üzeresin. Bu işlem geri alınamaz.",
        }
    )
    return render(request, "superadmin/contact_confirm_delete.html", context)


@superadmin_required
def superadmin_iletisim_durum_guncelle(request, pk):
    basvuru = get_object_or_404(IletisimBasvurusu, pk=pk)
    if request.method == "POST":
        basvuru.incelendi = request.POST.get("incelendi") == "1"
        basvuru.save(update_fields=["incelendi"])
        messages.success(request, "Başvuru durumu güncellendi.")
    return redirect("superadmin_iletisim")


@superadmin_required
def superadmin_yazarlar(request):
    yazarlar = YazarProfil.objects.select_related("user").order_by("ad_soyad")
    context = build_superadmin_context(request)
    context.update({"page_title": "Yazarlar", "yazarlar": yazarlar[:50]})
    return render(request, "superadmin/authors.html", context)


@superadmin_required
def superadmin_kitaplar(request):
    kitaplar = Kitap.objects.select_related("yazar").order_by("-created_at")
    context = build_superadmin_context(request)
    context.update({"page_title": "Kitaplar", "kitaplar": kitaplar[:50]})
    return render(request, "superadmin/books.html", context)


@superadmin_required
def superadmin_kitap_maliyeti_ayarlari(request):
    ayarlar = KitapMaliyetiAyarlari.get_ayarlar()
    if request.method == "POST":
        form = SuperadminKitapMaliyetiForm(request.POST, instance=ayarlar)
        if form.is_valid():
            form.save()
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
        messages.success(request, "Kullanım istatistiği sıfırlandı.")
        return redirect("superadmin_kitap_maliyeti_ayarlari")

    context = build_superadmin_context(request)
    context.update(
        {
            "page_title": "Kullanım İstatistiğini Sıfırla",
            "item_title": "Kullanım İstatistiğini Sıfırla",
            "cancel_url": reverse("superadmin_kitap_maliyeti_ayarlari"),
            "confirm_message": (
                "Kitap maliyeti hesaplama aracının toplam kullanım sayısını ve tür dağılımını "
                "kalıcı olarak sıfırlamak üzeresin. Bu işlem geri alınamaz."
            ),
        }
    )
    return render(request, "superadmin/kitap_maliyeti_istatistik_sifirla.html", context)


@superadmin_required
def superadmin_icerik_yonetimi(request):
    context = build_superadmin_context(request)
    context.update({"page_title": "İçerik Yönetimi"})
    return render(request, "superadmin/content_management.html", context)


def build_content_form_kwargs(request, config):
    extra = config.get("form_kwargs")
    return extra(request) if callable(extra) else {}


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

    queryset = config["model"].objects.all().order_by("-pk")
    context = build_superadmin_context(request)
    context.update(
        {
            "page_title": config["title"],
            "content_config": config,
            "content_headers": config["list_headers"],
            "content_rows": build_content_rows(queryset[:100], config),
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
            messages.success(request, f"{config['singular'].capitalize()} oluşturuldu.")
            return redirect("superadmin_icerik_model_duzenle", model_key=model_key, pk=nesne.pk)
    else:
        form = form_class(**form_kwargs)

    context = build_superadmin_context(request)
    context.update(
        {
            "page_title": f"{config['singular'].capitalize()} ekle",
            "content_config": config,
            "model_key": model_key,
            "form": form,
            "form_title": f"{config['singular'].capitalize()} ekle",
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
            messages.success(request, f"{config['singular'].capitalize()} güncellendi.")
            return redirect("superadmin_icerik_model_duzenle", model_key=model_key, pk=nesne.pk)
    else:
        form = form_class(instance=nesne, **form_kwargs)

    context = build_superadmin_context(request)
    context.update(
        {
            "page_title": f"{config['singular'].capitalize()} düzenle",
            "content_config": config,
            "model_key": model_key,
            "object": nesne,
            "form": form,
            "form_title": f"{config['singular'].capitalize()} düzenle",
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
            nesne.delete()
            messages.success(request, f"{config['singular'].capitalize()} silindi: {nesne_etiketi}")
            return redirect(back_url)
        except ProtectedError:
            messages.error(request, "Bu kayıt başka içeriklerle bağlantılı olduğu için silinemiyor.")
        except Exception:
            messages.error(request, "Kayıt silinirken beklenmeyen bir hata oluştu.")
        return redirect("superadmin_icerik_model_duzenle", model_key=model_key, pk=pk)

    context = build_superadmin_context(request)
    context.update(
        {
            "page_title": f"{config['singular'].capitalize()} sil",
            "content_config": config,
            "model_key": model_key,
            "object": nesne,
            "back_url": back_url,
            "confirm_title": f"{config['singular'].capitalize()} sil",
            "confirm_message": f"'{nesne}' kaydını kalıcı olarak silmek üzeresin. Bu işlem geri alınamaz.",
        }
    )
    return render(request, "superadmin/content_model_confirm_delete.html", context)


@superadmin_required
def superadmin_kullanicilar(request):
    context = build_superadmin_context(request)
    context.update(
        {
            "page_title": "Kullanıcılar",
            "kullanicilar": User.objects.order_by("username"),
        }
    )
    return render(request, "superadmin/users.html", context)


@superadmin_required
def superadmin_kullanici_yeni(request):
    if request.method == "POST":
        form = SuperadminKullaniciForm(request.POST)
        if form.is_valid():
            kullanici = form.save(commit=False)
            kullanici.set_unusable_password()
            kullanici.save()
            messages.success(request, "Kullanıcı oluşturuldu. Şimdi şifresini belirle.")
            return redirect("superadmin_kullanici_sifre", pk=kullanici.pk)
    else:
        form = SuperadminKullaniciForm()

    context = build_superadmin_context(request)
    context.update(
        {
            "page_title": "Kullanıcı ekle",
            "form": form,
            "form_title": "Yeni kullanıcı",
            "submit_label": "Kaydet ve şifre belirle",
            "back_url": reverse("superadmin_kullanicilar"),
        }
    )
    return render(request, "superadmin/user_form.html", context)


@superadmin_required
def superadmin_kullanici_duzenle(request, pk):
    kullanici = get_object_or_404(User, pk=pk)
    if request.method == "POST":
        form = SuperadminKullaniciForm(request.POST, instance=kullanici)
        if form.is_valid():
            kendi_hesabi = kullanici.pk == request.user.pk
            erisim_kisitlaniyor = not form.cleaned_data["is_active"] or not form.cleaned_data["is_staff"]
            if kendi_hesabi and erisim_kisitlaniyor:
                messages.error(request, "Kendi hesabının erişimini bu ekrandan kısıtlayamazsın.")
            else:
                form.save()
                messages.success(request, "Kullanıcı güncellendi.")
            return redirect("superadmin_kullanici_duzenle", pk=pk)
    else:
        form = SuperadminKullaniciForm(instance=kullanici)

    context = build_superadmin_context(request)
    context.update(
        {
            "page_title": "Kullanıcı düzenle",
            "object": kullanici,
            "form": form,
            "form_title": f"{kullanici.username} düzenle",
            "submit_label": "Değişiklikleri Kaydet",
            "back_url": reverse("superadmin_kullanicilar"),
        }
    )
    return render(request, "superadmin/user_form.html", context)


@superadmin_required
def superadmin_kullanici_sifre(request, pk):
    kullanici = get_object_or_404(User, pk=pk)
    if request.method == "POST":
        form = SuperadminKullaniciSifreForm(request.POST)
        if form.is_valid():
            kullanici.set_password(form.cleaned_data["yeni_sifre1"])
            kullanici.save(update_fields=["password"])
            if kullanici.pk == request.user.pk:
                update_session_auth_hash(request, kullanici)
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


def build_panel_stats(profil):
    yazi_listesi = (
        BlogYazisi.objects.select_related("kategori")
        .prefetch_related("kategoriler")
        .filter(yazar=profil)
        .order_by("-yayin_tarihi", "-created_at")
    )
    kategori_dagilimi = list(
        yazi_listesi.exclude(kategori__isnull=True)
        .values("kategori__ad")
        .annotate(sayi=Count("id"))
        .order_by("-sayi", "kategori__ad")[:6]
    )
    return {
        "toplam_yazi": yazi_listesi.count(),
        "yayindaki_yazi": yazi_listesi.filter(durum=BlogYazisi.DurumSecenekleri.YAYINDA).count(),
        "incelemedeki_yazi": yazi_listesi.filter(durum=BlogYazisi.DurumSecenekleri.INCELEMEDE).count(),
        "kitap_sayisi": Kitap.objects.filter(Q(yazar=profil) | Q(ikinci_yazar=profil), yayinda=True).count(),
        "taslak_yazi": yazi_listesi.filter(durum=BlogYazisi.DurumSecenekleri.TASLAK).count(),
        "son_yazilar": yazi_listesi[:5],
        "tum_yazilar": yazi_listesi[:20],
        "kategori_dagilimi": kategori_dagilimi,
        "toplam_kategori_yazi": sum(item["sayi"] for item in kategori_dagilimi) or 1,
    }


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
    one_cikan_alintilar = list(
        Alinti.objects.select_related("kitap", "kitap__yazar__user")
        .filter(yayinda=True)
        .order_by("-created_at")[:6]
    )
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
            "yazar": alinti.kitap.yazar_adi,
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
        Kitap.objects.select_related("yazar__user").prefetch_related("turler", "alintilar"),
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
    context = {
        "kitap": kitap,
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
        YazarProfil.objects.select_related("user")
        .prefetch_related("kitaplar", "ikinci_yazar_kitaplar", "blog_yazilari")
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


def blog_detay(request, slug):
    yazi = get_object_or_404(
        BlogYazisi.objects.select_related("yazar__user", "kategori").prefetch_related("kategoriler"),
        slug=slug,
        durum=BlogYazisi.DurumSecenekleri.YAYINDA,
    )
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


def alintilar(request):
    alinti_listesi = (
        Alinti.objects.select_related("kitap", "kategori", "kitap__yazar__user")
        .prefetch_related("etiketler")
        .filter(yayinda=True)
        .order_by("-created_at")
    )
    sayfa_nesnesi = Paginator(alinti_listesi, 12).get_page(request.GET.get("sayfa"))

    return render(
        request,
        "alintilar.html",
        {
            "alintilar": alinti_listesi,
            "sayfa_nesnesi": sayfa_nesnesi,
            "sayfalandirildi_mi": sayfa_nesnesi.paginator.num_pages > 1,
            **seo_context(
                "Alintilar | Tecrit Edebiyat",
                "Kitaplardan secilmis, paylasilmaya deger alintilar ve kaynak eser bilgileri.",
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
            messages.success(request, "Hesabiniz basariyla olusturuldu!")
            return redirect("yazar_paneli")
    else:
        form = UserCreationForm()
    return render(request, "kayit.html", {"form": form, **seo_context("Kayit Ol", "Tecrit Edebiyat yazar veya okur hesabi olusturma sayfasi.")})


def giris(request):
    if request.method == "POST":
        username = request.POST["username"]
        password = request.POST["password"]
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect("yazar_paneli")
        messages.error(request, "Kullanici adi veya sifre hatali.")
    return render(request, "giris.html", seo_context("Giris Yap", "Tecrit Edebiyat hesabina giris yapma sayfasi."))


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


@login_required(login_url="giris")
def yazar_paneli(request):
    profil = get_or_create_user_profile(request.user)
    stats = build_panel_stats(profil)

    return render(
        request,
        "admin/ozel_admin_panel.html",
        {
            "profil": profil,
            "stats": stats,
            **seo_context(
                "Yazar Paneli | Tecrit Edebiyat",
                "Yazara ozel panel, yayin durumu ve icerik istatistikleri.",
                request.build_absolute_uri(),
            ),
        },
    )


@login_required(login_url="giris")
def yazar_panel_profil(request):
    profil = get_or_create_user_profile(request.user)
    if request.method == "POST":
        user_form = PanelUserForm(request.POST, instance=request.user)
        profile_form = PanelProfileForm(request.POST, request.FILES, instance=profil)
        if user_form.is_valid() and profile_form.is_valid():
            user = user_form.save()
            profil_nesnesi = profile_form.save(commit=False)
            ad_soyad = " ".join(parca for parca in [user.first_name.strip(), user.last_name.strip()] if parca)
            profil_nesnesi.ad_soyad = ad_soyad or user.username
            profil_nesnesi.save()
            messages.success(request, "Profil bilgilerin güncellendi.")
            return redirect("yazar_panel_profil")
    else:
        user_form = PanelUserForm(instance=request.user)
        profile_form = PanelProfileForm(instance=profil)

    return render(
        request,
        "admin/panel_profil.html",
        {
            "profil": profil,
            "user_form": user_form,
            "profile_form": profile_form,
            "stats": build_panel_stats(profil),
        },
    )


@login_required(login_url="giris")
def yazar_panel_sifre(request):
    profil = get_or_create_user_profile(request.user)
    if request.method == "POST":
        form = PanelPasswordForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)
            messages.success(request, "Şifren başarıyla güncellendi.")
            return redirect("yazar_panel_sifre")
    else:
        form = PanelPasswordForm(request.user)

    return render(
        request,
        "admin/panel_sifre.html",
        {
            "profil": profil,
            "form": form,
            "stats": build_panel_stats(profil),
        },
    )


@login_required(login_url="giris")
def yazar_panel_yeni_yazi(request):
    profil = get_or_create_user_profile(request.user)
    is_superadmin = profil.rol == YazarProfil.RolSecenekleri.SUPERADMIN
    if request.method == "POST":
        post_data = request.POST.copy()
        if not is_superadmin:
            post_data["durum"] = BlogYazisi.DurumSecenekleri.INCELEMEDE
        form = PanelBlogYazisiForm(post_data, request.FILES, is_superadmin=is_superadmin)
        if form.is_valid():
            yazi = form.save(commit=False)
            yazi.yazar = profil
            if is_superadmin:
                if yazi.durum == BlogYazisi.DurumSecenekleri.YAYINDA and not yazi.onaylayan:
                    yazi.onaylayan = request.user
            else:
                yazi.durum = BlogYazisi.DurumSecenekleri.INCELEMEDE
                yazi.onaylayan = None
                yazi.yayin_tarihi = None
            yazi.save()
            form.save_m2m()
            if is_superadmin and yazi.durum == BlogYazisi.DurumSecenekleri.YAYINDA:
                messages.success(request, "Yazın doğrudan yayına alındı.")
            elif is_superadmin:
                messages.success(request, "Yazın kaydedildi.")
            else:
                messages.success(request, "Yazın editör onayına gönderildi.")
            return redirect("yazar_paneli")
    else:
        form = PanelBlogYazisiForm(is_superadmin=is_superadmin)

    return render(
        request,
        "admin/panel_yazi_form.html",
        {
            "profil": profil,
            "form": form,
            "form_title": "Yeni Yazı Ekle",
            "submit_label": "Yazıyı Kaydet",
            "stats": build_panel_stats(profil),
            "is_superadmin": is_superadmin,
        },
    )


@login_required(login_url="giris")
def yazar_panel_yazi_duzenle(request, pk):
    profil = get_or_create_user_profile(request.user)
    is_superadmin = profil.rol == YazarProfil.RolSecenekleri.SUPERADMIN
    yazi = get_object_or_404(BlogYazisi, pk=pk, yazar=profil)

    if request.method == "POST":
        mevcut_gorsel = yazi.gorsel if yazi.gorsel else None
        gorsel_temizle = request.POST.get("gorsel-clear") == "on"
        yeni_gorsel = request.FILES.get("gorsel")
        post_data = request.POST.copy()
        if not is_superadmin:
            post_data["durum"] = BlogYazisi.DurumSecenekleri.INCELEMEDE

        form = PanelBlogYazisiForm(
            post_data,
            request.FILES,
            instance=yazi,
            is_superadmin=is_superadmin,
        )

        if form.is_valid():
            yazi = form.save(commit=False)

            if gorsel_temizle and not yeni_gorsel:
                if mevcut_gorsel:
                    mevcut_gorsel.delete(save=False)
                yazi.gorsel = None
            elif yeni_gorsel and mevcut_gorsel and mevcut_gorsel.name != yazi.gorsel.name:
                mevcut_gorsel.delete(save=False)

            yazi.yazar = profil
            if is_superadmin:
                if yazi.durum == BlogYazisi.DurumSecenekleri.YAYINDA and not yazi.onaylayan:
                    yazi.onaylayan = request.user
            else:
                yazi.durum = BlogYazisi.DurumSecenekleri.INCELEMEDE
                yazi.onaylayan = None
                yazi.yayin_tarihi = None

            yazi.save()
            form.save_m2m()

            if is_superadmin and yazi.durum == BlogYazisi.DurumSecenekleri.YAYINDA:
                messages.success(request, "Yazın güncellendi ve yayında tutuldu.")
            elif is_superadmin:
                messages.success(request, "Yazın güncellendi.")
            else:
                messages.success(request, "Güncellenen yazın yeniden editör onayına gönderildi.")

            return redirect("yazar_paneli")
    else:
        form = PanelBlogYazisiForm(instance=yazi, is_superadmin=is_superadmin)

    return render(
        request,
        "admin/panel_yazi_form.html",
        {
            "profil": profil,
            "form": form,
            "yazi": yazi,
            "form_title": "Yazıyı Düzenle",
            "submit_label": "Değişiklikleri Kaydet",
            "stats": build_panel_stats(profil),
            "is_superadmin": is_superadmin,
        },
    )


@login_required(login_url="giris")
def yazar_panel_yazi_sil(request, pk):
    profil = get_or_create_user_profile(request.user)
    yazi = get_object_or_404(BlogYazisi, pk=pk, yazar=profil)

    if request.method == "POST":
        yazi_baslik = yazi.baslik
        yazi.delete()
        messages.success(request, f'"{yazi_baslik}" başlıklı yazı silindi.')
        return redirect("yazar_paneli")

    return redirect("yazar_panel_yazi_duzenle", pk=pk)

