# Icerik ve kullanici yonetimi core/admin_urls.py + core/views.py altindaki
# "superadmin" panelinden yapiliyor. Django'nun kendi admin arayuzu (admin.site.urls)
# sadece giris/cikis/parola degistirme altyapisi ile auth.Group ve admin_interface.Theme
# yonetimi icin (superadmin panelinden linklenerek) etkin tutuluyor; buraya baska
# model kaydi eklenmemeli.
