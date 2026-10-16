# Sunucu yapilandirmasi (kayit icin)

Bu klasordeki dosyalar sunucuya elle kurulur; uygulama bunlari okumaz.

## systemd: yetim medya temizligi
    sudo install -m 644 deploy/systemd/yetim-medya-temizle.* /etc/systemd/system/
    sudo systemctl daemon-reload && sudo systemctl enable --now yetim-medya-temizle.timer

## nginx (www.tecritedebiyat.com sunucu blogu)
- `client_max_body_size 210M;`  (video siniri 200 MB + form verisi; core/medya.py ile uyumlu tutun)
- `location /media/ { ... add_header X-Content-Type-Options nosniff always; }`
- Statik metin dosyalari icin sikistirma (yalnizca www blogunda; HTML zaten varsayilan olarak sikistirilir):

      gzip_vary on;
      gzip_comp_level 6;
      gzip_min_length 1024;
      gzip_types text/css application/javascript text/javascript application/json application/manifest+json image/svg+xml text/plain text/xml application/xml;

## gunicorn.service
- ExecStart'a `--timeout 120` (buyuk yuklemelerin islenmesi icin)

## GitHub (gizli kopya: github.com/hhycode/tecritedebiyat)
Sunucuda `github` uzak deposu ve yalnizca bu depoya yazabilen deploy key (`~/.ssh/github_tecrit`,
`~/.ssh/config` icinde `Host github-tecrit`) tanimli.
    install -m 755 deploy/github/post-receive .git/hooks/post-receive
Her guncelleme gelince ve her gece yedekten sonra kod GitHub'a gonderilir.
Kayit: `backups/github-gonderim.log`
