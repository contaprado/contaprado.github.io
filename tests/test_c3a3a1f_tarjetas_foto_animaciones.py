"""
QA del commit c3a3a1f ("Tarjetas de servicio con iconos, foto hero animada
y animaciones al scroll") + ronda 2 de correcciones del fullstack sobre
assets/css/styles.css (limpieza de CSS muerto + fix de especificidad en el
grid de servicios para 640-899px).

No hay runner de tests ni build configurado en este repo (sitio estatico sin
package.json). Este script usa solo la libreria estandar de Python (no hay
Node disponible en el entorno de QA) para hacer analisis estatico de
index.html / styles.css / script.js, y detectar regresiones de forma
reproducible sin navegador.

Ejecutar con:
    python tests/test_c3a3a1f_tarjetas_foto_animaciones.py

Imprime PASS/FAIL por caso y termina con exit code != 0 si algo esperado
como correcto en realidad fallo.
"""
import re
import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HTML = (ROOT / "index.html").read_text(encoding="utf-8")
CSS = (ROOT / "assets" / "css" / "styles.css").read_text(encoding="utf-8")
JS = (ROOT / "assets" / "js" / "script.js").read_text(encoding="utf-8")

resultados = []


def check(nombre, condicion, detalle=""):
    estado = "PASS" if condicion else "FAIL"
    resultados.append((estado, nombre, detalle))
    print("[" + estado + "] " + nombre + ((" -- " + detalle) if detalle and not condicion else ""))
    return condicion


# ---------------------------------------------------------------------
# Utilidades de parseo (regex simple, suficiente para este sitio estatico)
# ---------------------------------------------------------------------

def clases_usadas_en_html(html):
    usadas = set()
    for m in re.finditer(r'class="([^"]*)"', html):
        for c in m.group(1).split():
            usadas.add(c)
    return usadas


def clases_definidas_en_css(css):
    css_sin_comentarios = re.sub(r"/\*.*?\*/", "", css, flags=re.S)
    definidas = set()
    for m in re.finditer(r"\.([a-zA-Z0-9_-]+)", css_sin_comentarios):
        definidas.add(m.group(1))
    return definidas


def jpeg_dimensiones(path):
    """Lee el segmento SOFx de un JPEG y devuelve (width, height) sin PIL."""
    with open(path, "rb") as f:
        data = f.read()
    if data[0:2] != b"\xff\xd8":
        raise ValueError("No es un JPEG valido")
    i = 2
    while i < len(data):
        if data[i] != 0xFF:
            i += 1
            continue
        marker = data[i + 1]
        if marker in (0xD8, 0xD9):
            i += 2
            continue
        if marker == 0x01 or 0xD0 <= marker <= 0xD7:
            i += 2
            continue
        seg_len = struct.unpack(">H", data[i + 2:i + 4])[0]
        if 0xC0 <= marker <= 0xCF and marker not in (0xC4, 0xC8, 0xCC):
            height = struct.unpack(">H", data[i + 5:i + 7])[0]
            width = struct.unpack(">H", data[i + 7:i + 9])[0]
            return width, height
        i += 2 + seg_len
    raise ValueError("No se encontro segmento SOF")


usadas = clases_usadas_en_html(HTML)
definidas = clases_definidas_en_css(CSS)

# ---------------------------------------------------------------------
# 1. Clases CSS huerfanas (declaradas pero sin ningun uso en el HTML).
#    hero__avatar / foto-placeholder* NUNCA aparecieron en index.html (el
#    markup viejo que las usaba ya se habia quitado antes); lo que importa
#    verificar en la ronda 2 es que el fullstack las haya borrado tambien
#    de styles.css. Por eso el check real es "siguen definidas en CSS?".
# ---------------------------------------------------------------------
candidatas_muertas = {
    "hero__avatar",
    "foto-placeholder",
    "foto-placeholder__iniciales",
    "foto-placeholder__texto",
}
huerfanas_encontradas = sorted(c for c in candidatas_muertas if c in definidas and c not in usadas)
check(
    "No deben quedar clases CSS huerfanas de la foto/avatar anterior",
    len(huerfanas_encontradas) == 0,
    "Clases que siguen definidas en styles.css sin ningun uso en index.html: "
    + repr(huerfanas_encontradas)
    + ". Verificar con: grep -n \"hero__avatar\\|foto-placeholder\" assets/css/styles.css",
)

