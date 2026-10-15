# Sunucu yapilandirmasi (kayit icin)

Bu klasordeki dosyalar sunucuya elle kurulur; uygulama bunlari okumaz.

## systemd: yetim medya temizligi
    sudo install -m 644 deploy/systemd/yetim-medya-temizle.* /etc/systemd/system/
    sudo systemctl daemon-reload && sudo systemctl enable --now yetim-medya-temizle.timer

## nginx (www.tecritedebiyat.com sunucu blogu)
- `client_max_body_size 210M;`  (video siniri 200 MB + form verisi; core/medya.py ile uyumlu tutun)
- `location /media/ { ... add_header X-Content-Type-Options nosniff always; }`

## gunicorn.service
- ExecStart'a `--timeout 120` (buyuk yuklemelerin islenmesi icin)
