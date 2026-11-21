import base64
import html
import inspect
import json
import re
from datetime import datetime, date
from pathlib import Path

import streamlit as st

from pdf_generator import (
    generar_pdf_enfermeria, CONSENTIMIENTOS, PATRONES_GORDON, INSTITUCION
)
from consentimientos import CAMPOS, OBLIGATORIOS

st.set_page_config(page_title="Historia Clínica de Enfermería", page_icon="🩺", layout="wide")

_ANCHO_BTN = ({"width": "stretch"} if "width" in inspect.signature(st.button).parameters
            else {"use_container_width": True})
_ANCHO_DF = ({"width": "stretch"} if "width" in inspect.signature(st.dataframe).parameters
            else {"use_container_width": True})

BASE = Path(__file__).resolve().parent

# Carga segura del CSS
for nombre_css in ("stilo.css", "estilo.css", "style.css", "styles.css"):
    css_path = BASE / nombre_css
    if css_path.is_file():
        try:
            st.markdown(f"<style>{css_path.read_text(encoding='utf-8')}</style>", unsafe_allow_html=True)
            break
        except Exception:
            pass

# ---------------- COMPONENTES VISUALES (clases Tailwind compiladas en stilo.css) ----------------
def _html(fragmento: str) -> str:
    # Streamlit interpreta como Markdown las líneas con sangría: se envía en una sola línea.
    return " ".join(linea.strip() for linea in fragmento.splitlines() if linea.strip())


def encabezado(logo_base64: str, institucion: str) -> None:
    logo = ""
    if logo_base64:
        logo = (
            '<div class="tw:shrink-0 tw:rounded-2xl tw:bg-white tw:p-3 tw:shadow-lg tw:ring-4 tw:ring-white/30 '
            'tw:transition tw:duration-300 tw:hover:scale-105 tw:hover:-rotate-2">'
            f'<img src="data:image/png;base64,{logo_base64}" alt="Escuela de Salud San Pedro Claver" '
            'class="tw:h-16 tw:w-40 tw:object-contain"></div>'
        )
    st.markdown(_html(f"""
    <header class="tw:group tw:relative tw:mb-4 tw:overflow-hidden tw:rounded-3xl tw:bg-linear-to-r
                tw:from-teal-800 tw:via-teal-700 tw:to-emerald-500 tw:px-8 tw:py-6 tw:shadow-xl
                tw:transition tw:duration-500 tw:hover:shadow-2xl">
    <div class="tw:pointer-events-none tw:absolute tw:-right-16 tw:-top-20 tw:size-64 tw:rounded-full
                tw:bg-white/10 tw:transition tw:duration-700 tw:group-hover:scale-125"></div>
    <div class="tw:pointer-events-none tw:absolute tw:-bottom-24 tw:right-1/3 tw:size-56 tw:rounded-full
                tw:bg-emerald-300/10 tw:transition tw:duration-700 tw:group-hover:-translate-y-4"></div>
    <div class="tw:relative tw:flex tw:flex-col tw:items-center tw:gap-5 tw:text-center
                tw:md:flex-row tw:md:text-left">
        {logo}
        <div class="tw:flex-1">
        <div class="tw:m-0 tw:text-xs tw:font-semibold tw:uppercase tw:tracking-[0.25em] tw:text-emerald-100">
            Simulador académico</div>
        <div class="tw:m-0 tw:text-3xl tw:font-extrabold tw:leading-tight tw:tracking-tight tw:text-white">
            Historia Clínica de Enfermería</div>
        <div class="tw:m-0 tw:mt-1 tw:text-sm tw:font-medium tw:text-white/90">
            {html.escape(institucion)} — Programa de Enfermería</div>
        </div>
        <div class="tw:flex tw:flex-col tw:items-center tw:gap-2 tw:md:items-end">
        <span class="tw:inline-flex tw:items-center tw:gap-2 tw:rounded-full tw:bg-white/20 tw:px-4 tw:py-2
                    tw:text-xs tw:font-bold tw:uppercase tw:tracking-wider tw:text-white tw:backdrop-blur
                    tw:transition tw:hover:bg-white/30">
            <span class="tw:relative tw:flex tw:size-2.5">
            <span class="tw:absolute tw:inline-flex tw:size-full tw:animate-ping tw:rounded-full tw:bg-emerald-300 tw:opacity-75"></span>
            <span class="tw:relative tw:inline-flex tw:size-2.5 tw:rounded-full tw:bg-emerald-300"></span>
            </span>
            Sesión abierta
        </span>
        <span class="tw:text-xs tw:text-white/80">🔒 Diligenciamiento seguro</span>
        </div>
    </div>
    </header>
    """), unsafe_allow_html=True)


def seccion(titulo: str, icono: str = "", modulo: int | None = None) -> None:
    """Tarjeta de título para cada sección del formulario."""
    badge = ""
    if modulo is not None:
        badge = (f'<span class="tw:rounded-full tw:bg-teal-600 tw:px-2.5 tw:py-0.5 tw:text-[0.68rem] '
                f'tw:font-bold tw:tracking-wider tw:text-white">MÓDULO {modulo}</span>')
    st.markdown(_html(f"""
    <div class="tw:group tw:mt-6 tw:mb-3 tw:flex tw:items-center tw:gap-3 tw:rounded-2xl tw:border
                tw:border-sky-100 tw:border-l-4 tw:border-l-teal-600 tw:bg-white tw:px-5 tw:py-3
                tw:shadow-sm tw:transition tw:duration-300 tw:hover:-translate-y-0.5 tw:hover:border-teal-200
                tw:hover:shadow-md">
    <span class="tw:grid tw:size-9 tw:place-items-center tw:rounded-xl tw:bg-teal-50 tw:text-lg
                tw:transition tw:duration-300 tw:group-hover:scale-110 tw:group-hover:bg-teal-100">{icono}</span>
    {badge}
    <span class="tw:text-sm tw:font-extrabold tw:uppercase tw:tracking-wide tw:text-teal-700">
        {html.escape(titulo)}</span>
    </div>
    """), unsafe_allow_html=True)


