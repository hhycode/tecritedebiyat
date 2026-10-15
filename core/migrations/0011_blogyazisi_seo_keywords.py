from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("core", "0010_blogyazisi_kategoriler")]

    operations = [
        migrations.AddField(
            model_name="blogyazisi",
            name="seo_keywords",
            field=models.CharField(blank=True, default="", max_length=320),
        ),
    ]
