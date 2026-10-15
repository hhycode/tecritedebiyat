import base64
import mimetypes
from decimal import Decimal

from django.contrib.auth.models import User
from django.core.validators import FileExtensionValidator
from django.db import models
from django.template.defaultfilters import slugify
from django.urls import reverse
from django.utils import timezone


def unique_slugify(instance, value, slug_field_name="slug"):
    base_slug = slugify(value) or "icerik"
    slug = base_slug
    model_class = instance.__class__
    counter = 2

    while model_class.objects.exclude(pk=instance.pk).filter(**{slug_field_name: slug}).exists():
        slug = f"{base_slug}-{counter}"
        counter += 1
    return slug


class YazarProfil(models.Model):
    class RolSecenekleri(models.TextChoices):
        YAZAR = "yazar", "Yazar"
        SUPERADMIN = "superadmin", "Süper admin"

    user = models.OneToOneField(
        User,
        on_delete=models.SET_NULL,
        related_name="profil",
        null=True,
        blank=True,
    )
    ad_soyad = models.CharField(max_length=150, blank=True, default="")
    slug = models.SlugField(unique=True, blank=True, null=True)
    biyografi = models.TextField(blank=True)
    dogum_tarihi = models.DateField(blank=True, null=True)
    fotograf = models.ImageField(upload_to="yazarlar/", blank=True, null=True)
    instagram = models.URLField(max_length=500, blank=True, default="")
    x_hesabi = models.URLField(max_length=500, blank=True, default="")
    websitesi = models.URLField(max_length=500, blank=True, default="")
    rol = models.CharField(max_length=20, choices=RolSecenekleri.choices, default=RolSecenekleri.YAZAR)
    onayli = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)

    class Meta:
        ordering = ["ad_soyad", "id"]
        verbose_name = "Yazar Profili"
        verbose_name_plural = "Yazar Profilleri"

    def save(self, *args, **kwargs):
        if not self.ad_soyad and self.user:
            self.ad_soyad = self.user.get_full_name() or self.user.username
        if not self.ad_soyad:
            self.ad_soyad = "Adsiz Yazar"
        if not self.slug:
            self.slug = unique_slugify(self, self.ad_soyad)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.ad_soyad

    def get_absolute_url(self):
        return reverse("yazarlar")


class KitapTur(models.Model):
    ad = models.CharField(max_length=50)
    slug = models.SlugField(unique=True, blank=True, null=True)
    aciklama = models.TextField(blank=True, default="")

    class Meta:
        verbose_name = "Kitap Kategorisi"
        verbose_name_plural = "Kitap Kategorileri"
        ordering = ["ad"]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = unique_slugify(self, self.ad)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.ad


class Etiket(models.Model):
    ad = models.CharField(max_length=30)
    slug = models.SlugField(unique=True, blank=True, null=True)

    class Meta:
        ordering = ["ad"]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = unique_slugify(self, self.ad)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.ad


class Kitap(models.Model):
    ad = models.CharField(max_length=200)
    slug = models.SlugField(unique=True, blank=True, null=True)
    yazar = models.ForeignKey(
        YazarProfil,
        on_delete=models.SET_NULL,
        related_name="kitaplar",
        blank=True,
        null=True,
    )
    ikinci_yazar = models.ForeignKey(
        YazarProfil,
        on_delete=models.SET_NULL,
        related_name="ikinci_yazar_kitaplar",
        blank=True,
        null=True,
        verbose_name="İkinci yazar",
    )
    aciklama = models.TextField()
    kapak_resmi = models.ImageField(upload_to="kitaplar/", blank=True, null=True)
    yayin_tarihi = models.DateField(blank=True, null=True)
    one_cikan = models.BooleanField(default=False)
    yayinda = models.BooleanField(default=True)
    meta_title = models.CharField(max_length=255, blank=True, default="")
    meta_description = models.CharField(max_length=320, blank=True, default="")
    kitapyurdu_link = models.URLField(max_length=500, blank=True, null=True)
    dr_link = models.URLField(max_length=500, blank=True, null=True)
    trendyol_link = models.URLField(max_length=500, blank=True, null=True)
    shopier_link = models.URLField(max_length=500, blank=True, null=True)
    turler = models.ManyToManyField(KitapTur, blank=True, related_name="kitaplar")
    etiketler = models.ManyToManyField(Etiket, blank=True, related_name="kitaplar")
    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True, null=True, blank=True)

    class Meta:
        ordering = ["-one_cikan", "-yayin_tarihi", "ad"]
        verbose_name = "Kitap"
        verbose_name_plural = "Kitaplar"

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = unique_slugify(self, self.ad)
        if not self.yayin_tarihi:
            self.yayin_tarihi = timezone.localdate()
        if not self.meta_title:
            self.meta_title = f"{self.ad} | Tecrit Edebiyat"
        if not self.meta_description:
            self.meta_description = self.aciklama[:300]
        super().save(*args, **kwargs)

    def __str__(self):
        return self.ad

    def get_absolute_url(self):
        return reverse("kitap_detay", args=[self.slug])

    @property
    def yazarlar_listesi(self):
        return [y for y in (self.yazar, self.ikinci_yazar) if y]

    @property
    def yazar_adi(self):
        yazarlar = self.yazarlar_listesi
        if not yazarlar:
            return "Yazar bilgisi eklenmedi"
        return " & ".join(y.ad_soyad for y in yazarlar)


