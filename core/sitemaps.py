from django.contrib.sitemaps import Sitemap
from django.urls import reverse

from .models import BlogYazisi, Kitap


class StaticViewSitemap(Sitemap):
    changefreq = "monthly"
    priority = 0.6

    priorities = {
        "anasayfa": 1.0,
        "kitap_maliyeti_hesapla": 0.9,
        "kitaplar": 0.8,
        "blog": 0.8,
        "yazarlar": 0.7,
        "iletisim": 0.7,
        "hakkimizda": 0.6,
        "alintilar": 0.5,
        "gizlilik_politikasi": 0.2,
        "kullanim_sartlari": 0.2,
    }

    changefreqs = {
        "anasayfa": "daily",
        "kitaplar": "daily",
        "blog": "daily",
        "kitap_maliyeti_hesapla": "monthly",
        "gizlilik_politikasi": "yearly",
        "kullanim_sartlari": "yearly",
    }

    def items(self):
        return list(self.priorities.keys())

    def location(self, item):
        return reverse(item)

    def priority(self, item):
        return self.priorities.get(item, 0.5)

    def changefreq(self, item):
        return self.changefreqs.get(item, "monthly")


class KitapSitemap(Sitemap):
    changefreq = "weekly"
    priority = 0.8

    def items(self):
        return Kitap.objects.filter(yayinda=True).exclude(slug__isnull=True).exclude(slug="")

    def lastmod(self, obj):
        return obj.updated_at

    def location(self, obj):
        return reverse("kitap_detay", args=[obj.slug])


class BlogYazisiSitemap(Sitemap):
    changefreq = "weekly"
    priority = 0.6

    def items(self):
        return (
            BlogYazisi.objects.filter(durum=BlogYazisi.DurumSecenekleri.YAYINDA)
            .exclude(slug__isnull=True)
            .exclude(slug="")
        )

    def lastmod(self, obj):
        return obj.updated_at

    def location(self, obj):
        return reverse("blog_detay", args=[obj.slug])
