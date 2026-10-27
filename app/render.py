# Póster Notas — motor de dibujo v3.2.
# Reproduce con alta fidelidad los temas, barras e insignias de RatingPosterDB.
import math, os
from PIL import Image, ImageDraw, ImageFilter, ImageFont

FONTS = os.environ.get("PN_FONTS", "/fonts")
_fcache = {}

# fuente_id: (etiqueta, color logo, color texto logo, escala)
FUENTES = {
    "imdb": ("IMDb", "#F5C518", "#000000", 10),
    "tmdb": ("TMDB", "#01B4E4", "#FFFFFF", 10),
    "trakt": ("Trakt", "#ED1C24", "#FFFFFF", 100),
    "rt": ("RT", "#FA320A", "#FFFFFF", 100),
    "rt_pub": ("🍿", "#FA320A", "#FFFFFF", 100),
    "mc": ("MC", "#66CC33", "#000000", 100),
    "mc_pub": ("MC·U", "#66CC33", "#000000", 10),
    "lb": ("LB", "#202830", "#FFFFFF", 5),
    "ebert": ("RE", "#E10600", "#FFFFFF", 4),
    "mal": ("MAL", "#2E51A2", "#FFFFFF", 10),
    "mdblist": ("MDB", "#4284CA", "#FFFFFF", 100),
    "media": ("★", "#F5C518", "#000000", 100),
}

NOMBRES = {
    "imdb": "IMDb", "tmdb": "TMDB", "trakt": "Trakt",
    "rt": "Rotten Tomatoes · crítica", "rt_pub": "Rotten Tomatoes · público",
    "mc": "Metacritic · crítica", "mc_pub": "Metacritic · usuarios",
    "lb": "Letterboxd", "ebert": "Roger Ebert",
    "mal": "MyAnimeList", "mdblist": "MDBList", "media": "Media de todas"
}

TEMAS = ["pastillas", "pastillas-barra", "bar", "blocks", "rounded-blocks", "boxes", "sharp-blocks", "stripes-left", "stripes-right"]


def fuente(px, peso=1):
    k = (int(px), peso)
    if k not in _fcache:
        nombre = {0: "NotoSans-Regular.ttf", 1: "NotoSans-Bold.ttf", 2: "NotoSans-Black.ttf"}.get(peso, "NotoSans-Bold.ttf")
        p = os.path.join(FONTS, nombre)
        _fcache[k] = ImageFont.truetype(p, max(6, int(px))) if os.path.exists(p) else ImageFont.load_default()
    return _fcache[k]


def hexa(c, a=255):
    c = (c or "#000000").lstrip("#")
    if len(c) == 3:
        c = "".join(x * 2 for x in c)
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


# ---------------- logotipos vectorizados / badges ----------------
def _logo(d, x, y, h, f, estilo_logo, peso, escala, n100=75):
    if estilo_logo == "no":
        return 0
    et, fondo, txt, _ = FUENTES[f]

    # En Rotten Tomatoes crítico: rojo fresco (>=60%) o verde podrido (<60%)
    if f == "rt":
        fondo = "#FA320A" if n100 >= 60 else "#688A22"

    # En Metacritic el fondo varía según la puntuación
    if f in ("mc", "mc_pub"):
        fondo = "#66CC33" if n100 >= 60 else "#FFCC33" if n100 >= 40 else "#FF0000"
        txt = "#000000" if n100 >= 40 else "#FFFFFF"

    fnt = fuente(h * 0.44 * escala, 2)

    if estilo_logo == "redondo":
        d.ellipse([x, y, x + h, y + h], fill=hexa(fondo))
        if f == "lb":  # 3 círculos oficiales Letterboxd
            r_dot = h * 0.12
            cy = y + h / 2
            d.ellipse([x + h * 0.28 - r_dot, cy - r_dot, x + h * 0.28 + r_dot, cy + r_dot], fill=hexa("#FF8000"))
            d.ellipse([x + h * 0.50 - r_dot, cy - r_dot, x + h * 0.50 + r_dot, cy + r_dot], fill=hexa("#00E054"))
            d.ellipse([x + h * 0.72 - r_dot, cy - r_dot, x + h * 0.72 + r_dot, cy + r_dot], fill=hexa("#40BCF4"))
        elif f == "rt_pub":
            fs = fuente(h * 0.46 * escala, 1)
            d.text((x + h / 2, y + h / 2), "🍿", font=fs, fill=hexa(txt), anchor="mm")
        else:
            fs = fuente(h * (0.34 if len(et) > 3 else 0.42) * escala, 2)
            d.text((x + h / 2, y + h / 2), et if len(et) <= 4 else et[:3], font=fs, fill=hexa(txt), anchor="mm")
        return h

    # Logo rectangular / pastilla
    if f == "lb":
        w = h * 1.5
        d.rounded_rectangle([x, y, x + w, y + h], int(h * 0.22), fill=hexa(fondo))
        r_dot = h * 0.13
        cy = y + h / 2
        d.ellipse([x + w * 0.28 - r_dot, cy - r_dot, x + w * 0.28 + r_dot, cy + r_dot], fill=hexa("#FF8000"))
        d.ellipse([x + w * 0.50 - r_dot, cy - r_dot, x + w * 0.50 + r_dot, cy + r_dot], fill=hexa("#00E054"))
        d.ellipse([x + w * 0.72 - r_dot, cy - r_dot, x + w * 0.72 + r_dot, cy + r_dot], fill=hexa("#40BCF4"))
        return w

    w = d.textlength(et, font=fnt) + h * 0.5
    d.rounded_rectangle([x, y, x + w, y + h], int(h * 0.2), fill=hexa(fondo))
    d.text((x + w / 2, y + h / 2), et, font=fnt, fill=hexa(txt), anchor="mm")
    return w


