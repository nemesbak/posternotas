#!/usr/bin/env python3
# Póster Notas — motor: notas + insignias grabadas en el póster (clon propio de RatingPosterDB).
# Notas: IMDb (dataset oficial diario), TMDB (CommunityRating de Jellyfin), RT crítica (CriticRating);
# el resto (Metacritic, RT público, Letterboxd, Trakt, Roger Ebert, MAL, MDBList) solo con MDBLIST_KEY.
# Calidad leída del propio archivo. Premios obtenidos vía Wikidata. Pósters originales guardados para revertir.
import base64, csv, gzip, hashlib, io, json, os, re, sqlite3, threading, time, urllib.parse, urllib.request
from PIL import Image
import render

DATA = os.environ.get("PN_DATA", "/data")
DB = os.path.join(DATA, "posternotas.sqlite")
ORIG = os.path.join(DATA, "originales")
CONF = os.path.join(DATA, "config.json")

DEFAULT_INSIGNIAS = ["res", "hdr_dv", "audio", "idioma", "premios", "edad"]

DEFAULT = {
    "servidores": {"emby": True, "jellyfin": True},
    "tipos": {"Movie": True, "Series": True},
    "imagen": {"origen": "actual", "idioma": "es", "ancho": 1000, "jpg": 90, "fallback": True, "fondos": False},
    "notas": {"fuentes": ["imdb", "rt", "tmdb"], "formato": 0, "decimales_coma": True, "min_votos_imdb": 0, "etiqueta": ""},
    "tema": "pastillas", "claro": False,
    "barra": {"posicion": "bottom", "opacidad": 0.78, "color": "#000000", "color_texto": "#FFFFFF", "redondeo": "default",
              "relleno": 10, "margen": 0, "borde": 0, "color_borde": "#FFFFFF", "lado_borde": "default",
              "inclinacion": "no", "escala_fuente": 1.1, "negrita": True, "logos": "normal", "sombra": True},
    "insignias": {"activar": True, "posicion": "right", "apilar": False, "max": 4, "escala": 1.0, "opacidad": 0.88,
                  "estilo": "nebula", "lista": DEFAULT_INSIGNIAS},
    "auto": {"programado": False, "hora": "03:40", "pausa_s": 0.4, "refrescar_dias": 7},
}

_lock = threading.Lock()


def get_id(it, clave):
    """Obtiene un ProviderId de forma insensible a mayúsculas/minúsculas (Imdb, IMDB, Tmdb, TMDB...)."""
    if not it:
        return None
    p = it.get("ProviderIds") or {}
    for k in (clave, clave.upper(), clave.lower(), clave.capitalize()):
        if p.get(k):
            return str(p[k]).strip()
    return None


def _mezcla(base, u):
    for k, v in (u or {}).items():
        if isinstance(v, dict) and isinstance(base.get(k), dict):
            _mezcla(base[k], v)
        elif k in base:
            base[k] = v
    return base


def conf():
    c = json.loads(json.dumps(DEFAULT))
    try:
        _mezcla(c, json.load(open(CONF)))
    except Exception:
        pass
    if not c.get("insignias", {}).get("lista"):
        c.setdefault("insignias", {})["lista"] = list(DEFAULT_INSIGNIAS)
    return c


def guardar_conf(c):
    os.makedirs(DATA, exist_ok=True)
    cfg = _mezcla(json.loads(json.dumps(DEFAULT)), c)
    if not cfg.get("insignias", {}).get("lista"):
        cfg["insignias"]["lista"] = list(DEFAULT_INSIGNIAS)
    json.dump(cfg, open(CONF + ".tmp", "w"), ensure_ascii=False, indent=1)
    os.replace(CONF + ".tmp", CONF)


def clave(n):
    try:
        for l in open(os.environ.get("PN_ENV", "/odin.env")):
            if l.startswith(n + "="):
                return l.split("=", 1)[1].strip().strip('"')
    except Exception:
        pass
    return ""


