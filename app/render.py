# Póster Notas — motor de dibujo. Reproduce los temas, la barra y las insignias de RatingPosterDB.
import math, os
from PIL import Image, ImageDraw, ImageFilter, ImageFont

FONTS = os.environ.get("PN_FONTS", "/fonts")
_fcache = {}

# fuente_id: (etiqueta, color logo, color texto logo, escala)
FUENTES = {
    "imdb": ("IMDb", "#F5C518", "#000000", 10), "tmdb": ("TMDB", "#01B4E4", "#FFFFFF", 10),
    "trakt": ("Trakt", "#ED1C24", "#FFFFFF", 100), "rt": ("RT", "#FA320A", "#FFFFFF", 100),
    "rt_pub": ("🍿", "#FA320A", "#FFFFFF", 100), "mc": ("MC", "#66CC33", "#000000", 100),
    "mc_pub": ("MC·U", "#66CC33", "#000000", 10), "lb": ("LB", "#202830", "#FFFFFF", 5),
    "ebert": ("RE", "#E10600", "#FFFFFF", 4), "mal": ("MAL", "#2E51A2", "#FFFFFF", 10),
    "mdblist": ("MDB", "#4284CA", "#FFFFFF", 100), "media": ("★", "#F5C518", "#000000", 100),
}
NOMBRES = {"imdb": "IMDb", "tmdb": "TMDB", "trakt": "Trakt", "rt": "Rotten Tomatoes · crítica", "rt_pub": "Rotten Tomatoes · público",
           "mc": "Metacritic · crítica", "mc_pub": "Metacritic · usuarios", "lb": "Letterboxd", "ebert": "Roger Ebert",
           "mal": "MyAnimeList", "mdblist": "MDBList", "media": "Media de todas"}
TEMAS = ["pastillas", "pastillas-barra", "bar", "blocks", "rounded-blocks", "boxes", "sharp-blocks", "stripes-left", "stripes-right"]


def fuente(px, peso):
    k = (px, peso)
    if k not in _fcache:
        nombre = {0: "NotoSans-Regular.ttf", 1: "NotoSans-Bold.ttf", 2: "NotoSans-Black.ttf"}[peso]
        p = os.path.join(FONTS, nombre)
        _fcache[k] = ImageFont.truetype(p, max(6, int(px))) if os.path.exists(p) else ImageFont.load_default()
    return _fcache[k]


def hexa(c, a=255):
    c = (c or "#000000").lstrip("#")
    if len(c) == 3: c = "".join(x * 2 for x in c)
    return (int(c[0:2], 16), int(c[2:4], 16), int(c[4:6], 16), a)


def color_nota(v100):
    return "#21C35B" if v100 >= 70 else "#F5A623" if v100 >= 50 else "#E5483B"


def texto_nota(f, v, formato, coma):
    """formato 0: 7,4/10 · 75% ; 1: normalizado a 100 ; 2: sin sufijos"""
    esc = FUENTES[f][3]
    n100 = v * 100 / esc
    if formato == 1:
        s = str(int(round(n100)))
    elif esc == 100:
        s = f"{int(round(v))}" + ("%" if formato == 0 and f in ("rt", "rt_pub", "trakt") else "")
    else:
        s = (f"{v:.1f}" if esc >= 10 else f"{v:.1f}") + (f"/{esc}" if formato == 0 and esc != 10 else "")
    return (s.replace(".", ",") if coma else s), n100


# ---------------- barra de notas ----------------
def _logo(d, x, y, h, f, estilo_logo, peso, escala):
    et, fondo, txt, _ = FUENTES[f]
    if estilo_logo == "no":
        return 0
    fnt = fuente(h * 0.42 * escala, 2)
    if estilo_logo == "redondo":
        d.ellipse([x, y, x + h, y + h], fill=hexa(fondo))
        fs = fuente(h * (0.36 if len(et) > 2 else 0.44) * escala, 2)
        d.text((x + h / 2, y + h / 2), et if len(et) <= 4 else et[:3], font=fs, fill=hexa(txt), anchor="mm")
        return h
    w = d.textlength(et, font=fnt) + h * 0.5
    d.rounded_rectangle([x, y, x + w, y + h], int(h * 0.18), fill=hexa(fondo))
    d.text((x + w / 2, y + h / 2), et, font=fnt, fill=hexa(txt), anchor="mm")
    return w


