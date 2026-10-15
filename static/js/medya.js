// Yazi formunda ses/video ekleme (templates/panel/yazi_form.html, #medya).
// Dosyalar yazidan bagimsiz, ilerleme cubuguyla yuklenir; yazi kaydedilince yaziya baglanir.
(function () {
    var kok = document.querySelector("[data-medya]");
    if (!kok) return;
    var form = kok.closest("form");
    var liste = kok.querySelector("[data-medya-liste]");
    var ekleAlani = kok.querySelector("[data-medya-ekle]");
    var doluNotu = kok.querySelector("[data-medya-dolu]");
    var yuklemeler = kok.querySelector("[data-medya-yuklemeler]");
    var hataKutusu = kok.querySelector("[data-medya-hata]");
    var csrf = form.querySelector("input[name=csrfmiddlewaretoken]").value;
    var EN_FAZLA = +kok.dataset.enFazla;
    var SES_SINIRI = +kok.dataset.sesSiniri;
    var VIDEO_SINIRI = +kok.dataset.videoSiniri;
    var ACIKLAMA_SINIRI = kok.dataset.aciklamaSiniri;
    var SES_UZANTILARI = ["mp3", "m4a", "ogg", "wav"];
    var VIDEO_UZANTILARI = ["mp4", "webm"];
    var suren = 0; // devam eden yukleme sayisi

    function mb(bayt) { return (bayt / 1048576).toFixed(1).replace(".", ",") + " MB"; }

    function hataGoster(mesaj) {
        hataKutusu.textContent = mesaj || "";
        hataKutusu.hidden = !mesaj;
    }

    function kartSayisi() {
        return liste.querySelectorAll("[data-medya-id]").length;
    }

    function durumuGuncelle() {
        var dolu = kartSayisi() + suren >= EN_FAZLA;
        ekleAlani.hidden = dolu;
        doluNotu.hidden = !dolu;
    }

    // ---------- Kart ----------
    function el(etiket, ozellikler, cocuklar) {
        var e = document.createElement(etiket);
        Object.keys(ozellikler || {}).forEach(function (k) {
            if (k === "metin") e.textContent = ozellikler[k];
            else if (k === "sinif") e.className = ozellikler[k];
            else e.setAttribute(k, ozellikler[k]);
        });
        (cocuklar || []).forEach(function (c) { if (c) e.appendChild(c); });
        return e;
    }

    function oynatici(m) {
        if (m.kaynak === "dosya") {
            var o = el(m.tur === "video" ? "video" : "audio", { controls: "", preload: "metadata", src: m.url });
            if (m.tur === "video") o.setAttribute("playsinline", "");
            return o;
        }
        var f = el("iframe", {
            src: m.gomme, title: m.saglayici + " oynatıcısı", loading: "lazy",
            allow: "autoplay; encrypted-media; fullscreen; picture-in-picture",
            referrerpolicy: "strict-origin-when-cross-origin", allowfullscreen: "",
        });
        if (m.yukseklik) f.setAttribute("height", m.yukseklik); else f.className = "is-video";
        return f;
    }

    function kartEkle(m) {
        var ikon = m.kaynak === "baglanti" ? "ph-link" : m.tur === "video" ? "ph-film-strip" : "ph-microphone";
        var turAdi = m.tur === "video" ? "Video" : "Ses";
        var kimlik = "medya-aciklama-" + m.id;
        var kart = el("li", { sinif: "yp-medya", "data-medya-id": m.id, "data-kaynak": m.kaynak }, [
            el("input", { type: "hidden", name: "medya", value: m.id }),
            el("div", { sinif: "yp-medya__head" }, [
                el("i", { sinif: "ph " + ikon + " yp-medya__icon", "aria-hidden": "true" }),
                el("div", { sinif: "yp-medya__info" }, [
                    el("strong", { metin: m.kaynak === "baglanti" ? m.saglayici : m.ad }),
                    el("span", { metin: m.kaynak === "baglanti" ? turAdi + " bağlantısı" : turAdi + " · " + m.boyut }),
                ]),
                el("button", { type: "button", sinif: "sa-btn sa-btn--danger-outline sa-btn--sm", "data-medya-kaldir": "" }, [
                    el("i", { sinif: "ph ph-x", "aria-hidden": "true" }), document.createTextNode("Kaldır"),
                ]),
            ]),
            el("div", { sinif: "yp-medya__oynatici" }, [oynatici(m)]),
            el("div", { sinif: "sa-field" }, [
                el("label", { for: kimlik }, [
                    document.createTextNode("Açıklama ya da transkript "),
                    el("span", { sinif: "sa-muted fw-normal", metin: "(isteğe bağlı)" }),
                ]),
                el("textarea", {
                    id: kimlik, name: "medya_aciklama_" + m.id, rows: "2", maxlength: ACIKLAMA_SINIRI,
                    placeholder: "Görme ya da işitme engelli okurlar için kısa açıklama veya metnin tamamı",
                }),
            ]),
        ]);
        liste.appendChild(kart);
        durumuGuncelle();
        return kart;
    }

    // Kaldir: kaydedilmemis yukleme sunucudan hemen silinir; yaziya bagli medya yazi kaydedilince kalkar
    liste.addEventListener("click", function (olay) {
        var dugme = olay.target.closest("[data-medya-kaldir]");
        if (!dugme) return;
        var kart = dugme.closest("[data-medya-id]");
        var bagli = kart.dataset.bagli === "1";
        var soru = bagli
            ? "Bu medya yazınızı kaydettiğinizde kaldırılacak. Devam edilsin mi?"
            : "Bu medya kaldırılacak. Devam edilsin mi?";
        if (!window.confirm(soru)) return;
        if (!bagli) {
            var veri = new FormData();
            veri.append("csrfmiddlewaretoken", csrf);
            fetch(kok.dataset.silUrl.replace("/0/", "/" + kart.dataset.medyaId + "/"), { method: "POST", body: veri, credentials: "same-origin" })
                .catch(function () {}); // basarisiz olsa da 24 saat sonra temizlenir
        }
        kart.remove();
        durumuGuncelle();
    });

    // ---------- Sunucu yaniti ----------
    function yanitHatasi(xhr) {
        if (xhr.status === 413) return "Dosya sunucunun kabul ettiği boyutu aşıyor.";
        if (xhr.status === 403) return "Oturum süreniz dolmuş olabilir. Sayfayı yenileyip yeniden deneyin.";
        if (xhr.status >= 500) return "Sunucuda bir sorun oluştu. Biraz sonra yeniden deneyin.";
        try {
            var j = JSON.parse(xhr.responseText);
            if (j.hata) return j.hata;
        } catch (e) {
            // JSON yerine giris sayfasi dondu: oturum kapanmis
            if (/<html/i.test(xhr.responseText || "")) return "Oturumunuz kapanmış. Sayfayı yenileyip yeniden giriş yapın.";
        }
        return "Beklenmeyen bir yanıt alındı. Yeniden deneyin.";
    }

    // ---------- Dosya yukleme ----------
    function uzantisi(ad) {
        var p = (ad || "").toLowerCase().split(".");
        return p.length > 1 ? p.pop() : "";
    }

    function istemciKontrolu(dosya, tur) {
        var uz = uzantisi(dosya.name);
        var ses = tur === "ses" || SES_UZANTILARI.indexOf(uz) !== -1;
        if (SES_UZANTILARI.indexOf(uz) === -1 && VIDEO_UZANTILARI.indexOf(uz) === -1) {
            return "Bu dosya türü desteklenmiyor. Ses için MP3, M4A, OGG ya da WAV; video için MP4 ya da WebM yükleyebilirsiniz.";
        }
        var sinir = ses ? SES_SINIRI : VIDEO_SINIRI;
        if (dosya.size > sinir) {
            return (ses ? "Ses dosyası" : "Video") + " en fazla " + Math.round(sinir / 1048576) + " MB olabilir; bu dosya " + mb(dosya.size) + ".";
        }
        return "";
    }

    function yukle(dosya, tur) {
        hataGoster("");
        if (kartSayisi() + suren >= EN_FAZLA) { hataGoster("En fazla " + EN_FAZLA + " medya ekleyebilirsiniz."); return; }
        var sorun = istemciKontrolu(dosya, tur);
        if (sorun) { hataGoster(sorun); return; }

        var cubuk = el("span", { sinif: "yp-ilerleme__dolgu" });
        var yuzde = el("span", { sinif: "yp-ilerleme__yuzde", metin: "%0" });
        var iptal = el("button", { type: "button", sinif: "sa-btn sa-btn--secondary sa-btn--sm", metin: "İptal" });
        var satir = el("li", { sinif: "yp-ilerleme" }, [
            el("div", { sinif: "yp-ilerleme__ust" }, [
                el("span", { sinif: "yp-ilerleme__ad", metin: dosya.name }),
                yuzde, iptal,
            ]),
            el("div", { sinif: "yp-ilerleme__cubuk", role: "progressbar", "aria-valuemin": "0", "aria-valuemax": "100", "aria-valuenow": "0", "aria-label": dosya.name + " yükleniyor" }, [cubuk]),
        ]);
        yuklemeler.appendChild(satir);
        suren++;
        durumuGuncelle();

        var veri = new FormData();
        veri.append("dosya", dosya, dosya.name);
        if (tur) veri.append("tur", tur);
        var xhr = new XMLHttpRequest();
        xhr.open("POST", kok.dataset.yukleUrl);
        xhr.setRequestHeader("X-CSRFToken", csrf);
        xhr.setRequestHeader("X-Requested-With", "XMLHttpRequest");
        xhr.upload.addEventListener("progress", function (e) {
            if (!e.lengthComputable) return;
            var p = Math.round((e.loaded / e.total) * 100);
            cubuk.style.width = p + "%";
            yuzde.textContent = p < 100 ? "%" + p : "İşleniyor…";
            satir.querySelector("[role=progressbar]").setAttribute("aria-valuenow", p);
        });
        function bitti() { suren--; satir.remove(); durumuGuncelle(); }
        xhr.addEventListener("load", function () {
            bitti();
            if (xhr.status === 201) {
                try { kartEkle(JSON.parse(xhr.responseText)); } catch (e) { hataGoster("Beklenmeyen bir yanıt alındı. Yeniden deneyin."); }
            } else {
                hataGoster(dosya.name + ": " + yanitHatasi(xhr));
            }
        });
        xhr.addEventListener("error", function () { bitti(); hataGoster(dosya.name + ": Bağlantı koptu. İnternetinizi kontrol edip yeniden deneyin."); });
        xhr.addEventListener("abort", bitti);
        iptal.addEventListener("click", function () { xhr.abort(); });
        xhr.send(veri);
    }

    var dosyaGirdisi = kok.querySelector("[data-medya-dosya]");
    dosyaGirdisi.addEventListener("change", function () {
        Array.prototype.forEach.call(dosyaGirdisi.files, function (d) { yukle(d); });
        dosyaGirdisi.value = "";
    });
    var birakma = kok.querySelector("[data-medya-birak]");
    ["dragenter", "dragover"].forEach(function (ad) {
        birakma.addEventListener(ad, function (e) { e.preventDefault(); birakma.classList.add("is-uzerinde"); });
    });
    ["dragleave", "drop"].forEach(function (ad) {
        birakma.addEventListener(ad, function () { birakma.classList.remove("is-uzerinde"); });
    });
    birakma.addEventListener("drop", function (e) {
        e.preventDefault();
        Array.prototype.forEach.call(e.dataTransfer.files || [], function (d) { yukle(d); });
    });

    // ---------- Baglanti ----------
    var baglantiGirdisi = kok.querySelector("[data-medya-baglanti]");
    var baglantiDugmesi = kok.querySelector("[data-medya-baglanti-ekle]");
    function baglantiEkle() {
        hataGoster("");
        var adres = baglantiGirdisi.value.trim();
        if (!adres) { hataGoster("Bir bağlantı yapıştırın."); baglantiGirdisi.focus(); return; }
        if (kartSayisi() + suren >= EN_FAZLA) { hataGoster("En fazla " + EN_FAZLA + " medya ekleyebilirsiniz."); return; }
        baglantiDugmesi.classList.add("is-loading");
        baglantiDugmesi.disabled = true;
        var veri = new FormData();
        veri.append("adres", adres);
        var xhr = new XMLHttpRequest();
        xhr.open("POST", kok.dataset.baglantiUrl);
        xhr.setRequestHeader("X-CSRFToken", csrf);
        xhr.setRequestHeader("X-Requested-With", "XMLHttpRequest");
        xhr.addEventListener("loadend", function () {
            baglantiDugmesi.classList.remove("is-loading");
            baglantiDugmesi.disabled = false;
            if (xhr.status === 201) {
                kartEkle(JSON.parse(xhr.responseText));
                baglantiGirdisi.value = "";
            } else {
                hataGoster(xhr.status ? yanitHatasi(xhr) : "Bağlantı koptu. Yeniden deneyin.");
            }
        });
        xhr.send(veri);
    }
    baglantiDugmesi.addEventListener("click", baglantiEkle);
    baglantiGirdisi.addEventListener("keydown", function (e) {
        if (e.key === "Enter") { e.preventDefault(); baglantiEkle(); }
    });

    // ---------- Sekmeler ----------
    var sekmeler = kok.querySelectorAll("[data-medya-sekme]");
    function sekmeAc(ad, odak) {
        sekmeler.forEach(function (s) {
            var secili = s.dataset.medyaSekme === ad;
            s.setAttribute("aria-selected", secili ? "true" : "false");
            if (secili) s.setAttribute("aria-current", "true"); else s.removeAttribute("aria-current");
            s.tabIndex = secili ? 0 : -1;
            if (secili && odak) s.focus();
        });
        kok.querySelectorAll("[data-medya-panel]").forEach(function (p) { p.hidden = p.dataset.medyaPanel !== ad; });
        hataGoster("");
    }
    sekmeler.forEach(function (s, i) {
        s.addEventListener("click", function (e) { e.preventDefault(); sekmeAc(s.dataset.medyaSekme); });
        s.addEventListener("keydown", function (e) {
            var yon = e.key === "ArrowRight" ? 1 : e.key === "ArrowLeft" ? -1 : 0;
            if (!yon) return;
            e.preventDefault();
            sekmeAc(sekmeler[(i + yon + sekmeler.length) % sekmeler.length].dataset.medyaSekme, true);
        });
    });

    // Ses kaydi (ses-kaydi.js) bu fonksiyonlarla kayitlari yukler
    window.TEMedya = {
        yukle: yukle,
        hataGoster: hataGoster,
        doluMu: function () { return kartSayisi() + suren >= EN_FAZLA; },
        enFazla: EN_FAZLA,
    };

    // ---------- Gonderim ----------
    // Yukleme surerken kaydetmeyi engelle (form dinleyicisi, panel.js'in belge dinleyicisinden once calisir)
    form.addEventListener("submit", function (olay) {
        if (suren > 0) {
            olay.preventDefault();
            hataGoster("Yükleme sürüyor. Bitince yazınızı kaydedin.");
            kok.scrollIntoView({ behavior: "smooth", block: "start" });
        } else if (kok.querySelector("[data-kayit].is-kayitta")) {
            olay.preventDefault();
            hataGoster("Ses kaydı sürüyor. Önce kaydı durdurup ekleyin.");
            kok.scrollIntoView({ behavior: "smooth", block: "start" });
        }
    });
    window.addEventListener("beforeunload", function (olay) {
        if (suren > 0 || kok.querySelector("[data-kayit].is-kayitta")) {
            olay.preventDefault();
            olay.returnValue = "";
        }
    });

    durumuGuncelle();
})();
