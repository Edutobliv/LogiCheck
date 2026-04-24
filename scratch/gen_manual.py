"""
Generador del Manual de Usuario Oficial de LogiCheck v1.0
Conforme a ICONTEC NTC 1486 — Estructura Instructiva 2026
"""

from docx import Document
from docx.shared import Inches, Pt, Cm, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.style import WD_STYLE_TYPE
from docx.oxml.ns import qn
import os

IMGS = r'C:\Users\samuv\Desktop\Programas_mios\LogiCheck\TESIS\Manual de Usuario\_imgs'
OUT  = r'C:\Users\samuv\Desktop\Programas_mios\LogiCheck\TESIS\Manual de Usuario\Manual_Usuario_LogiCheck_v1.docx'

doc = Document()

# ── Configurar estilos globales ──────────────────────────────
style = doc.styles['Normal']
font = style.font
font.name = 'Arial'
font.size = Pt(12)

style_h1 = doc.styles['Heading 1']
style_h1.font.size = Pt(16)
style_h1.font.bold = True
style_h1.font.color.rgb = RGBColor(0x1A, 0x1A, 0x2E)

style_h2 = doc.styles['Heading 2']
style_h2.font.size = Pt(14)
style_h2.font.bold = True
style_h2.font.color.rgb = RGBColor(0x2C, 0x2C, 0x4A)

style_h3 = doc.styles['Heading 3']
style_h3.font.size = Pt(12)
style_h3.font.bold = True
style_h3.font.color.rgb = RGBColor(0x3A, 0x3A, 0x5C)

fig_counter = [0]  # mutable counter for figures

def img(filename, caption=None, width=Inches(5.5)):
    """Inserta imagen con numeración de figura tipo ICONTEC."""
    path = os.path.join(IMGS, filename)
    if os.path.exists(path):
        doc.add_picture(path, width=width)
        last_paragraph = doc.paragraphs[-1]
        last_paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
        if caption:
            fig_counter[0] += 1
            cap = doc.add_paragraph()
            cap.alignment = WD_ALIGN_PARAGRAPH.CENTER
            run = cap.add_run(f'Figura {fig_counter[0]}. {caption}')
            run.italic = True
            run.font.size = Pt(10)
            run.font.color.rgb = RGBColor(0x55, 0x55, 0x55)
    else:
        doc.add_paragraph(f'[Imagen no encontrada: {filename}]')

def nota_seguridad(texto):
    """Inserta un recuadro de Nota de Seguridad."""
    p = doc.add_paragraph()
    run = p.add_run('⚠ Nota de Seguridad: ')
    run.bold = True
    run.font.size = Pt(11)
    run2 = p.add_run(texto)
    run2.font.size = Pt(11)
    # Sombreado mediante indentación
    pf = p.paragraph_format
    pf.left_indent = Cm(1)
    pf.right_indent = Cm(1)

def consejo(texto):
    """Inserta un consejo práctico."""
    p = doc.add_paragraph()
    run = p.add_run('💡 Consejo: ')
    run.bold = True
    run.font.size = Pt(11)
    run2 = p.add_run(texto)
    run2.font.size = Pt(11)
    pf = p.paragraph_format
    pf.left_indent = Cm(1)
    pf.right_indent = Cm(1)


# ╔══════════════════════════════════════════════════════════════╗
# ║                        PORTADA                              ║
# ╚══════════════════════════════════════════════════════════════╝

for _ in range(4):
    doc.add_paragraph()

p = doc.add_paragraph()
p.alignment = WD_ALIGN_PARAGRAPH.CENTER
run = p.add_run('CORPORACIÓN UNIVERSITARIA MINUTO DE DIOS')
run.font.size = Pt(14)
run.bold = True

p = doc.add_paragraph()
p.alignment = WD_ALIGN_PARAGRAPH.CENTER
run = p.add_run('Facultad de Ingeniería\nPrograma de Tecnología en Desarrollo de Software')
run.font.size = Pt(12)

doc.add_paragraph()
doc.add_paragraph()

p = doc.add_paragraph()
p.alignment = WD_ALIGN_PARAGRAPH.CENTER
run = p.add_run('MANUAL DE USUARIO DEL SISTEMA LOGICHECK')
run.font.size = Pt(16)
run.bold = True

doc.add_paragraph()

p = doc.add_paragraph()
p.alignment = WD_ALIGN_PARAGRAPH.CENTER
run = p.add_run('Sistema de Auditoría Logística con Visión Artificial\npara la Ferretería Durán')
run.font.size = Pt(12)
run.italic = True

for _ in range(4):
    doc.add_paragraph()

p = doc.add_paragraph()
p.alignment = WD_ALIGN_PARAGRAPH.CENTER
run = p.add_run('Samuel Vargas')
run.font.size = Pt(12)

doc.add_paragraph()

p = doc.add_paragraph()
p.alignment = WD_ALIGN_PARAGRAPH.CENTER
run = p.add_run('Docente: María Angélica Fajardo')
run.font.size = Pt(12)

for _ in range(3):
    doc.add_paragraph()

p = doc.add_paragraph()
p.alignment = WD_ALIGN_PARAGRAPH.CENTER
run = p.add_run('Girardot, Cundinamarca\n2025')
run.font.size = Pt(12)

doc.add_page_break()


# ╔══════════════════════════════════════════════════════════════╗
# ║                   TABLA DE CONTENIDO                        ║
# ╚══════════════════════════════════════════════════════════════╝

doc.add_heading('TABLA DE CONTENIDO', level=1)
doc.add_paragraph()

toc_entries = [
    ('1.', 'INTRODUCCIÓN'),
    ('2.', 'DESCRIPCIÓN GENERAL DEL SISTEMA'),
    ('3.', 'DESCRIPCIÓN DE LAS OPCIONES DEL MENÚ'),
    ('4.', 'DESCRIPCIÓN Y FUNCIONALIDAD DE LAS PANTALLAS DEL SISTEMA'),
    ('4.1.', 'Inicio de Sesión'),
    ('4.2.', 'Pantalla de Carga (Splash Screen)'),
    ('4.3.', 'Dashboard Principal'),
    ('4.4.', 'Carga de Factura PDF (Siigo)'),
    ('4.5.', 'Análisis de Video con IA'),
    ('4.6.', 'Cámara en Vivo'),
    ('4.7.', 'IA vs Factura (Conteo Cruzado)'),
    ('4.8.', 'Asignación Vehicular'),
    ('4.9.', 'Reportes'),
    ('4.10.', 'Registro de Actividad'),
    ('4.11.', 'Gestión de Usuarios'),
    ('4.12.', 'Configuración del Sistema'),
    ('5.', 'DESCRIPCIÓN DE LOS REPORTES DEL SISTEMA'),
    ('6.', 'INTERPRETACIÓN DE MENSAJES Y ERRORES'),
    ('7.', 'PROCEDIMIENTO A SEGUIR EN CASO DE FALLOS'),
    ('', 'GLOSARIO'),
]

for num, title in toc_entries:
    p = doc.add_paragraph()
    indent = Cm(1) if '.' in num and len(num) > 2 else Cm(0)
    p.paragraph_format.left_indent = indent
    run = p.add_run(f'{num} {title}')
    run.font.size = Pt(12)

doc.add_page_break()


