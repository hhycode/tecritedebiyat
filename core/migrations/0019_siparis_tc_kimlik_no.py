from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0018_dogrudan_satis'),
    ]

    operations = [
        migrations.AddField(
            model_name='siparis',
            name='tc_kimlik_no',
            field=models.CharField(default='', help_text='iyzico odeme dogrulamasi icin zorunludur.', max_length=11),
            preserve_default=False,
        ),
    ]
