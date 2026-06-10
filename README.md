# Enterprise Chatbot API

Backend RAG (Retrieval-Augmented Generation) construido con **FastAPI + PostgreSQL + pgvector + OpenAI**.  
Permite a empresas subir documentos y consultarlos mediante lenguaje natural.

---

## Tabla de contenido

1. [Arquitectura conceptual](#arquitectura-conceptual)
2. [Jerarquía de datos](#jerarquía-de-datos)
3. [Cómo funciona el RAG](#cómo-funciona-el-rag)
4. [Los tres niveles de consulta](#los-tres-niveles-de-consulta)
5. [Referencia de endpoints](#referencia-de-endpoints)
   - [Health](#health)
   - [Organizations](#organizations)
   - [Knowledge Bases](#knowledge-bases)
   - [Agents](#agents)
6. [Flujo completo de ejemplo](#flujo-completo-de-ejemplo)
7. [Formatos de archivo soportados](#formatos-de-archivo-soportados)
8. [Variables de entorno](#variables-de-entorno)
9. [Logs](#logs)
10. [Docker](#docker)

---

## Arquitectura conceptual

```
Organization (empresa)
│
├── Knowledge Base "RRHH"            ← documentos de recursos humanos
│   ├── contrato_laboral.pdf
│   └── politica_vacaciones.docx
│
├── Knowledge Base "Ventas"          ← documentos de ventas
│   ├── catalogo_productos.pdf
│   └── lista_precios.xlsx
│
├── Knowledge Base "Tesorería"
│   └── presupuesto_2026.xlsx
│
├── Agent "Bot Interno RRHH"         ← solo consulta KB de RRHH
│   └── → Knowledge Base "RRHH"
│
├── Agent "Bot Comercial Externo"    ← consulta Ventas + Atención al Cliente
│   ├── → Knowledge Base "Ventas"
│   └── → Knowledge Base "Atención al Cliente"
│
└── Agent "Bot General"              ← consulta TODAS las KBs de la empresa
    ├── → Knowledge Base "RRHH"
    ├── → Knowledge Base "Ventas"
    └── → Knowledge Base "Tesorería"
```

---

## Jerarquía de datos

```
Organization
  └── Knowledge Base (N)           una org puede tener N bases de conocimiento
        └── Document (N)           una KB puede tener N documentos
              └── DocumentChunk    cada doc se divide en fragmentos de ~1000 chars
                    └── Embedding  cada chunk tiene un vector (1536 dims) para búsqueda semántica

Agent
  └── AgentKnowledgeBase (N)       un agente puede apuntar a N bases de conocimiento
```

---

## Cómo funciona el RAG

Cuando se hace una pregunta:

1. **Embedding de la pregunta** — la pregunta se convierte en un vector con `text-embedding-3-small`
2. **Búsqueda semántica** — se buscan los chunks más similares mediante distancia coseno en pgvector
3. **Construcción del contexto** — los top-N chunks se concatenan como contexto
4. **Generación de respuesta** — se llama a `gpt-4.1-mini` con el contexto + la pregunta
5. **Respuesta** — si no hay información relevante, responde `"No encontré información suficiente para responder."`

---

## Los tres niveles de consulta

| Nivel | Endpoint | Busca en... | Cuándo usarlo |
|-------|----------|-------------|---------------|
| **KB específica** | `POST /knowledge-bases/{kb_id}/ask` | Un solo documento/grupo de docs en esa KB | Bot especializado en un tema exacto |
| **Por área** | `POST /organizations/{org_id}/ask?area=ventas` | Todas las KBs de esa área | Consultar todo lo de un departamento |
| **Toda la org** | `POST /organizations/{org_id}/ask` | Todas las KBs de la empresa | Bot general sin filtro |
| **Agente** | `POST /agents/{agent_id}/ask` | Las KBs que el agente tiene vinculadas | Bot personalizado con control total |

**El agente es el nivel más flexible:** puedes vincularle exactamente las KBs que necesite, sin importar el área.

---

## Referencia de endpoints

### Health

#### `GET /health`
Verifica conectividad con la base de datos.

**Respuesta**
```json
{ "database": true }
```

---

### Organizations

#### `POST /organizations`
Crea una empresa/organización.

**Body**
```json
{
  "trade_name": "Empresa XYZ",
  "business_name": "Empresa XYZ S.A.S.",
  "tax_id": "900123456-7",
  "contact_phone": "+57 300 0000000",
  "address": "Calle 100 # 15-20",
  "department": "Cundinamarca",
  "city": "Bogotá"
}
```

**Respuesta `201`**
```json
{
  "id": "uuid",
  "trade_name": "Empresa XYZ",
  "business_name": "Empresa XYZ S.A.S.",
  "tax_id": "900123456-7",
  "contact_phone": "+57 300 0000000",
  "address": "Calle 100 # 15-20",
  "department": "Cundinamarca",
  "city": "Bogotá",
  "created_at": "2026-06-09T14:00:00Z"
}
```

---

#### `GET /organizations/{organization_id}/agents`
Lista todos los agentes (bots) de una organización.

**Respuesta `200`**
```json
[
  {
    "id": "agent-uuid",
    "organization_id": "org-uuid",
    "name": "Bot Comercial Externo",
    "description": "Atiende consultas de clientes externos",
    "visibility": "external",
    "created_at": "2026-06-09T14:00:00Z",
    "knowledge_bases": [
      { "knowledge_base_id": "kb-uuid-ventas", "added_at": "2026-06-09T14:05:00Z" },
      { "knowledge_base_id": "kb-uuid-atencion", "added_at": "2026-06-09T14:06:00Z" }
    ]
  }
]
```

---

#### `POST /organizations/{organization_id}/ask`
Consulta **todas** las bases de conocimiento de la organización.  
Opcionalmente filtra por área con el query param `?area=`.

**Query params opcionales**
| Param | Descripción | Ejemplo |
|-------|-------------|---------|
| `area` | Filtra solo las KBs de esa área | `?area=ventas` |

**Body**
```json
{ "question": "¿Cuántos días de vacaciones tiene un empleado nuevo?" }
```

**Respuesta `200`**
```json
{
  "question": "¿Cuántos días de vacaciones tiene un empleado nuevo?",
  "answer": "Según la política de la empresa, un empleado nuevo..."
}
```

**Ejemplos de uso:**
```
POST /organizations/org-uuid/ask                    → busca en TODAS las KBs
POST /organizations/org-uuid/ask?area=rrhh          → busca solo en KBs de RRHH
POST /organizations/org-uuid/ask?area=ventas        → busca solo en KBs de ventas
```

---

#### `POST /organizations/{organization_id}/ask/stream`
Igual que el anterior pero la respuesta llega en tiempo real como **Server-Sent Events**.

**Respuesta** `text/event-stream`
```
data: "Según"
data: " la"
data: " política..."
data: [DONE]
```

Acepta el mismo query param `?area=`.

---

### Knowledge Bases

Una Knowledge Base (KB) es un contenedor lógico de documentos relacionados.  
Una empresa puede tener tantas KBs como necesite.

#### `POST /knowledge-bases`
Crea una base de conocimiento.

**Body**
```json
{
  "organization_id": "org-uuid",
  "name": "Políticas de RRHH",
  "description": "Contratos, vacaciones, reglamento interno",
  "area": "rrhh"
}
```

> El campo `area` es libre — puede ser cualquier texto: `"rrhh"`, `"ventas"`, `"tesoreria"`, `"legal"`, etc.  
> Se usa para filtrar con `?area=` en el endpoint de la organización.

**Respuesta `201`**
```json
{
  "id": "kb-uuid",
  "organization_id": "org-uuid",
  "name": "Políticas de RRHH",
  "description": "Contratos, vacaciones, reglamento interno",
  "area": "rrhh",
  "created_at": "2026-06-09T14:00:00Z"
}
```

---

#### `POST /knowledge-bases/{knowledge_base_id}/documents`
Sube un documento a la KB. El sistema lo procesa automáticamente:  
extrae texto → limpia → divide en chunks → genera embeddings → almacena.

**Form-data**
| Campo | Tipo | Descripción |
|-------|------|-------------|
| `file` | archivo | PDF, DOCX, CSV, JSON o XLSX |

**Formatos soportados:** `.pdf` `.docx` `.csv` `.json` `.xlsx`

**Respuesta `201`**
```json
{
  "id": "doc-uuid",
  "knowledge_base_id": "kb-uuid",
  "file_name": "contrato_laboral.pdf",
  "file_type": "pdf",
  "file_size": 204800,
  "status": "PROCESSED",
  "chunks_total": 24,
  "chunks_processed": 24,
  "created_at": "2026-06-09T14:01:00Z"
}
```

**Estados posibles del documento**
| Estado | Descripción |
|--------|-------------|
| `PENDING` | Recibido, pendiente de procesar |
| `PROCESSING` | Extrayendo texto y generando embeddings |
| `PROCESSED` | Listo para consultas |
| `FAILED` | Error durante el procesamiento |

> Si `SUPABASE_URL` está configurado, el archivo original se sube al bucket de Supabase y se guarda la URL en `file_url`.

---

#### `POST /knowledge-bases/{knowledge_base_id}/ask`
Consulta **solo** esta base de conocimiento.

**Body**
```json
{ "question": "¿Cuál es el proceso para solicitar vacaciones?" }
```

**Respuesta `200`**
```json
{
  "question": "¿Cuál es el proceso para solicitar vacaciones?",
  "answer": "Según el reglamento interno, el empleado debe..."
}
```

---

#### `POST /knowledge-bases/{knowledge_base_id}/ask/stream`
Igual que el anterior con streaming SSE.

---

### Agents

Un **agente** es un bot configurado con exactamente las bases de conocimiento que necesita.  
Es el nivel de personalización más alto.

**Un agente puede tener de 1 a N knowledge bases vinculadas.**  
Cada llamada a `POST /agents/{agent_id}/knowledge-bases` agrega una KB.  
No hay límite máximo.

---

#### `POST /agents`
Crea un agente.

**Body**
```json
{
  "organization_id": "org-uuid",
  "name": "Bot Comercial Externo",
  "description": "Responde preguntas de clientes sobre productos y precios",
  "visibility": "external"
}
```

**Campo `visibility`**
| Valor | Descripción |
|-------|-------------|
| `"internal"` | Solo para uso interno (empleados) |
| `"external"` | Para clientes externos |
| `"both"` | Ambos públicos |

> `visibility` es metadata — hoy te ayuda a organizar. En el futuro se puede usar para control de acceso con autenticación.

**Respuesta `201`**
```json
{
  "id": "agent-uuid",
  "organization_id": "org-uuid",
  "name": "Bot Comercial Externo",
  "description": "Responde preguntas de clientes sobre productos y precios",
  "visibility": "external",
  "created_at": "2026-06-09T14:00:00Z",
  "knowledge_bases": []
}
```

---

#### `GET /agents/{agent_id}`
Obtiene el agente con todas sus KBs vinculadas.

**Respuesta `200`**
```json
{
  "id": "agent-uuid",
  "organization_id": "org-uuid",
  "name": "Bot Comercial Externo",
  "description": "Responde preguntas de clientes sobre productos y precios",
  "visibility": "external",
  "created_at": "2026-06-09T14:00:00Z",
  "knowledge_bases": [
    { "knowledge_base_id": "kb-uuid-ventas",   "added_at": "2026-06-09T14:05:00Z" },
    { "knowledge_base_id": "kb-uuid-productos", "added_at": "2026-06-09T14:06:00Z" }
  ]
}
```

---

#### `POST /agents/{agent_id}/knowledge-bases`
Vincula **una** base de conocimiento al agente.  
Llama este endpoint tantas veces como KBs quieras agregar.

**Body**
```json
{ "knowledge_base_id": "kb-uuid-ventas" }
```

**Respuesta `204 No Content`**

**Para vincular 3 KBs a un agente, haces 3 llamadas:**
```
POST /agents/agent-uuid/knowledge-bases  → { "knowledge_base_id": "kb-ventas" }
POST /agents/agent-uuid/knowledge-bases  → { "knowledge_base_id": "kb-productos" }
POST /agents/agent-uuid/knowledge-bases  → { "knowledge_base_id": "kb-garantias" }
```

---

#### `DELETE /agents/{agent_id}/knowledge-bases/{knowledge_base_id}`
Desvincula una base de conocimiento del agente.

**Respuesta `204 No Content`**

---

#### `POST /agents/{agent_id}/ask`
Consulta el agente. Busca en **todas** las KBs que tiene vinculadas simultáneamente.

**Body**
```json
{ "question": "¿El producto X tiene garantía de 2 años?" }
```

**Respuesta `200`**
```json
{
  "question": "¿El producto X tiene garantía de 2 años?",
  "answer": "Sí, según el catálogo de productos...",
  "sources": []
}
```

---

#### `POST /agents/{agent_id}/ask/stream`
Igual que el anterior con streaming SSE.

---

## Flujo completo de ejemplo

### Caso: Empresa con bot interno de RRHH y bot externo de ventas

```
# 1. Crear la empresa
POST /organizations
→ org_id = "org-abc"

# 2. Crear knowledge bases
POST /knowledge-bases
  { "organization_id": "org-abc", "name": "Recursos Humanos", "area": "rrhh" }
  → kb_id = "kb-rrhh"

POST /knowledge-bases
  { "organization_id": "org-abc", "name": "Catálogo de Ventas", "area": "ventas" }
  → kb_id = "kb-ventas"

POST /knowledge-bases
  { "organization_id": "org-abc", "name": "Manual de Garantías", "area": "ventas" }
  → kb_id = "kb-garantias"

# 3. Subir documentos
POST /knowledge-bases/kb-rrhh/documents        → contrato_laboral.pdf
POST /knowledge-bases/kb-rrhh/documents        → politica_vacaciones.docx
POST /knowledge-bases/kb-ventas/documents      → catalogo_2026.pdf
POST /knowledge-bases/kb-garantias/documents   → manual_garantias.pdf

# 4. Crear agentes
POST /agents
  { "organization_id": "org-abc", "name": "Bot RRHH Interno", "visibility": "internal" }
  → agent_id = "agent-rrhh"

POST /agents
  { "organization_id": "org-abc", "name": "Bot Ventas Externo", "visibility": "external" }
  → agent_id = "agent-ventas"

# 5. Vincular KBs a cada agente
POST /agents/agent-rrhh/knowledge-bases    → { "knowledge_base_id": "kb-rrhh" }

POST /agents/agent-ventas/knowledge-bases  → { "knowledge_base_id": "kb-ventas" }
POST /agents/agent-ventas/knowledge-bases  → { "knowledge_base_id": "kb-garantias" }

# 6. Consultar
# Bot de RRHH — solo sabe de contratos y vacaciones
POST /agents/agent-rrhh/ask
  { "question": "¿Cuántos días de vacaciones tengo?" }

# Bot de Ventas — sabe de catálogo Y garantías al mismo tiempo
POST /agents/agent-ventas/ask
  { "question": "¿El televisor Samsung tiene garantía de 2 años?" }

# Consulta por área — sin agente, directo por org
POST /organizations/org-abc/ask?area=ventas
  { "question": "¿Qué productos nuevos hay en 2026?" }

# Consulta global — busca en TODO
POST /organizations/org-abc/ask
  { "question": "¿Qué beneficios tienen los empleados de ventas?" }
```

---

## Cuándo usar cada endpoint de consulta

```
Tengo una KB específica y quiero consultarla sola
→ POST /knowledge-bases/{kb_id}/ask

Quiero consultar todas las KBs de un departamento
→ POST /organizations/{org_id}/ask?area=rrhh

Quiero un bot con control total (exactamente estas KBs, no más)
→ Crear un Agent → vincular KBs → POST /agents/{agent_id}/ask

Quiero un bot que sepa TODO lo de la empresa
→ POST /organizations/{org_id}/ask  (sin filtro de área)
   o crear un Agent y vincularle todas las KBs
```

---

## Formatos de archivo soportados

| Formato | Extensión | MIME type |
|---------|-----------|-----------|
| PDF | `.pdf` | `application/pdf` |
| Word | `.docx` | `application/vnd.openxmlformats-officedocument.wordprocessingml.document` |
| Excel | `.xlsx` | `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet` |
| CSV | `.csv` | `text/csv` |
| JSON | `.json` | `application/json` |

---

## Variables de entorno

| Variable | Requerida | Descripción |
|----------|-----------|-------------|
| `DATABASE_URL` | ✅ | URL async para FastAPI (`postgresql+asyncpg://...`) |
| `ALEMBIC_DATABASE_URL` | ✅ | URL sync para Alembic (`postgresql+psycopg://...`) |
| `OPENAI_API_KEY` | ✅ | API key de OpenAI |
| `SUPABASE_URL` | ⬜ | URL del proyecto Supabase (si está vacío, los archivos no se suben) |
| `SUPABASE_SERVICE_KEY` | ⬜ | Service Role Key de Supabase |
| `SUPABASE_BUCKET_NAME` | ⬜ | Nombre del bucket (default: `documents`) |
| `APP_NAME` | ⬜ | Nombre de la app (default: `Enterprise Chatbot`) |
| `ENVIRONMENT` | ⬜ | `development` / `production` (default: `development`) |

> **Supabase es opcional.** Si `SUPABASE_URL` está vacío, los documentos se procesan normalmente pero el archivo original no se guarda en el bucket.

---

## Logs

Los logs se escriben en `./logs/` y se rotan automáticamente cada medianoche (30 días de retención).

| Archivo | Contenido |
|---------|-----------|
| `application.log` | Eventos de negocio: org creada, KB creada, documento subido/procesado |
| `rag.log` | Cada consulta: pregunta, KBs buscadas, chunks encontrados, tiempo de búsqueda |
| `openai.log` | Cada llamada a OpenAI: modelo, tokens usados, costo estimado en USD |
| `errors.log` | Errores con traceback completo: fallas de procesamiento, errores de API |

---

## Docker

```bash
# Levantar todo (API + PostgreSQL)
docker compose up

# Los logs persisten entre reinicios gracias al bind mount
docker compose down
docker compose up  # los logs siguen ahí en ./logs/

# Ejecutar migraciones
docker compose exec api alembic upgrade head

# Ver logs en tiempo real
tail -f logs/application.log
tail -f logs/rag.log
tail -f logs/openai.log
```

**Puertos:**
- API: `http://localhost:8000`
- Docs interactivas: `http://localhost:8000/docs`
- PostgreSQL: `localhost:5433`