def db():
    os.makedirs(DATA, exist_ok=True)
    c = sqlite3.connect(DB, timeout=30)
    c.executescript("""
    create table if not exists imdb(tt text primary key, nota real, votos int);
    create table if not exists mdb(tt text primary key, datos text, ts int);
    create table if not exists premios(tt text primary key, premio text, ts int);
    create table if not exists aplicado(servidor text, item text, firma text, tag text, ts int, titulo text, primary key(servidor,item));
    create table if not exists meta(k text primary key, v text);
    """)
    return c


# ---------- notas ----------
def actualizar_imdb(forzar=False):
    c = db()
    r = c.execute("select v from meta where k='imdb_ts'").fetchone()
    if r and not forzar and time.time() - float(r[0]) < 20 * 3600:
        return "al día"
    raw = urllib.request.urlopen("https://datasets.imdbws.com/title.ratings.tsv.gz", timeout=300).read()
    filas = csv.reader(io.TextIOWrapper(gzip.GzipFile(fileobj=io.BytesIO(raw)), "utf-8"), delimiter="\t")
    next(filas)
    with c:
        c.execute("delete from imdb")
        c.executemany("insert into imdb values(?,?,?)", ((t, float(n), int(v)) for t, n, v in filas))
        c.execute("insert or replace into meta values('imdb_ts',?)", (str(time.time()),))
    return "%d títulos" % c.execute("select count(*) from imdb").fetchone()[0]


MDB_MAP = {
    "metacritic": "mc", "metacriticuser": "mc_pub", "tomatoes": "rt",
    "popcorn": "rt_pub", "tomatoesaudience": "rt_pub",
    "letterboxd": "lb", "trakt": "trakt", "rogerebert": "ebert", "myanimelist": "mal"
}


def mdblist(tt):
    k = clave("MDBLIST_KEY")
    if not k or not tt:
        return {}
    c = db()
    r = c.execute("select datos, ts from mdb where tt=?", (tt,)).fetchone()
    if r and time.time() - r[1] < conf()["auto"]["refrescar_dias"] * 86400:
        return json.loads(r[0])
    try:
        d = json.loads(urllib.request.urlopen(f"https://mdblist.com/api/?apikey={k}&i={tt}", timeout=20).read())
        out = {MDB_MAP[x["source"]]: x["value"] for x in d.get("ratings", []) if x.get("source") in MDB_MAP and x.get("value")}
        if d.get("score"):
            out["mdblist"] = d["score"]
        with c:
            c.execute("insert or replace into mdb values(?,?,?)", (tt, json.dumps(out), int(time.time())))
        return out
    except Exception:
        return {}


def buscar_premios(tt):
    """Consulta galardones destacados en Wikidata por ID de IMDb (tt) y los almacena en caché."""
    if not tt:
        return None
    c = db()
    r = c.execute("select premio, ts from premios where tt=?", (tt,)).fetchone()
    if r and time.time() - r[1] < 30 * 86400:
        return r[0] if r[0] else None

    sparql = f"""SELECT DISTINCT ?awardLabel WHERE {{
      ?m wdt:P345 "{tt}" .
      ?m wdt:P166 ?award .
      ?award rdfs:label ?awardLabel .
      FILTER(LANG(?awardLabel) = "en")
    }} LIMIT 25"""
    url = "https://query.wikidata.org/sparql?query=" + urllib.parse.quote(sparql)
    req = urllib.request.Request(url, headers={"Accept": "application/json", "User-Agent": "PosterNotas/2.0"})
    premio = None
    try:
        data = json.loads(urllib.request.urlopen(req, timeout=4).read())
        raw = [b["awardLabel"]["value"] for b in data.get("results", {}).get("bindings", [])]
        oscars = sum(1 for a in raw if "Academy Award" in a or "Oscar" in a)
        emmys = sum(1 for a in raw if "Emmy" in a)
        gg = sum(1 for a in raw if "Golden Globe" in a)
        bafta = sum(1 for a in raw if "BAFTA" in a)
        cannes = sum(1 for a in raw if "Palme d'Or" in a or "Cannes" in a)
        goya = sum(1 for a in raw if "Goya" in a)

        if oscars > 1: premio = f"🏆 {oscars} OSCARS"
        elif oscars == 1: premio = "🏆 OSCAR"
        elif cannes >= 1: premio = "🏆 PALMA DE ORO"
        elif goya > 1: premio = f"🏆 {goya} GOYAS"
        elif goya == 1: premio = "🏆 GOYA"
        elif emmys > 1: premio = f"🏆 {emmys} EMMYS"
        elif emmys == 1: premio = "🏆 EMMY"
        elif gg >= 1: premio = "🏆 GLOBO DE ORO"
        elif bafta >= 1: premio = "🏆 BAFTA"
    except Exception:
        pass

    with c:
        c.execute("insert or replace into premios values(?,?,?)", (tt, premio or "", int(time.time())))
    return premio


