import os
from docx import Document
from docx.shared import Pt, RGBColor, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

def add_heading(doc, text, level):
    h = doc.add_heading(text, level=level)
    run = h.runs[0]
    run.font.color.rgb = RGBColor(0, 0, 0)
    run.font.name = 'Arial'
    run.bold = True
    return h

def add_paragraph(doc, text, bold=False, italic=False):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    run = p.add_run(text)
    run.bold = bold
    run.italic = italic
    run.font.name = 'Arial'
    run.font.size = Pt(11)
    return p

def add_code_block(doc, text):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.LEFT
    run = p.add_run(text)
    run.font.name = 'Courier New'
    run.font.size = Pt(10)
    run.font.color.rgb = RGBColor(220, 220, 220)
    
    shading_elm = OxmlElement('w:shd')
    shading_elm.set(qn('w:fill'), '2E3440')
    p.runs[0]._element.get_or_add_rPr().append(shading_elm)

    p_pr = p._element.get_or_add_pPr()
    shading_p = OxmlElement('w:shd')
    shading_p.set(qn('w:fill'), '2E3440')
    p_pr.append(shading_p)
    return p

def add_table(doc, header, rows):
    table = doc.add_table(rows=1, cols=len(header))
    table.style = 'Table Grid'
    hdr_cells = table.rows[0].cells
    for i, h in enumerate(header):
        p = hdr_cells[i].paragraphs[0]
        run = p.add_run(h)
        run.bold = True
        run.font.name = 'Arial'
        run.font.size = Pt(10)
    
    for r in rows:
        row_cells = table.add_row().cells
        for i, val in enumerate(r):
            p = row_cells[i].paragraphs[0]
            run = p.add_run(str(val))
            run.font.name = 'Arial'
            run.font.size = Pt(10)
            
    doc.add_paragraph()
    return table

def add_image_inline(doc, image_path, caption):
    if os.path.exists(image_path):
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r = p.add_run()
        r.add_picture(image_path, width=Inches(6.0))
        
        caption_p = doc.add_paragraph()
        caption_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        c_run = caption_p.add_run(caption)
        c_run.italic = True
        c_run.font.size = Pt(9)
        c_run.font.name = 'Arial'
        doc.add_paragraph()
    else:
        print(f"ATENCIÓN: No se encontró la imagen {image_path}")
        add_paragraph(doc, f"[Marcador para imagen: {caption} - Colocar aquí cuando esté disponible]", italic=True)


document = Document()

# --- PORTADA ---
for _ in range(5):
    document.add_paragraph()

p_inst = document.add_paragraph()
p_inst.alignment = WD_ALIGN_PARAGRAPH.CENTER
run = p_inst.add_run("INSTITUCIÓN EDUCATIVA / UNIVERSIDAD\nFACULTAD DE INGENIERÍA\nPROGRAMA DE INGENIERÍA DE SISTEMAS\n\n\n\n")
run.bold = True
run.font.size = Pt(14)
run.font.name = 'Arial'

p_title = document.add_paragraph()
p_title.alignment = WD_ALIGN_PARAGRAPH.CENTER
run = p_title.add_run("MANUAL TÉCNICO DEL SISTEMA LOGICHECK\nSISTEMA DE VERIFICACIÓN DE DESPACHOS BASADO EN VISIÓN ARTIFICIAL\n\n\n\n")
run.bold = True
run.font.size = Pt(16)
run.font.name = 'Arial'

p_authors = document.add_paragraph()
p_authors.alignment = WD_ALIGN_PARAGRAPH.CENTER
run_authors = p_authors.add_run("MIGUEL ANGEL GONZALEZ POSADA\nSAMUEL ESTEBAN VILLALBA DURAN\n\n\n\n")
run_authors.bold = True
run_authors.font.size = Pt(12)
run_authors.font.name = 'Arial'