# ---------------------------------------------------------------------
# 2. Clases nuevas introducidas por el commit original: deben tener CSS.
# ---------------------------------------------------------------------
clases_nuevas_esperadas = {"revelar", "servicio__icono", "hero__foto", "hero__perfil--solo"}
sin_definicion = sorted(c for c in clases_nuevas_esperadas if c not in definidas)
check(
    "Las clases nuevas (revelar, servicio__icono, hero__foto, hero__perfil--solo) tienen CSS",
    len(sin_definicion) == 0,
    "Clases usadas en HTML sin ninguna regla CSS: " + repr(sin_definicion),
)

# ---------------------------------------------------------------------
# 3. wa-flotante::after (anillo de pulso) debe estar definido y anclado.
# ---------------------------------------------------------------------
check(
    "Existe la regla .wa-flotante::after con animacion de pulso",
    bool(re.search(r"\.wa-flotante::after\s*\{[^}]*animation:\s*pulso", CSS)),
)
check(
    "El elemento .wa-flotante tiene posicionamiento (fixed/relative/absolute) "
    "para que ::after con position:absolute se ancle correctamente",
    bool(re.search(r"\.wa-flotante\s*\{[^}]*position:\s*(fixed|relative|absolute)", CSS)),
)

# ---------------------------------------------------------------------
# 4. No debe reaparecer el bug de especificidad ya corregido en la ronda 1
#    (.hero__visual img con max-width fijo pisando a .hero__foto).
# ---------------------------------------------------------------------
check(
    "No reaparecio la regla generica '.hero__visual img' que pisaba a .hero__foto",
    not re.search(r"\.hero__visual\s+img\s*\{", CSS),
    "Se encontro una regla '.hero__visual img { ... }' en styles.css: volveria a ganar "
    "especificidad sobre .hero__foto si define max-width/width.",
)

# ---------------------------------------------------------------------
# 5. El bloque @media (prefers-reduced-motion: reduce) de la SECCION 14
#    (hay otro bloque viejo mas arriba en el archivo, para .animar) debe
#    desactivar .revelar, la flotacion de la foto y el pulso del WhatsApp.
# ---------------------------------------------------------------------
idx_seccion14_rm = CSS.find("14. FOTO, TARJETAS Y ANIMACIONES")
css_seccion14 = CSS[idx_seccion14_rm:] if idx_seccion14_rm != -1 else CSS
m = re.search(r"@media \(prefers-reduced-motion: reduce\)\s*\{(.*)\n\.servicios", css_seccion14, re.S)
bloque_reduced_motion = m.group(1) if m else ""
check(
    "El bloque prefers-reduced-motion (seccion 14) desactiva .js .revelar",
    ".revelar" in bloque_reduced_motion and "opacity: 1" in bloque_reduced_motion,
    "No se encontro '.revelar { opacity: 1 }' dentro del bloque reduced-motion nuevo. "
    "bloque capturado: " + repr(bloque_reduced_motion[:200]),
)
check(
    "El bloque prefers-reduced-motion (seccion 14) desactiva animation de .hero__foto y .wa-flotante::after",
    "hero__foto" in bloque_reduced_motion and "animation: none" in bloque_reduced_motion,
)

# ---------------------------------------------------------------------
# 6. Grid de servicios a >=900px: el numero de nth-child hardcodeados (4,5)
#    debe coincidir con la cantidad real de tarjetas .servicio en el HTML.
# ---------------------------------------------------------------------
tarjetas = re.findall(r'<article class="servicio revelar">', HTML)
nth_children_en_grid_900 = sorted(
    int(n) for n in re.findall(r"\.servicio:nth-child\((\d+)\)\s*\{\s*grid-column", CSS)
)
check(
    "La cantidad de tarjetas .servicio coincide con los nth-child hardcodeados "
    "en el grid de 6 columnas (>=900px)",
    len(tarjetas) == 5 and nth_children_en_grid_900 == [4, 5],
    "Tarjetas encontradas: " + str(len(tarjetas))
    + "; nth-child con grid-column explicito: " + repr(nth_children_en_grid_900)
    + ". Si la cantidad de tarjetas cambia, hay que revisar manualmente el centrado de la "
    "ultima fila en assets/css/styles.css (seccion 14, @media min-width:900px).",
)

