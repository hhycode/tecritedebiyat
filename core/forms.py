from django import forms
from django.utils.text import capfirst
from django.forms import DateInput
from django.contrib.auth.forms import PasswordChangeForm, PasswordResetForm, SetPasswordForm
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password

from .models import (
    Alinti,
    AlintiKategori,
    AnaSayfaYayinKarti,
    BlogKategori,
    BlogReklam,
    BlogUrun,
    BlogYazisi,
    Etiket,
    IletisimBasvurusu,
    Kitap,
    KitapMaliyetiAyarlari,
    KitapMaliyetTuru,
    KitapTur,
    Slider,
    SSS,
    YazarProfil,
)


def assign_tag_relations(instance, tag_names):
    tags = []
    for tag_name in tag_names:
        tag = Etiket.objects.filter(ad__iexact=tag_name).first()
        if tag:
            if tag.ad != tag_name:
                tag.ad = tag_name
                tag.slug = None
                tag.save()
        else:
            tag = Etiket.objects.create(ad=tag_name)
        tags.append(tag)
    instance.etiketler.set(tags)


class ContactForm(forms.Form):
    MAX_FILE_SIZE = 10 * 1024 * 1024

    name = forms.CharField(
        max_length=80,
        label="Ad",
        widget=forms.TextInput(
            attrs={
                "placeholder": "Adınız *",
                "autocomplete": "given-name",
            }
        ),
    )
    surname = forms.CharField(
        max_length=80,
        label="Soyad",
        widget=forms.TextInput(
            attrs={
                "placeholder": "Soyadınız *",
                "autocomplete": "family-name",
            }
        ),
    )
    email = forms.EmailField(
        label="E-posta",
        widget=forms.EmailInput(
            attrs={
                "placeholder": "E-posta adresiniz *",
                "autocomplete": "email",
            }
        ),
    )
    phone = forms.CharField(
        max_length=30,
        required=True,
        label="Telefon",
        widget=forms.TextInput(
            attrs={
                "placeholder": "Telefon numaranız *",
                "autocomplete": "tel",
            }
        ),
    )
    purpose = forms.ChoiceField(
        label="İletişim amacı",
        choices=IletisimBasvurusu.AmacSecenekleri.choices,
        widget=forms.Select(),
    )
    message = forms.CharField(
        label="Mesaj",
        widget=forms.Textarea(
            attrs={
                "placeholder": "Mesajınızı yazın *",
                "rows": 6,
            }
        ),
    )
    attachment = forms.FileField(
        required=False,
        label="Word dosyası",
        widget=forms.ClearableFileInput(
            attrs={
                "accept": ".doc,.docx",
            }
        ),
    )

    def clean_attachment(self):
        attachment = self.cleaned_data.get("attachment")
        if not attachment:
            return attachment

        ext = attachment.name.rsplit(".", 1)[-1].lower() if "." in attachment.name else ""
        if ext not in {"doc", "docx"}:
            raise forms.ValidationError("Sadece .doc veya .docx uzantılı Word dosyaları yükleyebilirsiniz.")
        if attachment.size > self.MAX_FILE_SIZE:
            raise forms.ValidationError("Dosya boyutu 10 MB sınırını aşamaz.")
        return attachment

    def clean(self):
        cleaned_data = super().clean()
        purpose = cleaned_data.get("purpose")
        attachment = cleaned_data.get("attachment")

        if purpose in {
            IletisimBasvurusu.AmacSecenekleri.YAZI_GONDERIMI,
            IletisimBasvurusu.AmacSecenekleri.KITAP_DOSYASI,
        } and not attachment:
            self.add_error("attachment", "Bu başvuru türünde Word dosyası yüklemeniz gerekiyor.")

        return cleaned_data