p_bottom = document.add_paragraph()
p_bottom.alignment = WD_ALIGN_PARAGRAPH.CENTER
run_bottom = p_bottom.add_run("DIRECTOR: [Nombre del Director]\n\n\n\nCIUDAD: [Ciudad]\nAÑO: 2026")
run_bottom.bold = True
run_bottom.font.size = Pt(12)
run_bottom.font.name = 'Arial'

document.add_page_break()

# --- TABLA DE CONTENIDO ---
add_heading(document, 'TABLA DE CONTENIDO', level=1)
add_paragraph(document, "PRESENTACIÓN\nRESUMEN EJECUTIVO\nFINALIDAD DEL MANUAL\nINTRODUCCIÓN\n\n1. REQUISITOS DEL SISTEMA\n   1.1 Requisitos de hardware\n   1.2 Requisitos de software\n   1.3 Configuraciones previas\n   1.4 Portabilidad y adaptabilidad\n   1.5 Contingencia\n\n2. DIAGRAMAS DE MODELAMIENTO\n\n3. ASPECTOS TÉCNICOS DEL DESARROLLO DEL SISTEMA\n   3.1 Arquitectura del sistema\n   a. Capa de presentación\n      i. Relación de directorios\n      ii. Mapa de navegación\n      iii. Archivos de configuración\n   b. Capa lógica (Inteligencia Artificial y Concurrencia)\n   c. Capa de base de datos\n      i. Diagrama entidad-relación\n      ii. Diccionario de datos\n\n4. INSTALACIÓN DEL SISTEMA Y SERVICIOS\n   4.1 Instalación del sistema\n   4.2 Instalación de servicios\n\n5. REQUERIMIENTOS DE HARDWARE (OPERACIÓN)\n\n6. BIBLIOGRAFÍA")
add_paragraph(document, "\n[Nota para edición: Reemplazar esta página usando la herramienta 'Tabla de Contenido Automática' de MS Word seleccionando las referencias de Título 1, Título 2].")

document.add_page_break()

# --- PRESENTACIÓN ---
add_heading(document, 'PRESENTACIÓN', level=1)
add_paragraph(document, "Este documento contextualiza la dimensión técnica del sistema LogiCheck. Hace referencia íntegra a los componentes, algoritmos y dependencias lógicas necesarias para la verificación de despachos logísticos mediante el análisis de cámaras RTSP e inteligencia artificial.")
add_paragraph(document, "El presente manual va dirigido rigurosamente a personal especializado en tecnologías de la información, abarcando perfiles tales como:\n- Ingenieros de Sistemas y Arquitectos de Software.\n- Desarrolladores especializados en librerías gráficas (Qt/PySide6) e Inteligencia Artificial.\n- Administradores de Bases de Datos SQLite.\n- Personal de Soporte Técnico enfocado en despliegues de hardware (GPU) y entornos Python.")
add_paragraph(document, "El nivel de conocimiento requerido para la manipulación e interpretación de este documento asume bases firmes en programación orientada a objetos, entendimiento avanzado sobre redes neuronales convolucionales, manejo de gestores de variables de entorno (Entornos Virtuales), y nociones de protocolos de video (RTSP/FFMPEG), así como conocimientos robustos de concurrencia e hilos.")
add_paragraph(document, "Visión General: LogiCheck opera estructurado bajo una Arquitectura Moderna en Capas y Patrón MVC acoplado a Componentes Modulares por Hilos. La plataforma desacopla la Capa de Visualización (Cliente - PySide6) de las capas de Procesamiento Profundo (Servicios de Inferencia Local) y la Base de Datos Relacional, posibilitando máxima fluidez de operación para el usuario final sin congelamientos de interfaz.")

