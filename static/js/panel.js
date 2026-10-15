// Yazar paneli davranislari (templates/panel/). Tema, kullanici menusu ve data-onay superadmin.js'te.
(function () {
    // Gonderilen formun dugmesi "Kaydediliyor..." durumuna gecer, ikinci kez gonderim engellenir.
    // superadmin.js'teki onay penceresi iptal edilirse olay defaultPrevented gelir; o zaman dokunulmaz.
    document.addEventListener("submit", function (olay) {
        var form = olay.target;
        if (olay.defaultPrevented || !form.hasAttribute("data-gonderim")) return;
        if (form.dataset.gonderiliyor === "1") { olay.preventDefault(); return; }
        form.dataset.gonderiliyor = "1";
        var dugme = olay.submitter || form.querySelector("[type=submit]");
        if (!dugme) return;
        // Devre disi dugmenin name/value degeri gonderilmez; gizli alana kopyalanir
        if (dugme.name) {
            var gizli = document.createElement("input");
            gizli.type = "hidden";
            gizli.name = dugme.name;
            gizli.value = dugme.value;
            form.appendChild(gizli);
        }
        dugme.classList.add("is-loading");
        var metin = dugme.querySelector("[data-metin]");
        if (metin && dugme.dataset.yukleniyor) metin.textContent = dugme.dataset.yukleniyor;
        form.querySelectorAll("[type=submit]").forEach(function (d) {
            setTimeout(function () { d.disabled = true; }, 0);
        });
    });

    // Geri tusuyla donulen sayfada dugmeler kilitli kalmasin
    window.addEventListener("pageshow", function (olay) {
        if (!olay.persisted) return;
        document.querySelectorAll("form[data-gonderim]").forEach(function (form) {
            form.dataset.gonderiliyor = "";
            form.querySelectorAll("[type=submit]").forEach(function (d) {
                d.disabled = false;
                d.classList.remove("is-loading");
            });
        });
    });

    // Gorsel secimi: onizleme, dosya adi, "kaldir" kutusuyla karsilikli temizleme
    document.querySelectorAll("[data-gorsel]").forEach(function (kap) {
        var girdi = kap.querySelector("input[type=file]");
        var onizleme = kap.querySelector("[data-onizleme]");
        var ad = kap.querySelector("[data-dosya-adi]");
        var kaldir = kap.querySelector("[data-kaldir]");
        if (!girdi) return;
        var ilk = onizleme ? onizleme.innerHTML : "";
        var ilkAd = ad ? ad.textContent : "";
        girdi.addEventListener("change", function () {
            var dosya = girdi.files && girdi.files[0];
            if (!dosya) return;
            if (kaldir) kaldir.checked = false;
            if (ad) ad.textContent = dosya.name;
            if (dosya.size > 5 * 1024 * 1024 && ad) {
                ad.textContent = dosya.name + " · 5 MB'tan büyük, kaydederken reddedilecek";
            }
            if (onizleme && /^image\//.test(dosya.type)) {
                var okuyucu = new FileReader();
                okuyucu.onload = function (e) {
                    var img = document.createElement("img");
                    img.src = e.target.result;
                    img.alt = "";
                    onizleme.innerHTML = "";
                    onizleme.appendChild(img);
                    onizleme.classList.remove("yp-avatar--harf");
                };
                okuyucu.readAsDataURL(dosya);
            }
        });
        if (kaldir) {
            kaldir.addEventListener("change", function () {
                if (!kaldir.checked) return;
                girdi.value = "";
                if (ad) ad.textContent = ilkAd;
                if (onizleme) onizleme.innerHTML = ilk;
            });
        }
    });

    // Karakter sayaci: data-sayac="<alan id>" [data-sinir="320"]
    document.querySelectorAll("[data-sayac]").forEach(function (sayac) {
        var alan = document.getElementById(sayac.getAttribute("data-sayac"));
        if (!alan) return;
        var sinir = parseInt(sayac.getAttribute("data-sinir") || "0", 10);
        function guncelle() {
            var n = alan.value.length;
            sayac.textContent = sinir ? n + " / " + sinir : n + " karakter";
            sayac.classList.toggle("is-over", sinir > 0 && n > sinir);
        }
        alan.addEventListener("input", guncelle);
        guncelle();
    });

    // Sifre goster/gizle
    document.querySelectorAll("[data-sifre-goster]").forEach(function (dugme) {
        var alan = dugme.parentElement.querySelector("input");
        if (!alan) return;
        dugme.addEventListener("click", function () {
            var gizli = alan.type === "password";
            alan.type = gizli ? "text" : "password";
            dugme.setAttribute("aria-label", gizli ? "Şifreyi gizle" : "Şifreyi göster");
            dugme.setAttribute("aria-pressed", gizli ? "true" : "false");
            dugme.querySelector("i").className = gizli ? "ph ph-eye-slash" : "ph ph-eye";
        });
    });
})();
