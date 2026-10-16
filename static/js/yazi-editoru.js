// Blog yazisi metin editoru: CKEditor 5 (GPL, static/vendor/ckeditor5/ altindan sunulur).
// Yazar panelindeki ve yonetim panelindeki yazi formlarinda <textarea data-editor="ckeditor"> alanina kurulur.
// Kaydedilen HTML sunucuda ayrica temizlenir (core/html_temizleme.py); burada izin verilenler onunla uyumludur.
(function () {
    "use strict";

    var alan = document.querySelector("textarea[data-editor='ckeditor']");
    if (!alan || !window.CKEDITOR || alan.dataset.editorKuruldu === "1") return;
    alan.dataset.editorKuruldu = "1";

    var C = window.CKEDITOR;
    var kaynakKodu = alan.dataset.kaynakKodu === "1"; // yalnizca yoneticiler

    var eklentiler = [
        C.Essentials, C.Paragraph, C.Heading, C.Bold, C.Italic, C.Underline, C.Strikethrough,
        C.RemoveFormat, C.Link, C.AutoLink, C.List, C.BlockQuote, C.HorizontalLine, C.Alignment,
        C.Table, C.TableToolbar, C.PasteFromOffice, C.GeneralHtmlSupport,
    ];
    var arac = [
        "heading", "|", "bold", "italic", "underline", "strikethrough", "removeFormat", "|",
        "alignment", "|", "link", "bulletedList", "numberedList", "blockQuote", "horizontalLine", "insertTable",
        "|", "undo", "redo",
    ];
    if (kaynakKodu) {
        eklentiler.push(C.SourceEditing);
        arac.push("|", "sourceEditing");
    }

    // Eski yazilarda (CKEditor 4 ve yapistirilan metinler) bulunan bicimler duzenlerken kaybolmasin.
    // Liste, sunucudaki temizleme kurallariyla (IZINLI_STILLER / IZINLI_OZELLIKLER) aynidir.
    var stiller = {};
    ["text-align", "text-justify", "font-family", "font-size", "font-weight", "font-style", "color",
        "background-color", "text-decoration", "margin-left", "padding-left"].forEach(function (s) { stiller[s] = true; });

    C.ClassicEditor.create(alan, {
        licenseKey: "GPL",
        language: "tr",
        plugins: eklentiler,
        toolbar: { items: arac, shouldNotGroupWhenFull: false },
        heading: {
            options: [
                { model: "paragraph", title: "Paragraf", class: "ck-heading_paragraph" },
                { model: "heading2", view: "h2", title: "Başlık", class: "ck-heading_heading2" },
                { model: "heading3", view: "h3", title: "Alt başlık", class: "ck-heading_heading3" },
                { model: "heading4", view: "h4", title: "Küçük başlık", class: "ck-heading_heading4" },
            ],
        },
        alignment: { options: ["left", "center", "right", "justify"] },
        link: { defaultProtocol: "https://", addTargetToExternalLinks: false },
        table: { contentToolbar: ["tableColumn", "tableRow", "mergeTableCells"] },
        htmlSupport: {
            allow: [
                { name: /^(p|span|div|font|h[1-6]|blockquote|pre|li|ol|ul|strong|b|em|i|u|s)$/, styles: stiller, attributes: { dir: true } },
                { name: "font", attributes: { size: true, face: true, color: true } },
                { name: "ol", attributes: { start: true } },
            ],
        },
    }).then(function (editor) {
        window.yaziEditoru = editor; // testler ve medya/alinti betikleri icin
        // Editor kendi formunu gonderirken alani gunceller; ek guvence olarak her degisiklikte de guncel tut
        editor.model.document.on("change:data", function () { editor.updateSourceElement(); });
    }).catch(function (hata) {
        // Editor yuklenemezse duz metin alani kullanilabilir kalir (kayit bozulmaz)
        alan.dataset.editorKuruldu = "";
        alan.style.display = "";
        if (window.console) console.error("Metin editörü açılamadı:", hata);
    });
})();
