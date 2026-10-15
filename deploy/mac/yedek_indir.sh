#!/bin/bash
# Sunucudaki en son gece yedegini bu Mac'e indirir (haftalik, launchd ile).
# Kurulu yeri: ~/Yedekler/tecrit-edebiyat/yedek_indir.sh
# Zamanlama:   ~/Library/LaunchAgents/com.tecritedebiyat.yedek.plist (Pazar 20:00; Mac kapaliysa acilinca)
# Son 8 haftalik kopya saklanir. Sorun olursa bildirim gosterir; ayrintilar yedek.log'da.
set -uo pipefail

SUNUCU="hhycode@160.153.190.169"
ANAHTAR="$HOME/.ssh/tecritedebiyat"
YEREL="$HOME/Yedekler/tecrit-edebiyat"
SAKLA=8
SSH="ssh -o BatchMode=yes -o ConnectTimeout=20 -o IdentitiesOnly=yes -i $ANAHTAR"

bildir() {
    /usr/bin/osascript -e "display notification \"$2\" with title \"Tecrit Edebiyat yedeği\" subtitle \"$1\"" >/dev/null 2>&1 || true
}
hata() {
    echo "$(date '+%Y-%m-%d %H:%M') HATA: $1"
    bildir "Yedek indirilemedi" "$1"
    exit 1
}

mkdir -p "$YEREL"
echo "$(date '+%Y-%m-%d %H:%M') basladi"

SON=$($SSH "$SUNUCU" 'ls -1d yayinevim/backups/gece/20[0-9]* 2>/dev/null | sort | tail -1') \
    || hata "Sunucuya bağlanılamadı. İnternet bağlantınızı kontrol edin."
[ -n "$SON" ] || hata "Sunucuda gece yedeği bulunamadı."
AD=$(basename "$SON")

if [ -f "$YEREL/$AD/db.sqlite3" ] && [ -f "$YEREL/$AD/media.tar.gz" ]; then
    echo "$AD zaten indirilmis; atlandi"
else
    /usr/bin/rsync -a --partial -e "$SSH" "$SUNUCU:$SON/" "$YEREL/$AD.indiriliyor/" \
        || hata "$AD indirilirken bağlantı koptu; bir sonraki çalışmada yeniden denenecek."
    # Indirilen kopya gercekten saglam mi?
    SONUC=$(/usr/bin/sqlite3 "$YEREL/$AD.indiriliyor/db.sqlite3" "pragma integrity_check;" 2>&1)
    [ "$SONUC" = "ok" ] || hata "İndirilen veritabanı bozuk görünüyor ($SONUC)."
    /usr/bin/tar tzf "$YEREL/$AD.indiriliyor/media.tar.gz" >/dev/null 2>&1 || hata "İndirilen medya arşivi açılamıyor."
    rm -rf "$YEREL/$AD"
    mv "$YEREL/$AD.indiriliyor" "$YEREL/$AD"
    YAZI=$(/usr/bin/sqlite3 "$YEREL/$AD/db.sqlite3" "select count(*) from core_blogyazisi;")
    echo "$AD indirildi ($(du -sh "$YEREL/$AD" | cut -f1), $YAZI yazi, saglam)"
fi

# En yeni SAKLA kopya kalir
LISTE=$(ls -1d "$YEREL"/20[0-9]* 2>/dev/null | grep -v '\.indiriliyor$' | sort)
SAYI=$(printf '%s\n' "$LISTE" | grep -c . || true)
if [ "$SAYI" -gt "$SAKLA" ]; then
    printf '%s\n' "$LISTE" | head -n $((SAYI - SAKLA)) | while read -r eski; do
        rm -rf "$eski" && echo "eski kopya silindi: $(basename "$eski")"
    done
fi
echo "$(date '+%Y-%m-%d %H:%M') bitti; bu Mac'te saklanan: $(ls -1d "$YEREL"/20[0-9]* 2>/dev/null | grep -vc '\.indiriliyor$')"