# ╔══════════════════════════════════════════════════════════════╗
# ║                  1. INTRODUCCIÓN                            ║
# ╚══════════════════════════════════════════════════════════════╝

doc.add_heading('1. INTRODUCCIÓN', level=1)

doc.add_paragraph(
    'Un manual de usuario es un documento que acompaña a todo sistema de software y '
    'cumple una función esencial: servir de guía práctica para que cualquier persona, '
    'sin importar su nivel de experiencia técnica, pueda operar el sistema de manera '
    'autónoma y sin contratiempos. En el contexto de la Ferretería Durán, donde el ritmo '
    'de trabajo exige rapidez y precisión, contar con un manual claro marca la diferencia '
    'entre un despacho correcto y uno con pérdidas por errores humanos.'
)

doc.add_paragraph(
    'El presente documento constituye el Manual de Usuario oficial de LogiCheck, '
    'el sistema de auditoría logística con visión artificial diseñado para verificar '
    'automáticamente los despachos de materiales de construcción. A lo largo de estas '
    'páginas, usted encontrará instrucciones detalladas para cada pantalla y función '
    'del sistema, acompañadas de capturas reales de la interfaz que facilitan la '
    'comprensión visual de cada paso.'
)

doc.add_heading('Alcance del manual', level=2)

doc.add_paragraph(
    'Este manual cubre todas las operaciones que un usuario puede realizar dentro de '
    'LogiCheck, desde el ingreso al sistema hasta la generación de reportes. No aborda '
    'aspectos de instalación, configuración de hardware ni mantenimiento del servidor; '
    'para esos temas, consulte el Manual Técnico.'
)

doc.add_heading('Público al que está dirigido', level=2)

doc.add_paragraph(
    'Este manual está pensado para tres tipos de usuario dentro de la ferretería:'
)

table = doc.add_table(rows=4, cols=3)
table.style = 'Light Shading Accent 1'
table.alignment = WD_TABLE_ALIGNMENT.CENTER

hdr = table.rows[0].cells
hdr[0].text = 'Rol'
hdr[1].text = 'Descripción'
hdr[2].text = 'Secciones relevantes'

data = [
    ('Administrador', 'Control total del sistema. Gestiona usuarios, configura cámaras y supervisa el funcionamiento general.', 'Todas las secciones'),
    ('Operador de Factura', 'Encargado de cargar las facturas PDF de Siigo y verificar que los materiales coincidan con lo despachado.', 'Secciones 4.3 a 4.9'),
    ('Operador de Video', 'Monitorea las cámaras en vivo y analiza los videos de descarga para validar el conteo con IA.', 'Secciones 4.5, 4.6, 4.7'),
]

for i, (rol, desc, secciones) in enumerate(data):
    row = table.rows[i+1].cells
    row[0].text = rol
    row[1].text = desc
    row[2].text = secciones

doc.add_paragraph()
doc.add_paragraph(
    'A lo largo del manual encontrará recuadros de Nota de Seguridad donde se incluyen '
    'advertencias relevantes, y Consejos que le ayudarán a sacar el máximo provecho de '
    'cada funcionalidad.'
)

doc.add_page_break()


# ╔══════════════════════════════════════════════════════════════╗
# ║          2. DESCRIPCIÓN GENERAL DEL SISTEMA                 ║
# ╚══════════════════════════════════════════════════════════════╝

doc.add_heading('2. DESCRIPCIÓN GENERAL DEL SISTEMA', level=1)

doc.add_paragraph(
    'LogiCheck es un sistema de escritorio desarrollado en Python que combina inteligencia '
    'artificial con procesamiento de documentos para auditar los despachos de materiales '
    'de construcción en la Ferretería Durán, ubicada en Apulo, Cundinamarca.'
)

doc.add_heading('Problema que resuelve', level=2)

doc.add_paragraph(
    'En una jornada típica de la ferretería, los despachadores cargan manualmente bultos '
    'de cemento y tuberías a los vehículos de transporte. Este proceso es propenso a '
    'errores: un bulto de más o de menos puede significar pérdidas económicas, reclamos '
    'de clientes y problemas de inventario. Antes de LogiCheck, la verificación dependía '
    'exclusivamente de la atención del trabajador, lo que resultaba impreciso cuando el '
    'volumen de despachos era alto.'
)

doc.add_heading('¿Cómo funciona LogiCheck?', level=2)

doc.add_paragraph('El sistema trabaja en cuatro pasos fundamentales:')

steps = [
    ('Carga de factura:', 'el operador sube la factura electrónica de Siigo en formato PDF. LogiCheck extrae automáticamente los materiales y cantidades relevantes.'),
    ('Análisis con IA:', 'mediante un motor de visión artificial llamado YOLO, el sistema analiza el video de descarga o la transmisión en vivo de las cámaras, detectando y contando cada material.'),
    ('Comparación cruzada:', 'LogiCheck confronta lo que dice la factura con lo que la cámara observó realmente, generando un veredicto de conformidad o discrepancia.'),
    ('Generación de reportes:', 'toda la información queda registrada y puede exportarse en PDF o Excel para trazabilidad y auditoría.'),
]

for i, (titulo, desc) in enumerate(steps, 1):
    p = doc.add_paragraph()
    run = p.add_run(f'{i}. {titulo} ')
    run.bold = True
    p.add_run(desc)

doc.add_paragraph()

doc.add_heading('Materiales detectados', level=2)

doc.add_paragraph(
    'Actualmente, el motor de inteligencia artificial de LogiCheck está entrenado para '
    'reconocer tres tipos de materiales:'
)

materiales = [
    ('Bultos de cemento gris', 'El material más frecuente en los despachos de la ferretería.'),
    ('Tubería de presión (PVC)', 'Utilizada en sistemas de agua potable, identificada por su color azul característico.'),
    ('Tubería sanitaria (PVC)', 'Empleada en desagües y alcantarillado, generalmente de color crema o blanco.'),
]

for nombre, desc in materiales:
    p = doc.add_paragraph()
    run = p.add_run(f'• {nombre}: ')
    run.bold = True
    p.add_run(desc)

doc.add_paragraph()

doc.add_heading('Tipo de sistema', level=2)

doc.add_paragraph(
    'LogiCheck es una aplicación de escritorio que se ejecuta directamente en el computador '
    'de la ferretería. No requiere navegador web ni conexión permanente a internet (salvo '
    'para las notificaciones por Telegram y WhatsApp). La interfaz gráfica fue construida '
    'con PySide6 y ofrece un diseño moderno con modo oscuro y modo claro.'
)

doc.add_page_break()


# ╔══════════════════════════════════════════════════════════════╗
# ║         3. DESCRIPCIÓN DE LAS OPCIONES DEL MENÚ            ║
# ╚══════════════════════════════════════════════════════════════╝

doc.add_heading('3. DESCRIPCIÓN DE LAS OPCIONES DEL MENÚ', level=1)

doc.add_paragraph(
    'La navegación de LogiCheck se organiza mediante un panel lateral (sidebar) ubicado '
    'al costado izquierdo de la pantalla. Cada opción del menú lleva a una sección '
    'específica del sistema. A continuación, se describe brevemente el propósito de cada una:'
)

