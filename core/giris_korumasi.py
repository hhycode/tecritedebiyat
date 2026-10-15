"""
Kaba kuvvet giris denemelerine karsi kilit.

Tum giris noktalari (/admin/login/, /giris/) authenticate() kullandigi icin
koruma kimlik dogrulama backend'inde. Sayaclar "giris" onbelleginde (dosya
tabanli, gunicorn isci surecleri arasinda ortak) tutulur; veritabanina tablo
eklemez.
"""
from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend
from django.core.cache import caches
from django.core.exceptions import PermissionDenied

KULLANICI_DENEME_LIMITI = 5   # ayni IP + ayni kullanici adi
IP_DENEME_LIMITI = 20         # ayni IP, tum kullanici adlari
KILIT_SURESI = 15 * 60        # saniye; son hatali denemeden itibaren


def istemci_ip(request):
    # nginx X-Real-IP'yi $remote_addr ile set ediyor; X-Forwarded-For istemci tarafindan uydurulabilir
    if request is None:
        return ""
    return (request.META.get("HTTP_X_REAL_IP") or request.META.get("REMOTE_ADDR") or "").strip()


def _sayac_anahtarlari(request, username):
    ip = istemci_ip(request)
    return f"giris:kullanici:{ip}:{(username or '').lower()}", f"giris:ip:{ip}"


def giris_kilitli_mi(request, username):
    onbellek = caches["giris"]
    kullanici_anahtari, ip_anahtari = _sayac_anahtarlari(request, username)
    return (
        onbellek.get(kullanici_anahtari, 0) >= KULLANICI_DENEME_LIMITI
        or onbellek.get(ip_anahtari, 0) >= IP_DENEME_LIMITI
    )


def _hatali_denemeyi_kaydet(request, username):
    onbellek = caches["giris"]
    for anahtar in _sayac_anahtarlari(request, username):
        onbellek.set(anahtar, onbellek.get(anahtar, 0) + 1, KILIT_SURESI)


def _sayaci_sifirla(request, username):
    kullanici_anahtari, _ = _sayac_anahtarlari(request, username)
    caches["giris"].delete(kullanici_anahtari)


class GirisKorumaliBackend(ModelBackend):
    def authenticate(self, request, username=None, password=None, **kwargs):
        if username is None:
            username = kwargs.get(get_user_model().USERNAME_FIELD)
        if giris_kilitli_mi(request, username):
            # PermissionDenied: Django diger backend'leri denemeden girisi reddeder
            raise PermissionDenied
        user = super().authenticate(request, username=username, password=password, **kwargs)
        if user is None:
            _hatali_denemeyi_kaydet(request, username)
        else:
            _sayaci_sifirla(request, username)
        return user