def _partes(d, f, txt, h, b):
    et = FUENTES[f][0]
    lw = 0 if b["logos"] == "no" else (h if b["logos"] == "redondo" else d.textlength(et, font=fuente(h * 0.42 * b["escala_fuente"], 2)) + h * 0.5)
    tw = d.textlength(txt, font=fuente(h * 0.56 * b["escala_fuente"], 2 if b["negrita"] else 1))
    return lw, tw


def _medir_item(d, f, txt, h, b, cajas=False, tema=""):
    if tema.startswith("pastillas"):
        pad = b["relleno"] * h / 68
        lw = 0 if b["logos"] == "no" else d.textlength(FUENTES[f][0], font=fuente(h * 0.5 * b["escala_fuente"], 2)) + pad * 2 + h * 0.2
        return lw + h * 0.2 + d.textlength(txt, font=fuente(h * 0.6 * b["escala_fuente"], 2 if b["negrita"] else 1))
    lw, tw = _partes(d, f, txt, h, b)
    return max(lw, tw) if cajas else lw + (h * 0.22 if lw else 0) + tw


def barra(img, notas, cf):
    b, n, tema = cf["barra"], cf["notas"], cf["tema"]
    claro = cf.get("claro")
    items = []
    for f in n["fuentes"]:
        if f in notas:
            t, n100 = texto_nota(f, notas[f], n["formato"], n["decimales_coma"])
            items.append((f, t, n100))
    if not items:
        return img
    W, H = img.size
    k = W / 1000.0
    h = 68 * k * b["escala_fuente"]
    pad = b["relleno"] * k
    mar = b["margen"] * k
    gap = 14 * k
    pos = b["posicion"]
    vertical = pos.startswith(("left", "right"))
    capa = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(capa)
    fondo = hexa(b["color"], int(255 * b["opacidad"]))
    if claro:
        fondo = hexa("#FFFFFF", int(255 * b["opacidad"]))
    color_txt = hexa("#111111" if claro and b["color_texto"].upper() in ("#FFFFFF", "#FFF") else b["color_texto"])
    cajas = tema == "boxes"  # logo arriba y nota debajo
    anchos = [_medir_item(d, f, t, h, b, cajas, tema) for f, t, _ in items]
    caja = [a + pad * 2 for a in anchos]
    alto_caja = h * (1.85 if cajas else 1) + pad * 2
    # disposición
    if vertical:
        tot_h = len(items) * alto_caja + (len(items) - 1) * gap
        maxw = max(caja)
        x0 = mar + 18 * k if pos.startswith("left") else W - mar - 18 * k - maxw
        y0 = {"top": mar + 18 * k, "center": (H - tot_h) / 2, "bottom": H - mar - 18 * k - tot_h}[pos.split("-")[1]]
        coords = [(x0, y0 + i * (alto_caja + gap), maxw) for i in range(len(items))]
    else:
        tot_w = sum(caja) + gap * (len(items) - 1)
        esc = min(1.0, (W - 2 * (mar + 18 * k)) / tot_w)
        if esc < 1:  # no cabe: reducir
            h *= esc; pad *= esc; gap *= esc
            anchos = [_medir_item(d, f, t, h, b, cajas, tema) for f, t, _ in items]
            caja = [a + pad * 2 for a in anchos]; alto_caja = h * (1.85 if cajas else 1) + pad * 2; tot_w = sum(caja) + gap * (len(items) - 1)
        y0 = H - mar - 18 * k - alto_caja if pos == "bottom" else mar + 18 * k
        x = (W - tot_w) / 2
        coords = []
        for c in caja:
            coords.append((x, y0, c)); x += c + gap
    r = {"default": h * 0.22, "full": alto_caja / 2}.get(str(b["redondeo"]), None)
    r = float(b["redondeo"]) * k if r is None else r
    borde = (1.5 * k if str(b["borde"]) == "default" else float(b["borde"]) * k)
    color_borde = hexa(b["color_borde"])
    # fondos según tema
    if tema in ("bar", "pastillas-barra"):
        if vertical:
            xs = coords[0][0] - 12 * k; xe = coords[0][0] + coords[0][2] + 12 * k
            d.rectangle([xs, coords[0][1] - 12 * k, xe, coords[-1][1] + alto_caja + 12 * k], fill=fondo)
        else:
            yb = coords[0][1] - 14 * k
            d.rectangle([0, yb, W, yb + alto_caja + 28 * k], fill=fondo)
    lado = b["lado_borde"]
    for (x, y, w), (f, t, n100) in zip(coords, items):
        if tema.startswith("pastillas"):  # diseño de la v1: etiqueta de color pegada a la nota sobre fondo oscuro
            et, col, col_txt, _ = FUENTES[f]
            rr = alto_caja * 0.32 if b["redondeo"] == "default" else r
            fondo_p = (12, 12, 16, 235) if tema == "pastillas-barra" else fondo
            d.rounded_rectangle([x, y, x + w, y + alto_caja], int(rr), fill=fondo_p,
                                outline=color_borde if borde > 0 else None, width=int(borde) if borde > 0 else 0)
            fnum = fuente(h * 0.6 * b["escala_fuente"], 2 if b["negrita"] else 1)
            vx = x + pad
            if b["logos"] != "no":
                fl = fuente(h * 0.5 * b["escala_fuente"], 2)
                sw = d.textlength(et, font=fl) + pad * 2 + h * 0.2
                d.rounded_rectangle([x, y, x + sw, y + alto_caja], int(rr), fill=hexa(col))
                d.rectangle([x + sw - rr, y, x + sw, y + alto_caja], fill=hexa(col))
                d.text((x + sw / 2, y + alto_caja / 2), et, font=fl, fill=hexa(col_txt), anchor="mm")
                vx = x + sw + h * 0.2
            d.text((vx, y + alto_caja / 2), t, font=fnum, fill=color_txt, anchor="lm")
            continue
        if tema in ("blocks", "rounded-blocks", "boxes", "sharp-blocks") or tema.startswith("stripes"):
            rr = {"blocks": h * 0.12, "rounded-blocks": alto_caja / 2, "boxes": h * 0.1, "sharp-blocks": 0}.get(tema, r)
            if b["redondeo"] != "default":
                rr = r
            if tema.startswith("stripes"):
                rr = 0
            caja_xy = [x, y, x + w, y + alto_caja]
            todo = lado == "default" and borde > 0
            d.rounded_rectangle(caja_xy, int(rr), fill=fondo, outline=color_borde if todo else None, width=int(borde) if todo else 0)
            if borde > 0 and lado != "default":  # borde solo en un lado
                lx = {"left": [x, y, x + borde, y + alto_caja], "right": [x + w - borde, y, x + w, y + alto_caja],
                      "top": [x, y, x + w, y + borde], "bottom": [x, y + alto_caja - borde, x + w, y + alto_caja]}[lado]
                d.rectangle(lx, fill=color_borde)
            if tema.startswith("stripes"):  # franja de color según la nota
                ancho = 7 * k
                cx = x if tema == "stripes-left" else x + w - ancho
                d.rectangle([cx, y, cx + ancho, y + alto_caja], fill=hexa(color_nota(n100)))
        fnum = fuente(h * 0.56 * b["escala_fuente"], 2 if b["negrita"] else 1)
        if cajas:
            lw, _ = _partes(d, f, t, h, b)
            if lw: _logo(d, x + (w - lw) / 2, y + pad, h * 0.92, f, b["logos"], b["negrita"], b["escala_fuente"])
            d.text((x + w / 2, y + pad + h * (1.35 if lw else 0.5)), t, font=fnum, fill=color_txt, anchor="mm")
            continue
        cx = x + pad
        lw = _logo(d, cx, y + pad, h, f, b["logos"], b["negrita"], b["escala_fuente"])
        cx += lw + (h * 0.22 if lw else 0)
        d.text((cx, y + pad + h / 2), t, font=fnum, fill=color_txt, anchor="lm")
    if b["inclinacion"] in ("left", "right"):
        s = 0.18 if b["inclinacion"] == "right" else -0.18
        capa = capa.transform(capa.size, Image.AFFINE, (1, s, -s * H * (0.95 if pos == "bottom" else 0.05), 0, 1, 0), Image.BICUBIC)
    if b.get("sombra"):
        sombra = capa.split()[-1].filter(ImageFilter.GaussianBlur(10 * k)).point(lambda p: int(p * 0.55))
        img = Image.composite(Image.new("RGBA", img.size, (0, 0, 0, 255)), img, sombra)
    return Image.alpha_composite(img, capa)


