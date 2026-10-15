import nh3

# Blog yazilarinda (CKEditor ve yapistirilan metinler) kullanilan guvenli HTML.
# Script, olay ozellikleri (onclick vb.) ve javascript: linkleri temizlenir.
IZINLI_ETIKETLER = {
    "p", "br", "hr", "span", "div", "pre", "blockquote", "article", "header",
    "h1", "h2", "h3", "h4", "h5", "h6",
    "b", "strong", "i", "em", "u", "s", "sub", "sup", "font",
    "ul", "ol", "li",
    "a", "img", "figure", "figcaption",
    "table", "thead", "tbody", "tr", "th", "td",
}
IZINLI_OZELLIKLER = {
    "*": {"style", "dir"},
    "a": {"href", "title", "target"},
    "img": {"src", "alt", "width", "height"},
    "font": {"size", "face", "color"},
    "ol": {"start"},
    "td": {"colspan", "rowspan"},
    "th": {"colspan", "rowspan"},
}
IZINLI_STILLER = {
    "text-align", "text-justify", "font-family", "font-size", "font-weight", "font-style",
    "color", "background-color", "text-decoration", "margin-left", "padding-left",
    "width", "height",
}


def temiz_html(html):
    if not html:
        return ""
    return nh3.clean(
        html,
        tags=IZINLI_ETIKETLER,
        attributes=IZINLI_OZELLIKLER,
        filter_style_properties=IZINLI_STILLER,
        link_rel="noopener noreferrer",
    )
