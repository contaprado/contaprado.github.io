"""
QA de la ronda "foto de Gabriela duplicada" (working tree, sin commitear).

Cambio revisado: se quito la foto de la seccion #sobre-mi (quedaba
duplicada con la del Hero). index.html pierde el <div class="sobre-mi__foto">
y su <img class="sobre-mi__imagen">; styles.css pierde las reglas base
.sobre-mi__foto/.sobre-mi__imagen y las porciones de .sobre-mi dentro de los
bloques @media(min-width:640px) y @media(min-width:900px), dejando el resto
de esos bloques (.credenciales, .proceso, .paso:nth-child, .hero__interior,
.problemas__interior, .contacto, .formulario, .nav, .menu-boton, etc.)
intacto.

No hay runner de tests ni Node disponible en este entorno; se usa solo la
libreria estandar de Python para analisis estatico de index.html / styles.css.

Ejecutar con:
    python tests/test_sobre_mi_foto_eliminada.py
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HTML = (ROOT / "index.html").read_text(encoding="utf-8")
CSS = (ROOT / "assets" / "css" / "styles.css").read_text(encoding="utf-8")

resultados = []


def check(nombre, condicion, detalle=""):
    estado = "PASS" if condicion else "FAIL"
    resultados.append((estado, nombre, detalle))
    print("[" + estado + "] " + nombre + ((" -- " + detalle) if detalle and not condicion else ""))
    return condicion


# ---------------------------------------------------------------------
# 1. gabriela.jpg debe aparecer exactamente 1 vez en index.html (solo Hero).
# ---------------------------------------------------------------------
apariciones_foto = len(re.findall(r"gabriela\.jpg", HTML))
check(
    "gabriela.jpg aparece exactamente 1 vez en index.html (solo en el Hero)",
    apariciones_foto == 1,
    "Apariciones encontradas: " + str(apariciones_foto),
)
check(
    "La unica aparicion de gabriela.jpg esta en el <img class=hero__foto>, no en sobre-mi",
    bool(re.search(r'<img class="hero__foto"[^>]*gabriela\.jpg', HTML)),
)

# ---------------------------------------------------------------------
# 2. .sobre-mi__foto y .sobre-mi__imagen no deben existir ni en CSS ni en HTML.
# ---------------------------------------------------------------------
check(
    "No quedan referencias a sobre-mi__foto en index.html",
    "sobre-mi__foto" not in HTML,
)
check(
    "No quedan referencias a sobre-mi__imagen en index.html",
    "sobre-mi__imagen" not in HTML,
)
check(
    "No quedan reglas .sobre-mi__foto en styles.css (ni sueltas ni dentro de @media)",
    not re.search(r"\.sobre-mi__foto\b", CSS),
    "Se encontro '.sobre-mi__foto' en styles.css: " + repr(
        [m.group(0) for m in re.finditer(r".{0,40}\.sobre-mi__foto.{0,40}", CSS)]
    ),
)
check(
    "No quedan reglas .sobre-mi__imagen en styles.css",
    not re.search(r"\.sobre-mi__imagen\b", CSS),
)

# ---------------------------------------------------------------------
# 3. .sobre-mi no debe tener grid-template-columns en ningun lado (base,
#    640px, 900px) -- si quedara alguno, el contenido unico quedaria
#    apretado en una fraccion angosta con espacio en blanco al lado.
# ---------------------------------------------------------------------
reglas_sobre_mi = re.findall(r"\.sobre-mi\s*\{([^}]*)\}", CSS)
con_grid_columns = [r for r in reglas_sobre_mi if "grid-template-columns" in r]
check(
    "Ninguna regla '.sobre-mi { ... }' define grid-template-columns "
    "(el unico hijo debe ocupar todo el ancho, no una fraccion angosta)",
    len(con_grid_columns) == 0,
    "Reglas .sobre-mi con grid-template-columns: " + repr(con_grid_columns),
)
check(
    "La regla base .sobre-mi sigue existiendo con display:grid (contenedor de 1 columna implicita)",
    bool(re.search(r"\.sobre-mi\s*\{\s*display:\s*grid", CSS)),
)

# ---------------------------------------------------------------------
# 4. .sobre-mi__contenido no debe tener max-width/width que limite el
#    ancho total de la seccion a una fraccion angosta del contenedor.
#    (sobre-mi__texto / sobre-mi__destacado SI tienen max-width en ch,
#    pero eso es para legibilidad de parrafo, no para el bloque completo
#    -- no se toca ni se evalua aqui).
# ---------------------------------------------------------------------
regla_contenido = re.search(r"\.sobre-mi__contenido\s*\{([^}]*)\}", CSS)
check(
    "Si existe una regla .sobre-mi__contenido, no limita el ancho con max-width/width fijo",
    regla_contenido is None or (
        "max-width" not in regla_contenido.group(1) and "width:" not in regla_contenido.group(1)
    ),
    "Regla encontrada: " + repr(regla_contenido.group(1) if regla_contenido else None),
)

# ---------------------------------------------------------------------
# 5. Las reglas combinadas de @media(640px) y @media(900px) deben seguir
#    bien formadas (llaves balanceadas) y conservar los selectores que NO
#    debian tocarse.
# ---------------------------------------------------------------------
bloque_640 = re.search(r"@media \(min-width: 640px\)\s*\{(.*?)\n\}", CSS, re.S)
bloque_640_txt = bloque_640.group(1) if bloque_640 else ""
check(
    "El bloque @media(min-width:640px) tiene llaves balanceadas",
    bloque_640_txt.count("{") == bloque_640_txt.count("}"),
    "'{': " + str(bloque_640_txt.count("{")) + " vs '}': " + str(bloque_640_txt.count("}")),
)
check(
    "El bloque @media(min-width:640px) ya NO menciona .sobre-mi (se elimino su fraccion de columnas)",
    ".sobre-mi" not in bloque_640_txt,
)
selectores_640_que_deben_seguir = [
    ".credenciales", ".proceso", ".paso:nth-child(odd)", ".paso:nth-child(even)",
    ".formulario", ".campo--completo", ".pie__interior", ".problemas__interior", ".servicios",
]
faltantes_640 = [s for s in selectores_640_que_deben_seguir if s not in bloque_640_txt]
check(
    "El bloque @media(min-width:640px) conserva intactos los selectores que no debian tocarse",
    len(faltantes_640) == 0,
    "Selectores esperados que ya no aparecen: " + repr(faltantes_640),
)

bloque_900 = re.search(r"@media \(min-width: 900px\)\s*\{(.*?)\n\}", CSS, re.S)
bloque_900_txt = bloque_900.group(1) if bloque_900 else ""
check(
    "El bloque @media(min-width:900px) tiene llaves balanceadas",
    bloque_900_txt.count("{") == bloque_900_txt.count("}"),
    "'{': " + str(bloque_900_txt.count("{")) + " vs '}': " + str(bloque_900_txt.count("}")),
)
check(
    "El bloque @media(min-width:900px) ya NO menciona .sobre-mi "
    "(se elimino la fraccion de columnas y el position:sticky de la foto)",
    ".sobre-mi" not in bloque_900_txt,
)
selectores_900_que_deben_seguir = [
    ".menu-boton", ".fondo-menu", ".nav", ".nav__lista", ".nav__enlace", ".nav__whatsapp",
    ".hero__interior", ".problemas__interior", ".contacto",
]
faltantes_900 = [s for s in selectores_900_que_deben_seguir if s not in bloque_900_txt]
check(
    "El bloque @media(min-width:900px) conserva intactos los selectores que no debian tocarse",
    len(faltantes_900) == 0,
    "Selectores esperados que ya no aparecen: " + repr(faltantes_900),
)

# ---------------------------------------------------------------------
# 6. Estructura HTML: .sobre-mi__contenido debe ser el UNICO hijo directo
#    de <div class="contenedor sobre-mi">.
# ---------------------------------------------------------------------
m_seccion = re.search(
    r'<div class="contenedor sobre-mi">(.*?)</div>\s*</div>\s*</section>',
    HTML, re.S,
)
# Fallback mas simple: contar cuantos divs de primer nivel hay comparando
# contra la cantidad de "sobre-mi__" wrappers de bloque conocidos.
seccion_sobre_mi = re.search(
    r'<section class="seccion sobre-mi-seccion" id="sobre-mi">(.*?)</section>',
    HTML, re.S,
)
texto_seccion = seccion_sobre_mi.group(1) if seccion_sobre_mi else ""
check(
    "La seccion #sobre-mi ya no contiene ningun <div class=\"sobre-mi__foto\">",
    seccion_sobre_mi is not None and "sobre-mi__foto" not in texto_seccion,
)
check(
    "La seccion #sobre-mi contiene exactamente un <div class=\"sobre-mi__contenido\">",
    seccion_sobre_mi is not None and texto_seccion.count('class="sobre-mi__contenido"') == 1,
    "Ocurrencias de sobre-mi__contenido: " + str(texto_seccion.count('class="sobre-mi__contenido"')),
)

# ---------------------------------------------------------------------
# 7. Regresion rapida: el Hero sigue teniendo su propia foto con atributos
#    completos (no se toco por error al editar sobre-mi).
# ---------------------------------------------------------------------
check(
    "El <img class=hero__foto> en el Hero conserva alt, width, height y loading=eager",
    bool(re.search(
        r'<img class="hero__foto"[^>]*alt="[^"]{10,}"[^>]*width="640"[^>]*height="800"[^>]*loading="eager"',
        HTML,
    )),
)

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
