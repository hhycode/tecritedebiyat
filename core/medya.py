"""Yazilara eklenen ses/video: sinirlar, dosya imzasi denetimi ve gomulu baglanti cozumleme.

Dosya turu tarayicinin bildirdigi Content-Type'a degil, dosyanin ilk baytlarina (imza) bakilarak
belirlenir; uzanti ile imza birbirini tutmazsa dosya reddedilir. Yeni bir kutuphane gerektirmez.
"""
import re
from urllib.parse import parse_qs, quote, urlparse

MB = 1024 * 1024

# Ayarlanabilir sinirlar
SES_SINIRI = 30 * MB
VIDEO_SINIRI = 200 * MB
YAZI_BASINA_MEDYA = 5
KULLANICI_KOTASI = 1024 * MB  # bir kullanicinin yukleyebilecegi toplam dosya boyutu
KAYIT_SURESI_SN = 15 * 60  # tarayicidan ses kaydinin en uzun suresi
ACIKLAMA_SINIRI = 5000

# uzanti -> (tur, kapsayici bicim, kaydedilecek MIME)
UZANTILAR = {
    "mp3": ("ses", "mp3", "audio/mpeg"),
    "m4a": ("ses", "mp4", "audio/mp4"),
    "ogg": ("ses", "ogg", "audio/ogg"),
    "wav": ("ses", "wav", "audio/wav"),
    "mp4": ("video", "mp4", "video/mp4"),
    # webm hem video hem tarayici ses kaydi (Chrome/Firefox) olabilir; tur istekten belirlenir
    "webm": ("video", "webm", "video/webm"),
}
SES_UZANTILARI = ("mp3", "m4a", "ogg", "wav", "webm")
VIDEO_UZANTILARI = ("mp4", "webm")


class MedyaHatasi(ValueError):
    """Kullaniciya oldugu gibi gosterilecek Turkce hata."""


def boyut_metni(bayt):
    if bayt >= MB:
        return f"{bayt / MB:.1f} MB".replace(".", ",")
    return f"{max(1, round(bayt / 1024))} KB"


def kapsayici_bicimi(bas):
    """Dosyanin ilk baytlarindan kapsayici bicimi: mp3 | mp4 | ogg | wav | webm | None."""
    if bas[:3] == b"ID3":
        return "mp3"
    if len(bas) > 1 and bas[0] == 0xFF and (bas[1] & 0xE0) == 0xE0:
        return "mp3"  # ID3 etiketi olmayan MPEG ses cercevesi
    if bas[4:8] == b"ftyp":
        return "mp4"
    if bas[:4] == b"OggS":
        return "ogg"
    if bas[:4] == b"RIFF" and bas[8:12] == b"WAVE":
        return "wav"
    if bas[:4] == b"\x1a\x45\xdf\xa3" and b"webm" in bas[:64]:
        return "webm"
    return None


BICIM_ADLARI = {"mp3": "MP3", "mp4": "MP4/M4A", "ogg": "OGG", "wav": "WAV", "webm": "WebM"}


def dosyayi_dogrula(dosya, istenen_tur=""):
    """Yuklenen dosyayi denetler. (tur, uzanti, mime) dondurur ya da MedyaHatasi firlatir."""
    ad = (dosya.name or "").lower()
    uzanti = ad.rsplit(".", 1)[-1] if "." in ad else ""
    if uzanti not in UZANTILAR:
        raise MedyaHatasi("Bu dosya türü desteklenmiyor. Ses için MP3, M4A, OGG ya da WAV; video için MP4 ya da WebM yükleyebilirsiniz.")

    tur, beklenen_bicim, mime = UZANTILAR[uzanti]
    if uzanti == "webm" and istenen_tur == "ses":
        tur, mime = "ses", "audio/webm"

    sinir = SES_SINIRI if tur == "ses" else VIDEO_SINIRI
    if dosya.size > sinir:
        raise MedyaHatasi(f"{'Ses dosyası' if tur == 'ses' else 'Video'} en fazla {sinir // MB} MB olabilir; bu dosya {boyut_metni(dosya.size)}.")
    if dosya.size == 0:
        raise MedyaHatasi("Dosya boş görünüyor.")

    dosya.seek(0)
    bas = dosya.read(64)
    dosya.seek(0)
    bulunan = kapsayici_bicimi(bas)
    if bulunan != beklenen_bicim:
        raise MedyaHatasi(
            f"Dosyanın içeriği .{uzanti} uzantısıyla uyuşmuyor"
            + (f" (içerik {BICIM_ADLARI[bulunan]} gibi görünüyor)." if bulunan else ".")
            + " Dosya bozuk ya da uzantısı değiştirilmiş olabilir."
        )
    return tur, uzanti, mime


# ---------- Gomulu baglantilar ----------

YOUTUBE_KIMLIK = re.compile(r"^[A-Za-z0-9_-]{11}$")
SPOTIFY_KIMLIK = re.compile(r"^[A-Za-z0-9]{22}$")
SOUNDCLOUD_PARCA = re.compile(r"^[A-Za-z0-9_-]+$")
SPOTIFY_TURLERI = {"track", "episode", "album", "playlist", "show"}

SAGLAYICI_ADLARI = {"youtube": "YouTube", "vimeo": "Vimeo", "soundcloud": "SoundCloud", "spotify": "Spotify"}