def notas(item, jf=None):
    cf = conf()["notas"]
    tt = get_id(item, "Imdb") or get_id(jf, "Imdb")
    n = {}
    r = db().execute("select nota, votos from imdb where tt=?", (tt,)).fetchone() if tt else None
    if r and r[1] >= cf["min_votos_imdb"]:
        n["imdb"] = r[0]
    crit = item.get("CriticRating") or (jf or {}).get("CriticRating")
    if crit:
        n["rt"] = int(crit)
    tm = (jf or {}).get("CommunityRating") or item.get("CommunityRating")
    if tm:
        n["tmdb"] = round(float(tm), 1)
    extra = {"mc", "mc_pub", "rt_pub", "lb", "trakt", "ebert", "mal", "mdblist"}
    if extra & set(cf["fuentes"]) or "rt" not in n:
        for k, v in mdblist(tt).items():
            n.setdefault(k, v)
    if "media" in cf["fuentes"]:
        vals = [v * 100 / render.FUENTES[k][3] for k, v in n.items() if k in render.FUENTES]
        if vals:
            n["media"] = round(sum(vals) / len(vals))
    return n


# ---------- calidad ----------
EDICIONES = [
    (r"director'?s?[ ._-]?cut|montaje del director", "MONTAJE DIRECTOR"),
    (r"extended|extendida", "EXTENDIDA"),
    (r"unrated|sin censura", "SIN CENSURA"),
    (r"remaster", "REMASTER"),
    (r"criterion", "CRITERION")
]

PAISES = {
    "spa": "es", "es": "es", "esp": "es",
    "eng": "gb", "en": "gb",
    "jpn": "jp", "ja": "jp",
    "fre": "fr", "fra": "fr", "fr": "fr",
    "ita": "it", "it": "it",
    "ger": "de", "deu": "de", "de": "de",
    "kor": "kr", "ko": "kr"
}


def parse_edad(oc):
    if not oc:
        return None
    oc_up = oc.upper()
    # Clasificación española
    m = re.search(r"\b(18|16|12|7)\b", oc_up)
    if m:
        return f"+{m.group(1)}"
    if "TP" in oc_up or "APTA" in oc_up:
        return "TP"
    # Clasificación estadounidense
    for us in ("TV-MA", "NC-17", "PG-13", "TV-14", "TV-PG", "PG", "R", "G"):
        if us in oc_up:
            return us
    return None


