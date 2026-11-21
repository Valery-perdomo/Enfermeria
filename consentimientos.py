"""
Textos de los consentimientos informados (modelos académicos).
"""
import html
import re

CONSENTIMIENTOS = {
    "general": "CONSENTIMIENTO INFORMADO GENERAL PARA ATENCIÓN DE ENFERMERÍA",
    "invasivos": "CONSENTIMIENTO INFORMADO PARA PROCEDIMIENTOS INVASIVOS DE ENFERMERÍA",
    "medicamentos": "CONSENTIMIENTO INFORMADO PARA ADMINISTRACIÓN DE MEDICAMENTOS Y VACUNAS",
    "datos": "AUTORIZACIÓN PARA TRATAMIENTO DE DATOS PERSONALES (LEY 1581 DE 2012)",
    "academico": "AUTORIZACIÓN PARA USO DE LA HISTORIA CLÍNICA, REGISTROS Y FOTOGRAFÍAS CON FINES ACADÉMICOS",
    "disentimiento": "DISENTIMIENTO (RECHAZO) INFORMADO DE PROCEDIMIENTO O TRATAMIENTO",
}

PROC_INVASIVOS = [
    "Venopunción / toma de muestras de sangre",
    "Canalización de vía venosa periférica",
    "Inyecciones (IM, SC, ID, IV)",
    "Sondaje vesical",
    "Sonda nasogástrica / orogástrica",
    "Curación de heridas / retiro de puntos",
    "Glucometría capilar",
    "Nebulización / aspiración de secreciones",
    "Otro (especificar)",
]

ACAD_OPCIONES = [
    "Acceso a mi historia clínica (cuidado y supervisión)",
    "Uso académico y de investigación (datos anonimizados)",
    "Fotografías o videos de la zona atendida",
]

CAMPOS = {
    "general": [],
    "invasivos": [
        ("proc", "Procedimientos que autoriza", "multi", PROC_INVASIVOS),
        ("proc_otro", "Si marcó 'Otro', ¿cuál?", "texto", None),
        ("info_clinica", "Alergias, anticoagulantes, embarazo u otras condiciones que informó el usuario", "texto", None),
    ],
    "medicamentos": [
        ("med", "Medicamento / vacuna", "texto", None),
        ("dosis", "Dosis", "texto", None),
        ("via", "Vía", "texto", None),
        ("lote", "Lote / fecha de vencimiento", "texto", None),
        ("alergias_med", "Alergias, embarazo/lactancia, reacciones previas informadas", "texto", None),
    ],
    "datos": [
        ("canal", "Canal para ejercer derechos (correo / teléfono / dirección)", "texto", None),
        ("autoriza", "¿El usuario autoriza el tratamiento de sus datos?", "opcion", ["SÍ", "NO"]),
    ],
    "academico": [
        ("acad", "Marque lo que el usuario autoriza", "multi", ACAD_OPCIONES),
        ("foto_extra", "Autorización adicional para fotos que muestren rasgos identificables (si aplica)", "texto", None),
    ],
    "disentimiento": [
        ("rechazo", "Procedimiento / recomendación rechazada", "texto", None),
        ("consecuencias", "Riesgos y consecuencias explicadas", "texto", None),
        ("motivo", "Motivo del rechazo (opcional)", "texto", None),
        ("notificado", "¿Se notificó al médico / docente responsable?", "opcion", ["Sí", "No"]),
        ("notif_nombre", "Nombre de quien fue notificado", "texto", None),
        ("notif_fecha", "Fecha y hora de la notificación", "texto", None),
    ],
}

# Campos que deben estar llenos para que cada consentimiento salga completo.
# (Los condicionales —"Otro", datos de notificación— se validan en app.py.)
OBLIGATORIOS = {
    "general": (),
    "invasivos": ("proc", "info_clinica"),
    "medicamentos": ("med", "dosis", "via", "lote", "alergias_med"),
    "datos": ("canal", "autoriza"),
    "academico": (),
    "disentimiento": ("rechazo", "consecuencias", "notificado"),
}