# --- RESUMEN EJECUTIVO ---
add_heading(document, 'RESUMEN EJECUTIVO', level=1)
add_paragraph(document, "El principal propósito de este resumen es brindar a un lector técnico una comprensión expedita sobre qué es LogiCheck y cómo ha sido construido, prescindiendo inicialmente de recorrer el manual entero.")
add_paragraph(document, "Descripción Global y Objetivo: LogiCheck es una solución fiscal y de auditoría in situ. Su objetivo principal es resolver la pérdida de inventarios debida a despachos erróneos rastreando en tiempo real cajas, bultos y tuberías cargadas a vehículos mediante inferencia óptica paralela a gran escala.")
add_paragraph(document, "Tecnologías Utilizadas y Arquitectura: Operando bajo una arquitectura por capas modulares (Presentación, Negocio Algorítmico, y Persistencia Relacional). Todo interactúa usando el patrón de eventos asíncronos 'Signals & Slots' de Qt. Emplea Python 3 como lenguaje matriz, PySide6 (interfaz Front-end), SQLite3 (acceso relacional seguro), Ultralytics/PyTorch (núcleo YOLOv26 Tensorizado), y solicitudes HTTP Asíncronas (Notificaciones Push API).")
add_paragraph(document, "El manual consta de 6 capítulos primarios. El primero encuadra requerimientos de funcionamiento base; el segundo, la abstracción gráfica arquitectónica; el tercero expone entrañas técnicas, interfaces, Inteligencia artificial y esquemas de Base de datos forense. El cuarto indica al operario los procesos algorítmicos para instaurar el software paso a paso; el quinto determina topes físicos empresariales; y el finaliza listando fundamentos bibliográficos.")

# --- FINALIDAD DEL MANUAL ---
add_heading(document, 'FINALIDAD DEL MANUAL', level=1)
add_paragraph(document, "Este manual técnico ha sido confeccionado obedeciendo cuatro preceptos fundacionales:")
add_paragraph(document, "1. Capacitar minuciosamente al personal técnico en el despliegue del software mitigando la complejidad subyacente de la configuración de ecosistemas con tecnología CUDA de NVIDIA.")
add_paragraph(document, "2. Proveer documentación resolutiva para facilitar tareas de mantenimiento correctivo y predictivo frente a anomalías de hardware o inestabilidad de protocolos de transmisión IP.")
add_paragraph(document, "3. Constituir el marco de referencia formal, brindando bases sólidas en POO (Programación Orientada a Objetos) a equipos futuros que aborden necesidades de integración, escalamiento y modificaciones modulares de LogiCheck sin mermar la estabilidad preexistente del framerate en la IA.")
add_paragraph(document, "4. Documentar con celo académico, avalado por código fidedigno (esquemas de migración y directivas procedimentales reales), la culminación funcional y estructural del aplicativo.")

# --- INTRODUCCIÓN ---
add_heading(document, 'INTRODUCCIÓN', level=1)
add_paragraph(document, "El presente manual guiará al ingeniero inmerso en la plataforma LogiCheck a través de una documentación dividida coherentemente para revelar su comportamiento interno frente a condiciones comerciales arduas.")
add_paragraph(document, "En el Capítulo 1, el lector ubicará los requerimientos físicos y entornos de software necesarios. El Capítulo 2 presentará a través del modelamiento diagramado universal la interacción y el flujo operativo. En el Capítulo 3 se efectúa la deconstrucción o 'disección' técnica, inspeccionando flujos visuales, concurrencia analítica compleja y el mapa tabular de retención SQLite. En el Capítulo 4 el despliegue es dictado paso por paso de forma replicable y validado por evidencia de consola, para por último estipular las limitantes lógicas continuas en el Capítulo 5 cerrando con los aportes al conocimiento investigado en el Capítulo 6.")
add_paragraph(document, "El lector puede utilizar este registro progresivamente para un sondeo amplio de aprendizaje o referenciar específicamente las sub-secciones de 'Diccionario de Datos' y 'Archivos de Configuración' con fines estrictamente investigativos de arquitectura subyacente.")

document.add_page_break()

# --- CAPÍTULO 1: REQUISITOS DEL SISTEMA ---
add_heading(document, '1. REQUISITOS DEL SISTEMA', level=1)

