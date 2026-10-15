from django.urls import path
from django.views.generic import RedirectView

from . import views


urlpatterns = [
    path("", views.superadmin_dashboard, name="superadmin_dashboard"),
    path("ara/", views.superadmin_ara, name="superadmin_ara"),
    path("auth/user/", RedirectView.as_view(pattern_name="superadmin_kullanicilar", permanent=False)),
    path("auth/user/add/", RedirectView.as_view(pattern_name="superadmin_kullanici_yeni", permanent=False)),
    path("auth/user/<int:pk>/change/", RedirectView.as_view(pattern_name="superadmin_kullanici_duzenle", permanent=False)),
    path("auth/user/<int:pk>/password/", RedirectView.as_view(pattern_name="superadmin_kullanici_sifre", permanent=False)),
    path("icerik-yonetimi/", views.superadmin_icerik_yonetimi, name="superadmin_icerik_yonetimi"),
    path("icerik-yonetimi/<str:model_key>/", views.superadmin_icerik_model_liste, name="superadmin_icerik_model_liste"),
    path("icerik-yonetimi/<str:model_key>/yeni/", views.superadmin_icerik_model_yeni, name="superadmin_icerik_model_yeni"),
    path("icerik-yonetimi/<str:model_key>/<int:pk>/duzenle/", views.superadmin_icerik_model_duzenle, name="superadmin_icerik_model_duzenle"),
    path("icerik-yonetimi/<str:model_key>/<int:pk>/sil/", views.superadmin_icerik_model_sil, name="superadmin_icerik_model_sil"),
    path("yazilar/", views.superadmin_yazilar, name="superadmin_yazilar"),
    path("yazilar/<int:pk>/", views.superadmin_yazi_detay, name="superadmin_yazi_detay"),
    path("yazilar/<int:pk>/durum/", views.superadmin_yazi_durum_guncelle, name="superadmin_yazi_durum_guncelle"),
    path("iletisim/", views.superadmin_iletisim, name="superadmin_iletisim"),
    path("iletisim/<int:pk>/", views.superadmin_iletisim_detay, name="superadmin_iletisim_detay"),
    path("iletisim/<int:pk>/sil/", views.superadmin_iletisim_sil, name="superadmin_iletisim_sil"),
    path("iletisim/<int:pk>/durum/", views.superadmin_iletisim_durum_guncelle, name="superadmin_iletisim_durum_guncelle"),
    path("yazarlar/", views.superadmin_yazarlar, name="superadmin_yazarlar"),
    path("kullanicilar/", views.superadmin_kullanicilar, name="superadmin_kullanicilar"),
    path("kullanicilar/yeni/", views.superadmin_kullanici_yeni, name="superadmin_kullanici_yeni"),
    path("kullanicilar/<int:pk>/duzenle/", views.superadmin_kullanici_duzenle, name="superadmin_kullanici_duzenle"),
    path("kullanicilar/<int:pk>/sifre/", views.superadmin_kullanici_sifre, name="superadmin_kullanici_sifre"),
    path("kitaplar/", views.superadmin_kitaplar, name="superadmin_kitaplar"),
    path("kitap-maliyeti-ayarlari/", views.superadmin_kitap_maliyeti_ayarlari, name="superadmin_kitap_maliyeti_ayarlari"),
    path("kitap-maliyeti-ayarlari/istatistik-sifirla/", views.superadmin_kitap_maliyeti_istatistik_sifirla, name="superadmin_kitap_maliyeti_istatistik_sifirla"),
    path("core/<str:model_key>/", views.superadmin_legacy_core_model_redirect, name="superadmin_legacy_core_model_liste"),
    path("core/<str:model_key>/add/", views.superadmin_legacy_core_model_redirect, {"action": "add"}, name="superadmin_legacy_core_model_add"),
    path("core/<str:model_key>/<int:pk>/change/", views.superadmin_legacy_core_model_redirect, {"action": "change"}, name="superadmin_legacy_core_model_change"),
]