menu_items = [
    ('📊 Dashboard', 'Primera pantalla que se muestra al iniciar sesión. Presenta un resumen ejecutivo con las estadísticas del día: cantidad de despachos auditados, discrepancias detectadas, precisión del conteo y vehículos asignados. También incluye una gráfica de tendencias de los últimos 30 días.', 'Todos los roles'),
    ('📄 Factura PDF', 'Permite cargar y analizar las facturas electrónicas emitidas por Siigo. Al subir un archivo PDF, el sistema extrae automáticamente los productos relevantes (cemento y tuberías) junto con sus cantidades.', 'Administrador, Operador de Factura'),
    ('📹 Análisis de Video', 'Aquí se cargan los archivos de video grabados por las cámaras de seguridad. El motor de IA procesa cada fotograma, detecta los materiales y genera un conteo detallado. Incluye controles de reproducción similares a los de un reproductor multimedia.', 'Administrador, Operador de Video'),
    ('📷 Cámara en Vivo', 'Conecta directamente a las cámaras IP de la ferretería a través del protocolo RTSP. Permite monitorear en tiempo real el proceso de carga con detección activa de materiales. Soporta el modo de triangulación con dos cámaras simultáneas.', 'Administrador, Operador de Video'),
    ('🚛 Asignación Vehicular', 'Calcula automáticamente el vehículo más adecuado para transportar los materiales del despacho actual, basándose en el peso y el volumen total. Muestra la flota disponible con sus capacidades.', 'Administrador, Operador de Video, Gerente'),
    ('📋 Reportes', 'Centraliza el historial de todas las auditorías realizadas. Permite exportar reportes en formato PDF o Excel, y consultar las capturas de evidencia visual tomadas durante los análisis.', 'Todos los roles'),
    ('📜 Actividad', 'Registro cronológico (bitácora) de todas las acciones realizadas en el sistema: inicios de sesión, facturas cargadas, videos analizados, cambios de configuración, entre otros. Funciona como un sistema de trazabilidad.', 'Todos los roles'),
    ('👥 Gestión de Usuarios', 'Permite crear, editar, desactivar y asignar permisos a las cuentas de usuario. Incluye la posibilidad de clonar permisos entre usuarios y cambiar contraseñas.', 'Solo Administrador'),
    ('⚙️ Configuración', 'Parámetros avanzados del sistema: credenciales de cámaras, configuración de Telegram, umbrales de confianza del modelo de IA y otras opciones técnicas.', 'Solo Administrador'),
]

for icono_nombre, desc, acceso in menu_items:
    doc.add_heading(icono_nombre, level=3)
    doc.add_paragraph(desc)
    p = doc.add_paragraph()
    run = p.add_run(f'Acceso: ')
    run.bold = True
    run.font.size = Pt(11)
    run2 = p.add_run(acceso)
    run2.font.size = Pt(11)
    run2.italic = True

doc.add_page_break()


# ╔══════════════════════════════════════════════════════════════╗
# ║    4. DESCRIPCIÓN Y FUNCIONALIDAD DE LAS PANTALLAS         ║
# ╚══════════════════════════════════════════════════════════════╝

doc.add_heading('4. DESCRIPCIÓN Y FUNCIONALIDAD DE LAS PANTALLAS DEL SISTEMA', level=1)

doc.add_paragraph(
    'Esta sección constituye la parte central del manual. A continuación se describe, '
    'pantalla por pantalla, cada elemento de la interfaz de LogiCheck, acompañado de '
    'capturas reales del sistema y explicaciones paso a paso.'
)

# ── 4.1 Login ──────────────────────────────────────────────────
doc.add_heading('4.1. Inicio de Sesión', level=2)

doc.add_paragraph(
    'Al ejecutar LogiCheck, lo primero que aparece es la ventana de inicio de sesión. '
    'Esta pantalla solicita las credenciales del usuario para verificar su identidad '
    'antes de conceder acceso al sistema.'
)

img('img_12.png', 'Pantalla de inicio de sesión de LogiCheck')

doc.add_paragraph('La pantalla de inicio de sesión cuenta con los siguientes elementos:')

login_fields = [
    ('Campo "Usuario":', 'ingrese aquí el nombre de usuario asignado por el administrador (por ejemplo: admin, samuel, etc.). No distingue mayúsculas de minúsculas.'),
    ('Campo "Contraseña":', 'escriba su contraseña. Los caracteres se mostrarán como puntos (••••) por seguridad. Si desea verificar lo que escribió, presione el botón del ojo (👁) ubicado a la derecha del campo.'),
    ('Botón "Ingresar al Sistema":', 'una vez completados ambos campos, presione este botón o pulse la tecla Enter para iniciar el proceso de verificación.'),
    ('Botón de cierre (✕):', 'cierra la aplicación completa sin iniciar sesión.'),
]

for titulo, desc in login_fields:
    p = doc.add_paragraph()
    run = p.add_run(f'• {titulo} ')
    run.bold = True
    p.add_run(desc)

doc.add_paragraph()
doc.add_paragraph(
    'Si las credenciales son correctas, el sistema mostrará brevemente el texto '
    '"Verificando..." y luego pasará a la pantalla de carga. Si son incorrectas, '
    'aparecerá un mensaje en color rosado indicando "Usuario o contraseña incorrectos" '
    'y la tarjeta se agitará ligeramente para alertar visualmente del error.'
)

nota_seguridad(
    'Los intentos fallidos de inicio de sesión quedan registrados en la bitácora del '
    'sistema. Si olvidó su contraseña, contacte directamente al administrador para que '
    'la restablezca desde el panel de Gestión de Usuarios.'
)

# ── 4.2 Splash Screen ─────────────────────────────────────────
doc.add_heading('4.2. Pantalla de Carga (Splash Screen)', level=2)

doc.add_paragraph(
    'Una vez verificadas las credenciales, aparece la pantalla de carga. Esta pantalla '
    'no requiere ninguna acción del usuario; simplemente muestra el progreso de '
    'inicialización del sistema mientras prepara los módulos internos.'
)

img('img_06.png', 'Pantalla de carga con barra de progreso animada')

doc.add_paragraph('Durante la carga, el sistema realiza las siguientes operaciones en segundo plano:')

load_steps = [
    'Inicialización y verificación de la base de datos.',
    'Carga del módulo de auditoría y registro de actividad.',
    'Aplicación de los permisos según el rol del usuario.',
    'Preparación del motor de inteligencia artificial (si el rol tiene acceso a las funciones de video).',
    'Calentamiento del motor de IA para optimizar la velocidad de respuesta.',
]

for step in load_steps:
    doc.add_paragraph(step, style='List Bullet')

doc.add_paragraph()
doc.add_paragraph(
    'La barra de progreso avanza gradualmente con una animación colorida. Cuando '
    'alcanza el 100%, la pantalla se desvanece y el Dashboard principal aparece '
    'automáticamente.'
)

consejo(
    'Si observa que la barra de progreso se detiene prolongadamente cerca del 80%, '
    'significa que el motor de IA está cargando los modelos de detección. Este proceso '
    'es normal la primera vez y puede tomar entre 10 y 30 segundos dependiendo del '
    'equipo.'
)

doc.add_page_break()

# ── 4.3 Dashboard ─────────────────────────────────────────────
doc.add_heading('4.3. Dashboard Principal', level=2)

doc.add_paragraph(
    'El Dashboard es el centro de comando de LogiCheck. Al ingresar al sistema, esta '
    'es la primera pantalla que verá. Su función es brindar un panorama general y '
    'actualizado de la operación del día.'
)