add_heading(document, '1.1 Requisitos de hardware', level=2)
add_paragraph(document, "LogiCheck realiza un uso intensivo y determinístico en cálculos vectoriales masivos. Como tal, el hardware trasciende el plano básico y demanda un acople gráfico específico.")
add_paragraph(document, "- Procesador Mínimo: Intel Core i5 de 9.ª Generación o AMD Ryzen 5 equivalente. (Recomendado: Intel Core i7 12.ª Generación).")
add_paragraph(document, "- Memoria RAM Principal: Mínimo 8 GB DDR4. (Recomendado: 16 GB DDR4/DDR5 para estabilizar cachés transitorios de OpenCV).")
add_paragraph(document, "- Almacenamiento: Capacidad Mínima de 20 GB libres idealmente en un disco en formato NVMe SSD para maximizar los flujos de lectura en tensores PT.")
add_paragraph(document, "- Arquitectura: Exclusivo para plataformas OS de 64 bits (x86_64 o amd64). LogiCheck maneja video en alta definición e Inteligencia Artificial al mismo tiempo, lo cual consume mucha memoria y potencia. Por eso, no puede correr en computadoras viejas de 32 bits; son necesarios los 64 bits para gestionar el gran volumen de datos sin colapsar el sistema.")
add_paragraph(document, "- GPU (Requisito Indivisible): Tarjeta gráfica NVIDIA GTX 1650 con VRAM de 4 GB o superior para delegación de cómputo en CUDA Cores.")

add_heading(document, '1.2 Requisitos de software', level=2)
add_paragraph(document, "- Sistema operativo: Windows 10/11 Professional (Compilación de 64 bits con DirectX habilitado) o Distribuciones Linux certificadas por NVIDIA Drivers (Ej: Ubuntu 22.04).")
add_paragraph(document, "- Lenguajes de programación: Python 3.10 o versiones minor release subsiguientes (exige soporte Tipificación Robusta estricta).")
add_paragraph(document, "- Framework visual: PySide6 (Binding transicional nativo Qt for Python).")
add_paragraph(document, "- Motores de base de datos: SQLite3. Es un motor relacional integrado directamente en el programa que no necesita de un servidor externo o conexión a internet para funcionar (está libre de sockets locales). Al funcionar como un archivo independiente dentro de la computadora, garantiza que LogiCheck sea extremadamente rápido, fácil de instalar y que los datos de la ferretería estén siempre seguros y disponibles sin depender de servicios de terceros.")
add_paragraph(document, "- Librerías y Dependencias Críticas: El sistema utiliza un conjunto de herramientas especializadas que actúan como sus órganos vitales: OpenCV funciona como los \"ojos\" para procesar el video de las cámaras; Ultralytics (YOLO) es el \"cerebro\" encargado de la Inteligencia Artificial; PyMuPDF es el lector especializado que extrae datos de las facturas de Siigo; y Pandas es el organizador que gestiona grandes tablas de información. Sin estas librerías, LogiCheck no podría realizar el ciclo completo de ver, pensar y auditar los despachos.")

add_heading(document, '1.3 Configuraciones previas', level=2)
add_paragraph(document, "Variables de Entorno: Se deben pre-instalar los binarios CUDNN/CUDA Runtime a nivel del PATH del Sistema Operativo Windows, vinculados estrictamente según coincidan contra la instalación del módulo 'Torch' definido.")
add_paragraph(document, "Permisos/Red: Garantizar que la unidad del firewall admita tráfico saliente en Puerto TCP/UDP 554 para decodificación RTSP interna de las videocámaras IP y tráfico seguro HTTPS (Puerto 443) para el posteo de Notificaciones CallMeBot y Telegram.")

add_heading(document, '1.4 Portabilidad y adaptabilidad', level=2)
add_paragraph(document, "LogiCheck exhibe una elevada adaptabilidad producto de su aislamiento en un Virtual Environment (.venv). Funciona intrínsecamente igual sin requerir refactorizado, saltando de ambiente servidor hacia laptops locales. Resulta en una facilidad de actualización notable con solo emplear rutinas de `pip install --upgrade` dado el esquema abstracto.")

