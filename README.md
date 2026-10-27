# Póster Notas 🎬

> Copia propia y autónoma de **RatingPosterDB** (RPDB) para **Emby** y **Jellyfin**. Graba calificaciones (IMDb, Rotten Tomatoes, TMDB, Metacritic, Trakt...) e insignias técnicas de calidad (resolución 4K, HDR10+, Dolby Vision, Atmos, pistas de audio, banderas de idioma, galardones de cine...) incrustadas directamente en el póster de cada película o serie.

---

## 🌟 Características

- **Calificaciones fiables**:
  - **IMDb**: Descarga automática diaria del conjunto oficial de datos de IMDb (~1,7 millones de títulos).
  - **TMDB**: Calificación comunitaria directa de la biblioteca (`CommunityRating`).
  - **Rotten Tomatoes**: Puntuación de la crítica (`CriticRating`).
  - **Metacritic, Letterboxd, Trakt, Roger Ebert, MAL, MDBList**: Soporte opcional mediante clave `MDBLIST_KEY`.
  - **Media ponderada**: Cálculo unificado sobre 100 de todas las fuentes disponibles.
- **Insignias técnicas de calidad (MediaStreams)**:
  - Extraídas directamente de los metadatos reales del archivo (no inferidas ni adivinadas):
    - **Resolución**: 4K UHD, 1080p, 720p, SD.
    - **Rango dinámico**: Dolby Vision, HDR10+, HDR, HLG, DV · HDR.
    - **Audio**: Dolby Atmos, DTS:X, TrueHD 7.1, DTS-HD, DD+ 5.1, DD 5.1, Lossless.
    - **Idioma y pistas**: Detección inteligente de pistas de doblaje en español (🇪🇸), copias en versión original subtitulada (`VOSE`) y audio dual (`DUAL`).
    - **Origen / Rip**: Remux, BluRay, WEB-DL, HDTV.
    - **Códec de vídeo**: AV1, H.265 (HEVC), H.264.
    - **Edición**: Montaje del director, Versión extendida, Sin censura, Remaster, Criterion.
    - **Clasificación por edad**: Clasificación por edades (TP, +7, +12, +16, +18, PG-13, R...).
    - **Premios y Galardones**: Integración con Wikidata mediante SPARQL para reconocer premios Óscar, Globos de Oro, Premios Goya, Palma de Oro de Cannes, Premios BAFTA y Premios Emmy.
- **Estilos visuales (RatingPosterDB)**:
  - 9 temas gráficos: *Pastillas (Nebula)*, *Pastillas en barra*, *Barra continua*, *Bloques*, *Bloques redondos*, *Cajas (dos pisos)*, *Bloques rectos*, *Franjas con acento de color (izq/dcha)*.
  - Modo claro (*Light*): Fondo blanco translúcido con tipografía oscura.
  - Estilo **Deportivo Inclinado**: Geometría en paralelogramo nítido de alta definición (~20° de inclinación real).
  - Paletas de insignias: *Nebula*, *Oro*, *Plata*, *Color dinámico*, *Grafito*.
  - Sombra y relieve 3D para máxima legibilidad sobre cualquier carátula (clara u oscura).
- **Panel Web de Control (`:8790`)**:
  - Previsualización en vivo en pantalla partida con deslizador interactivo *Antes / Después*.
  - Galería visual de 14 estilos prediseñados (Presets) con carga en un clic.
  - Mapas interactivos para elegir la posición de las notas y las insignias (8 zonas).
  - Listas reordenables mediante arrastrar y soltar o botones táctiles.
  - Búsqueda en tiempo real sobre las bibliotecas de Emby y Jellyfin.
  - Inspección instantánea de metadatos leídos.