MODULOS = [
    "1. Identificación",
    "2. Anamnesis",
    "3. Antecedentes",
    "4. Valoración",
    "5. Diagnósticos y PAE",
    "6. Medicamentos y notas",
    "7. Consentimientos y PDF",
]
NAV_KEY = "nav_modulos"  # Pestaña activa (la barra de pestañas está oculta; se navega con las tarjetas)


def ir_a_modulo(etiqueta: str) -> None:
    st.session_state[NAV_KEY] = etiqueta


def fila(n, ancho=None):
    """Una fila de columnas alineadas por abajo (los campos quedan parejos aunque una etiqueta ocupe 2 líneas)."""
    try:
        return st.columns(ancho or n, vertical_alignment="bottom")
    except TypeError:
        return st.columns(ancho or n)


ICONOS_MODULO = ["🗂️", "🗣️", "📋", "🩺", "🧾", "💊", "✍️"]


def panel_avance(contenedor, modulos: list[tuple[str, float]], listo_pdf: bool) -> None:
    """Panel de avance: anillo con el total y una tarjeta por módulo; cada tarjeta abre su módulo."""
    total = round(100 * sum(p for _, p in modulos) / max(len(modulos), 1))
    completos = sum(1 for _, p in modulos if p >= 1)
    if listo_pdf:
        estado = ('<span class="tw:inline-flex tw:items-center tw:gap-1.5 tw:rounded-full tw:bg-emerald-100 tw:px-3 '
                'tw:py-1.5 tw:text-xs tw:font-bold tw:text-emerald-700">✅ Lista para generar el PDF</span>')
    else:
        estado = ('<span class="tw:inline-flex tw:items-center tw:gap-1.5 tw:rounded-full tw:bg-amber-100 tw:px-3 '
                'tw:py-1.5 tw:text-xs tw:font-bold tw:text-amber-700">✏️ En diligenciamiento</span>')
    activo = st.session_state.get(NAV_KEY, MODULOS[0])

    with contenedor.container(key="panel_avance"):
        st.markdown(_html(f"""
        <div class="tw:flex tw:flex-wrap tw:items-center tw:gap-4">
        <div class="tw:grid tw:size-16 tw:shrink-0 tw:place-items-center tw:rounded-full tw:shadow-inner"
               style="background:conic-gradient(#0d9488 {total * 3.6}deg, #e2e8f0 0deg)">
            <div class="tw:grid tw:size-12 tw:place-items-center tw:rounded-full tw:bg-white tw:text-sm
                        tw:font-extrabold tw:text-teal-700">{total}%</div>
        </div>
        <div class="tw:min-w-48 tw:flex-1">
            <div class="tw:text-base tw:font-bold tw:text-slate-800">Avance de la historia clínica</div>
            <div class="tw:text-xs tw:text-slate-500">{completos} de {len(modulos)} módulos completos ·
            haz clic en un módulo para abrirlo</div>
        </div>
        {estado}
        </div>
        """), unsafe_allow_html=True)

        columnas = st.columns(len(modulos))
        for i, ((nombre, p), col) in enumerate(zip(modulos, columnas), start=1):
            pct = round(100 * p)
            es_activo = MODULOS[i - 1] == activo
            if pct >= 100:
                tipo = "completo"
                fondo_icono, relleno = "tw:bg-emerald-50", "tw:bg-emerald-500"
                chip = ('<span class="tw:grid tw:size-6 tw:place-items-center tw:rounded-full tw:bg-emerald-500 '
                        'tw:text-xs tw:font-bold tw:text-white tw:shadow-sm">✓</span>')
            elif pct > 0:
                tipo = "parcial"
                fondo_icono, relleno = "tw:bg-amber-50", "tw:bg-amber-400"
                chip = ('<span class="tw:rounded-full tw:bg-amber-100 tw:px-2 tw:py-0.5 tw:text-[0.65rem] '
                        f'tw:font-bold tw:text-amber-700">{pct}%</span>')
            else:
                tipo = "vacio"
                fondo_icono, relleno = "tw:bg-slate-100", "tw:bg-slate-300"
                chip = '<span class="tw:text-[0.65rem] tw:font-semibold tw:text-slate-400">Pendiente</span>'
            if es_activo:  # Tarjeta abierta: fondo verde degradado y textos blancos
                fondo_icono, relleno = "tw:bg-white/20", "tw:bg-white"
                chip = ('<span class="tw:rounded-full tw:bg-white/25 tw:px-2 tw:py-0.5 tw:text-[0.65rem] '
                        'tw:font-bold tw:text-white">Abierto</span>')
            texto_suave = "tw:text-white/80" if es_activo else "tw:text-slate-400"
            pista = "tw:bg-white/25" if es_activo else "tw:bg-slate-100"

            clave = f"tarjeta_{'activa_' if es_activo else ''}{tipo}_{i}"
            with col.container(key=clave):
                st.markdown(_html(f"""
                <div class="tw:flex tw:items-center tw:justify-between">
                <span class="tw:grid tw:size-10 tw:place-items-center tw:rounded-xl tw:text-xl {fondo_icono}">
                    {ICONOS_MODULO[i - 1]}</span>
                {chip}
                </div>
                <div class="tw:mt-2 tw:text-[0.62rem] tw:font-bold tw:uppercase tw:tracking-widest {texto_suave}">
                Módulo {i}</div>
                """), unsafe_allow_html=True)
                st.button(nombre, key=f"nav_{i}", on_click=ir_a_modulo, args=(MODULOS[i - 1],), **_ANCHO_BTN)
                st.markdown(_html(f"""
                <div class="tw:h-1.5 tw:overflow-hidden tw:rounded-full {pista}">
                <div class="tw:h-full tw:rounded-full tw:transition-all tw:duration-700 {relleno}" style="width:{pct}%"></div>
                </div>
                """), unsafe_allow_html=True)


logo_path = BASE / "logo.png"
logo_base64 = base64.b64encode(logo_path.read_bytes()).decode("ascii") if logo_path.exists() else ""
encabezado(logo_base64, INSTITUCION)
panel_progreso = st.empty()  # Se llena al final, cuando ya se conocen todos los datos

for k in ("pae", "meds", "notas", "sv", "liquidos"):
    st.session_state.setdefault(k, [])