add_heading(document, '1.5 Contingencia', level=2)
add_paragraph(document, "El código fuente es provisto de rutinas robustas frente al estrangulamiento térmico de la gráfica (GPU OOM) forzando instrucciones como 'torch.cuda.empty_cache()' ante fallas previsoras. De mismo modo, las latencias o caídas de internet que desestabilicen el RTSP no causan un 'Crash Loop' gracias a la programación defensiva que inyecta el flag 'rtsp_transport;tcp' de FFMPEG induciendo silenciosamente una reinicialización de flujo del circuito de video que auto-recupera la imagen de auditoría sin obstruir la aplicación gráfica.")

document.add_page_break()

# --- CAPÍTULO 2: DIAGRAMAS DE MODELAMIENTO ---
add_heading(document, '2. DIAGRAMAS DE MODELAMIENTO', level=1)
add_paragraph(document, "Para abstraer la operativa empresarial de Ferretería Durán en consonancia algorítmica, se modela el comportamiento usando arquetipos de ingeniería altamente detallados:")

add_heading(document, 'Diagrama de Arquitectura Multihilo (Signals y QThread)', level=2)
add_paragraph(document, "El siguiente diagrama presenta la organización de concurrrencia y flujo modular del sistema. Evidencia tajantemente la separación de tareas (Separation of Concerns). El sistema PySide ejerce de hilo maestro escuchando pulsaciones e interfaz en la Capa de Presentación. Separado de este hilo maestro, reside el núcleo analítico de YoloV26 y OpenCV encapsulados en algoritmos paralelos que se conectan finalmente a la base de datos local SQLite.")

img_arch = r'C:\Users\samuv\.gemini\antigravity\brain\9fa41548-5a18-488d-9efb-c8c251ea2133\architecture_diagram_1776041839865.png'
add_image_inline(document, img_arch, "Figura 1: Diagrama de Arquitectura de Capas de LogiCheck (Presentación, Lógica y Datos).")

add_paragraph(document, "Propósito: Asegurar que el lector entienda que la aplicación no sufre bloqueos colaterales y separa el proceso UI y Negocio de manera formal y trazable.")

add_heading(document, 'Diagrama de Casos de Uso Sistemáticos', level=2)
add_paragraph(document, "Relación interactiva del aplicativo: El Usuario ('Administrador'/'Operador') interactúa en el caso de uso 'Iniciar Jornada' llamando a 'ui.login_dialog'. Seguidamente, el caso 'Aprobar Carga de Factura' inicializa el 'invoice_parser.py' de modo hermético, retornando las métricas leídas directamente hacia los objetos observables en 'main_window.py'.")

img_usecase = r'C:\Users\samuv\.gemini\antigravity\brain\9fa41548-5a18-488d-9efb-c8c251ea2133\use_case_diagram_1776042429419.png'
add_image_inline(document, img_usecase, "Figura 2: Diagrama de Casos de Uso - Interacción de Capas.")

document.add_page_break()

# --- CAPÍTULO 3: ASPECTOS TÉCNICOS ---
add_heading(document, '3. ASPECTOS TÉCNICOS DEL DESARROLLO DEL SISTEMA', level=1)

add_heading(document, '3.1 Arquitectura del sistema', level=2)
add_paragraph(document, "La solución implementada posee un diseño en capas con alta cohesión y bajo acoplamiento, distinguiendo drásticamente el espacio donde interfiere el usuario del perímetro analítico IA.")

add_heading(document, 'a. Capa de presentación', level=3)
add_paragraph(document, "Tecnologías utilizadas: Instanciada enteramente en entorno Python apoyada por PySide6 operando interfaces QWidgets tradicionales con estilos impulsados mediante Glassmorphism y la paleta de colores CSS/QSS Catppuccin. Esta capa gestiona las notificaciones on-screen, transiciones suaves (QPropertyAnimation) y alertas en Modal.")
add_paragraph(document, "Forma de interacción: Orientada a eventos. El despachador invoca análisis cruzado dando un click tras confirmar un número de remisión. Al presionar el botón de disparo algorítmico, los componentes de la interfaz restringen el click transitoriamente mitigando peticiones redundantes.")

