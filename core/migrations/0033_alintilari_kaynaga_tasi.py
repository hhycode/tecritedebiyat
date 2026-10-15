"""Mevcut alintilari yeni kaynak yapisina tasir (geri alinabilir).

Ileri:
- Yazari olan her katalog kitabi icin bir KaynakKitap (yayinevi "Tecrit Edebiyat", onayli, katalog_kitabi bagli)
  ve yazari icin bir KaynakYazar (yazar_profili bagli) olusturulur.
- Her alintinin kaynak'i katalog kitabinin kaynak kaydi olur; yayinda=True -> durum "yayinda", degilse "taslak".
Geri:
- Alintilarin kitap/yayinda alanlari kaynak/durum'dan doldurulur; olusturulan kaynak kayitlari silinir.

Normallestirme fonksiyonlari core/kaynak.py'nin bu tarihteki kopyasidir; migration ileride degismesin diye
buraya alinmistir.
"""
import re

from django.db import migrations
from django.utils.text import slugify

_HARFLER = str.maketrans({
    "ı": "i", "ş": "s", "ğ": "g", "ü": "u", "ö": "o", "ç": "c",
    "â": "a", "î": "i", "û": "u", "é": "e", "è": "e", "ë": "e", "á": "a", "à": "a", "ä": "a",
})


def normal_anahtar(metin):
    sade = (metin or "").replace("I", "ı").replace("İ", "i").lower().translate(_HARFLER)
    sade = re.sub(r"[^\w\s]", " ", sade)
    return re.sub(r"\s+", " ", sade).strip()


def benzersiz_slug(model, metin):
    taban = (slugify(normal_anahtar(metin)) or "kaynak")[:80].strip("-") or "kaynak"
    slug, sayac = taban, 2
    while model.objects.filter(slug=slug).exists():
        slug, sayac = f"{taban}-{sayac}", sayac + 1
    return slug


def ileri(apps, schema_editor):
    Kitap = apps.get_model("core", "Kitap")
    KaynakYazar = apps.get_model("core", "KaynakYazar")
    KaynakKitap = apps.get_model("core", "KaynakKitap")
    Alinti = apps.get_model("core", "Alinti")

    for kitap in Kitap.objects.select_related("yazar").exclude(yazar__isnull=True).order_by("id"):
        yazar_adi = " ".join(kitap.yazar.ad_soyad.split())
        anahtar = normal_anahtar(yazar_adi)
        yazar = KaynakYazar.objects.filter(ad_normal=anahtar).first()
        if yazar is None:
            yazar = KaynakYazar.objects.create(
                ad=yazar_adi, ad_normal=anahtar, slug=benzersiz_slug(KaynakYazar, yazar_adi),
                yazar_profili_id=kitap.yazar_id,
            )
        kitap_adi = " ".join(kitap.ad.split())
        yil = kitap.yayin_tarihi.year if kitap.yayin_tarihi and kitap.yayin_tarihi.year >= 1450 else None
        kaynak = KaynakKitap.objects.filter(ad_normal=normal_anahtar(kitap_adi), yazar=yazar).first()
        if kaynak is None:
            kaynak = KaynakKitap.objects.create(
                ad=kitap_adi, ad_normal=normal_anahtar(kitap_adi), slug=benzersiz_slug(KaynakKitap, f"{kitap_adi} {yazar_adi}"),
                yazar=yazar, yayinevi="Tecrit Edebiyat", basim_yili=yil, katalog_kitabi_id=kitap.id, onayli=True,
            )

    for alinti in Alinti.objects.all():
        if alinti.kitap_id:
            alinti.kaynak = KaynakKitap.objects.filter(katalog_kitabi_id=alinti.kitap_id).first()
        alinti.durum = "yayinda" if alinti.yayinda else "taslak"
        if alinti.yayinda and not alinti.yayin_tarihi:
            alinti.yayin_tarihi = alinti.created_at
        alinti.save(update_fields=["kaynak", "durum", "yayin_tarihi"])


def geri(apps, schema_editor):
    Alinti = apps.get_model("core", "Alinti")
    KaynakYazar = apps.get_model("core", "KaynakYazar")
    KaynakKitap = apps.get_model("core", "KaynakKitap")
    for alinti in Alinti.objects.select_related("kaynak"):
        if alinti.kaynak_id and alinti.kaynak.katalog_kitabi_id:
            alinti.kitap_id = alinti.kaynak.katalog_kitabi_id
        alinti.yayinda = alinti.durum == "yayinda"
        alinti.save(update_fields=["kitap", "yayinda"])
    # Katalog disi kitaptan yapilmis alintilar eski yapida temsil edilemez (kitap zorunluydu)
    Alinti.objects.filter(kitap__isnull=True).delete()
    Alinti.objects.update(kaynak=None)
    KaynakKitap.objects.all().delete()
    KaynakYazar.objects.all().delete()


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0032_kaynak_kitap_ve_alinti_alanlari"),
    ]

    operations = [
        migrations.RunPython(ileri, geri),
    ]
