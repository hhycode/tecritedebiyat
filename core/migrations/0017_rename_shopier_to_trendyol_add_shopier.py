from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0016_kitapmaliyetiayarlari'),
    ]

    operations = [
        migrations.RenameField(
            model_name='kitap',
            old_name='shopier_link',
            new_name='trendyol_link',
        ),
        migrations.AddField(
            model_name='kitap',
            name='shopier_link',
            field=models.URLField(blank=True, max_length=500, null=True),
        ),
    ]