# ---------------- CONSECUTIVO DE HISTORIA CLÍNICA ----------------
# El último número usado se guarda en consecutivo_hc.json (uno por año) para que
# cada historia nueva reciba el siguiente número, aunque se cierre la app.
CONSECUTIVO_PATH = BASE / "consecutivo_hc.json"
PREFIJO_HC = "AT-ENF"  # Consecutivo de atención (la HC se identifica con el documento, Res. 1995/1999 art. 6)


def _leer_consecutivos() -> dict:
    try:
        return json.loads(CONSECUTIVO_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}


def siguiente_hc() -> str:
    anio = str(date.today().year)
    ultimo = int(_leer_consecutivos().get(anio, 0))
    return f"{PREFIJO_HC}-{anio}-{ultimo + 1:03d}"


def registrar_hc_usada(numero_hc: str) -> None:
    """Guarda el número como usado para que la próxima historia tome el siguiente."""
    m = re.fullmatch(rf"{PREFIJO_HC}-(\d{{4}})-(\d+)", (numero_hc or "").strip())
    if not m:
        return  # Número escrito a mano con otro formato: no altera el consecutivo
    anio, num = m.group(1), int(m.group(2))
    datos_c = _leer_consecutivos()
    if num > int(datos_c.get(anio, 0)):
        datos_c[anio] = num
        try:
            CONSECUTIVO_PATH.write_text(json.dumps(datos_c, indent=2), encoding="utf-8")
        except Exception:
            pass


st.session_state.setdefault("id_hc_num", siguiente_hc())
if not str(st.session_state.get("id_hc_num", "")).startswith(PREFIJO_HC):
    st.session_state["id_hc_num"] = siguiente_hc()


def faltantes_consentimientos(d, elegidos, edad):
    """Devuelve {sección: [campos que faltan]} para los consentimientos elegidos."""
    if not elegidos:
        return {}
    falta = {}

    def vacio(v):
        return v is None or (isinstance(v, str) and not v.strip()) or (isinstance(v, (list, tuple)) and not v)

    # Datos que aparecen en el encabezado y las firmas de TODOS los consentimientos
    comunes = [
        ("Paciente", "Nombre del paciente (Módulo 1)"),
        ("Documento Paciente", "N° de documento (Módulo 1)"),
        ("Fecha de Atención", "Fecha de atención (Módulo 1)"),
        ("Enfermero Tratante", "Auxiliar de enfermería / estudiante responsable"),
        ("Código/Registro", "N° ReTHUS / código de estudiante"),
    ]
    if edad < 18:
        comunes += [
            ("Acompañante", "Nombre del representante legal (Módulo 1)"),
            ("Parentesco", "Parentesco del representante (Módulo 1)"),
            ("Doc Acompañante", "Documento del representante (Módulo 1)"),
        ]
    f = [etq for clave, etq in comunes if vacio(d.get(clave))]
    if f:
        falta["Datos generales"] = f

    etiquetas = {k: {c[0]: c[1] for c in CAMPOS.get(k, [])} for k in CAMPOS}
    for k in elegidos:
        oblig = list(OBLIGATORIOS.get(k, ()))
        # Obligatorios condicionales
        if k == "invasivos" and "Otro (especificar)" in (d.get("proc") or []):
            oblig.append("proc_otro")
        if k == "disentimiento" and d.get("notificado") == "Sí":
            oblig += ["notif_nombre", "notif_fecha"]
        f = [etiquetas[k].get(c, c) for c in oblig if vacio(d.get(c))]
        if f:
            falta[CONSENTIMIENTOS[k].capitalize()] = f
    return falta


OTROS_PENDIENTES = []  # Opciones "Otro/Otra" elegidas sin especificar


def select_con_otro(contenedor, etiqueta, opciones, key, **kwargs):
    """Selectbox que, si se elige 'Otro'/'Otra', muestra un cuadro para especificar.
    Devuelve p. ej. 'Otra: Mordedura de perro'."""
    valor = contenedor.selectbox(etiqueta, opciones, key=key, **kwargs)
    if valor in ("Otro", "Otra"):
        detalle = contenedor.text_input(f"ESPECIFIQUE ({etiqueta.capitalize()})", key=f"{key}_otro",
                                        placeholder="Escriba cuál…").strip()
        if not detalle:
            OTROS_PENDIENTES.append(etiqueta.capitalize())
            return valor
        return f"{valor}: {detalle}"
    return valor


def calcular_edad(nacimiento: date) -> int:
    hoy = date.today()
    return hoy.year - nacimiento.year - ((hoy.month, hoy.day) < (nacimiento.month, nacimiento.day))


# Todas las pestañas se siguen ejecutando (para que el PDF tenga todos los datos);
# la pestaña visible la eligen las tarjetas del panel de avance.
tabs = st.tabs(MODULOS, key=NAV_KEY, on_change="rerun")
d = {}