class AlintiKategori(models.Model):
    ad = models.CharField(max_length=50)
    slug = models.SlugField(unique=True, blank=True, null=True)

    class Meta:
        verbose_name = "Alinti Kategorisi"
        verbose_name_plural = "Alinti Kategorileri"
        ordering = ["ad"]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = unique_slugify(self, self.ad)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.ad


class Alinti(models.Model):
    kitap = models.ForeignKey(Kitap, on_delete=models.CASCADE, related_name="alintilar")
    metin = models.TextField()
    sayfa_no = models.IntegerField(blank=True, null=True)
    kategori = models.ForeignKey(
        AlintiKategori,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="alintilar",
    )
    etiketler = models.ManyToManyField(Etiket, blank=True, related_name="alintilar")
    one_cikan = models.BooleanField(default=False)
    yayinda = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)

    class Meta:
        ordering = ["-one_cikan", "-created_at"]
        verbose_name = "Alinti"
        verbose_name_plural = "Alintilar"

    def __str__(self):
        return f"{self.kitap.ad} - {self.metin[:30]}..."


class SSS(models.Model):
    soru = models.CharField(max_length=300)
    cevap = models.TextField()
    sira = models.IntegerField(default=1)
    aktif = models.BooleanField(default=True)
    eklenme_tarihi = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "SSS"
        verbose_name_plural = "SSS"
        ordering = ["sira", "-eklenme_tarihi"]

    def __str__(self):
        return self.soru


class BlogKategori(models.Model):
    ad = models.CharField(max_length=50)
    slug = models.SlugField(unique=True, blank=True, null=True)

    class Meta:
        verbose_name = "Blog Kategorisi"
        verbose_name_plural = "Blog Kategorileri"
        ordering = ["ad"]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = unique_slugify(self, self.ad)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.ad


class BlogYazisi(models.Model):
    class DurumSecenekleri(models.TextChoices):
        TASLAK = "taslak", "Taslak"
        INCELEMEDE = "incelemede", "İncelemede"
        YAYINDA = "yayinda", "Yayında"
        REDDEDILDI = "reddedildi", "Reddedildi"

    yazar = models.ForeignKey(YazarProfil, on_delete=models.CASCADE, related_name="blog_yazilari")
    baslik = models.CharField(max_length=200)
    slug = models.SlugField(unique=True, blank=True, null=True)
    ozet = models.CharField(max_length=320, blank=True, default="")
    icerik = models.TextField()
    gorsel = models.ImageField(upload_to="blog/", blank=True, null=True)
    kategori = models.ForeignKey(BlogKategori, on_delete=models.SET_NULL, null=True, related_name="blog_yazilari")
    kategoriler = models.ManyToManyField(
        BlogKategori,
        blank=True,
        related_name="blog_yazilari_coklu",
    )
    etiketler = models.ManyToManyField(Etiket, blank=True, related_name="blog_yazilari")
    durum = models.CharField(max_length=20, choices=DurumSecenekleri.choices, default=DurumSecenekleri.TASLAK)
    admin_notu = models.TextField(blank=True, default="")
    onaylayan = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="onaylanan_blog_yazilari",
    )
    meta_title = models.CharField(max_length=255, blank=True, default="")
    meta_description = models.CharField(max_length=320, blank=True, default="")
    seo_keywords = models.CharField(max_length=320, blank=True, default="")
    yayin_tarihi = models.DateTimeField(blank=True, null=True)
    # Blog sayfasinin goruntulenme sayisi (botlar ve panel kullanicilari haric); 15.10.2026'dan itibaren
    okunma_sayisi = models.PositiveIntegerField("Okunma sayısı", default=0, editable=False)
    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True, null=True, blank=True)

    class Meta:
        ordering = ["-yayin_tarihi", "-created_at"]
        verbose_name = "Blog Yazisi"
        verbose_name_plural = "Blog Yazilari"

    def save(self, *args, **kwargs):
        from django.utils import timezone

        from .html_temizleme import temiz_html

        self.icerik = temiz_html(self.icerik)
        if not self.slug:
            self.slug = unique_slugify(self, self.baslik)
        if not self.meta_title:
            self.meta_title = f"{self.baslik} | Tecrit Edebiyat"
        if not self.meta_description:
            self.meta_description = self.ozet[:300]
        if self.durum == self.DurumSecenekleri.YAYINDA and not self.yayin_tarihi:
            self.yayin_tarihi = timezone.now()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.yazar.ad_soyad} - {self.baslik}"

    def get_absolute_url(self):
        return reverse("blog_detay", args=[self.slug])

    @property
    def tum_kategoriler(self):
        kategoriler = []
        gorulenler = set()

        if self.kategori_id and self.kategori:
            kategoriler.append(self.kategori)
            gorulenler.add(self.kategori_id)

        if self.pk:
            prefetched = getattr(self, "_prefetched_objects_cache", {}).get("kategoriler")
            ek_kategoriler = prefetched if prefetched is not None else self.kategoriler.all()
            for kategori in ek_kategoriler:
                if kategori.pk not in gorulenler:
                    kategoriler.append(kategori)
                    gorulenler.add(kategori.pk)

        return kategoriler

    @property
    def ilk_kategori(self):
        return self.tum_kategoriler[0] if self.tum_kategoriler else None

    @property
    def kategori_listesi(self):
        return ", ".join(kategori.ad for kategori in self.tum_kategoriler) or "-"

    @property
    def etiket_listesi(self):
        if not self.pk:
            return ""
        return ", ".join(self.etiketler.order_by("ad").values_list("ad", flat=True))