def calidad(item, ruta=""):
    ms = item.get("MediaStreams") or []
    v = next((s for s in ms if s.get("Type") == "Video"), None)
    au = [s for s in ms if s.get("Type") == "Audio"]
    ruta = (ruta or item.get("Path") or "").lower()
    q = {}

    if v:
        w, h = v.get("Width") or 0, v.get("Height") or 0
        q["res"] = "4K" if w >= 3200 or h >= 1700 else "1080p" if w >= 1800 or h >= 1000 else "720p" if w >= 1200 or h >= 700 else "SD"
        rng = " ".join(str(v.get(k) or "") for k in ("VideoRange", "VideoRangeType", "ExtendedVideoType", "ExtendedVideoSubType", "DisplayTitle")).upper()
        if "DOVI" in rng or "DOLBYVISION" in rng or "DOLBY VISION" in rng:
            q["dv"] = True
        if "HDR10PLUS" in rng or "HDR10+" in rng:
            q["hdr"] = "HDR10+"
        elif "HDR" in rng or "HLG" in rng:
            q["hdr"] = "HDR"
        c = (v.get("Codec") or "").lower()
        q["codec"] = {"hevc": "H.265", "h265": "H.265", "h264": "H.264", "avc": "H.264", "av1": "AV1", "vvc": "H.266"}.get(c, c.upper() or None)
        if v.get("Video3DFormat") or re.search(r"\b3d\b|sbs|half-ou", ruta):
            q["3d"] = True

    if au:
        txt = " ".join(" ".join(str(s.get(k) or "") for k in ("Profile", "DisplayTitle", "Title", "Codec")) for s in au).lower()
        mx = max((s.get("Channels") or 0) for s in au)
        canales = "7.1" if mx >= 8 else "5.1" if mx >= 6 else "2.0"
        if "atmos" in txt: q["audio"] = "ATMOS"
        elif "truehd" in txt: q["audio"] = "TRUEHD " + canales
        elif "dts:x" in txt or "dts-x" in txt: q["audio"] = "DTS:X"
        elif "dts-hd" in txt or "dts hd" in txt: q["audio"] = "DTS-HD " + canales
        elif "eac3" in txt or "e-ac-3" in txt or "dd+" in txt: q["audio"] = "DD+ " + canales
        elif "ac3" in txt: q["audio"] = "DD " + canales
        elif "dts" in txt: q["audio"] = "DTS " + canales
        elif "flac" in txt or "pcm" in txt: q["audio"] = "LOSSLESS " + canales
        else: q["audio"] = canales

        langs = [(s.get("Language") or "").lower() for s in au]
        tiene_es = any(l in ("spa", "es", "esp", "spanish") for l in langs)
        tiene_otro = any(l and l not in ("spa", "es", "esp", "spanish", "und") for l in langs)

        q["es"] = tiene_es
        q["dual"] = tiene_es and tiene_otro
        q["vose"] = not tiene_es and (tiene_otro or any(s.get("Type") == "Subtitle" for s in ms))

        pais = next((PAISES[l] for l in langs if l in PAISES and l not in ("spa", "es", "esp")), None)
        if pais:
            q["pais"] = pais

    q["fuente"] = "REMUX" if "remux" in ruta else "BLURAY" if re.search(r"blu-?ray|bdrip|brrip", ruta) else "WEB" if re.search(r"web-?dl|webrip|\bweb\b", ruta) else None
    q["edicion"] = next((e for p, e in EDICIONES if re.search(p, ruta)), None)
    q["imax"] = "imax" in ruta or any("imax" in (s.get("DisplayTitle") or "").lower() for s in ms)
    q["edad"] = parse_edad(item.get("OfficialRating"))

    # Premios (vía Wikidata)
    tt = get_id(item, "Imdb")
    if tt:
        prem = buscar_premios(tt)
        if prem:
            q["premios"] = prem

    return {k: v for k, v in q.items() if v}


# ---------- servidores ----------
SRV = {"emby": "http://192.168.1.25:8097", "jellyfin": "http://192.168.1.25:8096"}