# ---------------- 1. IDENTIFICACIÓN ----------------
with tabs[0]:
    seccion("Datos Administrativos de la Consulta", "🗂️", modulo=1)
    c1, c2, c3 = fila(3)
    # Res. 1995 de 1999, art. 6: la historia clínica se identifica con el número del documento del usuario.
    _doc_hc = str(st.session_state.get("id_doc_paciente", "") or "").strip()
    _tipo_hc = st.session_state.get("id_tipo_doc", "CC")
    d["Historia Clínica N°"] = f"{_tipo_hc} {_doc_hc}" if _doc_hc else ""
    c1.text_input("HISTORIA CLÍNICA N° (= DOCUMENTO DEL USUARIO)",
                value=d["Historia Clínica N°"] or "Se llena con el N° de documento", disabled=True,
                help="Por norma (Res. 1995 de 1999, art. 6) la historia clínica se identifica con el documento del usuario.")
    d["N° Atención"] = c2.text_input("N° DE ATENCIÓN (CONSECUTIVO)", key="id_hc_num",
                                    help="Se asigna automáticamente y avanza cada vez que descargas un PDF.")
    d["Fecha de Atención"] = c3.text_input("FECHA Y HORA DE INICIO DE LA ATENCIÓN", datetime.now().strftime("%Y-%m-%d %H:%M"), key="id_fecha_atencion")
    c1, c2, c3 = fila(3)
    d["Servicio"] = c1.text_input("SERVICIO / ESCENARIO DE PRÁCTICA", key="id_servicio")
    d["Vía de Ingreso"] = select_con_otro(c2, "VÍA DE INGRESO", ["Consulta externa", "Urgencias", "Remitido de otra institución",
                                                        "Hospitalización", "Atención extramural / domiciliaria", "Otra"], key="id_via_ingreso")
    d["Causa Atención"] = select_con_otro(c3, "CAUSA QUE MOTIVA LA ATENCIÓN", ["Enfermedad general", "Accidente", "Promoción y prevención",
                                                                    "Control / seguimiento", "Otra"], key="id_causa")

    seccion("Datos Personales del Paciente", "👤", modulo=1)
    c1, c2, c3 = fila(3)
    d["Paciente"] = c1.text_input("NOMBRE DEL PACIENTE (COMPLETO)", key="id_paciente")
    d["Tipo Doc"] = c2.selectbox("TIPO DE DOCUMENTO", ["CC", "TI", "RC", "CE", "PA", "PEP", "PPT"], key="id_tipo_doc")
    d["Documento Paciente"] = c3.text_input("N° DE DOCUMENTO", key="id_doc_paciente")
    
    # Fecha de nacimiento con calendario y edad calculada automáticamente.
    hoy = date.today()
    f1, f2, f3 = fila(3)
    d["Zona"] = f3.selectbox("ZONA DE RESIDENCIA", ["Urbana", "Rural"], key="id_zona")
    nacimiento = f1.date_input("FECHA DE NACIMIENTO (DD/MM/AAAA)", date(1990, 1, 1),
                            min_value=date(1900, 1, 1), max_value=hoy, format="DD/MM/YYYY",
                            key="id_nacimiento",
                            help="Puedes escribir la fecha directamente (ej. 04/05/1992) o elegirla en el calendario.")
    f4 = f2
    d["Fecha Nacimiento"] = nacimiento.strftime("%Y-%m-%d")
    edad = calcular_edad(nacimiento)
    d["Edad"] = edad
    if edad == 0:
        meses_vida = (hoy.year - nacimiento.year) * 12 + hoy.month - nacimiento.month - (hoy.day < nacimiento.day)
        texto_edad = f"{max(meses_vida, 0)} meses"
    else:
        texto_edad = f"{edad} años"
    # El valor de un campo con key se fija por session_state; así se actualiza en cada cambio.
    st.session_state["id_edad_disp"] = texto_edad
    f4.text_input("EDAD (CALCULADA)", disabled=True, key="id_edad_disp")

    c1, c2, c3 = fila(3)
    d["Identidad de Género"] = select_con_otro(c1, "IDENTIDAD DE GÉNERO", ["Femenino", "Masculino", "Transgénero", "No binario",
                                                                    "Otra", "Prefiere no responder"], key="id_genero")
    d["Nacionalidad"] = c2.text_input("PAÍS DE NACIONALIDAD", "Colombia", key="id_nacionalidad")
    d["Sexo"] = c3.selectbox("SEXO BIOLÓGICO", ["Mujer", "Hombre", "Indeterminado / intersexual"], key="id_sexo")

    c1, c2, c3 = fila(3)
    d["Estado Civil"] = c1.text_input("ESTADO CIVIL", key="id_estado_civil")
    d["Teléfono"] = c2.text_input("TELÉFONO", key="id_telefono")
    d["Discapacidad"] = c3.selectbox("CATEGORÍA DE DISCAPACIDAD", ["Ninguna", "Física", "Auditiva", "Visual", "Sordoceguera",
                                                                "Intelectual", "Psicosocial (mental)", "Múltiple"], key="id_discapacidad")

    c1, c2, c3 = fila(3)
    d["Ciudad/Departamento"] = c1.text_input("CIUDAD / DEPARTAMENTO", "Neiva, Huila", key="id_ciudad")
    d["EPS"] = c2.text_input("EPS DEL PACIENTE", key="id_eps")
    d["Dirección"] = c3.text_input("DIRECCIÓN DE VIVIENDA", key="id_direccion")

    c1, c2, c3 = fila(3)
    d["Tipo Plan"] = c1.selectbox("RÉGIMEN", ["Contributivo", "Subsidiado", "Especial", "Particular"], key="id_regimen")
    d["Condición Usuario"] = c2.text_input("CONDICIÓN (COTIZANTE/BENEFICIARIO)", key="id_condicion")
    d["Ocupación"] = c3.text_input("OCUPACIÓN", key="id_ocupacion")

    c1, c2, c3 = fila(3)
    d["Religión"] = c1.text_input("RELIGIÓN / CREENCIAS", key="id_religion")
    d["Grupo Étnico"] = c2.text_input("PERTENENCIA ÉTNICA", "Ninguna", key="id_etnia")
    d["Escolaridad"] = c3.text_input("ESCOLARIDAD", key="id_escolaridad")

    seccion("ACOMPAÑANTE O REPRESENTANTE LEGAL", "👥")
    c1, c2, c3 = fila(3)
    d["Acompañante"] = c1.text_input("NOMBRE DEL ACOMPAÑANTE", key="id_acomp")
    d["Parentesco"] = c2.text_input("PARENTESCO", key="id_parentesco")
    d["Tel Acompañante"] = c3.text_input("TELÉFONO DEL ACOMPAÑANTE", key="id_tel_acomp")
    c1, c2, c3 = fila(3)
    d["Doc Acompañante"] = c1.text_input("DOCUMENTO DEL REPRESENTANTE", key="id_doc_acomp")
    
    if edad < 18:
        st.warning("El usuario es menor de edad: los consentimientos deben ser firmados por su representante legal.")

