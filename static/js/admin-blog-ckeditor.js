document.addEventListener("DOMContentLoaded", function () {
  const textarea = document.querySelector("#id_icerik[data-editor='ckeditor']");

  if (!textarea || typeof CKEDITOR === "undefined") {
    return;
  }

  if (textarea.dataset.ckeditorInitialized === "true") {
    return;
  }

  if (CKEDITOR.instances[textarea.id]) {
    CKEDITOR.instances[textarea.id].destroy(true);
  }

  // Telefonda alti satirlik arac cubugu yerine yazarin en cok kullandigi araclar
  const darEkran = window.matchMedia("(max-width: 767.98px)").matches;
  const kisaAraclar = [
    { name: "basicstyles", items: ["Bold", "Italic", "Underline", "RemoveFormat"] },
    { name: "paragraph", items: ["NumberedList", "BulletedList", "Blockquote", "JustifyCenter"] },
    { name: "links", items: ["Link", "Unlink"] },
    { name: "history", items: ["Undo", "Redo"] }
  ];

  CKEDITOR.replace(textarea.id, {
    height: darEkran ? 320 : 420,
    removeButtons: "",
    toolbar: darEkran ? kisaAraclar : [
      {
        name: "document",
        items: ["Source", "-", "Preview", "Print"]
      },
      {
        name: "clipboard",
        items: ["Cut", "Copy", "Paste", "PasteText", "PasteFromWord", "-", "Undo", "Redo"]
      },
      {
        name: "basicstyles",
        items: ["Bold", "Italic", "Underline", "Strike", "RemoveFormat"]
      },
      {
        name: "paragraph",
        items: ["NumberedList", "BulletedList", "-", "Outdent", "Indent", "-", "Blockquote", "-", "JustifyLeft", "JustifyCenter", "JustifyRight", "JustifyBlock"]
      },
      {
        name: "links",
        items: ["Link", "Unlink", "Anchor"]
      },
      {
        name: "insert",
        items: ["Image", "Table", "HorizontalRule", "SpecialChar"]
      },
      {
        name: "styles",
        items: ["Styles", "Format", "Font", "FontSize"]
      },
      {
        name: "colors",
        items: ["TextColor", "BGColor"]
      }
    ],
    allowedContent: true,
    // Surum uyarisi yazarlara gosterilmez; CKEditor 4'un destek sonu ayrica takip ediliyor
    versionCheck: false
  });

  textarea.dataset.ckeditorInitialized = "true";
});