add_heading(document, 'i. Relación de directorios', level=4)
add_paragraph(document, "Visualización de la distribución orientada al mantenimiento estructural de la aplicación en disco:\n")
add_code_block(document, 
"LogiCheck/\n"
"├── .venv/                 [Librerías compiladas locales]\n"
"├── assets/                [Iconos de la capa de presentación]\n"
"├── core/                  [Lógica profunda del aplicativo]\n"
"│   ├── db_migrations.py   [Migraciones y scripts de SQLite]\n"
"│   ├── invoice_parser.py  [Motor PDF Siigo con PyMuPDF]\n"
"│   └── yolo_manager.py    [IA con multihilo en QThread]\n"
"├── ui/                    [Vistas y Componentes GUI PySide6]\n"
"│   ├── main_window.py     [Renderizador central]\n"
"│   ├── splash_screen.py   [Vista de Carga de librerías CUDA]\n"
"│   └── login_dialog.py    [Formulario de Autenticación]\n"
"├── resources/\n"
"│   └── style.qss          [Hoja de Configuracion CSS Visual]\n"
"├── logicheck_users.db     [Archivo Físico de Base de Datos]\n"
"├── main.py                [Archivo Inicializador Maestro]\n"
"└── requirements.txt")

add_heading(document, 'ii. Mapa de navegación o estructura del sistema', level=4)
add_paragraph(document, "1. Pantalla Inicial (ui.login_dialog): Formulario aislado y modal demandando credenciales para protección RBAC.\n2. Splash Screen Dinámico (ui.splash_screen): Sirve como amortiguador para instanciar en RAM la carga pesada del modelo Pytorch sin pasmar agresivamente el Front-end.\n3. Main Window / Interfaz Maestra (ui.main_window): Donde coexisten sub-ventanas (Submenús integrados en Layouts y Widgets QStackedLayout). En este lienzo se transmiten las gráficas, tableros de registro fotográfico forense y despliegue del Grid principal de cámaras IP.")

# ----------------- UI SCREENSHOT INSERTION -----------------
add_paragraph(document, "Para ilustrar este lienzo interactivo, la siguiente captura real refleja la distribución del panel de control de LogiCheck ('Dashboard') durante una jornada de auditoría activa. Se exponen los Bounding Boxes de Inteligencia Artificial superpuestos en tiempo real al video y los paneles laterales con las comparativas simultáneas frente a la factura SIIGO:")

img_ui = r'C:\Users\samuv\Desktop\Programas_mios\LogiCheck\TESIS\Manual Tecnico\Dashboard real.png'
add_image_inline(document, img_ui, "Figura 3: Dashboard Real de LogiCheck - Monitorización en Tiempo Real con IA y UI Catppuccin.")
# -----------------------------------------------------------

add_heading(document, 'iii. Archivos de configuración', level=4)
add_paragraph(document, "- Nombre de Archivo: requirements.txt. Sujeta el versionamiento absoluto dependiente de los frameworks para lograr clonaciones idénticas de Python.\n- Nombre de Archivo: resources/style.qss. Retiene las variables genéricas de estilos (colores base de catppuccin, curvaturas px) asumiendo un papel análogo a un CSS global de arquitectura web, evitando la inyección dura de hojas de estilo (hardcoded) en cada código Python UI.")

add_heading(document, 'b. Capa Lógica y Visión Artificial', level=3)
add_paragraph(document, "El corazón intelectual del aplicativo. Cada píxel recuperado por OpenCV es matemáticamente normalizado de rango matricial int de 0 a 255 a notación fraccional continua [0,1], sufriendo además una mutación espacial (Letterbox Resize). Posteriormente se inyecta en el objeto Yolo de Ultralytics (yolo26). Resulta imprescindible la especificación técnica de la evaluación lógica:")
add_paragraph(document, "- Confidence Threshold = 0.20 (Asume predicciones por encima del veinte por ciento permitiendo operar con baja luminosidad o desenfoque en la bodega).")
add_paragraph(document, "- IoU Threshold = 0.5 (Intersect on Union, encargado de impedir sobre-conteos al ignorar cajas delimitadoras colindantes o encima de las mismas si se empalman). Con los datos ya asimilados en tensores CUDA, se envían directivas por Signal Event Loops liberando al 'Main Thread'.")