class BlogReklam(models.Model):
    isim = models.CharField(max_length=160)
    sponsor_etiketi = models.CharField(max_length=50, default="Sponsorlu İçerik")
    link = models.URLField(max_length=500, blank=True, default="")
    resim = models.ImageField(upload_to="blog/reklamlar/", blank=True, null=True)
    aktif = models.BooleanField(default=True)
    sira = models.PositiveIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["sira", "-created_at"]
        verbose_name = "Blog Reklamı"
        verbose_name_plural = "Blog Reklamları"

    def __str__(self):
        return self.isim

    @property
    def resim_base64(self):
        if not self.resim:
            return None
        try:
            with self.resim.open("rb") as image_file:
                return base64.b64encode(image_file.read()).decode("utf-8")
        except Exception:
            return None

    @property
    def resim_mime(self):
        if not self.resim:
            return ""
        mime, _ = mimetypes.guess_type(self.resim.name)
        return mime or "image/jpeg"


class BlogUrun(models.Model):
    isim = models.CharField(max_length=180)
    satis_linki = models.URLField(max_length=500)
    resim = models.ImageField(upload_to="blog/urunler/", blank=True, null=True)
    fiyat = models.DecimalField(max_digits=10, decimal_places=2)
    indirimli_fiyat = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    kategori_etiketi = models.CharField(max_length=60, default="Kitap - Dergi")
    aktif = models.BooleanField(default=True)
    one_cikar = models.BooleanField(default=False)
    sira = models.PositiveIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-one_cikar", "sira", "-created_at"]
        verbose_name = "Blog Ürünü"
        verbose_name_plural = "Blog Ürünleri"

    def __str__(self):
        return self.isim

    @property
    def indirim_var_mi(self):
        return bool(self.indirimli_fiyat and self.indirimli_fiyat < self.fiyat)

    @property
    def resim_optimized(self):
        return self.resim


class AnaSayfaYayinKarti(models.Model):
    baslik = models.CharField(max_length=180)
    link = models.URLField(max_length=500, blank=True, default="")
    mobil_gorsel = models.ImageField(upload_to="anasayfa/yayin-kartlari/", blank=True, null=True)
    masaustu_gorsel = models.ImageField(upload_to="anasayfa/yayin-kartlari/", blank=True, null=True)
    etiket_bir = models.CharField(max_length=60, blank=True, default="")
    etiket_iki = models.CharField(max_length=60, blank=True, default="")
    etiket_uc = models.CharField(max_length=60, blank=True, default="")
    aktif = models.BooleanField(default=True)
    sira = models.PositiveIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["sira", "-created_at"]
        verbose_name = "Ana Sayfa Yayın Kartı"
        verbose_name_plural = "Ana Sayfa Yayın Kartları"

    def __str__(self):
        return self.baslik

    @property
    def etiketler(self):
        return [etiket for etiket in [self.etiket_bir, self.etiket_iki, self.etiket_uc] if etiket]


class Slider(models.Model):
    baslik = models.CharField(max_length=100)
    aciklama = models.TextField(blank=True)
    gorsel = models.ImageField(upload_to="slider/")
    link = models.URLField(max_length=500, blank=True, null=True)
    aktif = models.BooleanField(default=True)
    sira = models.IntegerField(default=1)
    eklenme_tarihi = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["sira", "-eklenme_tarihi"]

    def __str__(self):
        return self.baslik