img('img_01.png', 'Vista general del Dashboard de LogiCheck')

doc.add_paragraph(
    'Como se aprecia en la captura, el Dashboard se organiza en varias secciones. '
    'En la parte superior encontrará un saludo personalizado con su nombre, seguido '
    'de tres botones de acceso rápido que le permiten saltar directamente a las '
    'funciones más usadas del sistema:'
)

img('img_19.png', 'Botones de acceso rápido y estadísticas del día')

quick_btns = [
    ('Analizar Video:', 'lleva directamente a la sección de análisis de video con IA.'),
    ('Cargar Factura:', 'abre la sección de carga de facturas PDF.'),
    ('Cámara en Vivo:', 'conecta con el módulo de monitoreo en tiempo real.'),
]

for titulo, desc in quick_btns:
    p = doc.add_paragraph()
    run = p.add_run(f'• {titulo} ')
    run.bold = True
    p.add_run(desc)

doc.add_paragraph()
doc.add_paragraph(
    'Justo debajo se encuentran las tarjetas de estadísticas, que muestran cifras clave '
    'del día en curso con animaciones numéricas al cargar:'
)

stats = [
    ('Despachos Auditados:', 'número total de despachos procesados hoy.'),
    ('Discrepancias Detectadas:', 'cantidad de casos donde el conteo de la IA no coincidió con la factura.'),
    ('Precisión del Conteo:', 'porcentaje de aciertos del sistema.'),
    ('Vehículos Asignados:', 'número de asignaciones vehiculares realizadas.'),
]

for titulo, desc in stats:
    p = doc.add_paragraph()
    run = p.add_run(f'• {titulo} ')
    run.bold = True
    p.add_run(desc)

doc.add_paragraph()
doc.add_paragraph(
    'En la parte inferior del Dashboard se ubica la gráfica de tendencias, que ilustra '
    'la evolución de los despachos y las discrepancias durante los últimos 30 días. '
    'A la derecha, una tabla muestra las auditorías más recientes con su estado '
    '(Conforme o Discrepancia).'
)

doc.add_paragraph(
    'Adicionalmente, encontrará tres tarjetas informativas en la franja inferior: '
    'el estado del Motor de IA (indicando si está activo y en qué dispositivo opera), '
    'el estado del sistema (memoria de la GPU y base de datos), y una línea de tiempo '
    'con las últimas acciones registradas.'
)

doc.add_page_break()

# ── 4.4 Factura PDF ───────────────────────────────────────────
doc.add_heading('4.4. Carga de Factura PDF (Siigo)', level=2)

doc.add_paragraph(
    'Esta sección permite cargar las facturas electrónicas firmadas digitalmente que '
    'emite la Ferretería Durán a través del sistema contable Siigo. LogiCheck lee el '
    'contenido del PDF y clasifica automáticamente los productos en las categorías '
    'que el motor de IA puede reconocer.'
)

doc.add_paragraph('El procedimiento para cargar una factura es el siguiente:')

invoice_steps = [
    'En el menú lateral, presione "📄 Factura PDF".',
    'Haga clic en el botón azul "Seleccionar Archivo PDF".',
    'En el explorador de archivos que se abre, localice y seleccione la factura deseada.',
    'El sistema procesa el PDF en unos segundos y extrae la información relevante.',
]

for i, step in enumerate(invoice_steps, 1):
    p = doc.add_paragraph()
    run = p.add_run(f'Paso {i}. ')
    run.bold = True
    p.add_run(step)

doc.add_paragraph()

img('img_17.png', 'Pantalla de carga de factura antes de seleccionar un archivo')

doc.add_paragraph(
    'Una vez cargada la factura, la pantalla se actualiza para mostrar los datos extraídos. '
    'Observe en la siguiente captura cómo aparece el cuadro de diálogo del sistema '
    'operativo al hacer clic en "Seleccionar Archivo PDF":'
)

img('img_13.png', 'Explorador de archivos solicitando la selección del PDF')

doc.add_paragraph(
    'Tras seleccionar el archivo, LogiCheck muestra la información general de la factura '
    'en la tarjeta "Información de la Factura". Podrá verificar:'
)

invoice_fields = [
    ('Número de factura:', 'código único asignado por Siigo.'),
    ('Fecha de expedición:', 'cuándo fue emitida la factura.'),
    ('Cliente:', 'nombre de la persona o empresa que realizó la compra.'),
    ('Total a pagar:', 'valor monetario total de la factura.'),
    ('Productos YOLO:', 'cantidad de ítems que el motor de IA puede verificar visualmente.'),
    ('Total ítems factura:', 'cantidad total de productos en la factura (incluyendo los que la IA no detecta, como pintura, tornillos, etc.).'),
]

for titulo, desc in invoice_fields:
    p = doc.add_paragraph()
    run = p.add_run(f'• {titulo} ')
    run.bold = True
    p.add_run(desc)

doc.add_paragraph()

img('img_07.png', 'Información extraída de la factura con los datos de facturación')

doc.add_paragraph(
    'Debajo de esta tarjeta se encuentra la tabla de "Productos para Detección YOLO". '
    'En ella se listan únicamente los materiales que LogiCheck sabe reconocer (cemento, '
    'tubería de presión y tubería sanitaria), junto con la descripción original que '
    'aparece en la factura, la cantidad facturada y su valor:'
)

img('img_02.png', 'Tabla de productos detectables por IA extraídos de la factura')

doc.add_paragraph(
    'Con esta información, LogiCheck ya sabe cuántos materiales esperar en el video. '
    'Estos datos se utilizarán más adelante en el proceso de conteo cruzado para '
    'determinar si lo despachado coincide con lo facturado.'
)

nota_seguridad(
    'Asegúrese de cargar la factura antes de iniciar el análisis de video. Si analiza '
    'un video sin factura, el sistema emitirá alertas de seguridad asumiendo que se '
    'está moviendo material sin autorización.'
)

doc.add_page_break()

# ── 4.5 Análisis de Video ─────────────────────────────────────
doc.add_heading('4.5. Análisis de Video con Inteligencia Artificial', level=2)

doc.add_paragraph(
    'Esta es una de las funciones centrales de LogiCheck. Aquí el sistema procesa '
    'archivos de video grabados por las cámaras de seguridad, detectando y contando '
    'cada material que aparezca en la grabación.'
)

doc.add_paragraph('Para realizar un análisis de video, siga estos pasos:')

video_steps = [
    'Navegue a "📹 Análisis de Video" desde el menú lateral.',
    'Presione el botón "Cargar Video" y seleccione el archivo de video desde la USB o la carpeta de grabaciones.',
    'Una vez cargado, presione "Iniciar Análisis YOLO" para que la IA comience a procesar fotograma por fotograma.',
    'Observe en tiempo real cómo el sistema identifica y encierra cada material detectado dentro de un recuadro verde.',
    'Al finalizar el análisis, revise la tabla de conteo en el panel derecho.',
]

for i, step in enumerate(video_steps, 1):
    p = doc.add_paragraph()
    run = p.add_run(f'Paso {i}. ')
    run.bold = True
    p.add_run(step)

doc.add_paragraph()

img('img_20.png', 'Pantalla de análisis de video con detecciones activas')

