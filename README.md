# Enterprise Chatbot API

Backend RAG (Retrieval-Augmented Generation) construido con **FastAPI + PostgreSQL + pgvector + OpenAI**.  
Permite a empresas subir documentos y consultarlos mediante lenguaje natural, con memoria conversacional por usuario y soporte multi-canal.

---

## Tabla de contenido

1. [Arquitectura conceptual](#arquitectura-conceptual)
2. [Jerarquía de datos](#jerarquía-de-datos)
3. [Cómo funciona el RAG](#cómo-funciona-el-rag)
4. [Sistema de memoria](#sistema-de-memoria)
5. [Módulo de Tools (canales e identidad)](#módulo-de-tools-canales-e-identidad)
6. [Flujos: interno vs externo](#flujos-interno-vs-externo)
7. [Los niveles de consulta](#los-niveles-de-consulta)
8. [Referencia de endpoints](#referencia-de-endpoints)
   - [Health](#health)
   - [Organizations](#organizations)
   - [Knowledge Bases](#knowledge-bases)
   - [Agents](#agents)
   - [Chat con memoria](#chat-con-memoria)
   - [Tools](#tools)
9. [Flujo completo de ejemplo](#flujo-completo-de-ejemplo)
10. [Configurar Google Sheets como fuente de empleados](#configurar-google-sheets-como-fuente-de-empleados)
11. [Formatos de archivo soportados](#formatos-de-archivo-soportados)
12. [Variables de entorno](#variables-de-entorno)
13. [Logs](#logs)
14. [Docker](#docker)

---

## Arquitectura conceptual

```
Organization (empresa)
│
├── Knowledge Base "RRHH"
│   ├── contrato_laboral.pdf
│   └── politica_vacaciones.docx
│
├── Knowledge Base "Ventas"
│   ├── catalogo_productos.pdf
│   └── lista_precios.xlsx
│
├── Agent "Bot Interno RRHH"
│   ├── → Knowledge Base "RRHH"
│   ├── Tool (canal: whatsapp, usuarios: internos, resolver: google_sheets)
│   └── Memoria por usuario (sesiones, memories, summaries)
│
└── Agent "Bot Comercial Externo"
    ├── → Knowledge Base "Ventas"
    ├── Tool (canal: whatsapp, usuarios: externos, onboarding: [nombre, empresa])
    └── Memoria por usuario
```

---

## Jerarquía de datos

```
Organization
  └── Knowledge Base (N)
        └── Document (N)
              └── DocumentChunk         (~1000 chars cada uno)
                    └── ChunkEmbedding  vector 1536 dims (text-embedding-3-small)

Agent
  └── AgentKnowledgeBase (N)            KBs vinculadas al agente
  └── AgentTool (N)                     configuración por canal

User (cross-canal)
  ├── canonical_id                      ID estable (employee_id o teléfono)
  ├── UserChannel (N)                   mapeo canal → usuario (whatsapp, teams, etc.)
  └── Por agente:
        ├── ChatSession                 sesión activa (auto-cierra a 30 min)
        │     └── Message (N)           historial completo
        ├── UserMemory (N)              hechos extraídos por el LLM
        └── ConversationSummary (N)     resúmenes auto-generados (cada 100 msgs)
```

---

## Cómo funciona el RAG

Cuando se hace una pregunta al agente:

1. **Embedding de la pregunta** — se convierte en un vector con `text-embedding-3-small`
2. **Búsqueda semántica** — se calculan similitudes coseno contra los chunks en pgvector  
   `similarity = 1 - cosine_distance` | filtro mínimo: `similarity ≥ 0.30`
3. **Top-K configurable** — se recuperan los N chunks más relevantes (1–20, default 5)
4. **Contexto enriquecido** — cada chunk incluye fuente y relevancia:
   ```
   [Fuente: contrato_laboral.pdf | Relevancia: 87%]
   Los empleados tienen derecho a 15 días hábiles de vacaciones...
   ```
5. **Generación de respuesta** — `gpt-4.1-mini` recibe el contexto + pregunta + memoria del usuario
6. **Sin información relevante** — responde `"No encontré información suficiente para responder."`

---

## Sistema de memoria

Cada conversación se asocia a un usuario identificado por canal. La memoria persiste entre sesiones.

### Componentes

| Componente | Descripción |
|------------|-------------|
| **ChatSession** | Sesión activa por agente+usuario. Se cierra automáticamente tras 30 min de inactividad. |
| **Message** | Cada turno (user/assistant) guardado con timestamp y token count. |
| **UserMemory** | Hechos extraídos del usuario por el LLM (`"Trabaja en Bogotá"`, `"Le interesa el producto X"`). Importancia: `low / medium / high`. |
| **ConversationSummary** | Resumen automático generado cada 100 mensajes para comprimir el historial. |

### Construcción del contexto

Antes de cada respuesta, el sistema construye el prompt completo con:

```
[PERFIL DEL USUARIO]
Nombre: Juan Pérez
Cargo: Analista de Nómina

[LO QUE SÉ DE ESTE USUARIO]
- Prefiere respuestas detalladas (high)
- Pregunta frecuentemente sobre vacaciones (medium)

[RESÚMENES DE CONVERSACIONES ANTERIORES]
En sesiones previas habló sobre ...

[INFORMACIÓN DE LA EMPRESA]
[Fuente: politica_vacaciones.pdf | Relevancia: 91%]
Los empleados con más de un año ...
```

### Identificación cross-canal

Un mismo empleado puede escribir desde WhatsApp y desde Teams y el sistema lo reconoce como la misma persona:

```
users
  id: uuid
  canonical_id: "EMP-001"    ← estable entre canales
  user_type: "internal"

user_channels
  channel: "whatsapp"    channel_id: "+57300..."    → user_id
  channel: "teams"       channel_id: "juan@..."     → user_id (mismo)
```

---

## Módulo de Tools (canales e identidad)

Un **Tool** define cómo el agente interactúa con usuarios en un canal específico: cómo identificarlos, si son internos o externos, cómo resolver su identidad y qué preguntas de onboarding hacer.

### Modelo AgentTool

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `channel` | string | Canal: `whatsapp`, `teams`, `webchat`, `slack` |
| `identifier_type` | string | Cómo llega el ID: `phone`, `email`, `employee_id` |
| `user_type` | string | `internal` o `external` |
| `resolver_type` | string | `none`, `rest_api`, `google_sheets` |
| `resolver_config` | JSON | Configuración del resolver (URL, credenciales, etc.) |
| `field_mapping` | JSON | Qué campos del resolver convertir en memorias del usuario |
| `onboarding_questions` | JSON | Preguntas para usuarios externos (ver formato abajo) |

### Resolvers disponibles

#### `rest_api`
Consulta un endpoint HTTP para verificar si el usuario existe.

```json
{
  "url": "https://api.empresa.com/employees/{identifier}",
  "method": "GET",
  "headers": { "Authorization": "Bearer TOKEN" },
  "response_path": "data.employee",
  "canonical_field": "employee_id"
}
```

#### `google_sheets`
Busca el usuario en una hoja de cálculo de Google.

```json
{
  "spreadsheet_id": "1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgVE2upms",
  "sheet_name": "Empleados",
  "identifier_column": "celular",
  "canonical_field": "cedula",
  "credentials_json": { "type": "service_account", "...": "..." }
}
```

### Field mapping

Convierte columnas del resolver en memorias automáticas del usuario:

```json
{
  "NOMBRE": "Nombre: {value}",
  "CARGO":  "Cargo: {value}",
  "JEFE":   "Jefe inmediato: {value}"
}
```

### Onboarding (usuarios externos)

Preguntas que el agente hace al nuevo usuario. El campo extra (además de `"question"`) define la etiqueta con la que se guarda la respuesta en memoria:

```json
[
  { "question": "¿Cuál es tu nombre?",                      "memory_key": "nombre" },
  { "question": "¿En qué empresa trabajas?",                "memory_key": "empresa" },
  { "question": "¿Qué producto o servicio te interesa?",    "memory_key": "interes" }
]
```

El agente humaniza las preguntas con el LLM — nunca las hace de forma robótica.

---

## Flujos: interno vs externo

### Usuario interno (empleado)

```
Usuario escribe → agente recibe channel + channel_id
                         ↓
              Busca Tool del agente para ese canal
                         ↓
              Llama al resolver (REST API / Google Sheets)
                         ↓
        ¿Existe en la fuente de datos?
        NO → "No estás registrado en el sistema"  (acceso denegado)
        SÍ → canonical_id = employee_id del resolver
             memorias = campos mapeados (nombre, cargo, jefe...)
                         ↓
              Crea/reutiliza usuario en BD
              Crea/reutiliza sesión de chat
                         ↓
              Chat normal con RAG + memoria
```

### Usuario externo (cliente)

```
Usuario escribe → agente recibe channel + channel_id (teléfono)
                         ↓
              Busca Tool del agente para ese canal
                         ↓
              canonical_id = channel_id (el teléfono ES el identificador)
                         ↓
        ¿Tiene onboarding pendiente?
        SÍ → Hace preguntas humanizadas con el LLM
             Guarda respuestas como memorias de alta importancia
        NO → Chat normal con RAG + memoria
```

---

## Los niveles de consulta

| Nivel | Endpoint | Busca en... | Cuándo usarlo |
|-------|----------|-------------|---------------|
| **KB específica** | `POST /knowledge-bases/{kb_id}/ask` | Una sola KB | Bot especializado en un tema exacto |
| **Por área** | `POST /organizations/{org_id}/ask?area=ventas` | KBs de esa área | Consultar un departamento completo |
| **Toda la org** | `POST /organizations/{org_id}/ask` | Todas las KBs | Bot general sin filtro |
| **Agente (RAG puro)** | `POST /agents/{agent_id}/ask` | KBs vinculadas | Consulta sin memoria de usuario |
| **Agente (con memoria)** | `POST /agents/{agent_id}/chat` | KBs + historial + memories | Chatbot conversacional completo |

---

## Referencia de endpoints

### Health

#### `GET /health`

```json
{ "database": true }
```

---

### Organizations

#### `POST /organizations`

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
  "created_at": "2026-06-09T14:00:00Z"
}
```

---

#### `GET /organizations/{organization_id}/agents`
Lista todos los agentes de una organización.

---

#### `POST /organizations/{organization_id}/ask`
Consulta todas las bases de conocimiento de la organización.

**Query params**

| Param | Descripción |
|-------|-------------|
| `area` | Filtra por área: `?area=ventas` |
| `top_k` | Chunks a recuperar (1–20, default 5) |

**Body**
```json
{ "question": "¿Cuántos días de vacaciones tiene un empleado nuevo?" }
```

---

#### `POST /organizations/{organization_id}/ask/stream`
Igual que el anterior con streaming SSE.

---

### Knowledge Bases

#### `POST /knowledge-bases`

**Body**
```json
{
  "organization_id": "org-uuid",
  "name": "Políticas de RRHH",
  "description": "Contratos, vacaciones, reglamento interno",
  "area": "rrhh"
}
```

> El campo `area` es libre: `"rrhh"`, `"ventas"`, `"tesoreria"`, etc. Se usa para filtrar con `?area=` en el endpoint de la organización.

---

#### `POST /knowledge-bases/{knowledge_base_id}/documents`
Sube un documento. El sistema extrae texto → limpia → divide en chunks → genera embeddings.

**Form-data:** campo `file` (PDF, DOCX, CSV, JSON o XLSX)

**Estados del documento**

| Estado | Descripción |
|--------|-------------|
| `PENDING` | Recibido, pendiente |
| `PROCESSING` | Generando embeddings |
| `PROCESSED` | Listo para consultas |
| `FAILED` | Error durante el procesamiento |

---

#### `POST /knowledge-bases/{knowledge_base_id}/ask`

**Query params:** `top_k` (1–20, default 5)

**Body**
```json
{ "question": "¿Cuál es el proceso para solicitar vacaciones?" }
```

---

#### `POST /knowledge-bases/{knowledge_base_id}/ask/stream`
Igual que el anterior con streaming SSE.

---

### Agents

#### `POST /agents`

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
| `"internal"` | Solo para empleados |
| `"external"` | Para clientes externos |
| `"both"` | Ambos públicos |

**Respuesta `201`**
```json
{
  "id": "agent-uuid",
  "organization_id": "org-uuid",
  "name": "Bot Comercial Externo",
  "visibility": "external",
  "created_at": "2026-06-09T14:00:00Z",
  "knowledge_bases": []
}
```

---

#### `GET /agents/{agent_id}`
Obtiene el agente con todas sus KBs vinculadas.

---

#### `POST /agents/{agent_id}/knowledge-bases`
Vincula una KB al agente. Para vincular varias, llama el endpoint N veces.

**Body**
```json
{ "knowledge_base_id": "kb-uuid-ventas" }
```

**Respuesta `204 No Content`**

---

#### `DELETE /agents/{agent_id}/knowledge-bases/{knowledge_base_id}`
Desvincula una KB del agente. **Respuesta `204 No Content`**

---

#### `POST /agents/{agent_id}/ask`
Consulta el agente sin memoria (RAG puro).

**Query params:** `top_k` (1–20, default 5)

**Body**
```json
{ "question": "¿El producto X tiene garantía de 2 años?" }
```

**Respuesta `200`**
```json
{
  "question": "¿El producto X tiene garantía de 2 años?",
  "answer": "Sí, según el catálogo de productos..."
}
```

---

#### `POST /agents/{agent_id}/ask/stream`
Igual que el anterior con streaming SSE.

---

### Chat con memoria

#### `POST /agents/{agent_id}/chat`
Chatbot conversacional completo: identidad, onboarding, RAG, memoria de usuario, historial.

**Query params:** `top_k` (1–20, default 5)

**Body**
```json
{
  "channel": "whatsapp",
  "channel_id": "+573001234567",
  "question": "¿Cuántos días de vacaciones me quedan?"
}
```

**Valores de `channel`:** `whatsapp`, `teams`, `webchat`, `slack`

**Respuesta `200`**
```json
{
  "answer": "Hola Juan! Según la política de la empresa, como llevas más de un año...",
  "session_id": "session-uuid",
  "user_id": "user-uuid"
}
```

**Respuesta si usuario interno no está en el resolver:**
```json
{
  "answer": "No estás registrado en el sistema. Por favor contacta a tu administrador.",
  "session_id": null,
  "user_id": null
}
```

---

#### `GET /agents/{agent_id}/users/{channel}/{channel_id}/history`
Historial de mensajes del usuario en ese canal.

**Query params:** `limit` (1–200, default 50)

**Respuesta `200`**
```json
[
  { "role": "user",      "content": "¿Cuántos días de vacaciones tengo?", "created_at": "..." },
  { "role": "assistant", "content": "Según el reglamento...",              "created_at": "..." }
]
```

---

#### `GET /agents/{agent_id}/users/{channel}/{channel_id}/memories`
Memorias de alta importancia extraídas del usuario.

**Respuesta `200`**
```json
[
  { "memory": "Nombre: Juan Pérez",        "importance": "high" },
  { "memory": "Cargo: Analista de Nómina", "importance": "high" }
]
```

---

### Tools

#### `POST /agents/{agent_id}/tools`
Crea un tool de canal para el agente.

**Body — usuarios internos con Google Sheets**
```json
{
  "channel": "whatsapp",
  "identifier_type": "phone",
  "user_type": "internal",
  "resolver_type": "google_sheets",
  "resolver_config": {
    "spreadsheet_id": "1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgVE2upms",
    "sheet_name": "Empleados",
    "identifier_column": "celular",
    "canonical_field": "cedula",
    "credentials_json": { "type": "service_account", "...": "..." }
  },
  "field_mapping": {
    "NOMBRE": "Nombre: {value}",
    "CARGO":  "Cargo: {value}",
    "JEFE":   "Jefe inmediato: {value}"
  },
  "onboarding_questions": []
}
```

**Body — usuarios externos con onboarding**
```json
{
  "channel": "whatsapp",
  "identifier_type": "phone",
  "user_type": "external",
  "resolver_type": "none",
  "resolver_config": null,
  "field_mapping": null,
  "onboarding_questions": [
    { "question": "¿Cuál es tu nombre?",                   "memory_key": "nombre" },
    { "question": "¿En qué empresa trabajas?",             "memory_key": "empresa" },
    { "question": "¿Qué producto o servicio te interesa?", "memory_key": "interes" }
  ]
}
```

**Respuesta `201`**
```json
{
  "id": "tool-uuid",
  "agent_id": "agent-uuid",
  "channel": "whatsapp",
  "identifier_type": "phone",
  "user_type": "external",
  "resolver_type": "none",
  "is_active": true
}
```

---

#### `GET /agents/{agent_id}/tools`
Lista todos los tools del agente.

---

#### `GET /agents/{agent_id}/tools/{tool_id}`
Obtiene un tool específico.

---

#### `DELETE /agents/{agent_id}/tools/{tool_id}`
Desactiva un tool. **Respuesta `204 No Content`**

---

## Flujo completo de ejemplo

### Caso: Bot interno de RRHH con Google Sheets + Bot externo de ventas

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

# 3. Subir documentos
POST /knowledge-bases/kb-rrhh/documents     → contrato_laboral.pdf
POST /knowledge-bases/kb-ventas/documents   → catalogo_2026.pdf

# 4. Crear agentes
POST /agents
  { "organization_id": "org-abc", "name": "Bot RRHH Interno", "visibility": "internal" }
  → agent_id = "agent-rrhh"

POST /agents
  { "organization_id": "org-abc", "name": "Bot Ventas Externo", "visibility": "external" }
  → agent_id = "agent-ventas"

# 5. Vincular KBs
POST /agents/agent-rrhh/knowledge-bases    → { "knowledge_base_id": "kb-rrhh" }
POST /agents/agent-ventas/knowledge-bases  → { "knowledge_base_id": "kb-ventas" }

# 6. Configurar Tools
POST /agents/agent-rrhh/tools
  → channel: whatsapp, user_type: internal, resolver_type: google_sheets
  → field_mapping: { "NOMBRE": "Nombre: {value}", "CARGO": "Cargo: {value}" }

POST /agents/agent-ventas/tools
  → channel: whatsapp, user_type: external, resolver_type: none
  → onboarding_questions: [nombre, empresa, interés]

# 7. Chatear
POST /agents/agent-rrhh/chat
  { "channel": "whatsapp", "channel_id": "+573001234567", "question": "¿Cuántos días de vacaciones tengo?" }

POST /agents/agent-ventas/chat
  { "channel": "whatsapp", "channel_id": "+573009876543", "question": "Hola" }
  # ← si es nuevo usuario, arranca el onboarding primero
```

---

## Configurar Google Sheets como fuente de empleados

### 1. Preparar la hoja de cálculo

La hoja debe tener encabezados que coincidan con los campos que usarás en `identifier_column`, `canonical_field` y `field_mapping`:

| cedula | celular | NOMBRE | CARGO | JEFE |
|--------|---------|--------|-------|------|
| 123456 | +57300... | Juan Pérez | Analista | Pedro Gómez |

### 2. Crear credenciales de Service Account

1. Ir a [Google Cloud Console](https://console.cloud.google.com) → IAM & Admin → Service Accounts
2. Crear una cuenta de servicio y descargar el archivo JSON de credenciales
3. Habilitar la API de **Google Sheets** en el proyecto
4. Compartir la hoja de cálculo con el email de la service account (rol: Lector)

### 3. Obtener el Spreadsheet ID

El ID está en la URL de la hoja:
```
https://docs.google.com/spreadsheets/d/SPREADSHEET_ID/edit
```

### 4. Crear el tool en el agente

Pasa el contenido completo del JSON de credenciales en `credentials_json` dentro del `resolver_config`.

---

## Formatos de archivo soportados

| Formato | Extensión |
|---------|-----------|
| PDF | `.pdf` |
| Word | `.docx` |
| Excel | `.xlsx` |
| CSV | `.csv` |
| JSON | `.json` |

---

## Variables de entorno

| Variable | Requerida | Descripción |
|----------|-----------|-------------|
| `DATABASE_URL` | ✅ | URL async para FastAPI (`postgresql+asyncpg://...`) |
| `ALEMBIC_DATABASE_URL` | ✅ | URL sync para Alembic (`postgresql+psycopg://...`) |
| `OPENAI_API_KEY` | ✅ | API key de OpenAI |
| `SUPABASE_URL` | ⬜ | URL del proyecto Supabase (si está vacío, los archivos no se suben al bucket) |
| `SUPABASE_SERVICE_KEY` | ⬜ | Service Role Key de Supabase |
| `SUPABASE_BUCKET_NAME` | ⬜ | Nombre del bucket (default: `documents`) |
| `APP_NAME` | ⬜ | Nombre de la app (default: `Enterprise Chatbot`) |
| `ENVIRONMENT` | ⬜ | `development` / `production` (default: `development`) |

---

## Logs

Los logs se escriben en `./logs/` y se rotan automáticamente cada medianoche (30 días de retención).

| Archivo | Contenido |
|---------|-----------|
| `application.log` | Eventos de negocio: org creada, KB creada, documento procesado, resolver hits/misses |
| `rag.log` | Cada consulta RAG: pregunta, KBs buscadas, chunks encontrados con similitud y fuente, tiempo |
| `openai.log` | Cada llamada a OpenAI: modelo, tokens usados, costo estimado en USD (RAG, chat-memory y onboarding) |
| `errors.log` | Errores con traceback completo |

**Tags relevantes en los logs:**

| Tag | Descripción |
|-----|-------------|
| `[rag]` | Consultas RAG directas (ask endpoints) |
| `[chat-memory]` | Llamadas al modelo en el flujo de chat con memoria |
| `[resolver:sheets]` | Búsquedas en Google Sheets |
| `[resolver]` | Llamadas al resolver REST API |

---

## Docker

```bash
# Levantar todo (API + PostgreSQL con pgvector)
docker compose up --build

# Ejecutar migraciones (crea todas las tablas: KBs, memoria, tools)
docker compose exec api alembic upgrade head

# Ver logs en tiempo real
tail -f logs/application.log
tail -f logs/rag.log
tail -f logs/openai.log

# Parar sin borrar datos
docker compose down
```

**Puertos:**
- API: `http://localhost:8000`
- Docs interactivas: `http://localhost:8000/docs`
- PostgreSQL: `localhost:5433`

> **Nota:** Si haces un factory reset de Docker Desktop, la extensión pgvector se pierde.  
> La migración `eced291ccbe9` incluye `CREATE EXTENSION IF NOT EXISTS vector` para recrearla automáticamente al correr `alembic upgrade head`.
