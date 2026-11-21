"""
Generador de PDF - Historia Clínica de ENFERMERÍA + Consentimientos Informados.
"""
import io
import html
import re
from pathlib import Path
from consentimientos import CONSENTIMIENTOS, TEXTOS

from reportlab.lib.pagesizes import letter
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, Image, HRFlowable, KeepTogether
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.utils import ImageReader
from reportlab.lib import colors
from reportlab.pdfgen import canvas as rl_canvas

INSTITUCION = "ESCUELA DE SALUD SAN PEDRO CLAVER"
PROGRAMA = "Programa de Enfermería"
LOGO_PATH = Path(__file__).resolve().with_name("logo.png")

PATRONES_GORDON = [
    "1. Percepción - manejo de la salud", "2. Nutricional - metabólico", "3. Eliminación",
    "4. Actividad - ejercicio", "5. Sueño - descanso", "6. Cognitivo - perceptual",
    "7. Autopercepción - autoconcepto", "8. Rol - relaciones", "9. Sexualidad - reproducción",
    "10. Adaptación - tolerancia al estrés", "11. Valores - creencias",
]
SIN_REGISTRO = "No registra"

def esc(valor):
    if valor is None: return ""
    return html.escape(str(valor))

def _leer_bytes(file_obj):
    if file_obj is None: return None
    try:
        if hasattr(file_obj, "seek"): file_obj.seek(0)
        content = file_obj.read()
        if hasattr(file_obj, "seek"): file_obj.seek(0)
        return content or None
    except Exception:
        return None

def _imagen_ajustada(fuente, max_w, max_h):
    try:
        origen = io.BytesIO(fuente) if isinstance(fuente, (bytes, bytearray)) else str(fuente)
        iw, ih = ImageReader(origen).getSize()
        escala = min(max_w / iw, max_h / ih)
        if isinstance(fuente, (bytes, bytearray)): origen = io.BytesIO(fuente)
        return Image(origen, width=iw * escala, height=ih * escala)
    except Exception:
        return ""

def _canvas_con_folios(encabezado_izq):
    class NumberedCanvas(rl_canvas.Canvas):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self._estados = []
        def showPage(self):
            self._estados.append(dict(self.__dict__))
            self._startPage()
        def save(self):
            total = len(self._estados)
            for estado in self._estados:
                self.__dict__.update(estado)
                self._pie(total)
                super().showPage()
            super().save()
        def _pie(self, total):
            self.setFont("Helvetica", 7)
            self.setFillColor(colors.HexColor("#475569"))
            self.drawString(36, 22, encabezado_izq)
            self.drawRightString(letter[0] - 36, 22, f"Folio {self._pageNumber} de {total}")
    return NumberedCanvas