class SuperadminAnaSayfaYayinKartiForm(forms.ModelForm):
    class Meta:
        model = AnaSayfaYayinKarti
        fields = "__all__"
        widgets = {
            "baslik": forms.TextInput(attrs={"placeholder": "Kart başlığı"}),
            "link": forms.URLInput(attrs={"placeholder": "https://... veya /iletisim/"}),
            "etiket_bir": forms.TextInput(attrs={"placeholder": "Etiket 1"}),
            "etiket_iki": forms.TextInput(attrs={"placeholder": "Etiket 2"}),
            "etiket_uc": forms.TextInput(attrs={"placeholder": "Etiket 3"}),
        }


class PanelUserForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ["username", "first_name", "last_name", "email"]
        widgets = {
            "username": forms.TextInput(attrs={"placeholder": "Kullanıcı adı"}),
            "first_name": forms.TextInput(attrs={"placeholder": "Ad"}),
            "last_name": forms.TextInput(attrs={"placeholder": "Soyad"}),
            "email": forms.EmailInput(attrs={"placeholder": "E-posta adresi"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name in ("username", "first_name", "last_name", "email"):
            self.fields[field_name].required = True


class PanelProfileForm(forms.ModelForm):
    class Meta:
        model = YazarProfil
        fields = ["biyografi", "fotograf", "instagram", "x_hesabi", "websitesi"]
        widgets = {
            "biyografi": forms.Textarea(attrs={"placeholder": "Kısa biyografin", "rows": 6}),
            "instagram": forms.URLInput(attrs={"placeholder": "Instagram bağlantısı"}),
            "x_hesabi": forms.URLInput(attrs={"placeholder": "X bağlantısı"}),
            "websitesi": forms.URLInput(attrs={"placeholder": "Website bağlantısı"}),
        }


class PanelPasswordForm(PasswordChangeForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["old_password"].widget.attrs.update({"placeholder": "Mevcut şifre"})
        self.fields["new_password1"].widget.attrs.update({"placeholder": "Yeni şifre"})
        self.fields["new_password2"].widget.attrs.update({"placeholder": "Yeni şifre tekrar"})


class SifremiUnuttumForm(PasswordResetForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["email"].widget.attrs.update({"placeholder": "Kayıtlı e-posta adresin"})


class SifreSifirlaForm(SetPasswordForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["new_password1"].widget.attrs.update({"placeholder": "Yeni şifre"})
        self.fields["new_password2"].widget.attrs.update({"placeholder": "Yeni şifre tekrar"})


class PanelBlogYazisiForm(forms.ModelForm):
    etiketler_input = forms.CharField(
        required=False,
        label="Etiketler",
        help_text="Virgülle ayırın: seo, web tasarım, dijital pazarlama",
    )

    class Meta:
        model = BlogYazisi
        fields = ["baslik", "ozet", "icerik", "gorsel", "kategoriler", "meta_title", "meta_description", "seo_keywords", "durum"]
        widgets = {
            "baslik": forms.TextInput(attrs={"placeholder": "Yazı başlığı"}),
            "ozet": forms.Textarea(attrs={"placeholder": "Kısa özet", "rows": 4}),
            "icerik": forms.Textarea(
                attrs={
                    "rows": 24,
                    "data-editor": "ckeditor",
                }
            ),
            "kategoriler": forms.SelectMultiple(attrs={"size": 6}),
            "meta_title": forms.TextInput(attrs={"placeholder": "SEO başlığı"}),
            "meta_description": forms.Textarea(attrs={"placeholder": "SEO açıklaması", "rows": 3}),
            "seo_keywords": forms.TextInput(attrs={"placeholder": "SEO anahtar kelimeleri"}),
        }

    class Media:
        js = (
            "https://cdn.ckeditor.com/4.22.1/full-all/ckeditor.js",
            "js/admin-blog-ckeditor.js",
        )

    def __init__(self, *args, is_superadmin=False, **kwargs):
        super().__init__(*args, **kwargs)
        turkce_etiketleri_uygula(self)
        self.is_superadmin = is_superadmin
        self.fields["kategoriler"].queryset = self.fields["kategoriler"].queryset.order_by("ad")
        self.fields["kategoriler"].required = False
        self.fields["kategoriler"].label = "Kategori"
        self.fields["kategoriler"].widget.attrs.update(
            {
                "class": "panel-multiselect",
                "data-placeholder": "Kategori seç",
            }
        )
        self.fields["meta_title"].label = "SEO başlığı"
        self.fields["meta_description"].label = "SEO açıklaması"
        self.fields["seo_keywords"].label = "SEO anahtar kelimeleri"
        self.fields["seo_keywords"].help_text = "Virgülle ayırın."
        if is_superadmin:
            self.fields["durum"].choices = [
                (BlogYazisi.DurumSecenekleri.YAYINDA, "Yayında"),
                (BlogYazisi.DurumSecenekleri.TASLAK, "Taslak"),
                (BlogYazisi.DurumSecenekleri.INCELEMEDE, "İncelemede"),
            ]
        else:
            self.fields["durum"].choices = [
                (BlogYazisi.DurumSecenekleri.INCELEMEDE, "İncelemede"),
            ]
            self.fields["durum"].widget = forms.HiddenInput()
            self.fields["durum"].initial = BlogYazisi.DurumSecenekleri.INCELEMEDE
        if not self.instance.pk and is_superadmin:
            self.fields["durum"].initial = BlogYazisi.DurumSecenekleri.YAYINDA
        if self.instance.pk and not self.is_bound:
            secili_kategoriler = list(self.instance.kategoriler.values_list("pk", flat=True))
            if self.instance.kategori_id and self.instance.kategori_id not in secili_kategoriler:
                secili_kategoriler.insert(0, self.instance.kategori_id)
            self.initial["kategoriler"] = secili_kategoriler
            self.initial["etiketler_input"] = self.instance.etiket_listesi

    def save(self, commit=True):
        yazi = super().save(commit=False)
        secili_kategoriler = list(self.cleaned_data.get("kategoriler") or [])
        etiketler_raw = self.cleaned_data.get("etiketler_input", "")
        yazi.kategori = secili_kategoriler[0] if secili_kategoriler else None
        etiket_isimleri = [parca.strip() for parca in etiketler_raw.split(",") if parca.strip()]
        etiket_isimleri = etiket_isimleri[:15]
        original_save_m2m = self.save_m2m

        def save_related():
            original_save_m2m()
            assign_tag_relations(yazi, etiket_isimleri)

        self.save_m2m = save_related
        if commit:
            yazi.save()
            self.save_m2m()
        return yazi


# Modelde verbose_name verilmemis alanlarin Turkce etiketleri (ozel etiketi olan alanlara dokunulmaz)
ALAN_ETIKETLERI = {
    "aciklama": "Açıklama",
    "baslik": "Başlık",
    "dogum_tarihi": "Doğum tarihi",
    "etiket_bir": "Etiket 1",
    "etiket_iki": "Etiket 2",
    "etiket_uc": "Etiket 3",
    "fotograf": "Fotoğraf",
    "gorsel": "Görsel",
    "icerik": "İçerik",
    "indirimli_fiyat": "İndirimli fiyat",
    "isim": "İsim",
    "kitapyurdu_link": "Kitapyurdu Linki",
    "link": "Bağlantı",
    "masaustu_gorsel": "Masaüstü görseli",
    "meta_description": "SEO açıklaması",
    "meta_title": "SEO başlığı",
    "mobil_gorsel": "Mobil görsel",
    "onayli": "Onaylı",
    "one_cikan": "Öne çıkan",
    "one_cikar": "Öne çıkar",
    "ozet": "Özet",
    "resim": "Görsel",
    "satis_linki": "Satış linki",
    "sayfa_no": "Sayfa numarası",
    "sira": "Sıra",
    "slug": "Kısa ad (URL)",
    "turler": "Türler",
    "user": "Kullanıcı hesabı",
    "websitesi": "Web sitesi",
    "x_hesabi": "X hesabı",
    "yayin_tarihi": "Yayın tarihi",
    "yayinda": "Yayında",
}


def turkce_etiketleri_uygula(form):
    for name, field in form.fields.items():
        if name in ALAN_ETIKETLERI and field.label == capfirst(name.replace("_", " ")):
            field.label = ALAN_ETIKETLERI[name]


class SuperadminStyledModelForm(forms.ModelForm):
    textarea_rows = 5
    multi_select_size = 6

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        turkce_etiketleri_uygula(self)
        for name, field in self.fields.items():
            widget = field.widget
            if isinstance(widget, forms.HiddenInput):
                continue
            if isinstance(widget, forms.Textarea):
                widget.attrs.setdefault("rows", self.textarea_rows)
                widget.attrs.setdefault("placeholder", field.label)
            elif isinstance(widget, forms.DateInput):
                widget.input_type = "date"
            elif isinstance(widget, forms.SelectMultiple):
                widget.attrs.setdefault("size", self.multi_select_size)
                widget.attrs["class"] = "panel-multiselect"
            elif isinstance(widget, forms.ClearableFileInput):
                widget.attrs.setdefault("class", "panel-file-input")
            elif not isinstance(widget, forms.CheckboxInput):
                widget.attrs.setdefault("placeholder", field.label)


class SuperadminAlintiKategoriForm(SuperadminStyledModelForm):
    class Meta:
        model = AlintiKategori
        fields = ["ad", "slug"]


class SuperadminSSSForm(SuperadminStyledModelForm):
    class Meta:
        model = SSS
        fields = ["soru", "cevap", "sira", "aktif"]


class SuperadminBlogKategoriForm(SuperadminStyledModelForm):
    class Meta:
        model = BlogKategori
        fields = ["ad", "slug"]


class SuperadminBlogReklamForm(SuperadminStyledModelForm):
    class Meta:
        model = BlogReklam
        fields = ["isim", "sponsor_etiketi", "link", "resim", "aktif", "sira"]


class SuperadminBlogUrunForm(SuperadminStyledModelForm):
    class Meta:
        model = BlogUrun
        fields = [
            "isim",
            "satis_linki",
            "resim",
            "fiyat",
            "indirimli_fiyat",
            "kategori_etiketi",
            "aktif",
            "one_cikar",
            "sira",
        ]


class SuperadminKitapTurForm(SuperadminStyledModelForm):
    class Meta:
        model = KitapTur
        fields = ["ad", "slug", "aciklama"]


class SuperadminSliderForm(SuperadminStyledModelForm):
    class Meta:
        model = Slider
        fields = ["baslik", "aciklama", "gorsel", "link", "aktif", "sira"]


class SuperadminYazarProfilForm(SuperadminStyledModelForm):
    class Meta:
        model = YazarProfil
        fields = [
            "user",
            "ad_soyad",
            "slug",
            "biyografi",
            "dogum_tarihi",
            "fotograf",
            "instagram",
            "x_hesabi",
            "websitesi",
            "rol",
            "onayli",
        ]
        widgets = {
            "dogum_tarihi": DateInput(),
        }


class SuperadminKitapForm(SuperadminStyledModelForm):
    etiketler_input = forms.CharField(
        required=False,
        label="Etiketler",
        help_text="Virgülle ayırın. En fazla 15 etiket.",
    )

    class Meta:
        model = Kitap
        fields = [
            "ad",
            "slug",
            "yazar",
            "ikinci_yazar",
            "aciklama",
            "kapak_resmi",
            "yayin_tarihi",
            "one_cikan",
            "yayinda",
            "meta_title",
            "meta_description",
            "kitapyurdu_link",
            "dr_link",
            "trendyol_link",
            "shopier_link",
            "turler",
        ]
        widgets = {
            "yayin_tarihi": DateInput(),
            "meta_description": forms.Textarea(attrs={"rows": 4}),
        }
        labels = {
            "ikinci_yazar": "İkinci Yazar",
            "dr_link": "D&R Linki",
            "trendyol_link": "Trendyol Linki",
            "shopier_link": "Shopier Linki",
            "fiyat": "Fiyat (TL) - Sitemizden Satış",
            "stok_adedi": "Stok Adedi",
            "dogrudan_satis_aktif": "Sitemizden Satışa Açık",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk and not self.is_bound:
            self.initial["etiketler_input"] = ", ".join(
                self.instance.etiketler.order_by("ad").values_list("ad", flat=True)
            )

    def save(self, commit=True):
        kitap = super().save(commit=False)
        etiketler_raw = self.cleaned_data.get("etiketler_input", "")
        etiket_isimleri = [parca.strip() for parca in etiketler_raw.split(",") if parca.strip()][:15]
        original_save_m2m = self.save_m2m

        def save_related():
            original_save_m2m()
            assign_tag_relations(kitap, etiket_isimleri)

        self.save_m2m = save_related
        if commit:
            kitap.save()
            self.save_m2m()
        return kitap


class SuperadminAlintiForm(SuperadminStyledModelForm):
    etiketler_input = forms.CharField(
        required=False,
        label="Etiketler",
        help_text="Virgülle ayırın. En fazla 15 etiket.",
    )

    class Meta:
        model = Alinti
        fields = ["kitap", "metin", "sayfa_no", "kategori", "one_cikan", "yayinda"]
        widgets = {
            "metin": forms.Textarea(attrs={"rows": 8}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk and not self.is_bound:
            self.initial["etiketler_input"] = ", ".join(
                self.instance.etiketler.order_by("ad").values_list("ad", flat=True)
            )

    def save(self, commit=True):
        alinti = super().save(commit=False)
        etiketler_raw = self.cleaned_data.get("etiketler_input", "")
        etiket_isimleri = [parca.strip() for parca in etiketler_raw.split(",") if parca.strip()][:15]
        original_save_m2m = self.save_m2m

        def save_related():
            original_save_m2m()
            assign_tag_relations(alinti, etiket_isimleri)

        self.save_m2m = save_related
        if commit:
            alinti.save()
            self.save_m2m()
        return alinti


class SuperadminKullaniciForm(SuperadminStyledModelForm):
    class Meta:
        model = User
        fields = ["username", "first_name", "last_name", "email", "is_active", "is_staff", "is_superuser"]
        labels = {
            "username": "Kullanıcı adı",
            "first_name": "Ad",
            "last_name": "Soyad",
            "email": "E-posta",
            "is_active": "Aktif",
            "is_staff": "Personel (admin girişi yapabilir)",
            "is_superuser": "Süper kullanıcı (tüm yetkiler)",
        }


class SuperadminKullaniciSifreForm(forms.Form):
    yeni_sifre1 = forms.CharField(
        label="Yeni şifre",
        widget=forms.PasswordInput(attrs={"placeholder": "Yeni şifre", "autocomplete": "new-password"}),
    )
    yeni_sifre2 = forms.CharField(
        label="Yeni şifre (tekrar)",
        widget=forms.PasswordInput(attrs={"placeholder": "Yeni şifre (tekrar)", "autocomplete": "new-password"}),
    )

    def clean(self):
        cleaned = super().clean()
        sifre1 = cleaned.get("yeni_sifre1")
        sifre2 = cleaned.get("yeni_sifre2")
        if sifre1 and sifre2 and sifre1 != sifre2:
            raise forms.ValidationError("Girdiğin şifreler eşleşmiyor.")
        if sifre1:
            validate_password(sifre1)
        return cleaned


class SuperadminKitapMaliyetiForm(SuperadminStyledModelForm):
    class Meta:
        model = KitapMaliyetiAyarlari
        fields = ["sayfa_basi_ucret", "sabit_ucret"]
        labels = {
            "sayfa_basi_ucret": "Sayfa başı ücret (TL)",
            "sabit_ucret": "Sabit hazırlık ve üretim bedeli (TL)",
        }


class SuperadminKitapMaliyetTuruForm(SuperadminStyledModelForm):
    class Meta:
        model = KitapMaliyetTuru
        fields = ["ad", "hesaplama_yontemi", "kelime_yogunlugu", "sira"]
        labels = {
            "ad": "Tür adı",
            "hesaplama_yontemi": "Hesaplama yöntemi",
            "kelime_yogunlugu": "Sayfa başı ortalama kelime sayısı",
            "sira": "Listeleme sırası",
        }