# ---------------- 2. ANAMNESIS ----------------
with tabs[1]:
    seccion("Anamnesis de Enfermería", "🗣️", modulo=2)
    d["Motivo de Consulta"] = st.text_area("MOTIVO DE CONSULTA (PALABRAS DEL USUARIO)", key="ana_motivo")
    d["Enfermedad Actual"] = st.text_area("ENFERMEDAD ACTUAL (CRONOLOGÍA Y SÍNTOMAS)", key="ana_enf_actual")
    
    seccion("REVISIÓN POR SISTEMAS", "🔎")
    c1, c2 = st.columns(2)
    d["Rev Sintomas Generales"] = c1.text_area("SÍNTOMAS GENERALES", key="rev_generales")
    d["Rev Piel"] = c2.text_area("PIEL Y ANEXOS", key="rev_piel")
    d["Rev Cabeza Cuello"] = c1.text_area("CABEZA Y ÓRGANOS DE LOS SENTIDOS", key="rev_cabeza")
    d["Rev Cardiorespiratorio"] = c2.text_area("CARDIORRESPIRATORIO", key="rev_cardio")
    d["Rev Gastrointestinal"] = c1.text_area("GASTROINTESTINAL", key="rev_gastro")
    d["Rev Genitourinario"] = c2.text_area("GENITOURINARIO", key="rev_genito")
    d["Rev Osteomuscular"] = c1.text_area("OSTEOMUSCULAR / EXTREMIDADES", key="rev_osteo")
    d["Rev Neurologico"] = c2.text_area("NEUROLÓGICO / PSIQUIÁTRICO", key="rev_neuro")

# ---------------- 3. ANTECEDENTES ----------------
with tabs[2]:
    seccion("Antecedentes Clínicos y Personales", "📋", modulo=3)
    c1, c2 = st.columns(2)
    d["Ant Patológicos"] = c1.text_area("PATOLÓGICOS", key="ant_pat")
    d["Ant Quirúrgicos"] = c2.text_area("QUIRÚRGICOS", key="ant_quir")
    d["Alergias"] = c1.text_area("ALÉRGICOS", key="ant_alergias")
    d["Ant Farmacológicos"] = c2.text_area("FARMACOLÓGICOS", key="ant_farma")
    d["Ant Familiares"] = c1.text_area("FAMILIARES", key="ant_fam")
    d["Ant Hospitalarios"] = c2.text_area("TRAUMÁTICOS / HOSPITALARIOS", key="ant_hosp")
    d["Hábitos"] = c1.text_area("HÁBITOS DE VIDA", key="ant_habitos")
    d["Ant Gineco"] = c2.text_area("GINECO-OBSTÉTRICOS", key="ant_gineco")
    d["Vacunación"] = c1.text_input("ESQUEMA DE VACUNACIÓN", key="ant_vacunacion")
    d["Riesgo Infección"] = c2.text_input("RIESGO DE INFECCIÓN", key="ant_riesgo_inf")

# ---------------- 4. VALORACIÓN ----------------
with tabs[3]:
    seccion("Antropometría y Signos Vitales", "📏", modulo=4)
    
    a1, a2, a3 = fila(3)
    peso = a1.number_input("PESO (KG)", min_value=0.0, max_value=400.0, value=0.0, step=0.1, format="%.1f", key="val_peso")
    talla = a2.number_input("TALLA (CM)", min_value=0.0, max_value=250.0, value=0.0, step=0.5, format="%.1f", key="val_talla")
    
    # Cálculo automático del IMC
    if peso > 0 and talla > 0:
        imc_calculado = round(peso / ((talla / 100) ** 2), 1)
        imc_texto = str(imc_calculado)
    else:
        imc_texto = ""

    st.session_state["val_imc"] = imc_texto
    a3.text_input("IMC (KG/M²)", key="val_imc", disabled=True)
    
    d["Peso"] = f"{peso:g}" if peso > 0 else ""
    d["Talla"] = f"{talla:g}" if talla > 0 else ""
    d["IMC"] = imc_texto

    with st.form("form_sv", clear_on_submit=True):
        s = fila(4) + fila(4)
        sv_hora = s[0].text_input("FECHA/HORA", datetime.now().strftime("%Y-%m-%d %H:%M"), key="sv_hora")
        sv_ta = s[1].text_input("TA (MMHG)", key="sv_ta")
        sv_fc = s[2].text_input("FC (LPM)", key="sv_fc")
        sv_fr = s[3].text_input("FR (RPM)", key="sv_fr")
        sv_t = s[4].text_input("T° (°C)", key="sv_t")
        sv_sat = s[5].text_input("SATO2 (%)", key="sv_sat")
        sv_glu = s[6].text_input("GLUCOMETRÍA", key="sv_glu")
        sv_resp = s[7].text_input("RESPONSABLE", key="sv_resp")
        
        if st.form_submit_button("➕ Agregar toma"):
            st.session_state.sv.append({
                "Hora": sv_hora, "TA": sv_ta, "FC": sv_fc, "FR": sv_fr,
                "Temperatura": sv_t, "SatO2": sv_sat, "Glucometría": sv_glu,
                "Responsable": sv_resp
            })
            st.rerun()

    if st.session_state.sv:
        st.dataframe(st.session_state.sv, **_ANCHO_DF)
        if st.button("🗑️ Borrar última toma", key="btn_borrar_sv"):
            st.session_state.sv.pop()
            st.rerun()

    seccion("VALORACIÓN FÍSICA CÉFALO-CAUDAL", "🩺")
    c1, c2 = st.columns(2)
    d["Aspecto General"] = c1.text_area("ASPECTO GENERAL", key="val_aspecto")
    d["Piel"] = c2.text_area("PIEL Y MUCOSAS (VALORACIÓN FÍSICA)", key="val_piel")
    d["Cabeza Cuello"] = c1.text_area("CABEZA Y CUELLO (VALORACIÓN FÍSICA)", key="val_cabeza")
    d["Tórax"] = c2.text_area("TÓRAX Y CARDIOPULMONAR", key="val_torax")
    d["Abdomen"] = c1.text_area("ABDOMEN", key="val_abdomen")
    d["Genitourinario"] = c2.text_area("GENITOURINARIO (VALORACIÓN FÍSICA)", key="val_genito")
    d["Extremidades"] = c1.text_area("EXTREMIDADES", key="val_extremidades")
    d["Neurológico"] = c2.text_area("NEUROLÓGICO", key="val_neuro")
    d["Dispositivos"] = c1.text_area("DISPOSITIVOS", key="val_dispositivos")
    d["Heridas"] = c2.text_area("HERIDAS / LESIONES", key="val_heridas")

    seccion("ESCALAS DE VALORACIÓN", "📊")
    NA = "No aplica"
    c1, c2, c3 = fila(3)
    _g = c1.selectbox("GLASGOW (/15)", [NA] + [str(x) for x in range(15, 2, -1)], key="esc_glasgow")
    _e = c2.selectbox("DOLOR - EVA (0 A 10)", [NA] + [str(x) for x in range(0, 11)], key="esc_eva")
    d["Braden"] = c3.text_input("BRADEN - RIESGO DE UPP (PUNTAJE E INTERPRETACIÓN)", key="esc_braden", placeholder="Ej.: 14 - riesgo moderado")
    c1, c2, c3 = fila(3)
    d["Morse"] = c1.text_input("MORSE - RIESGO DE CAÍDAS (PUNTAJE E INTERPRETACIÓN)", key="esc_morse", placeholder="Ej.: 45 - riesgo alto")
    d["Barthel"] = c2.text_input("BARTHEL / KATZ - DEPENDENCIA (PUNTAJE E INTERPRETACIÓN)", key="esc_barthel", placeholder="Ej.: 90 - dependencia leve")
    d["Otra Escala"] = c3.text_input("OTRA ESCALA (NOMBRE Y RESULTADO)", key="esc_otra")
    d["Glasgow"] = "" if _g == NA else _g
    d["EVA"] = "" if _e == NA else _e

    if _e not in (NA, "0"):
        seccion("VALORACIÓN DEL DOLOR", "💢")
        c1, c2, c3 = fila(3)
        d["Dolor Ubicación"] = c1.text_input("UBICACIÓN / IRRADIACIÓN", key="dolor_ubic")
        d["Dolor Tipo"] = c2.text_input("TIPO / CARÁCTER (PUNZANTE, OPRESIVO…)", key="dolor_tipo")
        d["Dolor Duración"] = c3.text_input("DURACIÓN / FRECUENCIA", key="dolor_dur")
        c1, c2, c3 = fila(3)
        d["Dolor Alivia"] = c1.text_input("QUÉ LO ALIVIA", key="dolor_alivia")
        d["Dolor Empeora"] = c2.text_input("QUÉ LO EMPEORA", key="dolor_empeora")

    seccion("PATRONES FUNCIONALES DE GORDON", "🧩")
    patrones = {}
    for p in PATRONES_GORDON:
        a, b = fila(2, [4, 1])
        h = a.text_input(p, key=f"h_{p}")
        e = b.selectbox("Estado", ["", "Funcional", "Disfuncional"], key=f"e_{p}", label_visibility="collapsed")
        patrones[p] = {"hallazgos": h, "estado": e}
    d["Patrones"] = patrones

