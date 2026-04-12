def generate_svg():
    svg_content = """<svg width="800" height="600" viewBox="0 0 800 600" fill="none" xmlns="http://www.w3.org/2000/svg">
  <!-- Background -->
  <rect width="800" height="600" fill="white"/>
  
  <!-- Definitions for arrows and shadows -->
  <defs>
    <marker id="arrowhead" markerWidth="10" markerHeight="7" refX="0" refY="3.5" orient="auto">
      <polygon points="0 0, 10 3.5, 0 7" fill="#2C3E50" />
    </marker>
    <filter id="shadow" x="-2%" y="-2%" width="104%" height="104%">
      <feDropShadow dx="0" dy="2" stdDeviation="2" flood-opacity="0.1"/>
    </filter>
  </defs>

  <!-- Layers Titles -->
  <text x="50" y="40" font-family="Arial" font-size="20" font-weight="bold" fill="#34495E">ARQUITECTURA LOGICHECK</text>

  <!-- Presentation Layer -->
  <rect x="50" y="80" width="700" height="80" rx="10" fill="#EBF5FB" stroke="#3498DB" stroke-width="2" filter="url(#shadow)"/>
  <text x="400" y="115" font-family="Arial" font-size="16" font-weight="bold" fill="#2980B9" text-anchor="middle">CAPA DE PRESENTACIÓN (GUI)</text>
  <text x="400" y="140" font-family="Arial" font-size="12" fill="#34495E" text-anchor="middle">Interfaz Qt | Dashboard KPIs | Configuración de Zonas</text>

  <!-- Business Logic Layer -->
  <rect x="50" y="200" width="700" height="80" rx="10" fill="#EAFAF1" stroke="#27AE60" stroke-width="2" filter="url(#shadow)"/>
  <text x="400" y="235" font-family="Arial" font-size="16" font-weight="bold" fill="#1E8449" text-anchor="middle">CAPA DE LÓGICA DE NEGOCIO</text>
  <text x="400" y="260" font-family="Arial" font-size="12" fill="#34495E" text-anchor="middle">Módulo Auditor Central | Validador de Facturas PDF (Siigo)</text>

  <!-- Vision Layer -->
  <rect x="50" y="320" width="700" height="80" rx="10" fill="#FEF9E7" stroke="#F1C40F" stroke-width="2" filter="url(#shadow)"/>
  <text x="400" y="355" font-family="Arial" font-size="16" font-weight="bold" fill="#B7950B" text-anchor="middle">CAPA DE VISIÓN ARTIFICIAL</text>
  <text x="400" y="380" font-family="Arial" font-size="12" fill="#34495E" text-anchor="middle">Inferencia YOLOv26 | Procesamiento OpenCV | Rastreo (DeepSORT)</text>

  <!-- Data & External Layer -->
  <rect x="50" y="440" width="340" height="80" rx="10" fill="#FBEEE6" stroke="#E67E22" stroke-width="2" filter="url(#shadow)"/>
  <text x="220" y="475" font-family="Arial" font-size="16" font-weight="bold" fill="#A04000" text-anchor="middle">CAPA DE DATOS</text>
  <text x="220" y="500" font-family="Arial" font-size="12" fill="#34495E" text-anchor="middle">SQLite Local (ACID)</text>

  <rect x="410" y="440" width="340" height="80" rx="10" fill="#F4ECF7" stroke="#8E44AD" stroke-width="2" filter="url(#shadow)"/>
  <text x="580" y="475" font-family="Arial" font-size="16" font-weight="bold" fill="#633974" text-anchor="middle">SERVICIOS EXTERNOS</text>
  <text x="580" y="500" font-family="Arial" font-size="12" fill="#34495E" text-anchor="middle">API Telegram/WhatsApp | RTSP Cámaras</text>

  <!-- Connectors -->
  <path d="M 400 160 L 400 200" stroke="#2C3E50" stroke-width="2" marker-end="url(#arrowhead)"/>
  <path d="M 400 280 L 400 320" stroke="#2C3E50" stroke-width="2" marker-end="url(#arrowhead)"/>
  <path d="M 220 400 L 220 440" stroke="#2C3E50" stroke-width="2" marker-end="url(#arrowhead)"/>
  <path d="M 580 400 L 580 440" stroke="#2C3E50" stroke-width="2" marker-end="url(#arrowhead)"/>
  
  <!-- Horizontal Data Flow -->
  <path d="M 220 280 L 220 320" stroke="#2C3E50" stroke-width="2" marker-end="url(#arrowhead)"/>
  <path d="M 580 320 L 580 280" stroke="#2C3E50" stroke-width="2" marker-end="url(#arrowhead)"/>

</svg>"""
    
    with open('arquitectura_logic_check.svg', 'w', encoding='utf-8') as f:
        f.write(svg_content)
    print("SVG generated successfully.")

if __name__ == "__main__":
    generate_svg()
