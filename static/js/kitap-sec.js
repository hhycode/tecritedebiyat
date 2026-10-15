// Alinti formunda kitap secimi (templates/panel/alinti_form.html): yazdikca kayitli kitaplari onerir,
// secilen kitap gizli kaynak_id alanina yazilir; bulunamazsa "yeni kitap ekle" alanlari acilir.
// ARIA combobox deseni: ok tuslari, Enter ile secim, Esc ile kapatma.
(function () {
    var kok = document.querySelector("[data-kitap-sec]");
    if (!kok) return;
    var url = kok.dataset.araUrl;
    var gizli = kok.querySelector("input[name=kaynak_id]");
    var arama = kok.querySelector("[data-arama]");
    var liste = kok.querySelector("[data-oneriler]");
    var durum = kok.querySelector("[data-oneri-durum]");
    var aramaAlani = kok.querySelector("[data-arama-alani]");
    var secili = kok.querySelector("[data-secili]");
    var yeni = kok.querySelector("[data-yeni-kitap]");
    var yeniAd = yeni.querySelector("input[name=yeni_kitap_ad]");
    var yazar = yeni.querySelector("[data-yazar]");
    var yazarOneri = yeni.querySelector("[data-yazar-oneriler]");
    var zamanlayici = null, istek = 0, aktif = -1, secenekler = [];

    function el(etiket, sinif, metin) {
        var e = document.createElement(etiket);
        if (sinif) e.className = sinif;
        if (metin != null) e.textContent = metin;
        return e;
    }

    function kapat() {
        liste.hidden = true;
        arama.setAttribute("aria-expanded", "false");
        arama.removeAttribute("aria-activedescendant");
        aktif = -1;
    }

    function vurgula(i) {
        secenekler.forEach(function (s, j) { s.setAttribute("aria-selected", j === i ? "true" : "false"); });
        aktif = i;
        if (i >= 0) {
            arama.setAttribute("aria-activedescendant", secenekler[i].id);
            secenekler[i].scrollIntoView({ block: "nearest" });
        }
    }

    function sec(kitap) {
        gizli.value = kitap.id;
        secili.querySelector("[data-secili-ad]").textContent = kitap.ad;
        secili.querySelector("[data-secili-yazar]").textContent = kitap.yazar + (kitap.kunye ? " · " + kitap.kunye : "");
        var kapak = secili.querySelector("[data-secili-kapak]");
        kapak.innerHTML = "";
        if (kitap.kapak) { var img = el("img"); img.src = kitap.kapak; img.alt = ""; kapak.appendChild(img); }
        else kapak.appendChild(el("i", "ph ph-book-open"));
        // Yeni kitap alanlari temizlenir: secilen kitap gecerlidir
        yeni.querySelectorAll("input:not([type=file])").forEach(function (i) { i.value = ""; });
        var dosya = yeni.querySelector("input[type=file]"); if (dosya) dosya.value = "";
        yeni.hidden = true;
        aramaAlani.hidden = true;
        secili.hidden = false;
        kapat();
        secili.querySelector("[data-degistir]").focus();
    }

    function yeniKitapAc(ad) {
        gizli.value = "";
        yeni.hidden = false;
        aramaAlani.hidden = true;
        secili.hidden = true;
        if (ad && !yeniAd.value) yeniAd.value = ad;
        kapat();
        (yeniAd.value ? yazar : yeniAd).focus();
    }

    function goster(veri, sorgu) {
        liste.innerHTML = "";
        secenekler = [];
        veri.kitaplar.forEach(function (k, i) {
            var li = el("li", "yp-combobox__secenek");
            li.id = "kitap-oneri-" + i;
            li.setAttribute("role", "option");
            var kapak = el("span", "yp-combobox__kapak");
            if (k.kapak) { var img = el("img"); img.src = k.kapak; img.alt = ""; kapak.appendChild(img); }
            else kapak.appendChild(el("i", "ph ph-book-open"));
            var metin = el("span", "yp-combobox__metin");
            metin.appendChild(el("strong", "", k.ad));
            metin.appendChild(el("span", "", k.yazar + (k.kunye ? " · " + k.kunye : "") + (k.onay_bekliyor ? " · onay bekliyor" : "")));
            li.appendChild(kapak); li.appendChild(metin);
            li.addEventListener("mousedown", function (e) { e.preventDefault(); sec(k); });
            liste.appendChild(li); secenekler.push(li);
        });
        var ekle = el("li", "yp-combobox__secenek yp-combobox__ekle");
        ekle.id = "kitap-oneri-yeni";
        ekle.setAttribute("role", "option");
        ekle.appendChild(el("i", "ph ph-plus-circle"));
        ekle.appendChild(el("span", "", "“" + sorgu + "” adlı kitabı yeni olarak ekle"));
        ekle.addEventListener("mousedown", function (e) { e.preventDefault(); yeniKitapAc(sorgu); });
        ekle._yeni = true;
        liste.appendChild(ekle); secenekler.push(ekle);
        liste.hidden = false;
        arama.setAttribute("aria-expanded", "true");
        durum.textContent = veri.kitaplar.length ? veri.kitaplar.length + " kitap bulundu. Ok tuşlarıyla seçin." : "Kayıtlı kitap bulunamadı; yeni kitap olarak ekleyebilirsiniz.";
        vurgula(-1);
        goster.son = veri.kitaplar;
    }

    function ara() {
        var sorgu = arama.value.trim();
        if (sorgu.length < 2) { kapat(); return; }
        var no = ++istek;
        fetch(url + "?q=" + encodeURIComponent(sorgu), { credentials: "same-origin", headers: { "X-Requested-With": "XMLHttpRequest" } })
            .then(function (r) { if (!r.ok) throw new Error(r.status); return r.json(); })
            .then(function (veri) { if (no === istek) goster(veri, sorgu); })
            .catch(function () {
                if (no !== istek) return;
                durum.textContent = "Öneriler yüklenemedi. Kitabı yeni olarak ekleyebilirsiniz.";
                goster({ kitaplar: [] }, sorgu);
            });
    }

    arama.addEventListener("input", function () {
        clearTimeout(zamanlayici);
        zamanlayici = setTimeout(ara, 200);
    });
    arama.addEventListener("keydown", function (e) {
        if (liste.hidden) {
            if (e.key === "ArrowDown") { ara(); e.preventDefault(); }
            return;
        }
        if (e.key === "ArrowDown") { e.preventDefault(); vurgula(Math.min(aktif + 1, secenekler.length - 1)); }
        else if (e.key === "ArrowUp") { e.preventDefault(); vurgula(Math.max(aktif - 1, 0)); }
        else if (e.key === "Escape") { kapat(); }
        else if (e.key === "Enter") {
            e.preventDefault(); // formu gondermesin
            if (aktif < 0) return;
            var s = secenekler[aktif];
            if (s._yeni) yeniKitapAc(arama.value.trim()); else sec(goster.son[aktif]);
        }
    });
    arama.addEventListener("blur", function () { setTimeout(kapat, 150); });

    secili.querySelector("[data-degistir]").addEventListener("click", function () {
        gizli.value = "";
        secili.hidden = true;
        aramaAlani.hidden = false;
        arama.value = "";
        arama.focus();
    });
    yeni.querySelector("[data-yeni-vazgec]").addEventListener("click", function () {
        yeni.hidden = true;
        aramaAlani.hidden = false;
        arama.value = yeniAd.value;
        yeni.querySelectorAll("input:not([type=file])").forEach(function (i) { i.value = ""; });
        arama.focus();
        ara();
    });

    // Yeni kitapta yazar adi onerileri (kayitli yazarlar; ayni yazarin iki kez eklenmesini azaltir)
    var yazarZaman = null;
    yazar.addEventListener("input", function () {
        clearTimeout(yazarZaman);
        var q = yazar.value.trim();
        if (q.length < 2) return;
        yazarZaman = setTimeout(function () {
            fetch(url + "?tur=yazar&q=" + encodeURIComponent(q), { credentials: "same-origin" })
                .then(function (r) { return r.ok ? r.json() : { yazarlar: [] }; })
                .then(function (veri) {
                    yazarOneri.innerHTML = "";
                    veri.yazarlar.forEach(function (y) { var o = document.createElement("option"); o.value = y.ad; yazarOneri.appendChild(o); });
                })
                .catch(function () {});
        }, 200);
    });
})();