def _partes(d, f, txt, h, b, n100=75):
    et = FUENTES[f][0]
    if b["logos"] == "no":
        lw = 0
    elif b["logos"] == "redondo":
        lw = h
    elif f == "lb":
        lw = h * 1.5
    else:
        lw = d.textlength(et, font=fuente(h * 0.44 * b["escala_fuente"], 2)) + h * 0.5
    tw = d.textlength(txt, font=fuente(h * 0.56 * b["escala_fuente"], 2 if b["negrita"] else 1))
    return lw, tw


def _medir_item(d, f, txt, h, b, cajas=False, tema=""):
    if tema.startswith("pastillas"):
        pad = b["relleno"] * h / 68
        et = FUENTES[f][0]
        lw = 0 if b["logos"] == "no" else (h * 1.5 if f == "lb" else d.textlength(et, font=fuente(h * 0.5 * b["escala_fuente"], 2)) + pad * 2 + h * 0.2)
        return lw + h * 0.25 + d.textlength(txt, font=fuente(h * 0.6 * b["escala_fuente"], 2 if b["negrita"] else 1))
    lw, tw = _partes(d, f, txt, h, b)
    return max(lw, tw) if cajas else lw + (h * 0.22 if lw else 0) + tw


# ---------------- barra de notas ----------------
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
    pos = b.get("posicion", "bottom")
    vertical = pos.startswith(("left", "right"))
    inclinacion = b.get("inclinacion", "no")

    capa = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(capa)

    fondo = hexa(b["color"], int(255 * b["opacidad"]))
    if claro:
        fondo = hexa("#FFFFFF", int(255 * b["opacidad"]))
    color_txt = hexa("#111111" if claro and b["color_texto"].upper() in ("#FFFFFF", "#FFF") else b["color_texto"])
    cajas = tema == "boxes"
    anchos = [_medir_item(d, f, t, h, b, cajas, tema) for f, t, _ in items]
    caja = [a + pad * 2 for a in anchos]
    alto_caja = h * (1.85 if cajas else 1.0) + pad * 2

    # Inclinación (paralelogramo geométrico nítido)
    slant_dx = int(alto_caja * 0.36) if inclinacion == "right" else -int(alto_caja * 0.36) if inclinacion == "left" else 0

    if vertical:
        tot_h = len(items) * alto_caja + (len(items) - 1) * gap
        maxw = max(caja) + abs(slant_dx)
        x0 = mar + 18 * k if pos.startswith("left") else W - mar - 18 * k - maxw
        y_side = pos.split("-")[1] if "-" in pos else "center"
        y0 = {"top": mar + 18 * k, "center": (H - tot_h) / 2, "bottom": H - mar - 18 * k - tot_h}.get(y_side, (H - tot_h) / 2)
        coords = [(x0, y0 + i * (alto_caja + gap), maxw) for i in range(len(items))]
    else:
        tot_w = sum(caja) + gap * (len(items) - 1) + abs(slant_dx)
        esc = min(1.0, (W - 2 * (mar + 18 * k)) / tot_w)
        if esc < 1:
            h *= esc; pad *= esc; gap *= esc
            anchos = [_medir_item(d, f, t, h, b, cajas, tema) for f, t, _ in items]
            caja = [a + pad * 2 for a in anchos]
            alto_caja = h * (1.85 if cajas else 1.0) + pad * 2
            slant_dx = int(alto_caja * 0.36) if inclinacion == "right" else -int(alto_caja * 0.36) if inclinacion == "left" else 0
            tot_w = sum(caja) + gap * (len(items) - 1) + abs(slant_dx)

        y0 = H - mar - 18 * k - alto_caja if pos.startswith("bottom") else mar + 18 * k

        # Alineación horizontal: izquierda, derecha o centro
        if pos in ("bottom-left", "top-left"):
            x = mar + 18 * k
        elif pos in ("bottom-right", "top-right"):
            x = W - mar - 18 * k - tot_w
        else:
            x = (W - tot_w) / 2

        coords = []
        for c in caja:
            coords.append((x, y0, c))
            x += c + gap

    r = {"default": h * 0.22, "full": alto_caja / 2}.get(str(b["redondeo"]), None)
    r = float(b["redondeo"]) * k if r is None else r
    borde = (1.5 * k if str(b["borde"]) == "default" else float(b["borde"]) * k)
    color_borde = hexa(b["color_borde"])
    lado = b["lado_borde"]

    # Barra continua de fondo
    if tema in ("bar", "pastillas-barra"):
        if vertical:
            xs = coords[0][0] - 12 * k
            xe = coords[0][0] + coords[0][2] + 12 * k
            d.rectangle([xs, coords[0][1] - 12 * k, xe, coords[-1][1] + alto_caja + 12 * k], fill=fondo)
        else:
            yb = coords[0][1] - 14 * k
            d.rectangle([0, yb, W, yb + alto_caja + 28 * k], fill=fondo)

    # Dibujar cada bloque
    for (x, y, w), (f, t, n100) in zip(coords, items):
        # 1. Pastillas (v1 / Nebula)
        if tema.startswith("pastillas"):
            et, col, col_txt, _ = FUENTES[f]
            rr = alto_caja * 0.32 if b["redondeo"] == "default" else r
            fondo_p = (12, 12, 16, 235) if tema == "pastillas-barra" else fondo

            if slant_dx != 0:
                poly = [(x + slant_dx, y), (x + w + slant_dx, y), (x + w, y + alto_caja), (x, y + alto_caja)]
                d.polygon(poly, fill=fondo_p, outline=color_borde if borde > 0 else None, width=int(borde) if borde > 0 else 0)
            else:
                d.rounded_rectangle([x, y, x + w, y + alto_caja], int(rr), fill=fondo_p,
                                    outline=color_borde if borde > 0 else None, width=int(borde) if borde > 0 else 0)

            fnum = fuente(h * 0.6 * b["escala_fuente"], 2 if b["negrita"] else 1)
            vx = x + pad + (slant_dx / 2 if slant_dx != 0 else 0)
            if b["logos"] != "no":
                fl = fuente(h * 0.5 * b["escala_fuente"], 2)
                sw = d.textlength(et, font=fl) + pad * 2 + h * 0.2
                if slant_dx != 0:
                    poly_l = [(x + slant_dx, y), (x + sw + slant_dx, y), (x + sw, y + alto_caja), (x, y + alto_caja)]
                    d.polygon(poly_l, fill=hexa(col))
                else:
                    d.rounded_rectangle([x, y, x + sw, y + alto_caja], int(rr), fill=hexa(col))
                    d.rectangle([x + sw - rr, y, x + sw, y + alto_caja], fill=hexa(col))
                d.text((x + sw / 2 + slant_dx / 2, y + alto_caja / 2), et, font=fl, fill=hexa(col_txt), anchor="mm")
                vx = x + sw + h * 0.22 + (slant_dx / 2 if slant_dx != 0 else 0)
            d.text((vx, y + alto_caja / 2), t, font=fnum, fill=color_txt, anchor="lm")
            continue

        # 2. Temas de bloques (Blocks, Rounded, Boxes, Sharp, Stripes)
        if tema in ("blocks", "rounded-blocks", "boxes", "sharp-blocks") or tema.startswith("stripes"):
            rr = {"blocks": h * 0.12, "rounded-blocks": alto_caja / 2, "boxes": h * 0.1, "sharp-blocks": 0}.get(tema, r)
            if b["redondeo"] != "default":
                rr = r
            if tema.startswith("stripes") or slant_dx != 0:
                rr = 0

            todo = lado == "default" and borde > 0

            # Paralelogramo inclinado nítido ("Deportivo")
            if slant_dx != 0:
                poly = [(x + slant_dx, y), (x + w + slant_dx, y), (x + w, y + alto_caja), (x, y + alto_caja)]
                d.polygon(poly, fill=fondo, outline=color_borde if todo else None, width=int(borde) if todo else 0)
                if borde > 0 and lado != "default":
                    if lado == "left":
                        d.line([(x + slant_dx, y), (x, y + alto_caja)], fill=color_borde, width=int(borde))
                    elif lado == "right":
                        d.line([(x + w + slant_dx, y), (x + w, y + alto_caja)], fill=color_borde, width=int(borde))
                    elif lado == "top":
                        d.line([(x + slant_dx, y), (x + w + slant_dx, y)], fill=color_borde, width=int(borde))
                    elif lado == "bottom":
                        d.line([(x, y + alto_caja), (x + w, y + alto_caja)], fill=color_borde, width=int(borde))

                if tema.startswith("stripes"):
                    ancho_st = int(8 * k)
                    if tema == "stripes-left":
                        poly_st = [(x + slant_dx, y), (x + ancho_st + slant_dx, y), (x + ancho_st, y + alto_caja), (x, y + alto_caja)]
                    else:
                        poly_st = [(x + w + slant_dx - ancho_st, y), (x + w + slant_dx, y), (x + w, y + alto_caja), (x + w - ancho_st, y + alto_caja)]
                    d.polygon(poly_st, fill=hexa(color_nota(n100)))
            else:
                caja_xy = [x, y, x + w, y + alto_caja]
                d.rounded_rectangle(caja_xy, int(rr), fill=fondo, outline=color_borde if todo else None, width=int(borde) if todo else 0)
                if borde > 0 and lado != "default":
                    lx = {"left": [x, y, x + borde, y + alto_caja], "right": [x + w - borde, y, x + w, y + alto_caja],
                          "top": [x, y, x + w, y + borde], "bottom": [x, y + alto_caja - borde, x + w, y + alto_caja]}[lado]
                    d.rectangle(lx, fill=color_borde)
                if tema.startswith("stripes"):
                    ancho = 8 * k
                    cx = x if tema == "stripes-left" else x + w - ancho
                    d.rectangle([cx, y, cx + ancho, y + alto_caja], fill=hexa(color_nota(n100)))

        fnum = fuente(h * 0.56 * b["escala_fuente"], 2 if b["negrita"] else 1)
        offset_x = slant_dx / 2 if slant_dx != 0 else 0

        # Boxes: logo arriba y nota debajo
        if cajas:
            lw, _ = _partes(d, f, t, h, b, n100)
            if lw:
                _logo(d, x + (w - lw) / 2 + offset_x, y + pad, h * 0.92, f, b["logos"], b["negrita"], b["escala_fuente"], n100)
            d.text((x + w / 2 + offset_x, y + pad + h * (1.35 if lw else 0.5)), t, font=fnum, fill=color_txt, anchor="mm")
            continue

        # Bloques normales horizontales
        cx = x + pad + offset_x
        lw = _logo(d, cx, y + pad, h, f, b["logos"], b["negrita"], b["escala_fuente"], n100)
        cx += lw + (h * 0.22 if lw else 0)
        d.text((cx, y + pad + h / 2), t, font=fnum, fill=color_txt, anchor="lm")

    # Sombra con elevación 3D nítida
    if b.get("sombra"):
        alpha = capa.split()[-1]
        sh_mask = Image.new("L", capa.size, 0)
        sh_mask.paste(alpha, (int(2 * k), int(5 * k)))
        sh_mask = sh_mask.filter(ImageFilter.GaussianBlur(9 * k)).point(lambda p: int(p * 0.65))
        sh_black = Image.new("RGBA", img.size, (0, 0, 0, 255))
        img = Image.composite(sh_black, img, sh_mask)

    return Image.alpha_composite(img, capa)