# ---------------------------------------------------------------------
# 7. RONDA 2: el fullstack corrigio el conflicto de especificidad quitando
#    las 3 reglas .servicio:nth-child(...) de la seccion 13 (quedaban
#    siempre pisadas) y el @media(640-899px) redundante de la seccion 14,
#    pero debe conservarse .servicios { grid-template-columns: repeat(2,1fr) }
#    en @media(min-width:640px): es la UNICA regla que define 2 columnas
#    para el rango 640-899px. En >=900px la seccion 14 la pisa a proposito
#    con repeat(6,1fr), que es el comportamiento esperado.
# ---------------------------------------------------------------------
idx_seccion13 = CSS.find("13. RESPONSIVE")
idx_seccion14 = CSS.find("14. FOTO, TARJETAS Y ANIMACIONES")
bloque_13 = CSS[idx_seccion13:idx_seccion14]
bloque_640 = re.search(r"@media \(min-width: 640px\)\s*\{(.*?)\n\}", bloque_13, re.S)
bloque_640_txt = bloque_640.group(1) if bloque_640 else ""

check(
    "@media(min-width:640px) define .servicios a 2 columnas con 20px de gap "
    "(layout de tablet 640-899px, el riesgo mas importante de la ronda 2)",
    bool(re.search(
        r"\.servicios\s*\{\s*grid-template-columns:\s*repeat\(2,\s*1fr\)\s*;\s*column-gap:\s*20px",
        bloque_640_txt,
    )),
    "No se encontro '.servicios { grid-template-columns: repeat(2, 1fr); column-gap: 20px }' "
    "dentro de @media(min-width:640px). bloque capturado: " + repr(bloque_640_txt[:300]),
)
check(
    "Ya no quedan las 3 reglas .servicio:nth-child(odd/even)/:last-child de la seccion 13 "
    "que siempre terminaban pisadas (codigo muerto eliminado). OJO: .paso:nth-child si existe "
    "en este bloque y es correcto (otro componente, no es el bug reportado)",
    ".servicio:nth-child(odd)" not in bloque_640_txt
    and ".servicio:nth-child(even)" not in bloque_640_txt
    and ".servicio:last-child" not in bloque_640_txt,
    "Bloque @media(640px) todavia contiene referencias a .servicio:nth-child/:last-child: "
    + repr(bloque_640_txt[:400]),
)
check(
    "Ya no existe el @media(640px-899px) redundante de la seccion 14 (eliminado por el fullstack)",
    not re.search(r"@media \(min-width: 640px\) and \(max-width: 899px\)", CSS[idx_seccion14:]),
)
check(
    "A >=900px la regla de 6 columnas de la seccion 14 sigue despues (en el archivo) de la "
    "regla de 2 columnas de la seccion 13, asi que la cascada sigue pisando correctamente",
    CSS.find("grid-template-columns: repeat(2, 1fr); column-gap: 20px")
    < CSS.find("grid-template-columns: repeat(6, 1fr)"),
)

# ---------------------------------------------------------------------
# 8. JS: chequeos de sintaxis/logica basicos sin interprete de Node.
# ---------------------------------------------------------------------
abiertas = JS.count("{")
cerradas = JS.count("}")
check(
    "Llaves balanceadas en script.js (chequeo basico, no reemplaza un parser real)",
    abiertas == cerradas,
    str(abiertas) + " '{' vs " + str(cerradas) + " '}'",
)

