"""Alinti'nin eski alanlarini kaldirir: kitap (yerine kaynak) ve yayinda (yerine durum).

Geri alinirsa alanlar yeniden eklenir ve RunPython ile kaynak/durum'dan doldurulur
(katalog kitabina bagli olmayan alintilarda kitap bos kalir).
"""
from django.db import migrations


def geri_doldur(apps, schema_editor):
    Alinti = apps.get_model("core", "Alinti")
    for alinti in Alinti.objects.select_related("kaynak"):
        alinti.yayinda = alinti.durum == "yayinda"
        alinti.kitap_id = alinti.kaynak.katalog_kitabi_id if alinti.kaynak_id else None
        alinti.save(update_fields=["yayinda", "kitap"])


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0033_alintilari_kaynaga_tasi"),
    ]

    operations = [
        # Geri alirken en son calisir: alanlar yeniden eklendikten sonra doldurur
        migrations.RunPython(migrations.RunPython.noop, geri_doldur),
        migrations.RemoveField(
            model_name="alinti",
            name="kitap",
        ),
        migrations.RemoveField(
            model_name="alinti",
            name="yayinda",
        ),
    ]
