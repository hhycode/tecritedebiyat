import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0017_rename_shopier_to_trendyol_add_shopier'),
    ]

    operations = [
        migrations.AddField(
            model_name='kitap',
            name='fiyat',
            field=models.DecimalField(blank=True, decimal_places=2, help_text='Sitemizden dogrudan satis icin fiyat (TL). Bos birakilirsa sepete eklenemez.', max_digits=8, null=True),
        ),
        migrations.AddField(
            model_name='kitap',
            name='stok_adedi',
            field=models.PositiveIntegerField(blank=True, help_text='Bos birakilirsa stok takibi yapilmaz (siniz yok sayilir).', null=True),
        ),
        migrations.AddField(
            model_name='kitap',
            name='dogrudan_satis_aktif',
            field=models.BooleanField(default=False, help_text='Isaretlenirse ve fiyat girilmisse bu kitap sitemizden sepete eklenebilir.'),
        ),
        migrations.CreateModel(
            name='Siparis',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('siparis_no', models.CharField(editable=False, max_length=40, unique=True)),
                ('ad_soyad', models.CharField(max_length=150)),
                ('email', models.EmailField(max_length=254)),
                ('telefon', models.CharField(max_length=20)),
                ('adres', models.TextField()),
                ('sehir', models.CharField(max_length=80)),
                ('ulke', models.CharField(default='Türkiye', max_length=80)),
                ('posta_kodu', models.CharField(blank=True, default='', max_length=12)),
                ('toplam_tutar', models.DecimalField(decimal_places=2, max_digits=10)),
                ('durum', models.CharField(choices=[('beklemede', 'Ödeme Bekleniyor'), ('odendi', 'Ödendi'), ('basarisiz', 'Ödeme Başarısız'), ('iptal', 'İptal Edildi'), ('kargolandi', 'Kargolandı')], default='beklemede', max_length=20)),
                ('iyzico_token', models.CharField(blank=True, default='', max_length=100)),
                ('iyzico_payment_id', models.CharField(blank=True, default='', max_length=100)),
                ('iyzico_hata_mesaji', models.TextField(blank=True, default='')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name': 'Sipariş',
                'verbose_name_plural': 'Siparişler',
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='SiparisKalemi',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('kitap_adi', models.CharField(max_length=200)),
                ('birim_fiyat', models.DecimalField(decimal_places=2, max_digits=8)),
                ('adet', models.PositiveIntegerField(default=1)),
                ('kitap', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='siparis_kalemleri', to='core.kitap')),
                ('siparis', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='kalemler', to='core.siparis')),
            ],
            options={
                'verbose_name': 'Sipariş Kalemi',
                'verbose_name_plural': 'Sipariş Kalemleri',
            },
        ),
    ]