def api(srv, path, data=None, ctype=None, metodo=None, crudo=False):
    k = clave("EMBY_KEY" if srv == "emby" else "JELLYFIN_KEY")
    h = {"Authorization": f'MediaBrowser Token="{k}"'}
    if ctype: h["Content-Type"] = ctype
    r = urllib.request.urlopen(urllib.request.Request(SRV[srv] + path, data=data, headers=h, method=metodo), timeout=120).read()
    return r if crudo else (json.loads(r) if r else None)


CAMPOS = "ProviderIds,CommunityRating,CriticRating,OfficialRating,MediaStreams,ImageTags,BackdropImageTags,ProductionYear,Path"


def listar(srv, tipos, buscar=None, limite=None):
    q = {"Recursive": "true", "IncludeItemTypes": ",".join(tipos), "Fields": CAMPOS, "SortBy": "DateCreated", "SortOrder": "Descending"}
    if buscar: q["SearchTerm"] = buscar
    if limite: q["Limit"] = str(limite)
    return api(srv, "/Items?" + urllib.parse.urlencode(q))["Items"]


def item(srv, iid):
    res = api(srv, f"/Items?Ids={iid}&Fields={CAMPOS}")
    if res and res.get("Items"):
        return res["Items"][0]
    return api(srv, f"/Users/{usuario_emby()}/Items/{iid}?Fields={CAMPOS}" if srv == "emby" else f"/Items/{iid}?Fields={CAMPOS}")


def par_jellyfin(it):
    pid = it.get("ProviderIds") or {}
    for c in listar("jellyfin", [it["Type"]], it["Name"], 20):
        c_pid = c.get("ProviderIds") or {}
        if any(get_id(it, k) and get_id(it, k) == get_id(c, k) for k in ("Imdb", "Tmdb", "Tvdb")):
            return c
    return None


def calidad_serie(srv, sid):
    try:
        ep_res = api(srv, "/Items?" + urllib.parse.urlencode({"ParentId": sid, "Recursive": "true", "IncludeItemTypes": "Episode", "Fields": "MediaStreams,Path", "Limit": "1", "SortBy": "DateCreated", "SortOrder": "Descending"}))
        ep = ep_res.get("Items", []) if ep_res else []
        q = calidad(ep[0]) if ep else {}
        # Incorporar premios y edad de la serie usando item() para evitar 404 en Emby
        sit = item(srv, sid)
        if sit:
            tt = get_id(sit, "Imdb")
            if tt:
                prem = buscar_premios(tt)
                if prem: q["premios"] = prem
            if not q.get("edad") and sit.get("OfficialRating"):
                q["edad"] = parse_edad(sit["OfficialRating"])
        return q
    except Exception:
        return {}


_ue = None
def usuario_emby():
    global _ue
    if not _ue:
        _ue = next(u["Id"] for u in api("emby", "/Users") if (u.get("Policy") or {}).get("IsAdministrator"))
    return _ue


def tmdb_poster(it, sin_texto, idioma):
    """Póster de TMDB: sin texto (iso_639_1 null) o en el idioma pedido."""
    tm = get_id(it, "Tmdb")
    if not tm:
        return None
    tipo = "movie" if it["Type"] == "Movie" else "tv"
    k = clave("TMDB_KEY")
    langs = "null" if sin_texto else f"{idioma},null"
    try:
        d = json.loads(urllib.request.urlopen(f"https://api.themoviedb.org/3/{tipo}/{tm}/images?api_key={k}&include_image_language={langs}", timeout=20).read())
        ps = [p for p in d.get("posters", []) if (p.get("iso_639_1") is None) == sin_texto or (not sin_texto and p.get("iso_639_1") == idioma)]
        if not ps:
            return None
        p = max(ps, key=lambda p: (p.get("vote_average", 0), p.get("width", 0)))
        return Image.open(io.BytesIO(urllib.request.urlopen("https://image.tmdb.org/t/p/original" + p["file_path"], timeout=60).read()))
    except Exception:
        return None


