"""Yetim medya temizligi (gunde bir kez systemd zamanlayicisiyla calisir).

1. 24 saatten eski, hicbir yaziya baglanmamis yuklemeler (form kaydedilmeden birakilmis) silinir;
   dosyalari post_delete sinyaliyle diskten gider.
2. media/medya/ altinda olup veritabaninda karsiligi olmayan, 24 saatten eski dosyalar silinir.
"""
import os
import time
from datetime import timedelta

from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils import timezone

from core.models import YaziMedyasi

BEKLEME = timedelta(hours=24)


class Command(BaseCommand):
    help = "Yaziya baglanmamis eski medya yuklemelerini ve diskteki sahipsiz medya dosyalarini siler."

    def add_arguments(self, parser):
        parser.add_argument("--kuru", action="store_true", help="Hicbir sey silmeden neyin silinecegini yazar.")

    def handle(self, *args, kuru=False, **options):
        sinir = timezone.now() - BEKLEME
        bekleyenler = YaziMedyasi.objects.filter(yazi__isnull=True, created_at__lt=sinir)
        kayit_sayisi = bekleyenler.count()
        if not kuru:
            for medya in bekleyenler.iterator():
                medya.delete()

        kok = os.path.join(settings.MEDIA_ROOT, "medya")
        # Liste, yukarida silinen kayitlardan sonra kurulur; onlarin dosyalari zaten sinyalle gitti
        bilinen = set(YaziMedyasi.objects.exclude(dosya="").values_list("dosya", flat=True))
        sahipsiz, bayt = [], 0
        esik = time.time() - BEKLEME.total_seconds()
        for dizin, _, dosyalar in os.walk(kok):
            for ad in dosyalar:
                yol = os.path.join(dizin, ad)
                goreli = os.path.relpath(yol, settings.MEDIA_ROOT).replace(os.sep, "/")
                if goreli not in bilinen and os.path.getmtime(yol) < esik:
                    sahipsiz.append(yol)
                    bayt += os.path.getsize(yol)
        if not kuru:
            for yol in sahipsiz:
                os.remove(yol)

        onek = "[kuru calisma] " if kuru else ""
        self.stdout.write(
            f"{onek}baglanmamis kayit: {kayit_sayisi}, sahipsiz dosya: {len(sahipsiz)} ({bayt // 1024} KB)"
        )
