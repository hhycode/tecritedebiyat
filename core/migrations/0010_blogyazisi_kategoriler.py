from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0009_alter_kitap_yazar'),
    ]

    operations = [
        migrations.AddField(
            model_name='blogyazisi',
            name='kategoriler',
            field=models.ManyToManyField(blank=True, related_name='blog_yazilari_coklu', to='core.blogkategori'),
        ),
    ]