# ---------------- 5. DIAGNÓSTICOS Y PAE ----------------
with tabs[4]:
    seccion("Diagnósticos Médicos", "🧾", modulo=5)
    c1, c2 = st.columns([3, 1])
    d["Diagnóstico Médico"] = c1.text_area("DIAGNÓSTICO MÉDICO PRINCIPAL", key="dx_med_principal")
    d["Codigo CIE"] = c2.text_input("CÓDIGO CIE-10 / CIE-11", key="dx_cie_code")
    d["Diagnosticos Secundarios"] = st.text_area("DIAGNÓSTICOS SECUNDARIOS / COMORBILIDADES", key="dx_med_secundarios")
    
    seccion("PROCESO DE ATENCIÓN DE ENFERMERÍA (PAE)", "🧠")
    d["Datos Significativos"] = st.text_area("DATOS SIGNIFICATIVOS DE LA VALORACIÓN", key="pae_datos_sig")
    with st.form("form_pae", clear_on_submit=True):
        dx = st.text_input("DIAGNÓSTICO NANDA", key="pae_dx_input")
        noc = st.text_input("RESULTADO ESPERADO (NOC)", key="pae_noc_input")
        nic = st.text_area("INTERVENCIONES (NIC)", key="pae_nic_input")
        ev = st.text_input("EVALUACIÓN", key="pae_ev_input")
        if st.form_submit_button("➕ Agregar Diagnóstico PAE") and dx:
            st.session_state.pae.append({"Diagnóstico": dx, "Resultado": noc, "Intervención": nic, "Evaluación": ev})
            st.rerun()
    if st.session_state.pae:
        st.dataframe(st.session_state.pae, **_ANCHO_DF)
        if st.button("🗑️ Borrar último diagnóstico", key="btn_borrar_pae"):
            st.session_state.pae.pop()
            st.rerun()