doc.add_heading('Los recuadros verdes (Bounding Boxes)', level=3)

doc.add_paragraph(
    'Cuando el motor de IA identifica un material en el video, lo encierra dentro de un '
    'recuadro verde, también llamado "bounding box". Este recuadro cumple dos funciones:'
)

bbox_funcs = [
    'Marca visualmente la posición exacta del objeto en la imagen, permitiendo al operador confirmar visualmente que la detección es correcta.',
    'Genera datos internos que alimentan el conteo automático del sistema.',
]

for func in bbox_funcs:
    doc.add_paragraph(func, style='List Bullet')

doc.add_paragraph()

img('img_15.png', 'Ejemplo de detección con recuadros verdes sobre los materiales')

doc.add_paragraph(
    'En la esquina superior de cada recuadro aparece una etiqueta que indica el tipo '
    'de material detectado (por ejemplo: "Cemento" o "Tubería") y un porcentaje de '
    'confianza. Cuanto más alto sea este porcentaje, mayor es la certeza del sistema '
    'sobre la identificación.'
)

doc.add_heading('Controles de reproducción', level=3)

doc.add_paragraph(
    'La interfaz de análisis de video cuenta con controles similares a los de un '
    'reproductor multimedia convencional:'
)

controles = [
    ('▶ (Reproducir/Pausar):', 'inicia o pausa la reproducción. También se activa con la barra espaciadora.'),
    ('⏪ 10s / ⏩ 10s:', 'retrocede o adelanta 10 segundos en el video. Útil para revisar un momento específico.'),
    ('Step - / Step +:', 'avanza o retrocede un solo fotograma, ideal para inspecciones detalladas.'),
    ('Velocidad (1x, 2x, 3x):', 'ajusta la velocidad de reproducción para agilizar o detallar el análisis.'),
    ('📸 Captura:', 'guarda una imagen del fotograma actual como evidencia visual.'),
    ('Línea de Conteo:', 'un deslizador que ajusta la posición de la línea imaginaria que el sistema usa como referencia para registrar el tránsito de materiales.'),
]

for titulo, desc in controles:
    p = doc.add_paragraph()
    run = p.add_run(f'• {titulo} ')
    run.bold = True
    p.add_run(desc)

doc.add_paragraph()

doc.add_heading('Panel lateral de resultados', level=3)

doc.add_paragraph(
    'A la derecha del video se encuentra el panel de "Conteo en Tiempo Real", organizado '
    'en tres secciones:'
)

panel_items = [
    ('Tabla de conteo:', 'muestra la cantidad de cada material detectado por la IA y la cantidad esperada según la factura.'),
    ('IA vs Factura:', 'un indicador visual que muestra si el conteo coincide (Conforme) o no (Discrepancia).'),
    ('Registro de Detecciones:', 'lista cronológica de cada detección. Puede hacer doble clic en cualquier entrada para saltar directamente al fotograma donde ocurrió.'),
]

for titulo, desc in panel_items:
    p = doc.add_paragraph()
    run = p.add_run(f'• {titulo} ')
    run.bold = True
    p.add_run(desc)

doc.add_page_break()

# ── 4.6 Cámara en Vivo ────────────────────────────────────────
doc.add_heading('4.6. Cámara en Vivo', level=2)

doc.add_paragraph(
    'Este módulo permite conectar directamente con las cámaras IP instaladas en la zona '
    'de carga de la ferretería. A diferencia del análisis de video (que trabaja con '
    'grabaciones), la cámara en vivo procesa la señal en tiempo real.'
)

img('img_10.png', 'Pantalla de cámara en vivo con detección activa')

doc.add_paragraph('Para conectarse a una cámara en vivo, siga estos pasos:')

cam_steps = [
    'Verifique que el campo "Host" contenga la dirección correcta del DVR (por defecto: ferreteria.viewdns.net).',
    'Seleccione el número de cámara deseada en el desplegable "Cámara".',
    'Presione el botón verde "Conectar".',
    'Espere a que el indicador cambie de ⚫ (Desconectado) a 🟢 (En vivo).',
]

for i, step in enumerate(cam_steps, 1):
    p = doc.add_paragraph()
    run = p.add_run(f'Paso {i}. ')
    run.bold = True
    p.add_run(step)

doc.add_paragraph()
doc.add_paragraph(
    'Una vez conectado, observará la transmisión en tiempo real con los recuadros verdes '
    'de detección. El panel lateral mostrará el conteo acumulado de materiales, y la '
    'columna "Meta" le permite escribir manualmente cuántos materiales espera recibir.'
)

doc.add_heading('Modo de Triangulación', level=3)

doc.add_paragraph(
    'LogiCheck incluye un modo avanzado llamado "Modo Triangulación (9+10)" que activa '
    'dos cámaras simultáneamente. Este modo mejora la precisión del conteo al cruzar '
    'las detecciones de ambas cámaras: si una cámara pierde un material pero la otra '
    'lo detecta, el sistema toma el valor más alto como referencia.'
)

doc.add_heading('Notificaciones automáticas', level=3)

doc.add_paragraph(
    'Cuando el conteo de un material alcanza la meta establecida, el sistema envía '
    'automáticamente una notificación al grupo de Telegram configurado. Además, incluye '
    'botones para generar reportes instantáneos vía WhatsApp o Telegram.'
)

nota_seguridad(
    'Si el sistema detecta movimiento de materiales sin que haya una factura cargada, '
    'emitirá automáticamente una alerta de seguridad vía Telegram con captura de '
    'evidencia. Esta función está diseñada para prevenir movimientos no autorizados.'
)

doc.add_page_break()

# ── 4.7 IA vs Factura ─────────────────────────────────────────
doc.add_heading('4.7. IA vs Factura (Conteo Cruzado)', level=2)

doc.add_paragraph(
    'El conteo cruzado es el corazón del proceso de auditoría. LogiCheck compara '
    'automáticamente los materiales extraídos de la factura con los contados por el '
    'motor de IA, y genera un veredicto para cada material.'
)

doc.add_paragraph('La tabla de comparación presenta cuatro columnas:')

cmp_cols = [
    ('Material:', 'el nombre del producto (Cemento, Tubería Presión, Tubería Sanitaria).'),
    ('Factura:', 'la cantidad registrada en la factura de Siigo.'),
    ('IA:', 'la cantidad detectada por el motor de visión artificial.'),
    ('Δ (Delta):', 'la diferencia numérica. Si es cero, significa que el conteo coincide. Un valor positivo indica que la IA detectó de más, y un valor negativo que detectó de menos.'),
]

for titulo, desc in cmp_cols:
    p = doc.add_paragraph()
    run = p.add_run(f'• {titulo} ')
    run.bold = True
    p.add_run(desc)

doc.add_paragraph()
doc.add_paragraph(
    'Dependiendo del resultado de la comparación, el sistema muestra uno de estos '
    'indicadores:'
)

results = [
    ('✅ CONFORME:', 'todas las cantidades coinciden. El despacho es correcto.'),
    ('⚠️ DISCREPANCIA:', 'al menos un material tiene una diferencia entre la factura y el conteo de la IA. Se recomienda verificar manualmente.'),
]

for titulo, desc in results:
    p = doc.add_paragraph()
    run = p.add_run(f'{titulo} ')
    run.bold = True
    p.add_run(desc)

