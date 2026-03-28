# Skill Registry — gc-housing-rag

## Compact Rules

### python-conventions

```
## Python Conventions (auto-resolved)

### Nomenclatura
- Variables/métodos en INGLÉS: total_records, load_more()
- Comentarios en CASTELLANO: # Obtener datos con eager loading
- Términos técnicos en inglés: API, endpoint, async, decorator

### Estructura del Proyecto
- src/
  - config.py      # Configuración global
  - ingest/        # Scripts de ingestión de datos
  - rag/           # Pipeline RAG (api, chat, embedder, indexer, pipeline)
  - frontend/      # HTML/JS estático
- data/
  - raw/           # Datos fuente (no commit)
  - processed/     # Datos curados

### Patrones RAG
- Pipeline: load_data → create_chunks → generate_embeddings → index_data
- Chunk: { id, text, metadata }
- Embedding: MiniMax API (embo-01, 384 dim)
- Vector DB: Pinecone

### FastAPI Endpoints
- @app.get / @app.post decorators
- Pydantic BaseModel para request/response
- HTTPException para errores
- CORS middleware habilitado

### API Keys
- Usar python-dotenv
- Cargar en config.py: load_dotenv()
- NUNCA commit .env
```

### fastapi-patterns

```
## FastAPI Patterns (auto-resolved)

### Imports
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional

### Request/Response
class QueryRequest(BaseModel):
    question: str
    top_k: Optional[int] = 5
    barrio: Optional[str] = None

### Error Handling
if not result:
    raise HTTPException(status_code=404, detail="No data found")

### CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### tidying

```
## Tidying First (auto-resolved)

### Señales de Código Desordenado
- Función > 50 líneas
- Mezcla de responsabilidades (queries + lógica + formatting)
- Condicionales anidados > 3 niveles
- Nombres crípticos: d, tmp, res
- Código muerto
- Duplicación > 3 líneas

### Catálogo de Tidyings
1. Guard Clause: if not condition: return early
2. Extraer función: bloques > 10 líneas → función privada
3. Renombrar: nombres descriptivos
4. Eliminar dead code: funciones comentadas, imports sin usar

### Árbol de Decisión
1. ¿Código necesita cambiar para tarea actual? → No: Tidy Later
2. ¿Limpiar facilita el cambio? → No: hacer cambio, considerar Tidy After
3. ¿Tidying < 15 min? → No: Tidy Later
4. → Sí: Tidy First, luego el cambio

### Commit Format
- refactor: extraer lógica a función
- feat: añadir nueva feature
- NUNCA mezclar refactor + feat en mismo commit
```

### code-redflags

```
## Code Red-Flags (auto-resolved)

### Funciones/Métodos
- > 50 líneas → extraer a funciones < 15 líneas
- > 4 parámetros → usar kwargs o destructuring
- Complejidad ciclomática > 10 → guard clauses

### Variables
- 0 variables globales (excepto constantes)
- Nombres < 3 caracteres → descriptivos

### Estado
- NO estáticos mutables (global counter)
- Usar clases o closures para estado

### API Keys
- NUNCA hardcodear keys en código
- Usar os.getenv() o python-dotenv

### SQL/Data
- NO concatenación en queries: usar bindings/parametrized
- Verificar que inputs de usuario se escapan
```

### architecture-redflags

```
## Architecture Red-Flags (auto-resolved)

### Acoplamiento
- Dependencias circulares entre módulos
- imports de carpetas parents: import from '....'
- Archivos > 500 líneas → demasiado grande

### SOLID Violations
- SRP: clase que hace parsing + lógica + API
- OCP: modificar clase para añadir tipo nuevo
- LSP: subtipo no reemplazable
- ISP: interfaz "god" con 30 métodos
- DIP: dependencias concretas en vez de abstracciones

### Dependencies
- Módulo dependiendo de 10+ otros módulos
- Config en código duro en vez de env/config
```

---

## User Skills

| Trigger (Regex) | Skill | Code Context |
|-----------------|-------|--------------|
| `fastapi\|FastAPI\|\.py.*api` | fastapi-patterns | src/rag/api.py |
| `python\|Python\|\.py` | python-conventions | Archivos Python |
| `test\|pytest\|unittest` | pytest-testing | tests/**/*.py |
| `tidying\|refactor\|limpiar\|tidy` | tidying | Cualquier archivo |
| `code.?red\|red.?flag\|smell` | code-redflags | Cualquier archivo |
| `architecture\|SOLID\|acoplamiento` | architecture-redflags | Archivos Python |
| `rag\|embedding\|pinecone\|chunk` | rag-patterns | src/rag/*.py |
| `skill|create.*skill|nuevo.*skill` | skill-creator | Archivos MD |
| `sdd|spec|specs|design|proposal` | sdd-*-skills | Cualquier cambio |
| `test|pytest|unittest|testing` | testing-specialist-agent | tests/**/*.py |
| `bug|debug|error|fallo|debugging` | superpowers:systematic-debugging | Cualquier archivo |

### SDD Workflow Triggers
| Phase | Skill | When |
|-------|-------|------|
| Start new change | sdd-init | Nuevo proyecto/cambio |
| Explore | sdd-explore | Investigar antes de proponer |
| Proposal | sdd-propose | Documentar intent + scope |
| Spec | sdd-spec | Requisitos formales |
| Design | sdd-design | Arquitectura técnica |
| Tasks | sdd-tasks | Descomposición en tareas |
| Apply | sdd-apply | Implementar tareas |
| Verify | sdd-verify | Validar contra specs |
| Archive | sdd-archive | Cerrar cambio |

---

## Project Conventions

- **Python**: src/, requirements.txt, venv/
- **API**: FastAPI con Pydantic
- **RAG**: Pinecone + MiniMax embeddings + Groq LLM
- **Frontend**: HTML vanilla + Leaflet.js (dark theme)
- **Data**: Pandas para CSV processing
- **Config**: .env + python-dotenv
- **Commits**: conventional commits (feat:, fix:, refactor:)

---

## Tech Stack

- **Backend**: FastAPI 0.109.2, Python 3.13
- **LLM**: MiniMax (embeddings) + Groq Llama 3.3 (chat)
- **Vector DB**: Pinecone 3.0.0
- **Data**: Pandas 2.2.1, NumPy 1.26.4
- **Frontend**: Vanilla HTML/JS + Leaflet.js
- **Dev**: Jupyter 1.0.0, pytest 8.0.2

---

*Registry ID: gc-housing-rag-v3*
*Actualizado: 2026-03-28*
*SDD skills agregados a la tabla de triggers*
