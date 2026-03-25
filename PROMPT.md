# Test Case Generator

## Categoria

**SDET / QA Engineering + AI**

## Descripcion

Herramienta que recibe texto del usuario (requisitos, user stories, PRDs, criterios de aceptacion, especificaciones) y genera automaticamente casos de prueba estructurados usando IA. Soporta multiples formatos de entrada y genera output exportable en Markdown, PDF, y Excel (XLSX). Aplica tecnicas de test design de ISTQB (equivalence partitioning, boundary value analysis, decision tables, state transitions).

## Stack tecnologico

- **Lenguaje**: Python 3.12+
- **LLM**: Claude API (Anthropic SDK)
- **CLI**: Typer + Rich
- **Web**: FastAPI + HTMX + Tailwind CSS (interfaz web opcional)
- **Export MD**: Jinja2 templates
- **Export PDF**: WeasyPrint
- **Export XLSX**: openpyxl
- **Testing**: pytest
- **CI/CD**: GitHub Actions

## Funcionalidades requeridas

### Input

- Texto libre (requisitos, user stories, PRDs)
- Paste directo o archivo (.txt, .md, .pdf)
- Formato Given/When/Then (Gherkin)
- Bulk: multiples requisitos de una vez

### Generacion de test cases

Por cada requisito, genera:
- **ID** unico (TC-001, TC-002...)
- **Titulo** descriptivo
- **Precondiciones**
- **Steps** (Given/When/Then o Step/Expected Result)
- **Datos de prueba** (inputs concretos)
- **Resultado esperado**
- **Prioridad** (High/Medium/Low)
- **Tipo** (Functional, Negative, Boundary, Security, Performance, Accessibility)
- **Tecnica ISTQB** aplicada (Equivalence Partitioning, BVA, Decision Table, State Transition, Error Guessing)
- **Trazabilidad** (link al requisito original)

### Tecnicas ISTQB

- **Equivalence Partitioning**: divide inputs en clases validas/invalidas
- **Boundary Value Analysis**: genera tests en los limites
- **Decision Tables**: combinaciones de condiciones
- **State Transitions**: flujos de estados
- **Error Guessing**: basado en experiencia comun

### Export

- **Markdown**: tabla formateada + detalles por test case
- **PDF**: documento profesional con portada, indice, tabla resumen, detalle
- **XLSX**: hoja "Summary" + hoja "Test Cases" + hoja "Traceability Matrix"
- **JSON**: estructura para integracion con otras herramientas

### CLI

```bash
# Desde texto directo
testgen generate "El usuario debe poder registrarse con email y password. El password debe tener minimo 8 caracteres."

# Desde archivo
testgen generate --file requirements.md

# Con formato de salida
testgen generate --file prd.md --format xlsx --output test-cases.xlsx
testgen generate --file prd.md --format pdf --output test-cases.pdf
testgen generate --file prd.md --format md --output test-cases.md
testgen generate --file prd.md --format all --output-dir ./output/

# Con opciones
testgen generate --file prd.md --techniques bva,ep,dt --priority high --types functional,negative,boundary

# Web UI
testgen serve --port 8000
```

### Web UI

- Textarea para pegar requisitos
- Vista previa de test cases generados
- Editar test cases antes de exportar
- Botones de descarga: MD, PDF, XLSX
- Historial de generaciones