doc.add_page_break()

# ── 4.8 Asignación Vehicular ──────────────────────────────────
doc.add_heading('4.8. Asignación Vehicular', level=2)

doc.add_paragraph(
    'En esta sección, LogiCheck calcula automáticamente el vehículo más adecuado para '
    'transportar los materiales del despacho actual. El cálculo se basa en dos variables: '
    'el peso total y el volumen total de los materiales facturados.'
)

img('img_08.png', 'Pantalla de asignación vehicular con recomendación automática')

doc.add_paragraph('La pantalla se compone de los siguientes elementos:')

vehicle_items = [
    ('Tarjetas superiores:', 'muestran el peso total (en kilogramos), el volumen total (en metros cúbicos), el vehículo recomendado por el sistema y el porcentaje de uso de capacidad.'),
    ('Tabla de Flota Disponible:', 'lista todos los vehículos registrados en el catálogo con su tipo, placa, capacidad de peso, capacidad de volumen y estado actual.'),
    ('Botón "Confirmar Asignación Vehicular":', 'registra la asignación en la base de datos y la incluye en el historial de auditorías.'),
]

for titulo, desc in vehicle_items:
    p = doc.add_paragraph()
    run = p.add_run(f'• {titulo} ')
    run.bold = True
    p.add_run(desc)

consejo(
    'El sistema resalta en color verde el vehículo recomendado dentro de la tabla, '
    'facilitando su identificación visual. Si ningún vehículo tiene capacidad suficiente, '
    'el sistema lo notificará para que considere dividir la carga.'
)

doc.add_page_break()

# ── 4.9 Reportes ──────────────────────────────────────────────
doc.add_heading('4.9. Reportes', level=2)

doc.add_paragraph(
    'La sección de Reportes centraliza toda la información histórica del sistema. '
    'Desde aquí puede consultar auditorías pasadas, exportar datos y revisar las '
    'capturas de evidencia.'
)

img('img_03.png', 'Pantalla de reportes con historial de auditorías')

doc.add_paragraph('La pantalla se organiza en tres tarjetas:')

report_items = [
    ('Generar Reporte de Auditoría:', 'contiene dos botones de exportación. El botón azul genera un reporte en formato PDF, mientras que el botón verde exporta los datos a Excel. Ambos formatos incluyen los resultados del conteo cruzado, las discrepancias y la asignación vehicular.'),
    ('Historial de Auditorías:', 'tabla con el registro completo de todas las auditorías realizadas, incluyendo la fecha, número de factura, materiales procesados, discrepancias encontradas, vehículo asignado y estado final.'),
    ('Historial de Capturas:', 'galería de imágenes con las capturas de evidencia tomadas durante los análisis. Puede hacer doble clic sobre cualquier captura para abrirla en tamaño completo.'),
]

for titulo, desc in report_items:
    p = doc.add_paragraph()
    run = p.add_run(f'• {titulo} ')
    run.bold = True
    p.add_run(desc)

doc.add_page_break()

# ── 4.10 Actividad ─────────────────────────────────────────────
doc.add_heading('4.10. Registro de Actividad', level=2)

doc.add_paragraph(
    'El registro de actividad funciona como la bitácora oficial de LogiCheck. Cada acción '
    'realizada dentro del sistema queda registrada automáticamente con fecha, hora, usuario '
    'responsable y una descripción detallada del evento.'
)

img('img_18.png', 'Pantalla de registro de actividad (bitácora del sistema)')

doc.add_paragraph('Entre los eventos que se registran automáticamente se encuentran:')

log_events = [
    'Inicios y cierres de sesión.',
    'Facturas cargadas o con errores de lectura.',
    'Análisis de video iniciados y finalizados.',
    'Conexiones y desconexiones de cámaras.',
    'Asignaciones vehiculares confirmadas.',
    'Reportes exportados.',
    'Intentos fallidos de inicio de sesión.',
    'Alertas de seguridad emitidas.',
    'Cambios de tema (oscuro/claro).',
]

for event in log_events:
    doc.add_paragraph(event, style='List Bullet')

doc.add_paragraph()
doc.add_paragraph(
    'Esta información es especialmente útil para auditorías internas, ya que permite '
    'rastrear quién hizo qué y en qué momento, garantizando total transparencia en la '
    'operación de la ferretería.'
)

doc.add_page_break()

# ── 4.11 Gestión de Usuarios ──────────────────────────────────
doc.add_heading('4.11. Gestión de Usuarios', level=2)

doc.add_paragraph(
    'Esta sección está disponible exclusivamente para el usuario con rol de Administrador. '
    'Desde aquí se gestionan todas las cuentas del sistema: creación de nuevos usuarios, '
    'asignación de permisos, cambio de contraseñas y desactivación de cuentas.'
)

img('img_11.png', 'Pantalla de gestión de usuarios')

doc.add_paragraph(
    'La tabla principal muestra la lista de todos los usuarios registrados con su nombre, '
    'usuario de acceso, rol asignado y estado (activo o inactivo). A la derecha de cada '
    'usuario se encuentran los botones de acción.'
)

doc.add_heading('4.11.1. Editar permisos de usuario', level=3)

doc.add_paragraph(
    'LogiCheck permite ajustar los permisos de cada usuario de forma granular. Al '
    'presionar el botón de edición, se despliega un panel donde puede activar o '
    'desactivar individualmente cada función del sistema para ese usuario.'
)

img('img_05.png', 'Panel de edición de permisos, donde cada función se activa individualmente')

doc.add_paragraph(
    'Como se observa en la captura, cada permiso se puede marcar o desmarcar de forma '
    'independiente. Esto permite, por ejemplo, que un operador de factura pueda ver el '
    'Dashboard pero no acceder a las cámaras en vivo.'
)

doc.add_heading('4.11.2. Cambiar contraseña', level=3)

doc.add_paragraph(
    'Si un trabajador olvida su contraseña, el administrador puede restablecerla desde '
    'esta opción sin necesidad de crear una cuenta nueva. Al presionar el botón de '
    'cambio de clave, aparece un cuadro de diálogo donde se ingresa la nueva contraseña.'
)

img('img_21.png', 'Diálogo de cambio de contraseña para un usuario')

nota_seguridad(
    'Se recomienda utilizar contraseñas de al menos 6 caracteres que combinen letras y '
    'números. La contraseña no se muestra en pantalla por motivos de seguridad.'
)

doc.add_heading('4.11.3. Clonar permisos', level=3)

doc.add_paragraph(
    'Cuando se necesita crear un nuevo usuario con los mismos permisos que otro ya existente, '
    'la función de clonación agiliza el proceso. En lugar de configurar cada permiso uno por '
    'uno, simplemente se selecciona el usuario de origen y los permisos se copian automáticamente '
    'al usuario de destino.'
)

img('img_16.png', 'Función de clonación de permisos entre usuarios')

doc.add_heading('4.11.4. Desactivar usuario', level=3)

doc.add_paragraph(
    'Cuando un trabajador deja de laborar en la ferretería o cuando una cuenta necesita '
    'ser bloqueada temporalmente, el administrador puede desactivarla. Un usuario desactivado '
    'no puede iniciar sesión, pero su historial de actividad se mantiene intacto en el sistema.'
)

img('img_14.png', 'Confirmación de desactivación de un usuario')