add_heading(document, 'c. Capa de base de datos', level=3)
add_paragraph(document, "Empleamos SQLite3. Optimizada debido a ser relacional, transaccional por lotes (Atomicity) y altamente portátil pues no exige correr como sub-proceso demonio en el host. La información cuenta con rigurosidad impidiendo corrupciones asíncronas de escritura.")

add_heading(document, 'i. Diagrama entidad–relación', level=4)
add_paragraph(document, "La entidad fuerte base 'usuarios' alberga los datos biográficos y permisos operacionales fijos. Esta distribuye una cardinalidad transversal delegándose en la tabla foránea 'auditorias', que asume las métricas de inspección en las remisiones cruzadas de SIIGO e IA. Si un usuario orquesta doce auditorías diurnas, existirá formalidad cardinal donde 1 id de empleado corresponde a N (1:N) despachos guardados por él mismo resguardado bajo clave foránea (Foreign Key referencial).")

img_erd = r'C:\Users\samuv\.gemini\antigravity\brain\9fa41548-5a18-488d-9efb-c8c251ea2133\erd_diagram_1776041853795.png'
add_image_inline(document, img_erd, "Figura 4: Diagrama Entidad-Relación entre Usuarios y las Auditorías Generadas.")

add_heading(document, 'ii. Diccionario de datos', level=4)
add_paragraph(document, "Estructura primaria forense recabada para mantenimiento de esquema:")

add_table(document, ['Campo de Tabla', 'Tipo Dato Primitivo', 'Restricciones / Integridad Foránea'], [
    ['[usuarios].id', 'INTEGER (PK)', 'PRIMARY KEY AUTOINCREMENT. Pilar de toda relación de llave ajena.'],
    ['[usuarios].username', 'TEXT', 'UNIQUE NOT NULL. Reclamo de ingreso irrepetible.'],
    ['[usuarios].password_hash', 'TEXT', 'NOT NULL. Cifrado unidireccional de la contraseña.'],
    ['[usuarios].password_salt', 'TEXT', 'NOT NULL. Entropía aleatoria para escudar hashes de diccionarios pre-computados.'],
    ['[usuarios].role', 'TEXT', 'NOT NULL. Nivel gerencial/técnico de RBAC.'],
    ['[auditorias].id', 'INTEGER (PK)', 'Identificador universal de registro remisional.'],
    ['[auditorias].user_id', 'INTEGER (FK)', 'FK (usuarios.id) ON DELETE SET NULL. Protege dependencias de usuario eliminado.'],
    ['[auditorias].fecha', 'TEXT/DATETIME', 'DEFAULT (datetime(\'now\')). Almacena instante del clic temporal exacto.'],
    ['[auditorias].factura_no', 'TEXT', 'DEFAULT. Número correlacional extraído por Invoice Parsing.'],
    ['[auditorias].resultado', 'TEXT', 'Condición Semántica dictada POST IA: Ej. CONFORME, DISCREPANCIA.']
])

add_paragraph(document, "Para impedir la impunidad documental a nivel de motor (Engine), aplicamos Triggers DDL inmutables que crean logs automáticos en 'auditorias_historico' ante modificaciones:")

add_code_block(document,
"CREATE TRIGGER IF NOT EXISTS trg_auditorias_update\n"
"AFTER UPDATE ON auditorias\n"
"BEGIN\n"
"    INSERT INTO auditorias_historico (auditoria_id, operacion, usuario_modificador, datos_anteriores, datos_nuevos)\n"
"    VALUES (NEW.id, 'UPDATE', NEW.username,\n"
"            'Resultado: ' || OLD.resultado || ', Vehículo: ' || OLD.vehiculo,\n"
"            'Resultado: ' || NEW.resultado || ', Vehículo: ' || NEW.vehiculo);\n"
"END;")