def original(srv, it, tipo="Primary"):
    p = os.path.join(ORIG, srv, it["Id"] + ("" if tipo == "Primary" else "_fondo") + ".jpg")
    tag = (it.get("ImageTags") or {}).get("Primary") if tipo == "Primary" else ((it.get("BackdropImageTags") or [None])[0])
    r = db().execute("select tag from aplicado where servidor=? and item=?", (srv, it["Id"] + ("" if tipo == "Primary" else "#fondo"))).fetchone()
    if os.path.exists(p) and (not tag or (r and r[0] == tag)):
        return Image.open(p)
    if not tag:
        return None
    raw = api(srv, f"/Items/{it['Id']}/Images/{tipo}" + ("/0" if tipo == "Backdrop" else "") + "?quality=100", crudo=True)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    open(p, "wb").write(raw)
    return Image.open(io.BytesIO(raw))


CLAVES_FIRMA = ("imagen", "notas", "tema", "claro", "barra", "insignias")


def firma(n, q, cf):
    return hashlib.sha1(json.dumps([n, q, {k: cf[k] for k in CLAVES_FIRMA}], sort_keys=True).encode()).hexdigest()[:16]


def generar(srv, it, jf=None, cf=None):
    """Devuelve (jpeg_bytes | motivo, notas, calidad)."""
    cf = cf or conf()
    n = notas(it, jf if srv == "emby" else it)
    q = calidad(it) if it["Type"] == "Movie" else calidad_serie(srv, it["Id"])
    if cf["imagen"]["fallback"] and not n and not (cf["insignias"]["activar"] and q):
        return "sin notas", n, q
    org = cf["imagen"]["origen"]
    base = tmdb_poster(it, org == "sin_texto", cf["imagen"]["idioma"]) if org in ("sin_texto", "idioma") else None
    base = base or original(srv, it)
    if base is None:
        return "sin póster", n, q
    out = render.componer(base, n, q, cf)
    buf = io.BytesIO()
    out.save(buf, "JPEG", quality=cf["imagen"]["jpg"])
    return buf.getvalue(), n, q


def subir(srv, iid, jpg, tipo="Primary"):
    api(srv, f"/Items/{iid}/Images/{tipo}" + ("/0" if tipo == "Backdrop" else ""), data=base64.b64encode(jpg), ctype="image/jpeg", metodo="POST")
    nuevo = item(srv, iid)
    return (nuevo.get("ImageTags") or {}).get("Primary") if tipo == "Primary" else ((nuevo.get("BackdropImageTags") or [None])[0])


def procesar(srv, it, jf=None, forzar=False):
    cf = conf()
    c = db()
    r = c.execute("select firma, tag from aplicado where servidor=? and item=?", (srv, it["Id"])).fetchone()
    tag = (it.get("ImageTags") or {}).get("Primary")
    if r and not forzar:  # comprobar antes de dibujar
        n0 = notas(it, jf if srv == "emby" else it)
        q0 = calidad(it) if it["Type"] == "Movie" else calidad_serie(srv, it["Id"])
        if r[0] == firma(n0, q0, cf) and r[1] == tag:
            return "igual"
    jpg, n, q = generar(srv, it, jf, cf)
    if isinstance(jpg, str):
        return jpg
    fi = firma(n, q, cf)
    nt = subir(srv, it["Id"], jpg)
    with c:
        c.execute("insert or replace into aplicado values(?,?,?,?,?,?)", (srv, it["Id"], fi, nt, int(time.time()), it["Name"]))
    if cf["imagen"]["fondos"] and (it.get("BackdropImageTags") or []):
        fo = original(srv, it, "Backdrop")
        if fo is not None:
            cfb = json.loads(json.dumps(cf))
            cfb["barra"]["posicion"] = "right-top"
            cfb["insignias"]["activar"] = False
            cfb["imagen"]["ancho"] = 1920
            out = render.componer(fo, n, q, cfb)
            buf = io.BytesIO()
            out.save(buf, "JPEG", quality=cf["imagen"]["jpg"])
            ntf = subir(srv, it["Id"], buf.getvalue(), "Backdrop")
            with c:
                c.execute("insert or replace into aplicado values(?,?,?,?,?,?)", (srv, it["Id"] + "#fondo", fi, ntf, int(time.time()), it["Name"]))
    return "aplicado"


