// Tarayicidan ses kaydi (MediaRecorder). Yazi formundaki "Ses kaydet" sekmesi; kayit dinlenip
// onaylaninca medya.js'in yukleme akisiyla (ilerleme cubugu, sunucu denetimi) eklenir.
(function () {
    var kok = document.querySelector("[data-medya]");
    var M = window.TEMedya;
    if (!kok || !M) return;
    var kayit = kok.querySelector("[data-kayit]");
    var KAYIT_SURESI = +kok.dataset.kayitSuresi;
    var hataGoster = M.hataGoster;
    var k = {
        basla: kayit.querySelector("[data-kayit-basla]"),
        durdur: kayit.querySelector("[data-kayit-durdur]"),
        ekle: kayit.querySelector("[data-kayit-ekle]"),
        yeniden: kayit.querySelector("[data-kayit-yeniden]"),
        dinle: kayit.querySelector("[data-kayit-dinle]"),
        sure: kayit.querySelector("[data-kayit-sure]"),
        bilgi: kayit.querySelector("[data-kayit-bilgi]"),
    };
    var kaydedici = null, akis = null, parcalar = [], sonKayit = null, sayac = null, baslangic = 0, dinleAdresi = null;

    function kayitDestekleniyor() {
        return !!(navigator.mediaDevices && navigator.mediaDevices.getUserMedia && window.MediaRecorder);
    }
    function kayitBicimi() {
        var adaylar = ["audio/webm;codecs=opus", "audio/mp4", "audio/ogg;codecs=opus", "audio/webm"];
        for (var i = 0; i < adaylar.length; i++) {
            if (MediaRecorder.isTypeSupported && MediaRecorder.isTypeSupported(adaylar[i])) return adaylar[i];
        }
        return "";
    }
    function uzantiBul(mime) {
        if (/mp4|aac|m4a/.test(mime)) return "m4a";
        if (/ogg/.test(mime)) return "ogg";
        return "webm";
    }
    function sureYaz(sn) {
        var d = Math.floor(sn / 60), s = Math.floor(sn % 60);
        k.sure.textContent = (d < 10 ? "0" : "") + d + ":" + (s < 10 ? "0" : "") + s;
    }
    function goster(durum) {
        // durum: hazir | kayitta | dinleme
        kayit.classList.toggle("is-kayitta", durum === "kayitta");
        k.basla.hidden = durum !== "hazir";
        k.durdur.hidden = durum !== "kayitta";
        k.ekle.hidden = k.yeniden.hidden = k.dinle.hidden = durum !== "dinleme";
    }
    function akisiKapat() {
        if (akis) akis.getTracks().forEach(function (t) { t.stop(); });
        akis = null;
        clearInterval(sayac);
    }

    if (!kayitDestekleniyor()) {
        k.bilgi.textContent = "Tarayıcınız ses kaydını desteklemiyor. Güncel bir Chrome, Safari, Firefox ya da Edge kullanın veya kaydınızı dosya olarak yükleyin.";
        k.basla.disabled = true;
    }

    k.basla.addEventListener("click", function () {
        hataGoster("");
        if (M.doluMu()) { hataGoster("En fazla " + M.enFazla + " medya ekleyebilirsiniz."); return; }
        k.basla.disabled = true;
        navigator.mediaDevices.getUserMedia({ audio: { echoCancellation: true, noiseSuppression: true } }).then(function (s) {
            akis = s;
            parcalar = [];
            var bicim = kayitBicimi();
            kaydedici = bicim ? new MediaRecorder(s, { mimeType: bicim }) : new MediaRecorder(s);
            kaydedici.addEventListener("dataavailable", function (e) { if (e.data && e.data.size) parcalar.push(e.data); });
            kaydedici.addEventListener("stop", function () {
                akisiKapat();
                var mime = (kaydedici.mimeType || bicim || "audio/webm").split(";")[0];
                sonKayit = new Blob(parcalar, { type: mime });
                if (dinleAdresi) URL.revokeObjectURL(dinleAdresi);
                dinleAdresi = URL.createObjectURL(sonKayit);
                k.dinle.src = dinleAdresi;
                k.bilgi.textContent = "Kaydı dinleyin. Beğendiyseniz “Kaydı ekle”ye basın.";
                goster("dinleme");
            });
            kaydedici.start(1000);
            baslangic = Date.now();
            sureYaz(0);
            sayac = setInterval(function () {
                var gecen = (Date.now() - baslangic) / 1000;
                sureYaz(gecen);
                if (gecen >= KAYIT_SURESI) {
                    k.bilgi.textContent = "En uzun kayıt süresine ulaşıldı.";
                    kaydedici.stop();
                }
            }, 250);
            k.bilgi.textContent = "Kaydediliyor… Bitirince “Durdur”a basın.";
            goster("kayitta");
            k.durdur.focus();
        }).catch(function (hata) {
            akisiKapat();
            var ad = hata && hata.name;
            if (ad === "NotAllowedError" || ad === "SecurityError") {
                hataGoster("Mikrofon izni verilmedi. Adres çubuğundaki kilit simgesinden bu siteye mikrofon izni verip yeniden deneyin.");
            } else if (ad === "NotFoundError" || ad === "OverconstrainedError") {
                hataGoster("Mikrofon bulunamadı. Bir mikrofon bağlayıp yeniden deneyin.");
            } else if (ad === "NotReadableError") {
                hataGoster("Mikrofon başka bir uygulama tarafından kullanılıyor olabilir. Onu kapatıp yeniden deneyin.");
            } else {
                hataGoster("Kayıt başlatılamadı. Kaydınızı dosya olarak yüklemeyi deneyebilirsiniz.");
            }
        }).then(function () { k.basla.disabled = !kayitDestekleniyor(); });
    });

    k.durdur.addEventListener("click", function () {
        if (kaydedici && kaydedici.state !== "inactive") kaydedici.stop();
    });

    k.yeniden.addEventListener("click", function () {
        sonKayit = null;
        k.dinle.removeAttribute("src");
        sureYaz(0);
        k.bilgi.textContent = "Hazır olduğunuzda “Kaydı başlat”a basın.";
        goster("hazir");
    });

    k.ekle.addEventListener("click", function () {
        if (!sonKayit) return;
        var simdi = new Date();
        var damga = simdi.toISOString().slice(0, 16).replace(/[-:T]/g, "");
        var ad = "ses-kaydi-" + damga + "." + uzantiBul(sonKayit.type);
        var dosya;
        try { dosya = new File([sonKayit], ad, { type: sonKayit.type }); }
        catch (e) { dosya = sonKayit; dosya.name = ad; }
        M.yukle(dosya, "ses");
        k.yeniden.click();
        k.bilgi.textContent = "Kayıt ekleniyor. İsterseniz yeni bir kayıt yapabilirsiniz.";
    });

    window.addEventListener("pagehide", akisiKapat);
})();