# ---------------- insignias ----------------
PALETA = {
    "normal": {"fondo": "#141414", "txt": "#FFFFFF", "borde": "#FFFFFF"},
    "oro": {"fondo": "#141414", "txt": "#E9C46A", "borde": "#E9C46A"},
    "color": None,
}
NEBULA = {"res": ("#FFFFFF", "#000000"), "hdr": ("#FFC400", "#000000"), "dv": ("#141414", "#FFFFFF"),
          "audio": ("#141414", "#FFFFFF"), "idioma": ("#3C3C3C", "#FFFFFF"), "etiqueta": ("#F5C518", "#000000")}
COLOR_TIPO = {"res": "#3A86FF", "dv": "#8E44AD", "hdr": "#F39C12", "audio": "#16A085", "fuente": "#C0392B",
              "codec": "#34495E", "edicion": "#7F8C8D", "edad": "#E67E22", "idioma": "#2C3E50", "imax": "#0077C8", "3d": "#2ECC71", "etiqueta": "#B03A2E"}


def bandera(d, x, y, h, pais):
    w = h * 1.5
    if pais == "es":
        d.rectangle([x, y, x + w, y + h], fill=(170, 21, 27)); d.rectangle([x, y + h / 4, x + w, y + 3 * h / 4], fill=(241, 191, 0))
    elif pais == "gb":
        d.rectangle([x, y, x + w, y + h], fill=(1, 33, 105))
        d.line([x, y, x + w, y + h], fill=(255, 255, 255), width=int(h / 5)); d.line([x, y + h, x + w, y], fill=(255, 255, 255), width=int(h / 5))
        d.rectangle([x + w * .42, y, x + w * .58, y + h], fill=(255, 255, 255)); d.rectangle([x, y + h * .38, x + w, y + h * .62], fill=(255, 255, 255))
        d.rectangle([x + w * .45, y, x + w * .55, y + h], fill=(200, 16, 46)); d.rectangle([x, y + h * .42, x + w, y + h * .58], fill=(200, 16, 46))
    elif pais == "jp":
        d.rectangle([x, y, x + w, y + h], fill=(255, 255, 255)); d.ellipse([x + w / 2 - h * .3, y + h * .2, x + w / 2 + h * .3, y + h * .8], fill=(188, 0, 45))
    elif pais == "fr":
        for i, c in enumerate(((0, 35, 149), (255, 255, 255), (237, 41, 57))): d.rectangle([x + i * w / 3, y, x + (i + 1) * w / 3, y + h], fill=c)
    elif pais == "it":
        for i, c in enumerate(((0, 146, 70), (255, 255, 255), (206, 43, 55))): d.rectangle([x + i * w / 3, y, x + (i + 1) * w / 3, y + h], fill=c)
    elif pais == "de":
        for i, c in enumerate(((0, 0, 0), (221, 0, 0), (255, 206, 0))): d.rectangle([x, y + i * h / 3, x + w, y + (i + 1) * h / 3], fill=c)
    elif pais == "kr":
        d.rectangle([x, y, x + w, y + h], fill=(255, 255, 255)); d.pieslice([x + w / 2 - h * .25, y + h * .25, x + w / 2 + h * .25, y + h * .75], 180, 360, fill=(205, 46, 58)); d.pieslice([x + w / 2 - h * .25, y + h * .25, x + w / 2 + h * .25, y + h * .75], 0, 180, fill=(0, 71, 160))
    else:
        return 0
    d.rectangle([x, y, x + w, y + h], outline=(0, 0, 0, 140), width=max(1, int(h / 16)))
    return w