# ---------------- banderas vectoriales ----------------
def bandera(d, x, y, h, pais):
    w = h * 1.5
    if pais == "es":
        d.rectangle([x, y, x + w, y + h], fill=(170, 21, 27))
        d.rectangle([x, y + h / 4, x + w, y + 3 * h / 4], fill=(241, 191, 0))
    elif pais == "gb":
        d.rectangle([x, y, x + w, y + h], fill=(1, 33, 105))
        d.line([x, y, x + w, y + h], fill=(255, 255, 255), width=int(h / 5))
        d.line([x, y + h, x + w, y], fill=(255, 255, 255), width=int(h / 5))
        d.rectangle([x + w * .42, y, x + w * .58, y + h], fill=(255, 255, 255))
        d.rectangle([x, y + h * .38, x + w, y + h * .62], fill=(255, 255, 255))
        d.rectangle([x + w * .45, y, x + w * .55, y + h], fill=(200, 16, 46))
        d.rectangle([x, y + h * .42, x + w, y + h * .58], fill=(200, 16, 46))
    elif pais == "us":
        d.rectangle([x, y, x + w, y + h], fill=(255, 255, 255))
        for i in range(7):
            d.rectangle([x, y + i * 2 * h / 13, x + w, y + (i * 2 + 1) * h / 13], fill=(179, 25, 66))
        d.rectangle([x, y, x + w * 0.42, y + 7 * h / 13], fill=(10, 49, 97))
    elif pais == "jp":
        d.rectangle([x, y, x + w, y + h], fill=(255, 255, 255))
        d.ellipse([x + w / 2 - h * .28, y + h * .22, x + w / 2 + h * .28, y + h * .78], fill=(188, 0, 45))
    elif pais == "fr":
        for i, c in enumerate(((0, 35, 149), (255, 255, 255), (237, 41, 57))):
            d.rectangle([x + i * w / 3, y, x + (i + 1) * w / 3, y + h], fill=c)
    elif pais == "it":
        for i, c in enumerate(((0, 146, 70), (255, 255, 255), (206, 43, 55))):
            d.rectangle([x + i * w / 3, y, x + (i + 1) * w / 3, y + h], fill=c)
    elif pais == "de":
        for i, c in enumerate(((0, 0, 0), (221, 0, 0), (255, 206, 0))):
            d.rectangle([x, y + i * h / 3, x + w, y + (i + 1) * h / 3], fill=c)
    elif pais == "kr":
        d.rectangle([x, y, x + w, y + h], fill=(255, 255, 255))
        d.pieslice([x + w / 2 - h * .25, y + h * .25, x + w / 2 + h * .25, y + h * .75], 180, 360, fill=(205, 46, 58))
        d.pieslice([x + w / 2 - h * .25, y + h * .25, x + w / 2 + h * .25, y + h * .75], 0, 180, fill=(0, 71, 160))
    else:
        return 0
    d.rectangle([x, y, x + w, y + h], outline=(0, 0, 0, 140), width=max(1, int(h / 16)))
    return w


