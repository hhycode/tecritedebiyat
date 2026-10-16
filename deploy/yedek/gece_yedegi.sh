#!/bin/bash
# Gece yedegi (yedek-al.timer ile her gece 03:30). Sonunda kodu GitHub'a da gonderir.
# Veritabani SQLite'in kendi yedekleme yontemiyle alinir (site calisirken de tutarli kalir),
# media klasoru arsivlenir. Son 14 gece saklanir; eskiler silinir.
# Klasor: ~/yayinevim/backups/gece/YYYYMMDD/{db.sqlite3, media.tar.gz}
set -euo pipefail

KOK=/home/hhycode/yayinevim
HEDEF="$KOK/backups/gece"
SAKLA=14
D="$HEDEF/$(date +%Y%m%d)"
GECICI="$D.yariminda"

mkdir -p "$HEDEF"
rm -rf "$GECICI"
mkdir -p "$GECICI"
cd "$KOK"

"$KOK/venv/bin/python" - "$GECICI/db.sqlite3" <<'PY'
import sqlite3, sys
kaynak = sqlite3.connect("db.sqlite3")
hedef = sqlite3.connect(sys.argv[1])
kaynak.backup(hedef)
durum = hedef.execute("pragma integrity_check").fetchone()[0]
yazi = hedef.execute("select count(*) from core_blogyazisi").fetchone()[0]
alinti = hedef.execute("select count(*) from core_alinti").fetchone()[0]
hedef.close()
kaynak.close()
if durum != "ok":
    sys.exit(f"HATA: veritabani yedegi bozuk ({durum})")
print(f"veritabani tamam: {yazi} yazi, {alinti} alinti")
PY

tar czf "$GECICI/media.tar.gz" media
tar tzf "$GECICI/media.tar.gz" > /dev/null   # arsiv okunabiliyor mu

# Yarim kalan yedek tamamlanmis gibi gorunmesin: ancak her sey bitince yerine tasinir
rm -rf "$D"
mv "$GECICI" "$D"

# En yeni SAKLA gece kalir
ls -1d "$HEDEF"/20[0-9]* 2>/dev/null | sort | head -n -"$SAKLA" | xargs -r rm -rf

# Kodun GitHub'daki gizli kopyasini da guncel tut (sunucuda dogrudan yapilan degisiklikler icin);
# basarisiz olsa da yedegi bozmaz
if git -C "$KOK" push -q github master 2>/dev/null; then
    echo "github: guncel ($(git -C "$KOK" rev-parse --short HEAD))"
else
    echo "github: gonderilemedi (yedek etkilenmedi)"
fi

echo "yedek hazir: $D ($(du -sh "$D" | cut -f1)); sunucuda saklanan gece sayisi: $(ls -1d "$HEDEF"/20[0-9]* | wc -l)"