def lista_insignias(q, ins, etiqueta):
    """Devuelve [(tipo, texto)] en el orden configurado."""
    out = []
    for t in ins["lista"]:
        if t == "res" and q.get("res"):
            out.append(("res", q["res"]))
        elif t == "hdr_dv":
            if q.get("dv") and q.get("hdr"): out.append(("dv", "DV · HDR"))
            elif q.get("dv"): out.append(("dv", "DOLBY VISION"))
            elif q.get("hdr"): out.append(("hdr", q["hdr"]))
        elif t == "audio" and q.get("audio"):
            out.append(("audio", q["audio"]))
        elif t == "fuente" and q.get("fuente"):
            out.append(("fuente", q["fuente"]))
        elif t == "codec" and q.get("codec"):
            out.append(("codec", q["codec"]))
        elif t == "edicion" and q.get("edicion"):
            out.append(("edicion", q["edicion"]))
        elif t == "imax" and q.get("imax"):
            out.append(("imax", "IMAX"))
        elif t == "3d" and q.get("3d"):
            out.append(("3d", "3D"))
        elif t == "edad" and q.get("edad"):
            out.append(("edad", q["edad"]))
        elif t == "idioma":
            if q.get("es"): out.append(("bandera", "es"))
            elif q.get("vose"): out.append(("idioma", "VOSE"))
        elif t == "pais" and q.get("pais"):
            out.append(("bandera", q["pais"]))
    if etiqueta:
        out.insert(0, ("etiqueta", etiqueta.upper()))
    return out[: ins["max"]]