# ---------------- insignias de calidad ----------------
PALETA = {
    "normal": {"fondo": "#141414", "txt": "#FFFFFF", "borde": "#444444"},
    "oro": {"fondo": "#111114", "txt": "#E9C46A", "borde": "#D4AF37"},
    "plata": {"fondo": "#111114", "txt": "#FFFFFF", "borde": "#A0AEC0"},
    "color": None,
}

NEBULA = {
    "res": ("#FFFFFF", "#000000"),
    "hdr": ("#FFC400", "#000000"),
    "dv": ("#12101E", "#FFFFFF"),
    "audio": ("#141414", "#FFFFFF"),
    "idioma": ("#2D3748", "#FFFFFF"),
    "etiqueta": ("#F5C518", "#000000"),
    "premios": ("#121214", "#E9C46A"),
    "edad": ("#DD6B20", "#FFFFFF"),
    "edicion": ("#2B6CB0", "#FFFFFF"),
}

COLOR_TIPO = {
    "res": "#3182CE", "dv": "#805AD5", "hdr": "#D69E2E", "audio": "#319795", "fuente": "#E53E3E",
    "codec": "#4A5568", "edicion": "#4C51BF", "edad": "#DD6B20", "idioma": "#2D3748",
    "imax": "#0077C8", "3d": "#38A169", "premios": "#D4AF37", "etiqueta": "#C53030"
}