def generar_pdf_enfermeria(datos, pae=None, medicamentos=None, notas=None,
                        firma_paciente_file=None, firma_enfermero_file=None,
                        signos_vitales=None, firma_docente_file=None, liquidos=None):
    liquidos = liquidos or []
    signos_vitales = signos_vitales or []
    pae = pae or []
    medicamentos = medicamentos or []
    notas = notas or []
    buffer = io.BytesIO()

    doc = SimpleDocTemplate(
        buffer, pagesize=letter, rightMargin=36, leftMargin=36, topMargin=30, bottomMargin=40,
        title="Historia Clínica de Enfermería", author="Programa de Enfermería"
    )

    styles = getSampleStyleSheet()
    PRIMARY = colors.HexColor("#0d8b7d")
    SECOND = colors.HexColor("#0f766e")
    DARK = colors.HexColor("#1e293b")
    LIGHT = colors.HexColor("#f8fafc")
    BORDER = colors.HexColor("#cbd5e1")

    title = ParagraphStyle("T", parent=styles["Heading1"], fontSize=11, leading=13, textColor=PRIMARY, fontName="Helvetica-Bold")
    sub = ParagraphStyle("S", parent=styles["Normal"], fontSize=8, leading=10, textColor=colors.HexColor("#475569"))
    sec = ParagraphStyle("Sec", parent=styles["Heading2"], fontSize=9, leading=11, textColor=colors.white, backColor=PRIMARY,
                        borderPadding=(3, 4, 3, 4), spaceBefore=8, spaceAfter=4, fontName="Helvetica-Bold", keepWithNext=1)
    body = ParagraphStyle("B", parent=styles["Normal"], fontSize=8, leading=10.5, textColor=DARK)
    small = ParagraphStyle("Sm", parent=body, fontSize=7.5, leading=9.5)
    th_style = ParagraphStyle("TH", parent=small, textColor=colors.white, fontName="Helvetica-Bold")

    cons_t = ParagraphStyle("CT", parent=styles["Heading1"], fontSize=11, leading=13, textColor=colors.black, fontName="Helvetica-Bold", alignment=1)
    cons_b = ParagraphStyle("CB", parent=styles["Normal"], fontSize=8.5, leading=12.5, textColor=colors.black)

    def P(txt, st=body): return Paragraph(txt, st)
    def valor(clave, defecto=SIN_REGISTRO): return datos.get(clave) if datos.get(clave) else defecto
    def campo(etq, clave, st=body, defecto=SIN_REGISTRO): return P(f"<b>{etq}:</b> {esc(valor(clave, defecto))}", st)

    def tabla(filas, widths, header_color=None, repeat=0):
        t = Table(filas, colWidths=widths, repeatRows=repeat)
        est = [("GRID", (0, 0), (-1, -1), 0.5, BORDER), ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("TOPPADDING", (0, 0), (-1, -1), 2), ("BOTTOMPADDING", (0, 0), (-1, -1), 2)]
        if header_color: est += [("BACKGROUND", (0, 0), (-1, 0), header_color)]
        else: est += [("BACKGROUND", (0, 0), (-1, -1), LIGHT)]
        t.setStyle(TableStyle(est))
        return t

    bytes_pac = _leer_bytes(firma_paciente_file)
    bytes_enf = _leer_bytes(firma_enfermero_file)
    bytes_docente = _leer_bytes(firma_docente_file)

    def logo(max_w=110, max_h=45):
        if LOGO_PATH.exists():
            img = _imagen_ajustada(LOGO_PATH, max_w, max_h)
            if img != "": return img
        return P(f"<b>{INSTITUCION}</b>", small)

    doc_pac = f"{datos.get('Tipo Doc', '')} {datos.get('Documento Paciente', '')}".strip()
    reg_prof = f"{datos.get('Código/Registro', '________________')}"

    story = []

    # ============================ ENCABEZADO HISTORIA CLÍNICA ============================
    hdr = [[logo(90, 38), P(f"<b>{INSTITUCION}</b>", title), P(f"<b>HISTORIA CLÍNICA N°:</b> {esc(valor('Historia Clínica N°'))}<br/><font size=8>N° de atención: {esc(valor('N° Atención'))}</font>", ParagraphStyle("N", parent=title, fontSize=9.5, alignment=2))],
            ["", P(PROGRAMA, sub), P(f"<b>Fecha y hora de atención:</b> {esc(valor('Fecha de Atención', ''))}", ParagraphStyle("F", parent=sub, alignment=2))],
            ["", P("<b>REGISTRO CLÍNICO DE ENFERMERÍA — PROCESO DE ATENCIÓN DE ENFERMERÍA (PAE)</b>", sub), ""]]
    th = Table(hdr, colWidths=[100, 260, 180])
    th.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("SPAN", (0, 0), (0, 2))]))
    story += [th, HRFlowable(width="100%", thickness=1, color=PRIMARY, spaceBefore=2, spaceAfter=4)]

    # ============================ 1-9 BLOQUES HC (Igual que antes) ============================
    story.append(P("1. DATOS DE IDENTIFICACIÓN DEL USUARIO", sec))
    story.append(tabla([
        [campo("Paciente", "Paciente"), P(f"<b>Documento:</b> {esc(doc_pac or SIN_REGISTRO)}"), campo("Edad", "Edad")],
        [campo("Fecha de nacimiento", "Fecha Nacimiento"), campo("Sexo", "Sexo"), campo("Estado civil", "Estado Civil")],
        [campo("Teléfono", "Teléfono"), campo("Dirección", "Dirección"), campo("Ciudad/Departamento", "Ciudad/Departamento")],
        [campo("EPS / Aseguradora", "EPS"), campo("Ocupación", "Ocupación"), P(f"<b>Régimen/Condición:</b> {esc(valor('Tipo Plan'))} / {esc(valor('Condición Usuario'))}")],
        [campo("Escolaridad", "Escolaridad"), campo("Religión / creencias", "Religión"), campo("Pertenencia étnica", "Grupo Étnico")],
        [campo("País de nacionalidad", "Nacionalidad"), campo("Identidad de género", "Identidad de Género"), campo("Discapacidad", "Discapacidad")],
        [campo("Zona de residencia", "Zona"), campo("Vía de ingreso", "Vía de Ingreso"), campo("Causa de la atención", "Causa Atención")],
        [campo("Acompañante / responsable", "Acompañante", defecto="Sin acompañante"), P(f"<b>Parentesco / Doc.:</b> {esc(valor('Parentesco', 'N/A'))} / {esc(valor('Doc Acompañante', 'N/A'))}"), campo("Tel. acompañante", "Tel Acompañante", defecto="N/A")],
    ], [190, 190, 160]))

    story.append(P("2. ANAMNESIS Y REVISIÓN POR SISTEMAS", sec))
    story.append(campo("Motivo de consulta", "Motivo de Consulta"))
    story.append(campo("Enfermedad actual", "Enfermedad Actual"))
    story.append(campo("Servicio / escenario de práctica", "Servicio"))
    story.append(Spacer(1, 3))
    story.append(P("<b>Revisión por Sistemas:</b>", small))
    story.append(tabla([
        [campo("Síntomas generales", "Rev Sintomas Generales", small), campo("Piel y anexos", "Rev Piel", small)],
        [campo("Cabeza y órganos de los sentidos", "Rev Cabeza Cuello", small), campo("Cardiorrespiratorio", "Rev Cardiorespiratorio", small)],
        [campo("Gastrointestinal", "Rev Gastrointestinal", small), campo("Genitourinario", "Rev Genitourinario", small)],
        [campo("Osteomuscular", "Rev Osteomuscular", small), campo("Neurológico / Psiquiátrico", "Rev Neurologico", small)],
    ], [270, 270]))

    story.append(P("3. ANTECEDENTES", sec))
    story.append(tabla([
        [campo("Patológicos", "Ant Patológicos", small), campo("Quirúrgicos", "Ant Quirúrgicos", small)],
        [campo("Alérgicos (medicamentos/alimentos/látex)", "Alergias", small), campo("Farmacológicos (medicación actual)", "Ant Farmacológicos", small)],
        [campo("Familiares", "Ant Familiares", small), campo("Traumáticos / hospitalarios", "Ant Hospitalarios", small)],
        [campo("Hábitos (tabaco, alcohol, SPA, actividad física)", "Hábitos", small), campo("Gineco-obstétricos (FUR, G-P-A-C)", "Ant Gineco", small, "N/A")],
        [campo("Esquema de vacunación", "Vacunación", small), campo("Inmunosupresión / riesgo de infección", "Riesgo Infección", small)],
    ], [270, 270]))

    story.append(P("4. SIGNOS VITALES Y ANTROPOMETRÍA", sec))
    story.append(tabla([[campo("Peso (kg)", "Peso", small, "—"), campo("Talla (cm)", "Talla", small, "—"), campo("IMC (kg/m²)", "IMC", small, "—")]], [180, 180, 180]))
    story.append(Spacer(1, 3))
    sv_h = ["Fecha / hora", "TA (mmHg)", "FC (lpm)", "FR (rpm)", "T° (°C)", "SatO2 (%)", "Glucometría", "Responsable"]
    sv_k = ["Hora", "TA", "FC", "FR", "Temperatura", "SatO2", "Glucometría", "Responsable"]
    filas = [[P(f"<b>{h}</b>", small) for h in sv_h]]
    if signos_vitales:
        for t in signos_vitales: filas.append([P(esc(t.get(k, "")) or "—", small) for k in sv_k])
    else:
        filas.append([P("Sin tomas registradas", small)] + [P("—", small)] * 7)
    story.append(tabla(filas, [78] + [57] * 6 + [120], repeat=1))

    story.append(P("5. VALORACIÓN FÍSICA CÉFALO-CAUDAL", sec))
    story.append(tabla([
        [campo("Aspecto general / estado de conciencia", "Aspecto General", small), campo("Piel y mucosas", "Piel", small)],
        [campo("Cabeza y cuello", "Cabeza Cuello", small), campo("Tórax y cardiopulmonar", "Tórax", small)],
        [campo("Abdomen", "Abdomen", small), campo("Genitourinario", "Genitourinario", small)],
        [campo("Extremidades / neurovascular", "Extremidades", small), campo("Neurológico / sensorial", "Neurológico", small)],
        [campo("Dispositivos (vía IV, sondas, drenes, O2)", "Dispositivos", small, "Sin dispositivos"), campo("Heridas / lesiones", "Heridas", small, "Sin heridas")],
    ], [270, 270]))

    story.append(P("6. ESCALAS DE VALORACIÓN", sec))
    story.append(tabla([
        [campo("Glasgow (/15)", "Glasgow", small, "No aplica"), campo("Dolor EVA (0-10)", "EVA", small, "No aplica"), campo("Braden (riesgo de UPP)", "Braden", small, "No aplica")],
        [campo("Morse (riesgo de caídas)", "Morse", small, "No aplica"), campo("Barthel / Katz (dependencia)", "Barthel", small, "No aplica"), campo("Otra escala", "Otra Escala", small, "N/A")],
    ], [180, 180, 180]))
    story.append(Spacer(1, 3))
    story.append(P("<b>Valoración del dolor</b>", small))
    story.append(tabla([
        [campo("Ubicación / irradiación", "Dolor Ubicación", small, "No aplica"), campo("Tipo / carácter", "Dolor Tipo", small, "No aplica"), campo("Duración / frecuencia", "Dolor Duración", small, "No aplica")],
        [campo("Qué lo alivia", "Dolor Alivia", small, "No aplica"), campo("Qué lo empeora", "Dolor Empeora", small, "No aplica"), P("", small)],
    ], [180, 180, 180]))

    story.append(P("7. VALORACIÓN POR PATRONES FUNCIONALES (M. GORDON)", sec))
    filas = [[P("Patrón", th_style), P("Hallazgos", th_style), P("Funcional / Disfuncional", th_style)]]
    patrones = datos.get("Patrones", {}) or {}
    for p in PATRONES_GORDON:
        v = patrones.get(p, {})
        filas.append([P(esc(p), small), P(esc(v.get("hallazgos", "")) or SIN_REGISTRO, small), P(esc(v.get("estado", "")) or "—", small)])
    story.append(tabla(filas, [160, 280, 100], header_color=SECOND, repeat=1))

    story.append(P("8. DIAGNÓSTICOS MÉDICOS Y PROCESO DE ATENCIÓN DE ENFERMERÍA (PAE)", sec))
    story.append(tabla([
        [campo("Diagnóstico médico principal", "Diagnóstico Médico", defecto="No referido"), campo("Código CIE-10 / CIE-11", "Codigo CIE", defecto="N/A")],
        [P(f"<b>Diagnósticos secundarios / Comorbilidades:</b> {esc(valor('Diagnosticos Secundarios', 'Sin registros'))}"), P("", small)]
    ], [400, 140]))
    story.append(Spacer(1, 4))
    story.append(campo("Valoración / datos significativos PAE", "Datos Significativos"))
    story.append(Spacer(1, 3))
    if pae:
        filas = [[P(h, th_style) for h in ["Diagnóstico de enfermería (NANDA)", "Resultado (NOC)", "Intervenciones (NIC)", "Evaluación"]]]
        for it in pae:
            filas.append([P(esc(it.get("Diagnóstico", "")), small), P(esc(it.get("Resultado", "")), small), P(esc(it.get("Intervención", "")), small), P(esc(it.get("Evaluación", "")), small)])
        story.append(tabla(filas, [150, 120, 150, 120], header_color=SECOND, repeat=1))
    else:
        story.append(P("No se registraron diagnósticos de enfermería.", small))

    story.append(P("9. MEDICAMENTOS Y NOTAS DE ENFERMERÍA", sec))
    if medicamentos:
        filas_m = [[P(h, th_style) for h in ["Fecha / hora admin.", "Prog.", "Medicamento", "Dosis / Vía", "Prescriptor", "Responsable", "Obs."]]]
        for m in medicamentos:
            filas_m.append([P(esc(m.get("Fecha y Hora", "")), small), P(esc(m.get("Hora Programada", "")), small), P(esc(m.get("Medicamento", "")), small), P(f"{esc(m.get('Dosis',''))} - {esc(m.get('Vía',''))}", small), P(esc(m.get("Prescriptor", "")), small), P(esc(m.get("Responsable", "")), small), P(esc(m.get("Observación", "")), small)])
        story.append(tabla(filas_m, [72, 40, 95, 80, 85, 85, 83], header_color=SECOND, repeat=1))
    else:
        story.append(P("Sin registros de administración de medicamentos.", small))

    story.append(Spacer(1, 4))
    if notas:
        filas_n = [[P(h, th_style) for h in ["Fecha / Hora", "Nota de enfermería", "Responsable"]]]
        for n in notas:
            filas_n.append([P(esc(n.get("Fecha y Hora", "")), small), P(esc(n.get("Nota", "")), small), P(esc(n.get("Responsable", "")), small)])
        story.append(tabla(filas_n, [90, 330, 120], header_color=SECOND, repeat=1))
    else:
        story.append(P("Sin notas de enfermería registradas.", small))

    story.append(P("10. CONTROL DE LÍQUIDOS (INGRESOS Y EGRESOS)", sec))
    if liquidos:
        filas_l = [[P(h, th_style) for h in ["Fecha / Hora", "Tipo", "Concepto", "Cantidad (mL)", "Responsable"]]]
        for x in liquidos:
            filas_l.append([P(esc(x.get("Fecha y Hora", "")), small), P(esc(x.get("Tipo", "")), small), P(esc(x.get("Concepto", "")), small),
                            P(esc(x.get("Cantidad (mL)", "")), small), P(esc(x.get("Responsable", "")), small)])
        story.append(tabla(filas_l, [100, 70, 150, 80, 140], header_color=SECOND, repeat=1))
        ing = sum(int(x.get("Cantidad (mL)") or 0) for x in liquidos if x.get("Tipo") == "Ingreso")
        egr = sum(int(x.get("Cantidad (mL)") or 0) for x in liquidos if x.get("Tipo") == "Egreso")
        story.append(Spacer(1, 3))
        story.append(P(f"<b>Total ingresos:</b> {ing} mL &nbsp;&nbsp; <b>Total egresos:</b> {egr} mL &nbsp;&nbsp; <b>Balance:</b> {ing - egr:+} mL", body))
    else:
        story.append(P("Sin registros de control de líquidos.", small))

    story.append(P("11. EDUCACIÓN Y EGRESO", sec))
    story.append(campo("Educación brindada al usuario / familia", "Educación"))
    story.append(campo("Condición de salida / destino", "Condición Salida"))
    story.append(campo("Recomendaciones y signos de alarma explicados", "Recomendaciones"))

    # Firmas en la HC (usuario, auxiliar/estudiante y docente supervisor)
    story.append(Spacer(1, 10))
    def firmas_genericas(nombre_pac, doc_pac, nombre_enf, reg_enf, st=body):
        def img(b): return _imagen_ajustada(b, 120, 35) if b else P("", st)
        t = Table([
            [img(bytes_pac), img(bytes_enf), img(bytes_docente)],
            ["______________________________", "______________________________", "______________________________"],
            [P(f"<b>PACIENTE / USUARIO</b><br/>{esc(nombre_pac)}<br/>{esc(doc_pac)}", st),
             P(f"<b>AUXILIAR DE ENFERMERÍA / ESTUDIANTE</b><br/>{esc(nombre_enf)}<br/>{esc(reg_enf)}", st),
             P(f"<b>DOCENTE SUPERVISOR(A)</b><br/>{esc(valor('Docente Supervisor', ''))}<br/>Registro: {esc(valor('Registro Docente', ''))}", st)]
        ], colWidths=[180, 180, 180])
        t.setStyle(TableStyle([("ALIGN", (0, 0), (-1, -1), "CENTER"), ("VALIGN", (0, 0), (-1, -1), "BOTTOM")]))
        return t

    story.append(KeepTogether([firmas_genericas(valor("Paciente"), doc_pac, valor("Enfermero Tratante"), f"ReTHUS / código: {reg_prof}")]))

    # ============================ CONSENTIMIENTOS INFORMADOS (MODELO PDF EXACTO) ============================
    elegidos = datos.get("Consentimientos Seleccionados") or []
    
    def l(texto_val, ancho=25):
        """Si el dato existe lo retorna limpio y subrayado; si no, devuelve un guion bajo largo (raya)"""
        val = str(texto_val).strip() if texto_val else ""
        return f"<u>{html.escape(val)}</u>" if val else "_" * ancho

    if elegidos:
        for k in elegidos:
            if k in TEXTOS:
                story.append(PageBreak())
                
                # ENCABEZADO SUPERIOR TÍTULO CONSENTIMIENTO
                titulo_doc = CONSENTIMIENTOS.get(k, '').upper()
                hdr_cons = [
                    [logo(90, 38), "", P(titulo_doc, cons_t)],
                    ["", "", P(f"<b>{INSTITUCION}</b>", ParagraphStyle("SI", parent=cons_t, fontSize=9, alignment=2))]
                ]
                th_c = Table(hdr_cons, colWidths=[100, 20, 420])
                th_c.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("SPAN", (0, 0), (0, 1))]))
                story += [th_c, Spacer(1, 10)]

                # TABLA DEMOGRÁFICA IDÉNTICA AL PDF
                demo_data = [
                    [P(f"<b>Nombre del usuario:</b> {l(datos.get('Paciente'), 45)}", cons_b), P(f"<b>Edad:</b> {l(datos.get('Edad'), 8)} años", cons_b)],
                    [P(f"<b>Documento de identidad:</b> {l(doc_pac, 40)}", cons_b), P(f"<b>Fecha:</b> {l(datos.get('Fecha de Atención'), 20)}", cons_b)],
                    [P(f"<b>HC N°:</b> {l(datos.get('Historia Clínica N°'), 30)}", cons_b), P(f"<b>Institución:</b> {INSTITUCION}", cons_b)]
                ]
                t_demo = Table(demo_data, colWidths=[360, 180])
                t_demo.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("BOTTOMPADDING", (0, 0), (-1, -1), 3)]))
                story.append(t_demo)
                story.append(Spacer(1, 10))

                # CUERPO DEL TEXTO
                texto_base = TEXTOS[k]
                
                def safe_casilla(m):
                    clave, opcion = m.group(1), m.group(2)
                    v = datos.get(clave, "")
                    if isinstance(v, (list, tuple)): marcado = opcion in v
                    else: marcado = str(v) == opcion
                    return "[X]" if marcado else "[&nbsp;&nbsp;]"

                def safe_campo(m):
                    clave = m.group(1)
                    # Las variantes "_largo" / "_larga" solo indican una raya más larga;
                    # el dato real se guarda con la clave base (p. ej. "med", "canal").
                    clave_base = re.sub(r"_(largo|larga)$", "", clave)
                    v = datos.get(clave, "") or datos.get(clave_base, "")
                    if isinstance(v, (list, tuple)): v = ", ".join(map(str, v))
                    # Lógica para determinar la longitud del subrayado en blanco
                    ancho = 25
                    if "largo" in clave or "larga" in clave: ancho = 120
                    elif clave in ["notif_nombre", "dosis", "via", "lote"]: ancho = 15
                    return l(v, ancho)

                texto_lleno = re.sub(r"\{\{chk:(\w+):([^}]+)\}\}", safe_casilla, texto_base)
                texto_lleno = re.sub(r"\{\{(\w+)\}\}", safe_campo, texto_lleno)

                # Los textos ya traen sus <br/>; los saltos de línea del código fuente
                # solo se convierten en espacio para no duplicar el espaciado.
                texto_lleno = texto_lleno.replace('\n', ' ')

                story.append(P(texto_lleno, cons_b))

                obs_cons = str(datos.get(f"Obs {k}") or "").strip()
                if obs_cons:
                    story.append(Spacer(1, 6))
                    story.append(P(f"<b>Observaciones / detalles adicionales:</b> {esc(obs_cons)}", cons_b))
                story.append(Spacer(1, 15))

                # BLOQUE DE FIRMAS DEL CONSENTIMIENTO
                bloque_firmas = []
                bloque_firmas.append(P("Si el usuario es menor de edad, firma su representante legal. Si es una persona adulta con discapacidad, decide por sí misma y puede firmar con la persona de apoyo que haya designado (Ley 1996 de 2019).", cons_b))
                bloque_firmas.append(Spacer(1, 10))

                rep_data = [
                    [P(f"<b>Nombre:</b> {l(datos.get('Acompañante'), 45)}", cons_b),
                     P(f"<b>Parentesco / calidad:</b> {l(datos.get('Parentesco'), 25)}", cons_b),
                     P(f"<b>Doc.:</b> {l(datos.get('Doc Acompañante'), 25)}", cons_b)]
                ]
                bloque_firmas.append(Table(rep_data, colWidths=[230, 170, 140]))
                bloque_firmas.append(Spacer(1, 20))

                # Imágenes de Firmas y Líneas
                fila_img = [
                    _imagen_ajustada(bytes_pac, 120, 35) if bytes_pac else P("", cons_b),
                    _imagen_ajustada(bytes_enf, 120, 35) if bytes_enf else P("", cons_b),
                ]

                # Si es Disentimiento, agregamos Testigo
                if k == "disentimiento":
                    firmas_data = [
                        fila_img,
                        ["_____________________________________", "_____________________________________"],
                        [P("<b>Firma del usuario / representante</b>", cons_b), P("<b>Firma del Auxiliar de enfermería / Estudiante</b><br/>" + f"ReTHUS / código: {l(reg_prof, 20)}", cons_b)],
                        ["", ""],
                        [P(f"<b>Testigo: Nombre</b> {l('', 30)} <b>Doc.</b> {l('', 20)} <b>Firma</b> {l('', 30)}", cons_b), ""]
                    ]
                    t_firm = Table(firmas_data, colWidths=[270, 270])
                    t_firm.setStyle(TableStyle([("ALIGN", (0, 0), (-1, -1), "LEFT"), ("VALIGN", (0, 0), (-1, -1), "BOTTOM"),
                                                ("SPAN", (0, 4), (1, 4))]))
                else:
                    firmas_data = [
                        fila_img,
                        ["_____________________________________", "_____________________________________"],
                        [P("<b>Firma del usuario / representante</b>", cons_b), P("<b>Firma del Auxiliar de enfermería / Estudiante</b><br/>" + f"ReTHUS / código: {l(reg_prof, 20)}", cons_b)]
                    ]
                    t_firm = Table(firmas_data, colWidths=[270, 270])
                    t_firm.setStyle(TableStyle([("ALIGN", (0, 0), (-1, -1), "LEFT"), ("VALIGN", (0, 0), (-1, -1), "BOTTOM")]))

                bloque_firmas.append(t_firm)
                story.append(KeepTogether(bloque_firmas))

    canvas_class = _canvas_con_folios(f"HC N° {valor('Historia Clínica N°', '')} · Atención {valor('N° Atención', '')}")
    doc.build(story, canvasmaker=canvas_class)
    return buffer.getvalue()