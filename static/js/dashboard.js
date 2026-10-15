// Kontrol paneli grafigi (templates/superadmin/dashboard.html). Chart.js 4 gerektirir.
// Chart.js yuklenemezse sunucunun cizdigi tablo gorunur kalir.
(function () {
    var kap = document.querySelector('.sa-chart[data-grafik="yayin"]');
    var veriEl = document.getElementById("yayin-grafigi-verisi");
    if (!kap || !veriEl) return;

    function hata() {
        kap.classList.remove("is-yukleniyor");
        kap.classList.add("is-hata");
        var not = document.createElement("p");
        not.className = "sa-chart__not";
        not.textContent = "Grafik yüklenemedi; veriler tablo olarak gösteriliyor.";
        kap.insertBefore(not, kap.firstChild);
    }

    if (!window.Chart) { hata(); return; }

    var veri;
    try { veri = JSON.parse(veriEl.textContent); } catch (e) { hata(); return; }

    var donem = "ay";
    var ozet = document.querySelector("[data-grafik-ozet]");
    var azHareket = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

    function renk(degisken) {
        return getComputedStyle(document.documentElement).getPropertyValue(degisken).trim();
    }
    // Tek vurgu rengi kurali: ana seri murekkep rengi, kitap vurgu rengi, alinti notr gri
    function seriRenkleri() {
        var koyu = document.documentElement.getAttribute("data-theme") === "dark";
        return [renk("--sa-primary"), renk("--sa-accent"), renk(koyu ? "--sa-subtle" : "--sa-border-strong")];
    }

    function veriKumeleri() {
        var renkler = seriRenkleri();
        return veri[donem].seriler.map(function (seri, i) {
            return {
                label: seri.ad,
                data: seri.veri,
                backgroundColor: renkler[i],
                // Acik temada vurgu rengi beyaz zeminde silik kalmasin
                borderColor: i === 1 && document.documentElement.getAttribute("data-theme") !== "dark" ? "rgba(24, 24, 27, .25)" : "transparent",
                borderWidth: i === 1 ? 1 : 0,
                borderRadius: 4,
                maxBarThickness: donem === "ay" ? 32 : 14,
                stack: "icerik",
            };
        });
    }

    function ozetMetni() {
        var toplam = veri[donem].toplam;
        var sure = donem === "ay" ? "Son 12 ayda" : "Son 30 günde";
        return toplam ? sure + " " + toplam + " içerik" : sure + " yayınlanan içerik yok";
    }

    Chart.defaults.font.family = renk("--sa-font") || "Inter, system-ui, sans-serif";
    Chart.defaults.font.size = 12;

    var tuval = kap.querySelector("canvas");
    var grafik;
    try {
        grafik = new Chart(tuval, {
            type: "bar",
            data: { labels: veri[donem].etiketler, datasets: veriKumeleri() },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                animation: azHareket ? false : { duration: 400 },
                interaction: { mode: "index", intersect: false },
                plugins: {
                    legend: {
                        position: "bottom",
                        align: "start",
                        labels: { usePointStyle: true, pointStyle: "rectRounded", boxWidth: 10, boxHeight: 10, padding: 16, color: renk("--sa-muted") },
                    },
                    tooltip: {
                        backgroundColor: renk("--sa-text"),
                        titleColor: renk("--sa-bg"),
                        bodyColor: renk("--sa-bg"),
                        padding: 10,
                        cornerRadius: 8,
                        boxPadding: 4,
                        footerColor: renk("--sa-bg"),
                        callbacks: {
                            footer: function (ogeler) {
                                var t = ogeler.reduce(function (a, o) { return a + o.parsed.y; }, 0);
                                return "Toplam: " + t;
                            },
                        },
                    },
                },
                scales: {
                    x: {
                        stacked: true,
                        grid: { display: false },
                        border: { color: renk("--sa-border") },
                        ticks: { color: renk("--sa-muted"), maxRotation: 0, autoSkip: true, autoSkipPadding: 12 },
                    },
                    y: {
                        stacked: true,
                        beginAtZero: true,
                        border: { display: false },
                        grid: { color: renk("--sa-border") },
                        ticks: { color: renk("--sa-muted"), precision: 0, maxTicksLimit: 5 },
                    },
                },
            },
        });
    } catch (e) {
        hata();
        return;
    }
    kap.classList.remove("is-yukleniyor");
    kap.classList.add("is-hazir");

    function temaUygula() {
        var o = grafik.options;
        o.plugins.legend.labels.color = renk("--sa-muted");
        o.plugins.tooltip.backgroundColor = renk("--sa-text");
        o.plugins.tooltip.titleColor = o.plugins.tooltip.bodyColor = o.plugins.tooltip.footerColor = renk("--sa-bg");
        o.scales.x.ticks.color = o.scales.y.ticks.color = renk("--sa-muted");
        o.scales.x.border.color = o.scales.y.grid.color = renk("--sa-border");
        grafik.data.datasets = veriKumeleri();
        grafik.update("none");
    }
    document.addEventListener("sa:tema", temaUygula);

    document.querySelectorAll("[data-donem]").forEach(function (dugme) {
        dugme.addEventListener("click", function () {
            donem = dugme.getAttribute("data-donem");
            document.querySelectorAll("[data-donem]").forEach(function (d) {
                d.setAttribute("aria-selected", d === dugme ? "true" : "false");
            });
            grafik.data.labels = veri[donem].etiketler;
            grafik.data.datasets = veriKumeleri();
            grafik.update();
            if (ozet) ozet.textContent = ozetMetni();
            tuval.setAttribute("aria-label", donem === "ay" ? "Aylara göre yayınlanan içerik grafiği" : "Son 30 günde günlere göre yayınlanan içerik grafiği");
        });
    });
})();