doc.add_page_break()

# ── 4.12 Configuración ────────────────────────────────────────
doc.add_heading('4.12. Configuración del Sistema', level=2)

doc.add_paragraph(
    'La sección de configuración permite ajustar los parámetros técnicos del sistema. '
    'Esta pantalla está reservada para el Administrador y el Dueño del negocio.'
)

img('img_09.png', 'Primera sección de la pantalla de configuración')

doc.add_paragraph(
    'Los acuerdos de configuración se organizan en categorías. Entre los parámetros '
    'más relevantes se encuentran:'
)

config_items = [
    ('Configuración de cámaras:', 'dirección IP o dominio del DVR, usuario y contraseña de acceso RTSP, y puerto de comunicación.'),
    ('Notificaciones Telegram:', 'token del bot de Telegram y ID del chat grupal para recibir alertas automáticas.'),
    ('Umbrales de confianza IA:', 'porcentaje mínimo de certeza que el motor de IA necesita para considerar válida una detección. Un umbral más alto reduce los falsos positivos pero podría ignorar detecciones legítimas.'),
]

for titulo, desc in config_items:
    p = doc.add_paragraph()
    run = p.add_run(f'• {titulo} ')
    run.bold = True
    p.add_run(desc)

doc.add_paragraph()

img('img_04.png', 'Configuración de cámaras y parámetros de notificación')

img('img_22.png', 'Parámetros avanzados del motor de inteligencia artificial')

nota_seguridad(
    'Modifique estos valores únicamente si comprende su impacto. Un cambio incorrecto '
    'en las credenciales de la cámara provocará que el sistema no pueda conectarse, y un '
    'umbral de confianza demasiado bajo podría generar detecciones erróneas.'
)

doc.add_page_break()


# ╔══════════════════════════════════════════════════════════════╗
# ║       5. DESCRIPCIÓN DE LOS REPORTES DEL SISTEMA           ║
# ╚══════════════════════════════════════════════════════════════╝

doc.add_heading('5. DESCRIPCIÓN DE LOS REPORTES DEL SISTEMA', level=1)

doc.add_paragraph(
    'LogiCheck genera dos tipos de reportes que facilitan la toma de decisiones y '
    'la trazabilidad de las operaciones logísticas:'
)

doc.add_heading('5.1. Reporte de Auditoría en PDF', level=2)

doc.add_paragraph(
    'Al presionar el botón azul "Exportar a PDF" en la sección de Reportes, el sistema '
    'genera un documento que incluye:'
)

pdf_contents = [
    'Datos generales de la auditoría (fecha, hora, usuario responsable).',
    'Número y datos de la factura procesada.',
    'Tabla comparativa de conteo IA vs Factura.',
    'Resultado final (Conforme o Discrepancia).',
    'Vehículo asignado y porcentaje de uso de capacidad.',
]

for item in pdf_contents:
    doc.add_paragraph(item, style='List Bullet')

doc.add_paragraph()
doc.add_paragraph(
    'Este reporte es útil para archivar como evidencia física o digital de cada '
    'despacho, y puede compartirse con clientes o superiores cuando sea necesario '
    'demostrar la verificación.'
)

doc.add_heading('5.2. Reporte en Excel', level=2)

doc.add_paragraph(
    'El botón verde "Exportar a Excel" genera una hoja de cálculo con todas las '
    'auditorías históricas. Este formato es ideal para análisis posteriores, '
    'gráficas personalizadas y consolidación de datos mensuales.'
)

doc.add_heading('5.3. Reportes por mensajería', level=2)

doc.add_paragraph(
    'Desde la sección de Cámara en Vivo, es posible enviar reportes instantáneos '
    'del conteo actual a través de WhatsApp o Telegram. Estos reportes incluyen '
    'el detalle de cada material, el conteo actual sobre la meta esperada y un '
    'indicador de estado (completo, faltante o sobrante).'
)

doc.add_page_break()


# ╔══════════════════════════════════════════════════════════════╗
# ║      6. INTERPRETACIÓN DE MENSAJES Y ERRORES               ║
# ╚══════════════════════════════════════════════════════════════╝

doc.add_heading('6. INTERPRETACIÓN DE MENSAJES Y ERRORES', level=1)

doc.add_paragraph(
    'Durante el uso diario de LogiCheck, el sistema emite diferentes tipos de mensajes '
    'que aparecen como notificaciones flotantes en la esquina superior derecha de la '
    'pantalla. A continuación se detalla cada uno.'
)

# Tabla de mensajes
table = doc.add_table(rows=9, cols=4)
table.style = 'Light Shading Accent 1'
table.alignment = WD_TABLE_ALIGNMENT.CENTER

hdr = table.rows[0].cells
hdr[0].text = 'Tipo'
hdr[1].text = 'Mensaje'
hdr[2].text = 'Causa probable'
hdr[3].text = 'Acción recomendada'

msgs = [
    ('✅', 'Factura cargada correctamente', 'La lectura del PDF fue exitosa y se encontraron productos YOLO.', 'Proceda al análisis de video.'),
    ('⚠️', 'Sin productos YOLO detectables', 'La factura no contiene cemento ni tuberías reconocibles por la IA.', 'Verifique que la factura sea la correcta o que los productos estén registrados con nombres estándar.'),
    ('⚠️', 'Discrepancia detectada', 'El conteo de la IA no coincide con la factura.', 'Revise manualmente el despacho. Compare los números de la tabla IA vs Factura.'),
    ('🚫', 'Error al leer PDF', 'El archivo está dañado o no es una factura válida de Siigo.', 'Intente descargar nuevamente la factura desde Siigo o contacte al administrador.'),
    ('🚫', 'Error de cámara', 'No se pudo establecer conexión con la cámara IP.', 'Verifique la dirección del host, el usuario/contraseña y que el DVR esté encendido.'),
    ('ℹ️', 'Cámara desconectada', 'Se interrumpió la conexión con la cámara.', 'Presione "Conectar" nuevamente o revise la red.'),
    ('🚨', 'ALERTA DE SEGURIDAD', 'Se detectó movimiento de material sin factura cargada.', 'Revise inmediatamente las cámaras. Este evento se reporta automáticamente por Telegram.'),
    ('✅', 'Meta alcanzada', 'El conteo de un material llegó al número esperado.', 'Confirme visualmente y proceda con el despacho.'),
]

for i, (tipo, msg, causa, accion) in enumerate(msgs):
    row = table.rows[i+1].cells
    row[0].text = tipo
    row[1].text = msg
    row[2].text = causa
    row[3].text = accion

doc.add_paragraph()
doc.add_paragraph(
    'Además de las notificaciones flotantes, el sistema emite un breve sonido audible '
    'cada vez que detecta un nuevo material en las cámaras. Este sonido permite al '
    'despachador mantener la atención en su trabajo físico sin necesidad de estar '
    'mirando la pantalla constantemente.'
)

doc.add_page_break()


# ╔══════════════════════════════════════════════════════════════╗
# ║     7. PROCEDIMIENTO A SEGUIR EN CASO DE FALLOS            ║
# ╚══════════════════════════════════════════════════════════════╝

doc.add_heading('7. PROCEDIMIENTO A SEGUIR EN CASO DE FALLOS', level=1)