# ---------------- 6. MEDICAMENTOS Y NOTAS ----------------
with tabs[5]:
    seccion("Administración de Medicamentos", "💊", modulo=6)
    with st.form("form_med", clear_on_submit=True):
        c1, c2, c3, c4 = fila(4)
        med = c1.text_input("MEDICAMENTO", key="med_nombre")
        dosis = c2.text_input("DOSIS", key="med_dosis")
        via = c3.text_input("VÍA", key="med_via")
        hora_prog = c4.text_input("HORA PROGRAMADA", key="med_hora_prog")
        c1, c2, c3 = fila(3)
        hora_admin = c1.text_input("FECHA/HORA DE ADMINISTRACIÓN", datetime.now().strftime("%Y-%m-%d %H:%M"), key="med_hora_admin")
        prescriptor = c2.text_input("PRESCRIPTOR / INDICACIÓN", key="med_prescriptor")
        resp = c3.text_input("RESPONSABLE (QUIEN ADMINISTRA)", key="med_resp")
        obs = st.text_input("OBSERVACIONES", key="med_obs")
        if st.form_submit_button("➕ Agregar Medicamento") and med:
            st.session_state.meds.append({"Fecha y Hora": hora_admin,
                                        "Hora Programada": hora_prog, "Medicamento": med, "Dosis": dosis,
                                        "Vía": via, "Prescriptor": prescriptor,
                                        "Observación": obs, "Responsable": resp})
            st.rerun()
    if st.session_state.meds:
        st.dataframe(st.session_state.meds, **_ANCHO_DF)
        if st.button("🗑️ Borrar último medicamento", key="btn_borrar_med"):
            st.session_state.meds.pop()
            st.rerun()

    seccion("NOTAS DE ENFERMERÍA (SOAP / PIE)", "📝")
    with st.form("form_nota", clear_on_submit=True):
        nota = st.text_area("NOTA DE ENFERMERÍA", key="nota_texto")
        resp_n = st.text_input("FIRMA / REGISTRO DEL AUTOR", key="nota_autor")
        if st.form_submit_button("➕ Agregar Nota") and nota:
            st.session_state.notas.append({"Fecha y Hora": datetime.now().strftime("%Y-%m-%d %H:%M"),
                                        "Nota": nota, "Responsable": resp_n})
            st.rerun()
    if st.session_state.notas:
        st.dataframe(st.session_state.notas, **_ANCHO_DF)
        if st.button("🗑️ Borrar última nota", key="btn_borrar_nota"):
            st.session_state.notas.pop()
            st.rerun()

    seccion("CONTROL DE LÍQUIDOS (INGRESOS Y EGRESOS)", "💧")
    with st.form("form_liq", clear_on_submit=True):
        c1, c2, c3, c4, c5 = fila(5)
        liq_hora = c1.text_input("FECHA/HORA", datetime.now().strftime("%Y-%m-%d %H:%M"), key="liq_hora")
        liq_tipo = c2.selectbox("TIPO", ["Ingreso", "Egreso"], key="liq_tipo")
        liq_concepto = c3.selectbox("CONCEPTO", ["Vía oral", "Líquidos endovenosos", "Sonda (nutrición)", "Medicamentos diluidos",
                                                "Diuresis", "Deposición", "Vómito", "Drenaje", "Sonda (residuo)", "Otro"], key="liq_concepto")
        liq_ml = c4.number_input("CANTIDAD (ML)", min_value=0, max_value=10000, step=10, key="liq_ml")
        liq_resp = c5.text_input("RESPONSABLE", key="liq_resp")
        liq_otro = st.text_input("SI EL CONCEPTO ES 'OTRO', ESPECIFIQUE CUÁL", key="liq_otro")
        if st.form_submit_button("➕ Agregar registro de líquidos"):
            if liq_ml <= 0:
                st.error("Escribe la cantidad en mL.")
            elif liq_concepto == "Otro" and not liq_otro.strip():
                st.error("Elegiste 'Otro': especifica cuál es el concepto.")
            else:
                if liq_concepto == "Otro":
                    liq_concepto = f"Otro: {liq_otro.strip()}"
                st.session_state.liquidos.append({"Fecha y Hora": liq_hora, "Tipo": liq_tipo, "Concepto": liq_concepto,
                                                "Cantidad (mL)": int(liq_ml), "Responsable": liq_resp})
                st.rerun()
    if st.session_state.liquidos:
        st.dataframe(st.session_state.liquidos, **_ANCHO_DF)
        ing = sum(x["Cantidad (mL)"] for x in st.session_state.liquidos if x["Tipo"] == "Ingreso")
        egr = sum(x["Cantidad (mL)"] for x in st.session_state.liquidos if x["Tipo"] == "Egreso")
        m1, m2, m3 = st.columns(3)
        m1.metric("Total ingresos", f"{ing} mL")
        m2.metric("Total egresos", f"{egr} mL")
        m3.metric("Balance", f"{ing - egr:+} mL")
        if st.button("🗑️ Borrar último registro de líquidos", key="btn_borrar_liq"):
            st.session_state.liquidos.pop()
            st.rerun()

    seccion("EDUCACIÓN Y EGRESO", "🎓")
    c1, c2 = st.columns(2)
    d["Educación"] = c1.text_area("EDUCACIÓN BRINDADA AL USUARIO / FAMILIA (TEMA Y COMPRENSIÓN)", key="edu_texto")
    d["Condición Salida"] = c2.text_area("CONDICIÓN DE SALIDA / DESTINO (CASA, REMISIÓN, HOSPITALIZACIÓN)", key="egreso_condicion")
    d["Recomendaciones"] = st.text_area("RECOMENDACIONES Y SIGNOS DE ALARMA EXPLICADOS", key="egreso_recomendaciones")