TEXTOS = {
    "general": """Apreciado(a) usuario(a): antes de recibir cuidado de enfermería usted tiene derecho a conocer en qué consiste la atención, sus beneficios, riesgos y alternativas, y a decidir libremente. Si tiene dudas, pregunte al profesional o estudiante tratante antes de firmar.<br/><br/>
<b>1. QUÉ ES LA ATENCIÓN DE ENFERMERÍA.</b> Es el cuidado integral que presta el profesional de enfermería o el estudiante en práctica, bajo supervisión docente, que incluye: valoración (entrevista, examen físico, signos vitales, medidas antropométricas), diagnóstico de enfermería, planeación, ejecución de cuidados, educación en salud y evaluación de resultados (Proceso de Atención de Enfermería).<br/><br/>
<b>2. OBJETIVOS Y BENEFICIOS.</b> Identificar necesidades de salud, promover el autocuidado, prevenir complicaciones, detectar signos de alarma y orientar la remisión oportuna cuando se requiera.<br/><br/>
<b>3. RIESGOS Y LIMITACIONES.</b> La valoración es no invasiva y de bajo riesgo; puede generar incomodidad leve o cansancio. La enfermería no reemplaza la valoración médica: si se detectan hallazgos que lo requieran, se le remitirá. La calidad del cuidado depende de que la información que usted suministre sea veraz y completa.<br/><br/>
<b>4. ALTERNATIVAS.</b> Usted puede rechazar total o parcialmente la atención y solicitar atención por otro profesional, sin que ello afecte su derecho a recibir servicios de salud.<br/><br/>
<b>5. PARTICIPACIÓN DE ESTUDIANTES.</b> Entiendo que la atención puede ser realizada por estudiantes de enfermería bajo supervisión de un docente o profesional con registro, y que puedo pedir que la atención la realice directamente el profesional.<br/><br/>
<b>6. CONFIDENCIALIDAD.</b> Mi historia clínica es un documento privado y reservado; solo puede ser conocida por terceros con mi autorización o en los casos previstos por la ley (Res. 1995 de 1999; Ley 911 de 2004).<br/><br/>
<b>7. REVOCATORIA.</b> Puedo retirar este consentimiento en cualquier momento, sin que ello afecte la atención futura.<br/><br/>
<b>Declaro que he leído (o me han leído) y comprendido esta información, que he podido hacer preguntas y que fueron respondidas. Autorizo de manera libre, voluntaria e informada la atención de enfermería descrita.</b>""",

    "invasivos": """Apreciado(a) usuario(a): por medio de este documento se le informa sobre procedimientos de enfermería que implican contacto con la piel, mucosas o fluidos corporales. Marque los procedimientos que autoriza:<br/><br/>
{{chk:proc:Venopunción / toma de muestras de sangre}} Venopunción / toma de muestras de sangre &nbsp;&nbsp; {{chk:proc:Canalización de vía venosa periférica}} Canalización de vía venosa periférica &nbsp;&nbsp; {{chk:proc:Inyecciones (IM, SC, ID, IV)}} Inyecciones (IM, SC, ID, IV)<br/>
{{chk:proc:Sondaje vesical}} Sondaje vesical &nbsp;&nbsp; {{chk:proc:Sonda nasogástrica / orogástrica}} Sonda nasogástrica / orogástrica &nbsp;&nbsp; {{chk:proc:Curación de heridas / retiro de puntos}} Curación de heridas / retiro de puntos<br/>
{{chk:proc:Glucometría capilar}} Glucometría capilar &nbsp;&nbsp; {{chk:proc:Nebulización / aspiración de secreciones}} Nebulización / aspiración de secreciones &nbsp;&nbsp; {{chk:proc:Otro (especificar)}} Otro: {{proc_otro}}<br/><br/>
<b>1. DESCRIPCIÓN.</b> Procedimientos realizados con técnica aséptica y material estéril o de un solo uso, previa explicación de la técnica, la posición y los cuidados posteriores.<br/><br/>
<b>2. BENEFICIOS.</b> Obtener diagnóstico oportuno, administrar tratamiento, mantener acceso para terapia, drenar, alimentar o proteger tejidos, según el procedimiento.<br/><br/>
<b>3. RIESGOS FRECUENTES.</b> Dolor o molestia local, hematoma o enrojecimiento, sangrado leve, flebitis o infiltración, infección local, reacción alérgica (látex, antisépticos, adhesivos), mareo o sensación de desmayo, y dificultad para lograr el procedimiento al primer intento. <b>Riesgos poco frecuentes:</b> lesión de nervio o vaso, perforación o trauma de tejidos (sondas), infección sistémica, broncoaspiración (sondas), entre otros.<br/><br/>
<b>4. RIESGOS DE NO REALIZARLO.</b> Retraso del diagnóstico o tratamiento, complicación de la herida o de la condición clínica.<br/><br/>
<b>5. ALTERNATIVAS.</b> Otros métodos o profesionales cuando existan; puede solicitar que el procedimiento lo realice el profesional con registro en lugar del estudiante.<br/><br/>
<b>6. INFORMACIÓN DEL USUARIO.</b> He informado antecedentes de alergias, enfermedades de la sangre, uso de anticoagulantes, embarazo y otras condiciones relevantes:<br/>{{info_clinica_larga}}<br/><br/>
<b>Declaro que me explicaron los procedimientos marcados, sus beneficios, riesgos y alternativas, que resolvieron mis dudas y autorizo su realización de forma libre y voluntaria. Entiendo que puedo revocar esta autorización antes o durante el procedimiento.</b>""",

    "medicamentos": """Apreciado(a) usuario(a): con este documento autorizo la administración de medicamentos y/o vacunas indicados por el profesional competente y aplicados por enfermería, bajo los 10 correctos (paciente, medicamento, dosis, vía, hora, registro, educación, alergias, respuesta y derecho a rechazar).<br/><br/>
<b>Medicamento / vacuna:</b> {{med_largo}} &nbsp; <b>Dosis:</b> {{dosis}} &nbsp; <b>Vía:</b> {{via}} &nbsp; <b>Lote / vence:</b> {{lote}}<br/><br/>
<b>1. BENEFICIOS.</b> Tratamiento o prevención de la enfermedad según indicación; en vacunas, protección individual y colectiva.<br/><br/>
<b>2. RIESGOS Y EFECTOS ESPERADOS.</b> Dolor, enrojecimiento o inflamación en el sitio de aplicación, fiebre leve, malestar general, somnolencia, náuseas u otros descritos para el medicamento. Poco frecuentes: reacción alérgica severa (anafilaxia), que requiere atención inmediata; por ello se recomienda permanecer en observación al menos 15-30 minutos tras la aplicación cuando aplique.<br/><br/>
<b>3. ALERGIAS Y ANTECEDENTES.</b> Declaro haber informado alergias a medicamentos, alimentos o látex, embarazo o lactancia, uso de otros medicamentos y reacciones previas:<br/>{{alergias_med_larga}}<br/><br/>
<b>4. SIGNOS DE ALARMA.</b> Dificultad para respirar, hinchazón de cara o garganta, ronchas generalizadas, mareo intenso, fiebre alta persistente o dolor intenso en el sitio: debo acudir de inmediato a urgencias.<br/><br/>
<b>5. ALTERNATIVAS Y RECHAZO.</b> Puedo no aceptar el medicamento o la vacuna y consultar con mi médico u otra alternativa terapéutica.<br/><br/>
<b>Declaro que recibí la información necesaria, pude preguntar y autorizo la administración de forma libre y voluntaria.</b>""",

    "datos": """<b>AUTORIZACIÓN PARA EL TRATAMIENTO DE DATOS PERSONALES Y DATOS SENSIBLES (Ley 1581 de 2012, Decreto 1074 de 2015 —que compila el Decreto 1377 de 2013— y normas concordantes).</b><br/><br/>
En calidad de titular, autorizo a ESCUELA DE SALUD SAN PEDRO CLAVER como responsable del tratamiento, para recolectar, almacenar, usar y custodiar mis datos personales y datos sensibles de salud (antecedentes, signos vitales, valoraciones, diagnósticos de enfermería, resultados y demás información de mi historia clínica) con las siguientes finalidades: (i) prestación y registro del cuidado de enfermería; (ii) seguimiento, remisión y continuidad de la atención; (iii) cumplimiento de obligaciones legales (Res. 1995 de 1999 y Res. 839 de 2017); (iv) gestión administrativa, calidad y auditoría; (v) fines estadísticos y académicos con datos anonimizados.<br/><br/>
<b>Derechos del titular:</b> conocer, actualizar y rectificar mis datos; solicitar prueba de la autorización; ser informado sobre el uso dado a mis datos; presentar quejas ante la Superintendencia de Industria y Comercio; revocar la autorización y/o solicitar la supresión cuando no exista deber legal o contractual de conservarlos; y acceder gratuitamente a mis datos. Entiendo que, por tratarse de datos sensibles, no estoy obligado(a) a autorizar su tratamiento ni a responder las preguntas que versen sobre ellos, pero que la historia clínica debe conservarse por un mínimo de 15 años contados desde la última atención (Res. 839 de 2017).<br/><br/>
<b>Canal para ejercer mis derechos:</b> {{canal_largo}} (correo / teléfono / dirección de la institución).<br/><br/>
Autorizo &nbsp; {{chk:autoriza:SÍ}} SÍ &nbsp; {{chk:autoriza:NO}} NO &nbsp; el tratamiento de mis datos en los términos anteriores.""",

    "academico": """La historia clínica es un documento privado, obligatorio y sometido a reserva. Teniendo en cuenta que la atención se presta en un entorno de formación, autorizo:<br/><br/>
{{chk:acad:Acceso a mi historia clínica (cuidado y supervisión)}} Que los estudiantes en práctica y docentes del programa de enfermería conozcan y registren la información de mi historia clínica para fines de cuidado y supervisión.<br/><br/>
{{chk:acad:Uso académico y de investigación (datos anonimizados)}} El uso de mi caso con fines académicos y de investigación (estudios de caso, PAE, socialización), con omisión de mi nombre, documento y datos que me identifiquen.<br/><br/>
{{chk:acad:Fotografías o videos de la zona atendida}} La toma de fotografías o videos de la zona atendida (p. ej., heridas) con fines clínicos y académicos, sin mostrar mi rostro ni rasgos identificables, salvo autorización expresa adicional:<br/>{{foto_extra_larga}}<br/><br/>
Entiendo que esta autorización es voluntaria, que no condiciona mi atención, que puedo revocarla en cualquier momento por escrito, y que el material será usado con reserva y confidencialidad.""",

    "disentimiento": """DISENTIMIENTO (RECHAZO) INFORMADO. Yo, el usuario o su representante, declaro que el profesional/estudiante de enfermería me explicó en lenguaje claro el procedimiento, cuidado o tratamiento propuesto:<br/><br/>
<b>Procedimiento / recomendación rechazada:</b> {{rechazo_largo}}<br/><br/>
También me informó sobre su finalidad, los beneficios esperados, y los riesgos y consecuencias de no realizarlo, que pueden incluir: empeoramiento de mi condición, complicaciones, discapacidad o, en casos graves, riesgo para la vida:<br/>{{consecuencias_larga}}<br/><br/>
Se me informaron las alternativas disponibles y que puedo cambiar de decisión en cualquier momento y solicitar el procedimiento después. Comprendo la información, tuve oportunidad de preguntar y decido de manera libre, consciente y voluntaria NO aceptarlo, asumiendo las consecuencias de mi decisión. Entiendo que esto no afecta mi derecho a recibir los demás servicios de salud.<br/><br/>
<b>Motivo del rechazo (opcional):</b> {{motivo_largo}}<br/><br/>
Se notificó al médico / docente responsable: &nbsp; {{chk:notificado:Sí}} Sí &nbsp; {{chk:notificado:No}} No &nbsp;&nbsp; Nombre: {{notif_nombre}} &nbsp;&nbsp; Fecha y hora: {{notif_fecha}}"""
}

def rellenar(clave, datos):
    return ""