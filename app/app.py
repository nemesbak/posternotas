#!/usr/bin/env python3
# Póster Notas — panel de ajustes (Flask) + pasada programada.
import io, json, threading, time
from flask import Flask, jsonify, request, Response
from PIL import Image
import motor, render

app = Flask(__name__)
_cache = {}  # (srv, id) -> (item, jf, ts) para que la vista previa sea rápida


def _item(srv, iid):
    k = (srv, iid)
    if k in _cache and time.time() - _cache[k][2] < 600:
        return _cache[k][0], _cache[k][1]
    it = motor.item(srv, iid)
    jf = motor.par_jellyfin(it) if srv == "emby" else it
    _cache[k] = (it, jf, time.time())
    return it, jf


def _conf_peticion():
    c = motor.conf()
    if request.args.get("conf"):
        motor._mezcla(c, json.loads(request.args["conf"]))
    return c


@app.get("/")
def index():
    return Response(open("/app/panel.html", encoding="utf-8").read(), mimetype="text/html")


@app.get("/api/meta")
def meta():
    return jsonify(fuentes=render.NOMBRES, temas=render.TEMAS, presets=render.PRESETS, mdblist=bool(motor.clave("MDBLIST_KEY")),
                   requieren_mdblist=["mc", "mc_pub", "rt_pub", "lb", "trakt", "ebert", "mal", "mdblist"])


@app.get("/api/config")
def get_conf():
    return jsonify(motor.conf())


@app.post("/api/config")
def set_conf():
    motor.guardar_conf(request.get_json() or {})
    return jsonify(ok=True)


@app.post("/api/config/reset")
def reset_conf():
    motor.guardar_conf(json.loads(json.dumps(motor.DEFAULT)))
    return jsonify(ok=True)


@app.get("/api/buscar")
def buscar():
    srv = request.args.get("srv", "emby")
    q = request.args.get("q", "")
    its = motor.listar(srv, ["Movie", "Series"], q or None, 18)
    return jsonify([{"id": i["Id"], "nombre": i["Name"], "anio": i.get("ProductionYear"), "tipo": i["Type"]} for i in its])


@app.get("/api/preview")
def preview():
    srv, iid = request.args.get("srv", "emby"), request.args.get("id")
    cf = _conf_peticion()
    it, jf = _item(srv, iid)
    jpg, n, q = motor.generar(srv, it, jf, cf)
    if isinstance(jpg, str):
        return Response(jpg, status=404)
    if request.args.get("w"):
        im = Image.open(io.BytesIO(jpg)); w = int(request.args["w"])
        im = im.resize((w, int(im.height * w / im.width)), Image.LANCZOS); b = io.BytesIO(); im.save(b, "JPEG", quality=85); jpg = b.getvalue()
    return Response(jpg, mimetype="image/jpeg", headers={"Cache-Control": "no-store"})


@app.get("/api/original")
def original():
    """Póster sin notas: el original guardado si ya se aplicó, o el actual del servidor."""
    import os
    srv, iid = request.args.get("srv", "emby"), request.args.get("id")
    p = os.path.join(motor.ORIG, srv, iid + ".jpg")
    raw = open(p, "rb").read() if os.path.exists(p) else motor.api(srv, f"/Items/{iid}/Images/Primary?quality=90", crudo=True)
    im = Image.open(io.BytesIO(raw)); w = int(request.args.get("w", 600))
    im = im.convert("RGB").resize((w, int(im.height * w / im.width)), Image.LANCZOS); b = io.BytesIO(); im.save(b, "JPEG", quality=85)
    return Response(b.getvalue(), mimetype="image/jpeg", headers={"Cache-Control": "no-store"})


@app.get("/api/detalle")
def detalle():
    srv, iid = request.args.get("srv", "emby"), request.args.get("id")
    it, jf = _item(srv, iid)
    n = motor.notas(it, jf)
    q = motor.calidad(it) if it["Type"] == "Movie" else motor.calidad_serie(srv, it["Id"])
    aplicado = motor.db().execute("select ts from aplicado where servidor=? and item=?", (srv, iid)).fetchone()
    return jsonify(notas=n, calidad=q, aplicado=bool(aplicado), nombre=it["Name"], anio=it.get("ProductionYear"))


@app.post("/api/aplicar")
def aplicar():
    b = request.get_json() or {}
    threading.Thread(target=motor.pasada, kwargs=dict(limite=b.get("limite"), buscar=b.get("buscar") or None, forzar=bool(b.get("forzar"))), daemon=True).start()
    return jsonify(ok=True)


@app.post("/api/aplicar_uno")
def aplicar_uno():
    b = request.get_json() or {}
    it, jf = _item(b["srv"], b["id"])
    _cache.pop((b["srv"], b["id"]), None)
    return jsonify(res=motor.procesar(b["srv"], it, jf, forzar=True))


@app.post("/api/revertir")
def revertir():
    b = request.get_json() or {}
    if b.get("todo"):
        threading.Thread(target=motor.pasada, kwargs=dict(revertir_todo=True), daemon=True).start()
        return jsonify(ok=True)
    _cache.pop((b["srv"], b["id"]), None)
    return jsonify(res=motor.revertir(b["srv"], b["id"]))


@app.get("/api/estado")
def estado():
    c = motor.db()
    porsrv = {s: n for s, n in c.execute("select servidor, count(*) from aplicado where item not like '%#fondo' group by servidor")}
    imdb = c.execute("select count(*) from imdb").fetchone()[0]
    recientes = [dict(zip(("srv", "id", "titulo", "ts"), r)) for r in c.execute("select servidor, item, titulo, ts from aplicado where item not like '%#fondo' order by ts desc limit 24")]
    return jsonify(dict(motor.ESTADO, aplicados=porsrv, imdb=imdb, recientes=recientes))


def programador():
    ultimo = None
    while True:
        time.sleep(30)
        a = motor.conf()["auto"]
        hoy = time.strftime("%Y-%m-%d")
        if a["programado"] and time.strftime("%H:%M") == a["hora"] and ultimo != hoy:
            ultimo = hoy
            motor.log("pasada programada")
            motor.pasada()


if __name__ == "__main__":
    threading.Thread(target=programador, daemon=True).start()
    app.run(host="0.0.0.0", port=8790, threaded=True)