document.add_page_break()

# --- CAPÍTULO 4: INSTALACIÓN DEL SISTEMA ---
add_heading(document, '4. INSTALACIÓN DEL SISTEMA Y SERVICIOS', level=1)
add_heading(document, '4.1 Instalación del sistema (Paso a Paso)', level=2)
add_paragraph(document, "Para inyectar el sistema LogiCheck por primera vez de manera pulcra:")
add_paragraph(document, "1. Virtual Environment Setup (Requisito Previo): Utilizar la CLI o Windows Console dentro de la raíz clonada del proyecto y emitir la instancia virgen de Python.")
add_code_block(document,
"C:\\Users\\...> python -m venv .venv\n"
"C:\\Users\\...> .venv\\Scripts\\activate\n"
"(.venv) C:\\Users\\...>")

add_paragraph(document, "2. Descarga de Archivos de Repositorios Pypi: Al consolidar la máquina aislada (denotada por paréntesis en la consola CLI), mandar la cascada analítica con PIP:")
add_code_block(document,
"(.venv) C:\\Users\\...> pip install -r requirements.txt\n"
"Collecting PySide6==6.8.1 ...\n"
"[100%] Successfully installed opencv-python ultralytics pymupdf requests")

add_heading(document, '4.2 Instalación de servicios adicionales', level=2)
add_paragraph(document, "LogiCheck actúa bajo arquitectura 'Stand-alone' sin necesidad de correr contenedores adicionales a nivel de red debido a que la BD SQLite3 se ejecuta desde sus propias bibliotecas embebidas, omitiendo puertos DDL engorrosos de PostgreSQL/MySQL en máquinas cliente.")

# --- CAPÍTULO 5: REQUERIMIENTOS HARDWARE (OPERACIÓN) ---
add_heading(document, '5. REQUERIMIENTOS DE HARDWARE (OPERACIÓN)', level=1)
add_paragraph(document, "Para gozar de plena estabilidad algorítmica ininterrumpida de Lunes a Sábado en operación logística continua, el hardware mandatorio de operación establece límites y cotas obligatorias para CUDA.")
add_paragraph(document, "Hardware de Escalabilidad Básica: Como se listaba, la GTX 1650 con 4GB es el umbral para 2 a 4 cámaras RTSP simultáneas (Streams de 720p). En proyecciones de una Escalabilidad Robusta intentando alojar la malla completa admisible para LogiCheck de 16 Canales Simultáneos, las recomendaciones de hardware migran obligatoriamente a soluciones Enterprise GPUs (Ej. Serie NVIDIA RTX 3060 de 12GB VRAM o hardware de Grado Data Center Tesla T4) para asegurar que el pool de tensores PyTorch que mantienen un 'Thread' por canal y no sucumba a excepciones fatales del recolector de basura de la tarjeta gráfica (Memory Overflow).")

# --- CAPÍTULO 6: BIBLIOGRAFÍA ---
add_heading(document, '6. BIBLIOGRAFÍA', level=1)
add_paragraph(document, "[1] PySide6 Documentation. (2026). Qt for Python Reference Handbook.\n[2] Ultralytics, LLC. (2026). YOLO Framework, Convolutional Foundations, and Tracking Paradigms.\n[3] NVIDIA Corporation. (2026). CUDA Platform, Unified Memory Model and Tensor Parallelization Compute Arch.\n[4] SQLite Consortium. (2026). SQL As Understood By SQLite DB Engine and Relational Foreign Key Actions.")

output_path = r'C:\Users\samuv\Desktop\Programas_mios\LogiCheck\TESIS\Manual Tecnico\Manual_Tecnico_LogiCheck_vFinal_Full.docx'
os.makedirs(os.path.dirname(output_path), exist_ok=True)
document.save(output_path)
print(f"Manual Final con imagen real integrada guardado en: {output_path}")
