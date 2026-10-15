// Admin paneli ortak davranislari (templates/superadmin/base.html)
(function () {
    var kok = document.documentElement;

    function kaydet(anahtar, deger) {
        try { localStorage.setItem(anahtar, deger); } catch (e) {}
    }

    // Acik/koyu tema
    document.querySelectorAll("[data-tema-degistir]").forEach(function (dugme) {
        dugme.addEventListener("click", function () {
            var yeni = kok.getAttribute("data-theme") === "dark" ? "light" : "dark";
            kok.setAttribute("data-theme", yeni);
            kok.setAttribute("data-bs-theme", yeni);
            kaydet("sa-tema", yeni);
            document.dispatchEvent(new CustomEvent("sa:tema", { detail: yeni }));
        });
    });

    // Masaustunde menuyu daralt/genislet
    document.querySelectorAll("[data-menu-daralt]").forEach(function (dugme) {
        dugme.addEventListener("click", function () {
            var dar = kok.classList.toggle("sa-menu-dar");
            kaydet("sa-menu-dar", dar ? "1" : "0");
        });
    });

    // Mobilde menu cekmecesi
    var acDugmesi = document.querySelector("[data-menu-ac]");
    function menuyuAyarla(acik) {
        kok.classList.toggle("sa-menu-acik", acik);
        if (acDugmesi) acDugmesi.setAttribute("aria-expanded", acik ? "true" : "false");
    }
    if (acDugmesi) acDugmesi.addEventListener("click", function () { menuyuAyarla(true); });
    document.querySelectorAll("[data-menu-kapat]").forEach(function (el) {
        el.addEventListener("click", function () { menuyuAyarla(false); });
    });

    // Kullanici menusu: disariya tiklayinca ya da Esc ile kapanir
    var kullanici = document.querySelector(".sa-user");
    document.addEventListener("click", function (olay) {
        if (kullanici && kullanici.open && !kullanici.contains(olay.target)) kullanici.open = false;
    });
    document.addEventListener("keydown", function (olay) {
        if (olay.key !== "Escape") return;
        if (kullanici) kullanici.open = false;
        menuyuAyarla(false);
    });

    // data-onay ozelligi olan formlar gonderilmeden once onay ister
    document.addEventListener("submit", function (olay) {
        var mesaj = olay.target.getAttribute("data-onay");
        if (mesaj && !window.confirm(mesaj)) olay.preventDefault();
    });
})();