# ---------------- 7. CONSENTIMIENTOS Y PDF ----------------
with tabs[6]:
    seccion("Firmas y Consentimientos Informados", "✍️", modulo=7)
    
    elegidos = st.multiselect(
        "SELECCIONA LOS CONSENTIMIENTOS A INCLUIR", options=list(CONSENTIMIENTOS.keys()),
        default=["general", "datos"], format_func=lambda k: CONSENTIMIENTOS[k], key="ms_consentimientos")
    d["Consentimientos Seleccionados"] = elegidos

    # Valores que se pueden traer de otros módulos para no escribirlos dos veces
    ultimo_med = st.session_state.meds[-1] if st.session_state.meds else {}
    sugeridos = {
        "info_clinica": d.get("Alergias", ""),
        "alergias_med": d.get("Alergias", ""),
        "med": ultimo_med.get("Medicamento", ""),
        "dosis": ultimo_med.get("Dosis", ""),
        "via": ultimo_med.get("Vía", ""),
    }

    # Generar todos los campos requeridos por los consentimientos elegidos
    if elegidos:
        st.caption("Los campos marcados con * son obligatorios para que el consentimiento salga completo en el PDF. "
                "Algunos se llenan solos con lo que ya registraste (alergias, último medicamento); puedes corregirlos.")
        for k in elegidos:
            st.markdown(f"#### 📝 {CONSENTIMIENTOS[k]}")
            campos_cons = CAMPOS.get(k, [])
            if not campos_cons:
                st.caption("Este consentimiento solo usa los datos de identificación del paciente y las firmas.")
            for c_id, label, tipo, opciones in campos_cons:
                key_widget = f"c_{k}_{c_id}"
                etiqueta = label.upper() + (" *" if c_id in OBLIGATORIOS.get(k, ()) else "")
                if tipo == "texto":
                    if sugeridos.get(c_id) and not st.session_state.get(key_widget):
                        st.session_state[key_widget] = sugeridos[c_id]
                    d[c_id] = st.text_input(etiqueta, key=key_widget)
                elif tipo == "opcion":
                    d[c_id] = st.radio(etiqueta, opciones, key=key_widget, horizontal=True, index=None)
                elif tipo == "multi":
                    d[c_id] = st.multiselect(etiqueta, opciones, key=key_widget)

            d[f"Obs {k}"] = st.text_input(f"OBSERVACIONES / DETALLES ADICIONALES", key=f"obs_{k}")
            st.divider()

    seccion("PROFESIONAL RESPONSABLE Y FIRMAS", "🧑‍⚕️")
    c1, c2 = st.columns(2)
    d["Enfermero Tratante"] = c1.text_input("AUXILIAR DE ENFERMERÍA / ESTUDIANTE RESPONSABLE", key="prof_enf_tratante")
    d["Código/Registro"] = c2.text_input("N° RETHUS / CÓDIGO DE ESTUDIANTE", key="prof_codigo_reg")
    d["Docente Supervisor"] = c1.text_input("DOCENTE SUPERVISOR(A)", key="prof_docente_sup")
    d["Registro Docente"] = c2.text_input("REGISTRO DEL DOCENTE", key="prof_reg_docente")
    f_pac = c1.file_uploader("FIRMA DEL PACIENTE (IMAGEN)", type=["png", "jpg", "jpeg"], key="up_firma_pac")
    f_enf = c2.file_uploader("FIRMA DEL AUXILIAR / ESTUDIANTE (IMAGEN)", type=["png", "jpg", "jpeg"], key="up_firma_enf")
    f_doc = c1.file_uploader("FIRMA DEL DOCENTE (IMAGEN)", type=["png", "jpg", "jpeg"], key="up_firma_doc")

    datos_representante = [
        (d.get(campo) or "").strip()
        for campo in ("Acompañante", "Parentesco", "Doc Acompañante")
    ]
    

    # ---- Revisión: qué falta para que los consentimientos salgan completos ----
    faltantes = faltantes_consentimientos(d, elegidos, edad)
    if OTROS_PENDIENTES:
        faltantes["Especificar opción 'Otro/Otra'"] = list(dict.fromkeys(OTROS_PENDIENTES))
    permitir_blancos = False
    if elegidos or faltantes:
        if faltantes:
            total = sum(len(v) for v in faltantes.values())
            st.error(f"📋 Faltan {total} dato(s) para que los consentimientos salgan completos:")
            for seccion, items in faltantes.items():
                st.markdown(f"**{seccion}:** " + " · ".join(items))
            permitir_blancos = st.checkbox(
                "Generar de todas formas (los datos faltantes quedarán como raya para llenar a mano)",
                key="chk_permitir_blancos")
        else:
            st.success("✅ Todos los datos de los consentimientos están completos.")

    if faltantes and not permitir_blancos:
        st.info("Completa los datos de la lista anterior para habilitar la descarga del PDF.")
    elif not d.get("Paciente") or not d.get("Enfermero Tratante"):
        st.warning("⚠️ Ingresa el nombre del paciente y del auxiliar / estudiante responsable para generar la Historia Clínica.")
    elif (
        elegidos
        and (edad < 18 or any(datos_representante))
        and not all(datos_representante)
    ):
        st.warning("⚠️ Completa los datos del representante legal para menores de edad.")
    else:
        pdf_nombre = (f"{(d.get('N° Atención') or 'AT').strip()}_"
                    f"{(d.get('Documento Paciente') or 'sin_documento').strip()}.pdf")
        st.download_button(
            label="📕 DESCARGAR HISTORIA CLÍNICA (PDF)",
            data=generar_pdf_enfermeria(
                d, 
                st.session_state.pae, 
                st.session_state.meds, 
                st.session_state.notas, 
                f_pac, 
                f_enf,
                signos_vitales=st.session_state.sv, 
                firma_docente_file=f_doc,
                liquidos=st.session_state.liquidos
            ),
            file_name=pdf_nombre,
            mime="application/pdf",
            type="primary",
            key="generar_pdf",
            on_click=registrar_hc_usada,
            args=(d.get("N° Atención", ""),),
            **_ANCHO_BTN
        )


# ---------------- PANEL DE AVANCE (Tailwind) ----------------
def _lleno(v):
    return bool(v.strip()) if isinstance(v, str) else bool(v)


def _avance(claves, extra=()):
    checks = [_lleno(d.get(c)) for c in claves] + list(extra)
    return sum(checks) / len(checks) if checks else 0


_patrones = d.get("Patrones", {}) or {}
avance_modulos = [
    ("Identificación", _avance(["Paciente", "Documento Paciente", "Fecha de Atención", "Servicio", "Teléfono",
                                "Dirección", "EPS", "Ocupación", "Estado Civil", "Escolaridad"])),
    ("Anamnesis", _avance(["Motivo de Consulta", "Enfermedad Actual", "Rev Sintomas Generales", "Rev Piel",
                        "Rev Cabeza Cuello", "Rev Cardiorespiratorio", "Rev Gastrointestinal",
                        "Rev Genitourinario", "Rev Osteomuscular", "Rev Neurologico"])),
    ("Antecedentes", _avance(["Ant Patológicos", "Ant Quirúrgicos", "Alergias", "Ant Farmacológicos",
                            "Ant Familiares", "Ant Hospitalarios", "Hábitos", "Ant Gineco", "Vacunación",
                            "Riesgo Infección"])),
    ("Valoración", _avance(["Peso", "Talla", "Aspecto General", "Piel", "Cabeza Cuello", "Tórax", "Abdomen",
                            "Extremidades", "Neurológico", "Glasgow"],
                        [bool(st.session_state.sv), any(v.get("hallazgos") for v in _patrones.values())])),
    ("Diagnósticos y PAE", _avance(["Diagnóstico Médico", "Datos Significativos"], [bool(st.session_state.pae)])),
    ("Medicamentos y notas", _avance(["Educación", "Condición Salida"],
                                    [bool(st.session_state.meds or st.session_state.notas)])),
    ("Consentimientos y PDF", _avance(["Enfermero Tratante", "Código/Registro", "Docente Supervisor"],
                                    [bool(elegidos) and not faltantes])),
]
panel_avance(panel_progreso, avance_modulos,
            listo_pdf=bool(d.get("Paciente") and d.get("Enfermero Tratante")) and not faltantes)