def insignias(img, q, cf):
    ins = cf["insignias"]
    if not ins["activar"]:
        return img
    lst = lista_insignias(q, ins, cf["notas"].get("etiqueta", ""))
    if not lst:
        return img
    W, H = img.size
    k = W / 1000.0
    h = 50 * k * ins["escala"]
    gap = 10 * k
    m = 26 * k
    capa = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(capa)
    fnt = fuente(h * 0.5, 2)
    est = ins["estilo"]
    anchos = [(h * 1.5 if t == "bandera" else d.textlength(s, font=fnt) + h * 0.7) for t, s in lst]
    pos = ins["posicion"]
    vertical = ins.get("apilar", True) and pos in ("left", "right", "bottom|left", "bottom|right")
    if vertical:
        tot = len(lst) * h + gap * (len(lst) - 1)
        y = m if not pos.startswith("bottom") else H - m - tot - (130 * k if cf["barra"]["posicion"] == "bottom" else 0)
        xs = [m if pos.endswith("left") else W - m - a for a in anchos]
        ys = [y + i * (h + gap) for i in range(len(lst))]
    else:
        tot = sum(anchos) + gap * (len(lst) - 1)
        y = m if not pos.startswith("bottom") else H - m - h - (130 * k if cf["barra"]["posicion"] == "bottom" else 0)
        lado = pos.split("|")[-1]
        x = m if lado == "left" else W - m - tot if lado == "right" else (W - tot) / 2
        xs, ys = [], []
        for a in anchos:
            xs.append(x); ys.append(y); x += a + gap
    for (t, s), a, x, y in zip(lst, anchos, xs, ys):
        if t == "bandera":
            bandera(d, x, y, h, s); continue
        if est == "nebula":
            fo, tx, bo = NEBULA.get(t, ("#141414", "#FFFFFF"))[0], NEBULA.get(t, ("#141414", "#FFFFFF"))[1], None
            if t == "res" and s != "4K": fo, tx = "#141414", "#FFFFFF"
        elif est == "color":
            fo, tx, bo = COLOR_TIPO.get(t, "#333333"), "#FFFFFF", None
        else:
            p = PALETA[est]; fo, tx, bo = p["fondo"], p["txt"], p["borde"]
        d.rounded_rectangle([x, y, x + a, y + h], int(h * 0.2), fill=hexa(fo, int(255 * ins["opacidad"])),
                            outline=hexa(bo, 200) if bo else None, width=max(1, int(2 * k)) if bo else 0)
        d.text((x + a / 2, y + h / 2), s, font=fnt, fill=hexa(tx), anchor="mm")
    return Image.alpha_composite(img, capa)