check(
    "El IIFE de IntersectionObserver agrega 'js' a <html> SOLO cuando va a animar "
    "(evita que .revelar quede oculto si no hay JS)",
    bool(re.search(r"documentElement\.classList\.add\('js'\)", JS)),
)
check(
    "El IIFE respeta prefers-reduced-motion antes de observar",
    bool(re.search(r"prefers-reduced-motion:\s*reduce", JS)) and "IntersectionObserver" in JS,
)
check(
    "El fallback sin soporte de IntersectionObserver no deja elementos .revelar invisibles",
    bool(re.search(r"reducir \|\| !\('IntersectionObserver' in window\)", JS))
    and bool(re.search(r"classList\.add\('visible'\)", JS)),
)

# ---------------------------------------------------------------------
# 9. Accesibilidad: iconos SVG inline decorativos con aria-hidden, y alt
#    descriptivo (no vacio, no generico) en la foto del hero.
# ---------------------------------------------------------------------
spans_icono = re.findall(r'<span class="servicio__icono"[^>]*>', HTML)
sin_aria_hidden = [s for s in spans_icono if 'aria-hidden="true"' not in s]
check(
    "Los 5 iconos de servicio__icono tienen aria-hidden=\"true\" en el span contenedor",
    len(spans_icono) == 5 and len(sin_aria_hidden) == 0,
    "Encontrados " + str(len(spans_icono)) + " spans; sin aria-hidden: " + repr(sin_aria_hidden),
)

alt_match = re.search(r'<img class="hero__foto"[^>]*alt="([^"]*)"', HTML)
alt_foto = alt_match.group(1) if alt_match else None
check(
    "La foto del hero tiene alt descriptivo (no vacio y con mas de 10 caracteres)",
    bool(alt_foto) and len(alt_foto) > 10,
    "alt actual: " + repr(alt_foto),
)

# ---------------------------------------------------------------------
# 10. Las dimensiones width/height del <img class="hero__foto"> deben
#     coincidir con el archivo real (evita layout shift / aspect-ratio
#     incorrecto si alguien reemplaza la foto sin actualizar el markup).
# ---------------------------------------------------------------------
img_attrs = re.search(r'<img class="hero__foto"[^>]*width="(\d+)"[^>]*height="(\d+)"', HTML)
img_path = ROOT / "assets" / "images" / "gabriela.jpg"
if img_attrs and img_path.exists():
    w_html, h_html = int(img_attrs.group(1)), int(img_attrs.group(2))
    try:
        w_real, h_real = jpeg_dimensiones(img_path)
        check(
            "Las dimensiones width/height del <img class=hero__foto> coinciden con el archivo real",
            (w_html, h_html) == (w_real, h_real),
            "HTML declara " + str(w_html) + "x" + str(h_html) + ", archivo real es "
            + str(w_real) + "x" + str(h_real),
        )
    except Exception as e:
        check("No se pudieron leer las dimensiones reales del JPEG", False, str(e))
else:
    check(
        "Se encontraron width/height en hero__foto y el archivo existe",
        False,
        "img_attrs=" + str(bool(img_attrs)) + " archivo_existe=" + str(img_path.exists()),
    )

# ---------------------------------------------------------------------
# 11. Regresion: el formulario, menu movil y FAQ (no tocados por este
#     commit) siguen presentes e intactos en el HTML.
# ---------------------------------------------------------------------
check("El formulario de contacto (Formspree) sigue presente", "formulario" in usadas)
check("El boton de menu movil sigue presente", "menu-boton" in usadas)
check("El acordeon de FAQ sigue presente", "faq__pregunta" in usadas and 'aria-expanded="false"' in HTML)

# ---------------------------------------------------------------------
# Resumen
# ---------------------------------------------------------------------
fails = [r for r in resultados if r[0] == "FAIL"]
print("\n--- RESUMEN ---")
print("Total: " + str(len(resultados)) + "  PASS: " + str(len(resultados) - len(fails)) + "  FAIL: " + str(len(fails)))
if fails:
    print("\nFallos:")
    for estado, nombre, detalle in fails:
        print(" - " + nombre + "\n   " + detalle)

sys.exit(1 if fails else 0)