def lista_insignias(q, ins, etiqueta):
    """Devuelve [(tipo, texto)] en el orden configurado."""
    out = []
    lista_cfg = ins.get("lista") or ["res", "hdr_dv", "audio", "idioma", "premios", "edad"]
    for t in lista_cfg:
        if t == "premios" and q.get("premios"):
            out.append(("premios", q["premios"]))
        elif t == "res" and q.get("res"):
            out.append(("res", q["res"]))
        elif t == "hdr_dv":
            if q.get("dv") and q.get("hdr"): out.append(("dv", "DV · HDR"))
            elif q.get("dv"): out.append(("dv", "DOLBY VISION"))
            elif q.get("hdr"): out.append(("hdr", q["hdr"]))
        elif t == "audio" and q.get("audio"):
            out.append(("audio", q["audio"]))
        elif t == "idioma":
            if q.get("dual"): out.append(("idioma", "DUAL"))
            elif q.get("es"): out.append(("bandera", "es"))
            elif q.get("vose"): out.append(("idioma", "VOSE"))
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
        elif t == "pais" and q.get("pais"):
            out.append(("bandera", q["pais"]))

    if etiqueta:
        out.insert(0, ("etiqueta", etiqueta.upper()))
    return out[: ins.get("max", 4)]


def insignias(img, q, cf):
    ins = cf["insignias"]
    if not ins.get("activar", True):
        return img
    lst = lista_insignias(q, ins, cf["notas"].get("etiqueta", ""))
    if not lst:
        return img

    W, H = img.size
    k = W / 1000.0
    h = 50 * k * ins.get("escala", 1.0)
    gap = 10 * k
    m = 26 * k
    capa = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(capa)
    fnt = fuente(h * 0.48, 2)
    est = ins.get("estilo", "nebula")

    anchos = [(h * 1.5 if t == "bandera" else d.textlength(s, font=fnt) + h * 0.72) for t, s in lst]
    pos = ins.get("posicion", "right")
    vertical = ins.get("apilar", False) and pos in ("left", "right", "bottom|left", "bottom|right")

    barra_pos = cf["barra"].get("posicion", "bottom")
    offset_barra_y = (130 * k * cf["barra"].get("escala_fuente", 1.0)) if cf["notas"].get("fuentes") else 0

    if vertical:
        tot = len(lst) * h + gap * (len(lst) - 1)
        if pos.startswith("bottom"):
            y = H - m - tot - (offset_barra_y if barra_pos.startswith("bottom") else 0)
        else:
            y = m + (offset_barra_y if barra_pos.startswith("top") else 0)
        xs = [m if pos.endswith("left") else W - m - a for a in anchos]
        ys = [y + i * (h + gap) for i in range(len(lst))]
    else:
        tot = sum(anchos) + gap * (len(lst) - 1)
        if pos.startswith("bottom"):
            y = H - m - h - (offset_barra_y if barra_pos.startswith("bottom") else 0)
        else:
            y = m + (offset_barra_y if barra_pos.startswith("top") else 0)
        lado = pos.split("|")[-1]
        x = m if lado == "left" else W - m - tot if lado == "right" else (W - tot) / 2
        xs, ys = [], []
        for a in anchos:
            xs.append(x); ys.append(y); x += a + gap

    for (t, s), a, x, y in zip(lst, anchos, xs, ys):
        if t == "bandera":
            bandera(d, x, y, h, s)
            continue

        if est == "nebula":
            fo, tx, bo = NEBULA.get(t, ("#141414", "#FFFFFF"))[0], NEBULA.get(t, ("#141414", "#FFFFFF"))[1], None
            if t == "res" and s != "4K":
                fo, tx = "#141414", "#FFFFFF"
            if t == "premios":
                bo = "#D4AF37"
        elif est == "color":
            fo, tx, bo = COLOR_TIPO.get(t, "#333333"), "#FFFFFF", None
        else:
            p = PALETA.get(est, PALETA["normal"])
            fo, tx, bo = p["fondo"], p["txt"], p["borde"]

        d.rounded_rectangle([x, y, x + a, y + h], int(h * 0.22), fill=hexa(fo, int(255 * ins.get("opacidad", 0.88))),
                            outline=hexa(bo, 220) if bo else None, width=max(1, int(2 * k)) if bo else 0)
        d.text((x + a / 2, y + h / 2), s, font=fnt, fill=hexa(tx), anchor="mm")

    # Sombra sutil para las insignias
    alpha = capa.split()[-1]
    sh_mask = Image.new("L", capa.size, 0)
    sh_mask.paste(alpha, (int(1.5 * k), int(3.5 * k)))
    sh_mask = sh_mask.filter(ImageFilter.GaussianBlur(6 * k)).point(lambda p: int(p * 0.55))
    sh_black = Image.new("RGBA", img.size, (0, 0, 0, 255))
    img = Image.composite(sh_black, img, sh_mask)

    return Image.alpha_composite(img, capa)