doc.add_paragraph(
    'Este apartado describe las acciones básicas que debe realizar un usuario cuando '
    'el sistema presenta un comportamiento inesperado. Recuerde que estas son medidas '
    'de primer nivel; si el problema persiste, contacte al encargado de soporte técnico.'
)

# Fallo 1
doc.add_heading('7.1. La pantalla de la cámara se ve negra u oscura', level=2)

doc.add_paragraph('Posibles causas y soluciones:')

fallo1 = [
    ('Iluminación insuficiente:', 'si la zona de carga no cuenta con luz adecuada, la cámara captará una imagen oscura. Encienda las luces de la bodega antes de conectar la cámara.'),
    ('Cable desconectado:', 'verifique que el cable de red (ethernet) que va desde la cámara al DVR está firmemente conectado.'),
    ('DVR apagado:', 'confirme que el grabador de video (DVR) está encendido y funcionando. El LED frontal debe estar parpadeando.'),
    ('Host o puerto incorrectos:', 'en la pantalla de Cámara en Vivo, verifique que la dirección del host y el puerto coincidan con los datos proporcionados por el administrador.'),
]

for titulo, desc in fallo1:
    p = doc.add_paragraph()
    run = p.add_run(f'• {titulo} ')
    run.bold = True
    p.add_run(desc)

# Fallo 2
doc.add_heading('7.2. No se puede iniciar sesión', level=2)

doc.add_paragraph('Verifique los siguientes puntos:')

fallo2 = [
    'Confirme que la tecla de Bloq Mayús (Caps Lock) esté desactivada.',
    'Verifique que está escribiendo el usuario exactamente como se lo asignaron.',
    'Si olvidó la contraseña, solicite al administrador que la restablezca desde Gestión de Usuarios.',
    'Si su cuenta fue desactivada, solo el administrador puede reactivarla.',
]

for item in fallo2:
    doc.add_paragraph(item, style='List Bullet')

# Fallo 3
doc.add_heading('7.3. El sistema emite alertas de discrepancia constantemente', level=2)

doc.add_paragraph(
    'Las alertas de discrepancia indican que la IA está contando una cantidad distinta '
    'a la registrada en la factura. Antes de asumir un error del sistema, considere lo '
    'siguiente:'
)

fallo3 = [
    'Confirme que la factura cargada corresponde al despacho que se está auditando.',
    'Si la factura es correcta, revise manualmente el vehículo para contar los materiales físicamente.',
    'Si identifica un error de la IA (por ejemplo, un falso positivo por un objeto similar), regístrelo como observación y proceda.',
    'Si la discrepancia indica que hay más material del facturado, alerte a su supervisor de inmediato.',
]

for item in fallo3:
    doc.add_paragraph(item, style='List Bullet')

# Fallo 4
doc.add_heading('7.4. El sistema se congela o no responde', level=2)

fallo4 = [
    ('Espere 30 segundos:', 'el motor de IA puede estar procesando una operación pesada (especialmente al inicio).'),
    ('Cierre y reinicie:', 'si el sistema no responde después de un minuto, cierre la aplicación desde el Administrador de Tareas de Windows (Ctrl + Alt + Supr) y vuelva a abrirla.'),
    ('Reporte el incidente:', 'anote la pantalla donde ocurrió el problema, el mensaje de error (si lo hubo) y la hora exacta. Comunique esta información al administrador del sistema.'),
]

for titulo, desc in fallo4:
    p = doc.add_paragraph()
    run = p.add_run(f'• {titulo} ')
    run.bold = True
    p.add_run(desc)

# Fallo 5
doc.add_heading('7.5. La IA no detecta los materiales correctamente', level=2)

doc.add_paragraph(
    'Si nota que la cámara está encendida y hay materiales visibles pero el sistema no '
    'los encierra en recuadros verdes, considere:'
)

fallo5 = [
    'La zona de detección puede estar mal configurada. Solicite al administrador que ajuste los deslizadores de zona en la configuración de la cámara.',
    'Los materiales pueden estar demasiado lejos de la cámara o parcialmente ocultos.',
    'Si el problema es constante, puede ser necesario reentrenar el modelo de IA con nuevas imágenes.',
]

for item in fallo5:
    doc.add_paragraph(item, style='List Bullet')

doc.add_paragraph()

doc.add_heading('Información mínima para reportar un fallo', level=2)

doc.add_paragraph(
    'Cuando contacte al administrador o soporte técnico, incluya siempre la siguiente '
    'información para agilizar la resolución del problema:'
)

report_info = [
    'Pantalla donde ocurrió el problema.',
    'Mensaje de error exacto (si aparece alguno).',
    'Fecha y hora del incidente.',
    'Pasos que estaba realizando cuando ocurrió.',
    'Su nombre de usuario en el sistema.',
]

for item in report_info:
    doc.add_paragraph(item, style='List Bullet')

doc.add_page_break()


# ╔══════════════════════════════════════════════════════════════╗
# ║                       GLOSARIO                             ║
# ╚══════════════════════════════════════════════════════════════╝

doc.add_heading('GLOSARIO', level=1)

glosario = [
    ('Bounding Box (Recuadro verde)', 'Marco rectangular que la inteligencia artificial dibuja alrededor de un objeto detectado en una imagen o video.'),
    ('Conteo Cruzado', 'Proceso mediante el cual LogiCheck compara las cantidades de materiales registradas en la factura con las detectadas por el motor de IA.'),
    ('Dashboard', 'Tablero o panel de control que presenta un resumen visual de las estadísticas y actividades del sistema.'),
    ('Discrepancia', 'Diferencia entre la cantidad esperada (factura) y la cantidad detectada (IA) de un material.'),
    ('DVR', 'Grabador Digital de Video (Digital Video Recorder). Dispositivo que almacena las grabaciones de las cámaras de seguridad.'),
    ('IA (Inteligencia Artificial)', 'Campo de la informática que permite a los sistemas aprender patrones y tomar decisiones. En LogiCheck, se utiliza para reconocer y contar materiales.'),
    ('RTSP', 'Protocolo de transmisión de video en tiempo real (Real Time Streaming Protocol) utilizado para conectar con las cámaras IP.'),
    ('Siigo', 'Software contable y de facturación electrónica utilizado por la Ferretería Durán para emitir sus facturas.'),
    ('Triangulación', 'Modo de operación que utiliza dos cámaras simultáneamente para mejorar la precisión del conteo.'),
    ('YOLO', 'Algoritmo de visión artificial que significa "You Only Look Once" (Solo miras una vez). Es el motor que permite detectar objetos en imágenes a alta velocidad.'),
]

table = doc.add_table(rows=len(glosario)+1, cols=2)
table.style = 'Light Shading Accent 1'
table.alignment = WD_TABLE_ALIGNMENT.CENTER

hdr = table.rows[0].cells
hdr[0].text = 'Término'
hdr[1].text = 'Definición'

for i, (termino, definicion) in enumerate(glosario):
    row = table.rows[i+1].cells
    row[0].text = termino
    row[1].text = definicion


# ── Guardar ──────────────────────────────────────────────────
os.makedirs(os.path.dirname(OUT), exist_ok=True)
doc.save(OUT)
print(f'\n[OK] Manual guardado exitosamente en:\n{OUT}')
print(f'   - {fig_counter[0]} figuras insertadas')
print(f'   - {len(doc.paragraphs)} parrafos')