def revertir(srv, iid):
    res = "sin original"
    for suf, tipo in (("", "Primary"), ("_fondo", "Backdrop")):
        p = os.path.join(ORIG, srv, iid + suf + ".jpg")
        if os.path.exists(p):
            api(srv, f"/Items/{iid}/Images/{tipo}" + ("/0" if tipo == "Backdrop" else ""), data=base64.b64encode(open(p, "rb").read()), ctype="image/jpeg", metodo="POST")
            os.remove(p)
            res = "revertido"
    with db() as c:
        c.execute("delete from aplicado where servidor=? and (item=? or item=?)", (srv, iid, iid + "#fondo"))
    return res


ESTADO = {"activo": False, "hecho": 0, "total": 0, "ultimo": "", "errores": 0, "log": []}


def log(msg):
    ESTADO["log"] = (ESTADO["log"] + [time.strftime("%d/%m %H:%M:%S ") + msg])[-300:]


def pasada(limite=None, buscar=None, forzar=False, revertir_todo=False):
    if not _lock.acquire(blocking=False):
        return "ya hay una pasada en marcha"
    try:
        cf = conf()
        ESTADO.update(activo=True, hecho=0, total=0, errores=0)
        if not revertir_todo:
            log("IMDb: " + actualizar_imdb())
        tipos = [t for t, on in cf["tipos"].items() if on]
        jf_idx = {}
        if not revertir_todo:
            for it in listar("jellyfin", tipos, buscar):
                for k in ("Imdb", "Tmdb", "Tvdb"):
                    v = get_id(it, k)
                    if v: jf_idx[(k, v)] = it
        for srv in ("emby", "jellyfin"):
            if not cf["servidores"].get(srv):
                continue
            if revertir_todo:
                ids = [r[0] for r in db().execute("select item from aplicado where servidor=? and item not like '%#fondo'", (srv,))]
                ESTADO["total"] += len(ids)
                for i in ids:
                    try:
                        log(f"{srv} {i}: {revertir(srv, i)}")
                    except Exception as e:
                        ESTADO["errores"] += 1
                        log(f"{srv} {i}: ERROR {e}")
                    ESTADO["hecho"] += 1
                    time.sleep(cf["auto"]["pausa_s"])
                continue
            items = listar(srv, tipos, buscar)
            hechos = {r[0] for r in db().execute("select item from aplicado where servidor=?", (srv,))}
            if forzar and not limite and not buscar:   # «redibujar aplicados»: solo los que ya tienen notas
                items = [i for i in items if i["Id"] in hechos]
            elif limite:
                items = (items if forzar else [i for i in items if i["Id"] not in hechos])[:limite]
            ESTADO["total"] += len(items)
            for it in items:
                ESTADO["ultimo"] = f"{srv}: {it['Name']}"
                jf = next((jf_idx[(k, get_id(it, k))] for k in ("Imdb", "Tmdb", "Tvdb") if get_id(it, k) and (k, get_id(it, k)) in jf_idx), None)
                try:
                    res = procesar(srv, it, jf, forzar)
                    if res != "igual":
                        log(f"{srv} · {it['Name']}: {res}")
                except Exception as e:
                    ESTADO["errores"] += 1
                    log(f"{srv} · {it['Name']}: ERROR {str(e)[:140]}")
                ESTADO["hecho"] += 1
                time.sleep(cf["auto"]["pausa_s"])
        log("pasada terminada")
        return "ok"
    finally:
        ESTADO["activo"] = False
        _lock.release()
