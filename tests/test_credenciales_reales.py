"""
QA de la ronda "credenciales reales" (12 anos de experiencia / CPA 8812 /
CPI 35512), working tree sin commitear. Solo index.html fue tocado (meta
description, og:description, Hero, seccion de credenciales y footer).

Ejecutar con:
    python tests/test_credenciales_reales.py
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HTML = (ROOT / "index.html").read_text(encoding="utf-8")

FRASE_EXPERIENCIA = "12 años de experiencia"
FRASE_COLEGIATURA = "CPA 8812 · CPI 35512"

resultados = []


def check(nombre, condicion, detalle=""):
    estado = "PASS" if condicion else "FAIL"
    resultados.append((estado, nombre, detalle))
    print("[" + estado + "] " + nombre + ((" -- " + detalle) if detalle and not condicion else ""))
    return condicion


# ---------------------------------------------------------------------
# 1. Las dos frases deben aparecer, con el formato exacto (punto medio,
#    no guion), en las 5 ubicaciones esperadas: meta description,
#    og:description, hero (span + chip), credenciales, footer.
# ---------------------------------------------------------------------
check(
    "'" + FRASE_EXPERIENCIA + "' aparece exactamente 5 veces (meta, og, hero, credenciales, footer)",
    HTML.count(FRASE_EXPERIENCIA) == 5,
    "Apariciones: " + str(HTML.count(FRASE_EXPERIENCIA)),
)
check(
    "'" + FRASE_COLEGIATURA + "' aparece exactamente 5 veces (meta, og, hero, credenciales, footer)",
    HTML.count(FRASE_COLEGIATURA) == 5,
    "Apariciones: " + str(HTML.count(FRASE_COLEGIATURA)),
)
check(
    "No existe una variante con guion en vez de punto medio (CPA 8812-CPI / CPA 8812 - CPI)",
    not re.search(r"CPA\s*8812\s*-+\s*CPI", HTML),
)

# ---------------------------------------------------------------------
# 2. meta description y og:description deben seguir siendo identicos.
# ---------------------------------------------------------------------
m_desc = re.search(r'<meta name="description" content="([^"]*)"', HTML)
m_og = re.search(r'<meta property="og:description" content="([^"]*)"', HTML)
desc = m_desc.group(1) if m_desc else None
og = m_og.group(1) if m_og else None
check(
    "meta[name=description] y meta[property=og:description] son identicos",
    desc is not None and desc == og,
    "description=" + repr(desc) + " | og:description=" + repr(og),
)
check(
    "meta description incluye las credenciales nuevas",
    desc is not None and FRASE_EXPERIENCIA in desc and FRASE_COLEGIATURA in desc,
)
check(
    "meta description tiene un largo razonable para SEO (<=160 caracteres orientativo)",
    desc is not None and len(desc) <= 160,
    "Largo actual: " + str(len(desc) if desc else -1) + " caracteres",
)

# ---------------------------------------------------------------------
# 3. No deben quedar comentarios VERIFICAR Y EDITAR.
# ---------------------------------------------------------------------
check(
    "No quedan comentarios 'VERIFICAR Y EDITAR' en index.html",
    "VERIFICAR Y EDITAR" not in HTML,
    "Ocurrencias: " + str(HTML.count("VERIFICAR Y EDITAR")),
)

# ---------------------------------------------------------------------
# 4. Estructura HTML de las listas tocadas.
# ---------------------------------------------------------------------
m_chips = re.search(r'<ul class="hero__chips[^"]*"[^>]*>(.*?)</ul>', HTML, re.S)
chips_li = len(re.findall(r"<li>", m_chips.group(1))) if m_chips else 0
check(
    "hero__chips tiene 4 <li> (antes 3; se agrego CPA 8812 · CPI 35512)",
    chips_li == 4,
    "<li> encontrados: " + str(chips_li),
)
check(
    "El primer <li> de hero__chips es la colegiatura nueva",
    bool(m_chips) and m_chips.group(1).strip().startswith("<li>" + FRASE_COLEGIATURA + "</li>"),
)

m_cred_bloque = re.search(r'<div class="credenciales">(.*?)</div>\s*<a class="linkedin-enlace"', HTML, re.S)
listas_cred = re.findall(r"<ul>(.*?)</ul>", m_cred_bloque.group(1), re.S) if m_cred_bloque else []
li_formacion = len(re.findall(r"<li>", listas_cred[0])) if listas_cred else 0
check(
    "La lista 'Formacion y colegiatura' tiene 6 <li> (antes 4; se agregaron CPA/CPI y anos de experiencia)",
    len(listas_cred) >= 1 and li_formacion == 6,
    "<li> encontrados: " + str(li_formacion),
)
check(
    "La lista 'Herramientas' de credenciales no fue tocada (sigue en 5 <li>)",
    len(listas_cred) >= 2 and len(re.findall(r"<li>", listas_cred[1])) == 5,
)

pie_desc = re.findall(r'<p class="pie__descripcion">([^<]*)</p>', HTML)
check(
    "El footer tiene 2 <p class=\"pie__descripcion\"> (el original + el nuevo de credenciales)",
    len(pie_desc) == 2,
    "Parrafos encontrados: " + repr(pie_desc),
)
check(
    "El segundo parrafo del footer contiene ambas credenciales nuevas",
    len(pie_desc) == 2 and FRASE_COLEGIATURA in pie_desc[1] and FRASE_EXPERIENCIA in pie_desc[1],
)

# ---------------------------------------------------------------------
# 5. Regresion basica: balance de tags clave en todo el documento (deteccion
#    rapida de HTML mal formado tras editar 4 zonas distintas del archivo).
# ---------------------------------------------------------------------
desbalanceados = []
for tag in ("div", "ul", "li", "section", "p", "span"):
    abiertas = len(re.findall(r"<" + tag + r"(\s|>)", HTML))
    cerradas = len(re.findall(r"</" + tag + r">", HTML))
    if abiertas != cerradas:
        desbalanceados.append((tag, abiertas, cerradas))
check(
    "Tags div/ul/li/section/p/span balanceados en todo el documento",
    len(desbalanceados) == 0,
    "Desbalanceados: " + repr(desbalanceados),
)

# ---------------------------------------------------------------------
# 6. Regresion: el resto del sitio sigue intacto (formulario, menu, FAQ,
#    unica foto en el Hero tras la ronda anterior).
# ---------------------------------------------------------------------
check("El formulario de contacto sigue presente", 'class="formulario"' in HTML)
check("El boton de menu movil sigue presente", "menu-boton" in HTML)
check("El acordeon de FAQ sigue presente", "faq__pregunta" in HTML and 'aria-expanded="false"' in HTML)
check(
    "gabriela.jpg aparece 2 veces (img de Sobre mi + JSON-LD)",
    len(re.findall(r"gabriela\.jpg", HTML)) == 2,
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
