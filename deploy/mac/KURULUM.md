# Mac'e haftalik yedek indirme

    mkdir -p ~/Yedekler/tecrit-edebiyat
    cp deploy/mac/yedek_indir.sh ~/Yedekler/tecrit-edebiyat/
    sed "s#EVDIZINI#$HOME#g" deploy/mac/com.tecritedebiyat.yedek.plist > ~/Library/LaunchAgents/com.tecritedebiyat.yedek.plist
    launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.tecritedebiyat.yedek.plist

Elle calistirmak:      launchctl kickstart gui/$(id -u)/com.tecritedebiyat.yedek
Son durum:             tail ~/Yedekler/tecrit-edebiyat/yedek.log
Kaldirmak:             launchctl bootout gui/$(id -u)/com.tecritedebiyat.yedek && rm ~/Library/LaunchAgents/com.tecritedebiyat.yedek.plist