def _host(url):
    host = (url.hostname or "").lower()
    return host[4:] if host.startswith("www.") else host


def baglantiyi_coz(adres):
    """Paylasim baglantisini cozer: {'saglayici', 'kimlik', 'tur'} ya da MedyaHatasi."""
    adres = (adres or "").strip()
    if not adres:
        raise MedyaHatasi("Bir bağlantı yapıştırın.")
    if not re.match(r"^https?://", adres, re.I):
        adres = "https://" + adres
    url = urlparse(adres)
    host = _host(url)
    parcalar = [p for p in url.path.split("/") if p]

    if host in ("youtube.com", "m.youtube.com", "music.youtube.com", "youtube-nocookie.com", "youtu.be"):
        kimlik = ""
        if host == "youtu.be" and parcalar:
            kimlik = parcalar[0]
        elif parcalar[:1] == ["watch"] or url.path == "/watch":
            kimlik = parse_qs(url.query).get("v", [""])[0]
        elif len(parcalar) >= 2 and parcalar[0] in ("shorts", "embed", "live", "v"):
            kimlik = parcalar[1]
        if YOUTUBE_KIMLIK.match(kimlik):
            return {"saglayici": "youtube", "kimlik": kimlik, "tur": "video"}
        raise MedyaHatasi("Bu YouTube bağlantısında video bulunamadı. Videonun paylaş bağlantısını kopyalayın.")

    if host in ("vimeo.com", "player.vimeo.com"):
        sayilar = [i for i, p in enumerate(parcalar) if p.isdigit()]
        if sayilar:
            i = sayilar[0]
            kimlik = parcalar[i]
            # Liste disi videolarda gizli anahtar: vimeo.com/123/abc ya da ?h=abc
            gizli = parse_qs(url.query).get("h", [""])[0]
            if not gizli and len(parcalar) > i + 1 and re.match(r"^[0-9a-f]{6,}$", parcalar[i + 1]):
                gizli = parcalar[i + 1]
            if gizli and re.match(r"^[0-9a-f]{6,}$", gizli):
                kimlik = f"{kimlik}:{gizli}"
            return {"saglayici": "vimeo", "kimlik": kimlik, "tur": "video"}
        raise MedyaHatasi("Bu Vimeo bağlantısında video bulunamadı.")

    if host in ("soundcloud.com", "m.soundcloud.com"):
        if len(parcalar) >= 2 and all(SOUNDCLOUD_PARCA.match(p) for p in parcalar[:4]):
            return {"saglayici": "soundcloud", "kimlik": "/".join(parcalar[:4]), "tur": "ses"}
        raise MedyaHatasi("Bu SoundCloud bağlantısı tanınmadı. Parçanın tam adresini (soundcloud.com/…) yapıştırın.")
    if host == "on.soundcloud.com":
        raise MedyaHatasi("Kısaltılmış SoundCloud bağlantıları desteklenmiyor. Parçayı tarayıcıda açıp adres çubuğundaki tam adresi yapıştırın.")

    if host == "open.spotify.com":
        if parcalar and parcalar[0].startswith("intl-"):
            parcalar = parcalar[1:]
        if parcalar[:1] == ["embed"]:
            parcalar = parcalar[1:]
        if len(parcalar) >= 2 and parcalar[0] in SPOTIFY_TURLERI and SPOTIFY_KIMLIK.match(parcalar[1]):
            return {"saglayici": "spotify", "kimlik": f"{parcalar[0]}/{parcalar[1]}", "tur": "ses"}
        raise MedyaHatasi("Bu Spotify bağlantısı tanınmadı. Şarkı, bölüm, albüm ya da çalma listesinin paylaş bağlantısını yapıştırın.")

    raise MedyaHatasi("Şimdilik yalnızca YouTube, Vimeo, SoundCloud ve Spotify bağlantıları eklenebilir.")


def gomme_adresi(saglayici, kimlik):
    """Oynaticinin iframe adresi; yalnizca dogrulanmis kimlikten kurulur."""
    if saglayici == "youtube":
        return f"https://www.youtube-nocookie.com/embed/{kimlik}?rel=0"
    if saglayici == "vimeo":
        video, _, gizli = kimlik.partition(":")
        return f"https://player.vimeo.com/video/{video}?dnt=1" + (f"&h={gizli}" if gizli else "")
    if saglayici == "soundcloud":
        hedef = quote(f"https://soundcloud.com/{kimlik}", safe="")
        return f"https://w.soundcloud.com/player/?url={hedef}&color=%2318181b&auto_play=false&show_comments=false&visual=false"
    if saglayici == "spotify":
        return f"https://open.spotify.com/embed/{kimlik}"
    return ""


def kaynak_adresi(saglayici, kimlik):
    """Kullanicinin oynaticiyi acamazsa gidebilecegi orijinal sayfa."""
    if saglayici == "youtube":
        return f"https://www.youtube.com/watch?v={kimlik}"
    if saglayici == "vimeo":
        video, _, gizli = kimlik.partition(":")
        return f"https://vimeo.com/{video}" + (f"/{gizli}" if gizli else "")
    if saglayici == "soundcloud":
        return f"https://soundcloud.com/{kimlik}"
    if saglayici == "spotify":
        return f"https://open.spotify.com/{kimlik}"
    return ""