def componer(img, notas, q, cf):
    W = cf["imagen"]["ancho"]
    img = img.convert("RGBA")
    if img.width != W:
        img = img.resize((W, int(img.height * W / img.width)), Image.LANCZOS)
    img = barra(img, notas, cf)
    img = insignias(img, q, cf)
    return img.convert("RGB")


# ---------------- estilos prediseñados (Presets) ----------------
_B = {"opacidad": 0.78, "color": "#000000", "color_texto": "#FFFFFF", "redondeo": "default", "relleno": 10, "margen": 0,
      "borde": 0, "color_borde": "#FFFFFF", "lado_borde": "default", "inclinacion": "no", "escala_fuente": 1.0,
      "negrita": True, "logos": "normal", "sombra": True, "posicion": "bottom"}
_I = {"activar": True, "posicion": "right", "apilar": False, "estilo": "normal", "escala": 1.0, "opacidad": 0.88}


def _p(nombre, desc, tema, claro=False, barra=None, ins=None):
    return {"nombre": nombre, "desc": desc, "conf": {"tema": tema, "claro": claro, "barra": {**_B, **(barra or {})}, "insignias": {**_I, **(ins or {})}}}


PRESETS = [
    _p("Nebula (Firma v1)", "Pastillas de dos colores de alta visibilidad con insignias Nebula", "pastillas",
       barra={"escala_fuente": 1.1, "opacidad": 0.85}, ins={"estilo": "nebula"}),
    _p("Nebula Barra", "Franja oscura con pastillas vibrantes integradas", "pastillas-barra",
       barra={"escala_fuente": 1.05, "opacidad": 0.72}, ins={"estilo": "nebula"}),
    _p("RPDB Clásico", "Barra negra minimalista a lo ancho del póster", "bar",
       barra={"opacidad": 0.65}),
    _p("RPDB Bloques", "Tarjetas independientes de esquinas redondeadas suaves", "blocks"),
    _p("RPDB Bloques Redondos", "Píldoras redondeadas modernas de estilo stream", "rounded-blocks"),
    _p("RPDB Cajas", "Diseño en dos pisos: logo de la plataforma arriba y nota grande abajo", "boxes",
       barra={"escala_fuente": 0.92}),
    _p("RPDB Bloques Rectos", "Bloques nítidos sin redondeo con máxima definición", "sharp-blocks",
       barra={"opacidad": 0.88}),
    _p("RPDB Franjas", "Acento vertical de color según la calificación de la obra", "stripes-right"),
    _p("RPDB Claro", "Elegante diseño blanco con tipografía oscura", "rounded-blocks", claro=True,
       barra={"opacidad": 0.92, "sombra": False}),
    _p("Deportivo Inclinado", "Paralelogramos agresivos e inclinados con corte deportivo", "sharp-blocks",
       barra={"inclinacion": "right", "opacidad": 0.9, "escala_fuente": 1.05}, ins={"estilo": "color"}),
    _p("Cine Dorado & Premios", "Negro grafito y oro con insignias doradas de galardones", "boxes",
       barra={"color": "#0E0E12", "color_texto": "#E9C46A", "borde": 2, "color_borde": "#E9C46A", "opacidad": 0.92, "escala_fuente": 0.92},
       ins={"estilo": "oro"}),
    _p("Columna Lateral", "Columna vertical en el lateral izquierdo con logos redondos", "rounded-blocks",
       barra={"posicion": "left-center", "logos": "redondo", "escala_fuente": 0.85},
       ins={"posicion": "bottom|right", "apilar": True}),
    _p("Minimalista", "Solo las cifras flotantes con sombra, sin marcos ni fondos", "bar",
       barra={"logos": "no", "opacidad": 0.01, "escala_fuente": 1.2, "sombra": True}, ins={"activar": False}),
    _p("Notas Arriba", "Notas en la parte superior e insignias en la inferior", "rounded-blocks",
       barra={"posicion": "top"}, ins={"posicion": "bottom|center", "estilo": "color"}),
]