def componer(img, notas, q, cf):
    W = cf["imagen"]["ancho"]
    img = img.convert("RGBA")
    if img.width != W:
        img = img.resize((W, int(img.height * W / img.width)), Image.LANCZOS)
    img = barra(img, notas, cf)
    img = insignias(img, q, cf)
    return img.convert("RGB")


# ---------------- estilos prediseñados (como los ejemplos de RPDB) ----------------
_B = {"opacidad": 0.78, "color": "#000000", "color_texto": "#FFFFFF", "redondeo": "default", "relleno": 10, "margen": 0,
      "borde": 0, "color_borde": "#FFFFFF", "lado_borde": "default", "inclinacion": "no", "escala_fuente": 1.0,
      "negrita": True, "logos": "normal", "sombra": True, "posicion": "bottom"}
_I = {"activar": True, "posicion": "right", "apilar": False, "estilo": "normal", "escala": 1.0, "opacidad": 0.88}


def _p(nombre, desc, tema, claro=False, barra=None, ins=None):
    return {"nombre": nombre, "desc": desc, "conf": {"tema": tema, "claro": claro, "barra": {**_B, **(barra or {})}, "insignias": {**_I, **(ins or {})}}}


PRESETS = [
    _p("Nebula (el de antes)", "Pastillas grandes con la etiqueta de color, como la primera versión", "pastillas", barra={"escala_fuente": 1.1, "opacidad": 0.82}, ins={"estilo": "nebula"}),
    _p("Nebula barra", "Franja oscura a lo ancho con las pastillas dentro (la «barra» de la v1)", "pastillas-barra", barra={"escala_fuente": 1.05, "opacidad": 0.7}, ins={"estilo": "nebula"}),
    _p("RPDB clásico", "Barra negra a lo ancho, abajo", "bar", barra={"opacidad": 0.62}),
    _p("RPDB bloques", "Bloques separados con esquinas suaves", "blocks"),
    _p("RPDB bloques redondos", "Píldoras redondeadas", "rounded-blocks"),
    _p("RPDB cajas", "Logo arriba y nota debajo", "boxes", barra={"escala_fuente": 0.9}),
    _p("RPDB bloques rectos", "Bloques de esquinas vivas", "sharp-blocks", barra={"opacidad": 0.85}),
    _p("RPDB franjas", "Franja de color según la nota", "stripes-right"),
    _p("RPDB claro", "Bloques blancos con texto oscuro (light)", "rounded-blocks", claro=True, barra={"opacidad": 0.9, "sombra": False}),
    _p("Lateral", "Columna a la izquierda con logos redondos", "rounded-blocks", barra={"posicion": "left-center", "logos": "redondo", "escala_fuente": 0.85},
       ins={"posicion": "bottom|right", "apilar": True}),
    _p("Cine dorado", "Negro y dorado, insignias doradas", "boxes", barra={"color": "#0E0E0E", "color_texto": "#E9C46A", "borde": 2, "color_borde": "#E9C46A", "opacidad": 0.9, "escala_fuente": 0.9},
       ins={"estilo": "oro"}),
    _p("Deportivo", "Bloques rectos inclinados", "sharp-blocks", barra={"inclinacion": "right", "opacidad": 0.88}),
    _p("Minimal", "Solo números, sin logos ni fondo", "bar", barra={"logos": "no", "opacidad": 0.01, "escala_fuente": 1.15, "sombra": True}, ins={"activar": False}),
    _p("Arriba", "Notas arriba y calidad abajo", "rounded-blocks", barra={"posicion": "top"}, ins={"posicion": "bottom|center", "estilo": "color"}),
]