- **Seguridad y Reversibilidad Total**:
  - Cada póster original se guarda en `/data/originales/<servidor>/<id>.jpg` antes de ser modificado.
  - Botón de reversión individual por título y botón de restauración total de la biblioteca en cualquier momento.
  - Procesamiento seguro por tandas (prueba de 10 títulos, tandas de 50, o biblioteca completa).
  - Detección de cambios manuales: si el usuario cambia una carátula a mano en Emby o Jellyfin, se adopta como nuevo original.

---

## 📁 Estructura del Proyecto

```text
/mnt/user/appdata/posternotas/
├── app/
│   ├── app.py          # Servidor Flask y API REST (:8790)
│   ├── motor.py        # Lógica de notas, insignias, Wikidata, Emby/Jellyfin y lotes
│   ├── render.py       # Motor gráfico de renderizado vectorial sobre Pillow
│   ├── panel.html      # Interfaz de usuario interactiva
│   └── Dockerfile      # Definición de contenedor basada en python:3.12-slim
├── data/               # Montado en /data
│   ├── config.json     # Configuración activa del usuario
│   ├── posternotas.sqlite  # Caché de IMDb (1,7M), premios y firmas
│   └── originales/     # Copias de seguridad de las carátulas originales
└── README.md
```

---

## 🚀 Despliegue y Reconstrucción

El contenedor se ejecuta en Unraid en el servidor **Odin** (`192.168.1.25`):

```bash
cd /mnt/user/appdata/posternotas/app && \
docker build -t posternotas:latest . && \
docker rm -f posternotas && \
docker run -d --name posternotas --restart unless-stopped -p 8790:8790 \
  -v /mnt/user/appdata/posternotas/data:/data \
  -v /usr/share/fonts/TTF:/fonts:ro \
  -v /boot/config/odin.env:/odin.env:ro posternotas:latest
```

> [!NOTE]
> Para modificaciones de interfaz en `panel.html` no es necesario reconstruir la imagen: basta con ejecutar:
> ```bash
> docker cp panel.html posternotas:/app/panel.html
> ```

---

## 🔌 API REST

| Método | Endpoint | Descripción |
|---|---|---|
| `GET` | `/` | Panel web de administración |
| `GET` | `/api/meta` | Catálogo de fuentes, temas, presets y estado de MDBList |
| `GET` | `/api/config` | Configuración activa en JSON |
| `POST` | `/api/config` | Guarda nuevos ajustes |
| `POST` | `/api/config/reset` | Restablece los ajustes a los valores iniciales de fábrica |
| `GET` | `/api/buscar?srv=emby&q=Dune` | Busca títulos en Emby o Jellyfin |
| `GET` | `/api/preview?srv=emby&id=123&w=860&conf={...}` | Genera vista previa dinámica en tiempo real |
| `GET` | `/api/original?srv=emby&id=123` | Devuelve el póster original sin notas |
| `GET` | `/api/detalle?srv=emby&id=123` | Devuelve las notas e insignias detectadas para el título |
| `POST` | `/api/aplicar` | Lanza pasada en segundo plano (`limite`, `buscar`, `forzar`) |
| `POST` | `/api/aplicar_uno` | Aplica notas a un único título seleccionado |
| `POST` | `/api/revertir` | Restaura el póster original (`srv`, `id`) o de toda la biblioteca (`todo: true`) |
| `GET` | `/api/estado` | Estado del trabajador en lote, títulos aplicados y registro en vivo |

---

## 🔒 Reglas del Servidor Odin

1. **Solo APIs**: Las bases de datos internas de Emby y Jellyfin nunca se modifican directamente por SQLite/disco, siempre a través de sus endpoints oficiales de API.
2. **Plantilla Unraid**: La plantilla del contenedor se ubica en `/boot/config/plugins/dockerMan/templates-user/my-posternotas.xml`.
3. **Claves Seguras**: Las claves (`EMBY_KEY`, `JELLYFIN_KEY`, `TMDB_KEY`, `MDBLIST_KEY`) residen en `/boot/config/odin.env` (montado en modo solo lectura en `/odin.env`).