class IletisimBasvurusu(models.Model):
    class AmacSecenekleri(models.TextChoices):
        YAZI_GONDERIMI = "yazi_gonderimi", "Yazı / Word dosyası gönderimi"
        KITAP_DOSYASI = "kitap_dosyasi", "Kitap dosyası değerlendirmesi"
        IS_BIRLIGI = "is_birligi", "İş birliği"
        REKLAM = "reklam", "Reklam / sponsorluk"
        GENEL = "genel", "Genel iletişim"

    ad = models.CharField(max_length=80)
    soyad = models.CharField(max_length=80)
    email = models.EmailField()
    telefon = models.CharField(max_length=30)
    amac = models.CharField(max_length=30, choices=AmacSecenekleri.choices)
    mesaj = models.TextField()
    dosya = models.FileField(
        upload_to="basvurular/",
        blank=True,
        null=True,
        validators=[FileExtensionValidator(allowed_extensions=["doc", "docx"])],
    )
    incelendi = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "İletişim Başvurusu"
        verbose_name_plural = "İletişim Başvuruları"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.ad} {self.soyad} - {self.get_amac_display()}"


class KitapMaliyetTuru(models.Model):
    HESAPLAMA_KELIME = "kelime"
    HESAPLAMA_SAYFA = "sayfa"
    HESAPLAMA_CHOICES = [
        (HESAPLAMA_KELIME, "Kelime sayısına göre"),
        (HESAPLAMA_SAYFA, "Sayfa sayısına göre"),
    ]

    ad = models.CharField(max_length=50, unique=True, help_text="Örn: Roman, Şiir, Öykü, Deneme")
    hesaplama_yontemi = models.CharField(
        max_length=10,
        choices=HESAPLAMA_CHOICES,
        default=HESAPLAMA_KELIME,
        help_text="Sayfa sayısına göre seçilirse kullanıcı hesaplamada doğrudan sayfa sayısını girer (örn. şiir).",
    )
    kelime_yogunlugu = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Bu türde sayfa başına ortalama kelime sayısı (yalnızca kelime sayısına göre hesaplamada kullanılır)",
    )
    sira = models.PositiveIntegerField(default=0, help_text="Hesaplama aracındaki listeleme sırası")

    class Meta:
        verbose_name = "Kitap Maliyeti Türü"
        verbose_name_plural = "Kitap Maliyeti Türleri"
        ordering = ["sira", "ad"]

    def __str__(self):
        if self.sayfa_bazli:
            return f"{self.ad} (sayfa sayısına göre)"
        return f"{self.ad} ({self.kelime_yogunlugu} kelime/sayfa)"

    @property
    def sayfa_bazli(self):
        return self.hesaplama_yontemi == self.HESAPLAMA_SAYFA

    def clean(self):
        from django.core.exceptions import ValidationError

        if not self.sayfa_bazli and not self.kelime_yogunlugu:
            raise ValidationError(
                {"kelime_yogunlugu": "Kelime sayısına göre hesaplamada sayfa başı kelime sayısı zorunludur."}
            )


class KitapMaliyetiAyarlari(models.Model):
    sayfa_basi_ucret = models.PositiveIntegerField(default=135, help_text="Sayfa başına basım ücreti (TL)")
    sabit_ucret = models.PositiveIntegerField(default=5000, help_text="Sabit hazırlık ve üretim bedeli (TL)")
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Kitap Maliyeti Ayarı"
        verbose_name_plural = "Kitap Maliyeti Ayarları"

    def __str__(self):
        return f"Sayfa başı {self.sayfa_basi_ucret} TL + Sabit {self.sabit_ucret} TL"

    @classmethod
    def get_ayarlar(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj


class KitapMaliyetiHesaplamaKaydi(models.Model):
    tur = models.ForeignKey(KitapMaliyetTuru, on_delete=models.SET_NULL, null=True, blank=True)
    kelime_sayisi = models.PositiveIntegerField(null=True, blank=True)
    sayfa_sayisi = models.PositiveIntegerField(null=True, blank=True)
    toplam_ucret = models.PositiveIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Kitap Maliyeti Hesaplama Kaydı"
        verbose_name_plural = "Kitap Maliyeti Hesaplama Kayıtları"
        ordering = ["-created_at"]

    def __str__(self):
        tur_adi = self.tur.ad if self.tur else "-"
        miktar = f"{self.sayfa_sayisi} sayfa" if self.sayfa_sayisi else f"{self.kelime_sayisi} kelime"
        return f"{tur_adi} - {miktar} - {self.toplam_ucret} TL"
