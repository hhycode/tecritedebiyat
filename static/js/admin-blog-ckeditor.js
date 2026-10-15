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

  CKEDITOR.replace(textarea.id, {
    height: 420,
    removeButtons: "",
    toolbar: [
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
    allowedContent: true
  });

  textarea.dataset.ckeditorInitialized = "true";
});
