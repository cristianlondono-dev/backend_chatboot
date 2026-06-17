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
6. [Tool Actions (acciones ejecutables)](#tool-actions-acciones-ejecutables)
7. [Configuración multi-tenant](#configuración-multi-tenant)
8. [Almacenamiento flexible](#almacenamiento-flexible)
9. [Flujos: interno vs externo](#flujos-interno-vs-externo)
10. [Los niveles de consulta](#los-niveles-de-consulta)
11. [Referencia de endpoints](#referencia-de-endpoints)
    - [Health](#health)
    - [Organizations](#organizations)
    - [Knowledge Bases](#knowledge-bases)
    - [Agents](#agents)
    - [Chat con memoria](#chat-con-memoria)
    - [Tools (canales)](#tools-canales)
    - [Tool Actions](#tool-actions)
12. [Flujo completo de ejemplo](#flujo-completo-de-ejemplo)
13. [Configurar Google Sheets como fuente de empleados](#configurar-google-sheets-como-fuente-de-empleados)
14. [Formatos de archivo soportados](#formatos-de-archivo-soportados)
15. [Variables de entorno](#variables-de-entorno)
16. [Logs](#logs)
17. [Docker](#docker)

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

## Tool Actions (acciones ejecutables)

Los **Tool Actions** son integraciones que el chatbot puede **ejecutar durante una conversación** usando el mecanismo de function calling de OpenAI. Cuando el usuario pide algo como _"confirma mi pedido #1234"_ o _"agenda una reunión para mañana a las 10am"_, el LLM detecta la intención, llama a la acción correspondiente y responde con el resultado real.

### Cómo funciona

```
Usuario: "¿En qué estado está mi pedido #1234?"
          ↓
LLM detecta intención → llama shopify_get_order({order_id: "1234"})
          ↓
Sistema ejecuta la acción → Shopify responde con status, tracking, etc.
          ↓
LLM recibe el resultado → responde en lenguaje natural:
"Tu pedido #1234 está en camino 🚚 Número de seguimiento: TRACK-987"
```

### Action Types disponibles

| `action_type` | Descripción | Servicio |
|--------------|-------------|----------|
| `shopify_get_order` | Consulta detalles de un pedido | Shopify Admin API |
| `shopify_confirm_order` | Confirma/cierra un pedido | Shopify Admin API |
| `google_calendar_create_event` | Crea un evento en el calendario | Google Calendar API |
| `google_calendar_list_events` | Lista los próximos eventos | Google Calendar API |
| `custom_rest` | Llama a cualquier endpoint HTTP externo | Genérico |

### Credenciales y config por action_type

#### `shopify_get_order` / `shopify_confirm_order`

```json
{
  "credentials": { "access_token": "shpat_xxxxxxxxxx" },
  "config": { "store_url": "https://mi-tienda.myshopify.com" }
}
```

#### `google_calendar_create_event` / `google_calendar_list_events`

**Opción A — Service Account (recomendado para servidor):**
```json
{
  "credentials": {
    "service_account_json": {
      "type": "service_account",
      "project_id": "mi-proyecto",
      "private_key_id": "...",
      "private_key": "-----BEGIN RSA PRIVATE KEY-----\n...",
      "client_email": "bot@mi-proyecto.iam.gserviceaccount.com"
    }
  },
  "config": {
    "calendar_id": "user@empresa.com",
    "timezone": "America/Bogota"
  }
}
```

**Opción B — OAuth2 token de usuario:**
```json
{
  "credentials": { "oauth_token": "ya29.xxxxxxxxxxxxxxxx" },
  "config": { "calendar_id": "primary", "timezone": "America/Bogota" }
}
```

> **Setup Google Calendar**: Crear Service Account en Google Cloud Console → Habilitar Calendar API → Compartir el calendario con el email de la service account (rol: "Hacer cambios en eventos" o "Ver todos los detalles").

#### `custom_rest`

Llama a cualquier endpoint con parámetros del usuario:

```json
{
  "credentials": {
    "headers": { "Authorization": "Bearer TOKEN_SECRETO" }
  },
  "config": {
    "url": "https://api.miapp.com/orders/{order_id}",
    "method": "GET",
    "headers": { "Content-Type": "application/json" },
    "timeout": 10
  }
}
```

Los placeholders `{param_name}` en la URL se reemplazan con los parámetros que el LLM proporciona.

### Dependencias adicionales

Según el action_type que uses, instala las dependencias correspondientes:

```bash
# Google Calendar
pip install google-api-python-client google-auth

# AWS S3 (si usas S3 como storage)
pip install boto3

# Cloudinary (si usas Cloudinary como storage)
pip install cloudinary
```

---

## Configuración multi-tenant

En despliegues donde múltiples empresas usan la misma instancia, cada organización puede tener su propio **API key de OpenAI** y su propio **proveedor de almacenamiento**.

### Cómo funciona

- Si la organización tiene configurado `openai_api_key`, ese key se usa para todas las llamadas al LLM (chat, embeddings, extracción de memoria) de esa org.
- Si no tiene, se usa la variable de entorno global `OPENAI_API_KEY`.
- Lo mismo aplica para el storage: si hay config de storage en la org, se usa ese provider; si no, se usa Supabase con las vars de entorno globales.

### Endpoint

```
PUT /organizations/{organization_id}/config
GET /organizations/{organization_id}/config
```

**Body — OpenAI propio + Supabase dedicado:**
```json
{
  "openai_api_key": "sk-proj-xxxxxxxx",
  "storage_provider": "supabase",
  "storage_credentials": {
    "url": "https://xyz.supabase.co",
    "service_key": "eyJhbGci..."
  },
  "storage_config": {
    "bucket_name": "mi-bucket-docs"
  }
}
```

**Body — OpenAI propio + S3:**
```json
{
  "openai_api_key": "sk-proj-xxxxxxxx",
  "storage_provider": "s3",
  "storage_credentials": {
    "access_key_id": "AKIA...",
    "secret_access_key": "xxxxxxxx"
  },
  "storage_config": {
    "bucket": "mi-bucket",
    "region": "us-east-1"
  }
}
```

**Body — OpenAI propio + Cloudinary:**
```json
{
  "openai_api_key": "sk-proj-xxxxxxxx",
  "storage_provider": "cloudinary",
  "storage_credentials": {
    "cloud_name": "mi-cloud",
    "api_key": "123456",
    "api_secret": "xxxxxxxxxx"
  },
  "storage_config": {
    "folder": "chatbot-docs"
  }
}
```

> **Seguridad**: Los campos `openai_api_key`, `storage_credentials` y tool action `credentials` se guardan como JSON en la base de datos. En producción se recomienda cifrar estas columnas (ej. con `pgcrypto` en Postgres o usando AWS KMS / Vault para la clave de cifrado).

---

## Almacenamiento flexible

El sistema soporta tres proveedores de almacenamiento para los documentos subidos a las Knowledge Bases:

| Provider | Clase | Cuándo usarlo |
|----------|-------|---------------|
| `supabase` | `SupabaseStorageService` | Default. Proyecto Supabase existente. |
| `s3` | `S3StorageService` | AWS, mínimo costo de almacenamiento a escala. |
| `cloudinary` | `CloudinaryStorageService` | Proyectos que ya usan Cloudinary. |

El proveedor se selecciona automáticamente usando la config de la organización (`PUT /organizations/{id}/config`). Si la org no tiene config, se usa Supabase con las variables de entorno globales.

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

### Tools (canales)

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

### Tool Actions

#### `GET /agents/tool-actions/types`
Lista todos los `action_type` disponibles con sus descripciones y schemas de parámetros por defecto.

**Respuesta `200`**
```json
[
  {
    "action_type": "shopify_get_order",
    "default_description": "Consulta el estado y los detalles de un pedido en Shopify...",
    "default_parameters_schema": { "type": "object", "properties": { "order_id": {...} }, "required": ["order_id"] }
  },
  { "action_type": "shopify_confirm_order", "..." : "..." },
  { "action_type": "google_calendar_create_event", "...": "..." },
  { "action_type": "google_calendar_list_events", "...": "..." },
  { "action_type": "custom_rest", "...": "..." }
]
```

---

#### `POST /agents/{agent_id}/tool-actions`
Registra una nueva acción ejecutable para el agente.

Si `parameters_schema` no se envía, se usa el schema por defecto del `action_type`.

**Body — Shopify consultar pedido:**
```json
{
  "name": "consultar_pedido",
  "action_type": "shopify_get_order",
  "description": "Consulta el estado de un pedido en nuestra tienda. Úsalo cuando el cliente pregunte por su pedido.",
  "parameters_schema": {},
  "credentials": {
    "access_token": "shpat_xxxxxxxxxxxxxxxxxxx"
  },
  "config": {
    "store_url": "https://mi-tienda.myshopify.com"
  }
}
```

**Body — Google Calendar crear evento:**
```json
{
  "name": "agendar_reunion",
  "action_type": "google_calendar_create_event",
  "description": "Agenda una reunión o cita en el calendario. Úsalo cuando el usuario quiera programar un encuentro.",
  "parameters_schema": {},
  "credentials": {
    "service_account_json": { "type": "service_account", "...": "..." }
  },
  "config": {
    "calendar_id": "ventas@empresa.com",
    "timezone": "America/Bogota"
  }
}
```

**Body — REST custom (consultar inventario propio):**
```json
{
  "name": "consultar_inventario",
  "action_type": "custom_rest",
  "description": "Consulta el stock disponible de un producto en nuestro sistema.",
  "parameters_schema": {
    "type": "object",
    "properties": {
      "sku": { "type": "string", "description": "Código SKU del producto" }
    },
    "required": ["sku"]
  },
  "credentials": {
    "headers": { "X-API-Key": "mi-secreto-api-key" }
  },
  "config": {
    "url": "https://api.miempresa.com/inventory/{sku}",
    "method": "GET"
  }
}
```

**Respuesta `201`**
```json
{
  "id": "action-uuid",
  "agent_id": "agent-uuid",
  "name": "consultar_pedido",
  "action_type": "shopify_get_order",
  "description": "Consulta el estado de un pedido en nuestra tienda...",
  "parameters_schema": { "type": "object", "properties": { "order_id": {...} }, "required": ["order_id"] },
  "config": { "store_url": "https://mi-tienda.myshopify.com" },
  "is_active": true,
  "created_at": "2026-06-16T12:00:00Z",
  "updated_at": "2026-06-16T12:00:00Z"
}
```

> **Nota de seguridad**: el campo `credentials` **no se devuelve en las respuestas** para evitar exposición accidental de tokens.

---

#### `GET /agents/{agent_id}/tool-actions`
Lista todas las tool actions del agente.

---

#### `GET /agents/{agent_id}/tool-actions/{action_id}`
Obtiene una tool action específica.

---

#### `PUT /agents/{agent_id}/tool-actions/{action_id}`
Actualiza una tool action (nombre, descripción, schema, config, credenciales, estado).

**Body:**
```json
{
  "name": "consultar_pedido",
  "description": "...",
  "parameters_schema": {},
  "credentials": { "access_token": "nuevo-token" },
  "config": { "store_url": "https://mi-tienda.myshopify.com" },
  "is_active": true
}
```

---

#### `DELETE /agents/{agent_id}/tool-actions/{action_id}`
Elimina una tool action. **Respuesta `204 No Content`**

---

#### `POST /agents/{agent_id}/tool-actions/{action_id}/test`
Ejecuta la acción directamente con los parámetros indicados para verificar credenciales y configuración.

**Body:**
```json
{
  "params": { "order_id": "5678901234" }
}
```

**Respuesta exitosa `200`:**
```json
{
  "success": true,
  "result": {
    "id": 5678901234,
    "name": "#1001",
    "financial_status": "paid",
    "fulfillment_status": "fulfilled",
    "total_price": "129000.00",
    "currency": "COP",
    "line_items": [{ "title": "Producto A", "quantity": 2, "price": "64500.00" }],
    "tracking_numbers": ["TRACK-ABC123"]
  },
  "error": null
}
```

**Respuesta con error `200`:**
```json
{
  "success": false,
  "result": null,
  "error": "401 Unauthorized: Invalid access token"
}
```

---

### Configuración de la organización (multi-tenant)

#### `PUT /organizations/{organization_id}/config`
Crea o actualiza la configuración de la organización.

**Body:**
```json
{
  "openai_api_key": "sk-proj-xxxxxxxxxx",
  "storage_provider": "supabase",
  "storage_credentials": {
    "url": "https://xyz.supabase.co",
    "service_key": "eyJhbGci..."
  },
  "storage_config": {
    "bucket_name": "mis-documentos"
  }
}
```

**Respuesta `200`**
```json
{
  "id": "config-uuid",
  "organization_id": "org-uuid",
  "openai_api_key": "sk-proj-xxxxxxxxxx",
  "storage_provider": "supabase",
  "storage_credentials": { "url": "...", "service_key": "..." },
  "storage_config": { "bucket_name": "mis-documentos" },
  "created_at": "2026-06-16T12:00:00Z",
  "updated_at": "2026-06-16T12:00:00Z"
}
```

---

#### `GET /organizations/{organization_id}/config`
Obtiene la configuración actual de la organización.

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

# 8. (Opcional) Configurar tool actions para el bot de ventas
# 8a. Consultar acción del pedido en Shopify
POST /agents/agent-ventas/tool-actions
  {
    "name": "consultar_pedido",
    "action_type": "shopify_get_order",
    "description": "Consulta el estado de un pedido. Úsalo cuando el cliente pregunte por su pedido.",
    "credentials": { "access_token": "shpat_xxx" },
    "config": { "store_url": "https://mi-tienda.myshopify.com" }
  }

# 8b. Probar que las credenciales funcionan
POST /agents/agent-ventas/tool-actions/{action_id}/test
  { "params": { "order_id": "1234" } }

# 8c. Ahora el bot puede responder preguntas como:
POST /agents/agent-ventas/chat
  { "channel": "whatsapp", "channel_id": "+573009876543",
    "question": "¿Dónde está mi pedido 1234?" }
  # El LLM detecta la intención → llama consultar_pedido → responde con el estado real

# 9. (Opcional) Configurar OpenAI key propia por organización
PUT /organizations/org-abc/config
  {
    "openai_api_key": "sk-proj-empresa-propia",
    "storage_provider": "s3",
    "storage_credentials": { "access_key_id": "AKIA...", "secret_access_key": "xxx" },
    "storage_config": { "bucket": "mis-docs", "region": "us-east-1" }
  }
```

---

## Diferencia entre Tools y Tool Actions

| | **Tool (AgentTool)** | **Tool Action** |
|---|---|---|
| **¿Qué es?** | Cómo el usuario llega al bot | Qué puede hacer el bot |
| **Configura** | Canal, identificación, resolver de identidad | Integraciones externas ejecutables |
| **Ejemplos** | WhatsApp + teléfono, Teams + email | Consultar Shopify, crear evento en Calendar |
| **Cuándo aplica** | En CADA mensaje (identifica al usuario) | Solo cuando el LLM detecta una intención |
| **Endpoint** | `POST /agents/{id}/tools` | `POST /agents/{id}/tool-actions` |

Un agente puede tener un Tool de WhatsApp **y** Tool Actions de Shopify + Google Calendar al mismo tiempo, sin conflicto.

```
Usuario de WhatsApp envía mensaje
     ↓
[Tool] Identifica al usuario por teléfono (resolver)
     ↓
[Chat] LLM analiza el mensaje
     ↓ (si detecta intención de acción)
[Tool Action] Ejecuta la integración → devuelve resultado → LLM responde
```

---

## Configurar Google Calendar paso a paso

### 1. Crear el proyecto en Google Cloud

1. Ve a [Google Cloud Console](https://console.cloud.google.com)
2. Crea un nuevo proyecto (o usa uno existente)
3. En el menú → **APIs y Servicios** → **Biblioteca**
4. Busca **"Google Calendar API"** → Habilitar

### 2. Crear la Service Account

1. Ve a **IAM y Administración** → **Cuentas de servicio**
2. Crear cuenta de servicio:
   - Nombre: `chatbot-calendar`
   - ID: se genera automáticamente
3. Roles: no necesita rol especial en Google Cloud (los permisos se dan desde Calendar)
4. Clic en **Crear clave** → tipo **JSON** → descarga el archivo

El archivo JSON tiene esta forma:
```json
{
  "type": "service_account",
  "project_id": "mi-proyecto",
  "private_key_id": "abc123",
  "private_key": "-----BEGIN RSA PRIVATE KEY-----\n...\n-----END RSA PRIVATE KEY-----\n",
  "client_email": "chatbot-calendar@mi-proyecto.iam.gserviceaccount.com",
  "client_id": "12345678",
  "auth_uri": "https://accounts.google.com/o/oauth2/auth",
  "token_uri": "https://oauth2.googleapis.com/token"
}
```

### 3. Compartir el calendario con la Service Account

Para **cada calendario** que quieras que el bot gestione:

1. Abre **Google Calendar** en el navegador
2. En el panel izquierdo, clic en los 3 puntos del calendario → **Configuración y uso compartido**
3. Sección **"Compartir con personas específicas"** → Agregar personas
4. Email: el `client_email` de tu Service Account (ej. `chatbot-calendar@mi-proyecto.iam.gserviceaccount.com`)
5. Permisos: **"Realizar cambios en eventos"** (para crear/editar/cancelar)
6. Guarda

### 4. Obtener el Calendar ID

En la misma pantalla de configuración del calendario:  
Sección **"Integrar el calendario"** → copia el **ID del calendario**

- Calendario personal: `primary` o `usuario@gmail.com`
- Calendario de empresa: algo como `c_xxxxxxxxxxxxxxxxxxxxxxxxxxxxx@group.calendar.google.com`

### 5. Configurar la Tool Action (multi-sede)

```
POST /agents/{agent_id}/tool-actions
```

**Para múltiples sedes/calendarios:**

```json
{
  "name": "agendar_cita",
  "action_type": "google_calendar_create_event",
  "description": "Agenda una cita o reunión. Sedes disponibles: Sede Centro, Sede Norte, Sede Sur. Pregunta al usuario en cuál sede quiere agendar si no lo especifica.",
  "parameters_schema": {
    "type": "object",
    "properties": {
      "calendar_name": {
        "type": "string",
        "enum": ["Sede Centro", "Sede Norte", "Sede Sur"],
        "description": "La sede donde agendar la cita."
      },
      "title": { "type": "string", "description": "Título de la cita." },
      "start": { "type": "string", "description": "Fecha y hora de inicio ISO 8601. Ej: '2025-07-15T10:00:00'" },
      "end": { "type": "string", "description": "Fecha y hora de fin ISO 8601." },
      "description": { "type": "string", "description": "Notas adicionales (opcional)." }
    },
    "required": ["calendar_name", "title", "start", "end"]
  },
  "credentials": {
    "service_account_json": {
      "type": "service_account",
      "project_id": "mi-proyecto",
      "private_key_id": "abc123",
      "private_key": "-----BEGIN RSA PRIVATE KEY-----\n...",
      "client_email": "chatbot-calendar@mi-proyecto.iam.gserviceaccount.com"
    }
  },
  "config": {
    "calendars": [
      {"id": "c_aaa@group.calendar.google.com", "name": "Sede Centro"},
      {"id": "c_bbb@group.calendar.google.com", "name": "Sede Norte"},
      {"id": "c_ccc@group.calendar.google.com", "name": "Sede Sur"}
    ],
    "timezone": "America/Bogota",
    "advance_notice_hours": 1
  }
}
```

Registra también las acciones de listar, cancelar y modificar con el mismo `credentials` y `config`:

```json
{ "name": "ver_citas",      "action_type": "google_calendar_list_events",  ... }
{ "name": "cancelar_cita",  "action_type": "google_calendar_cancel_event",  ... }
{ "name": "modificar_cita", "action_type": "google_calendar_update_event",  ... }
```

### 6. Probar antes de activar

```
POST /agents/{agent_id}/tool-actions/{action_id}/test
{
  "params": {
    "calendar_name": "Sede Centro",
    "title": "Prueba de integración",
    "start": "2025-12-31T10:00:00",
    "end": "2025-12-31T11:00:00"
  }
}
```

---

## Regla de 1 hora de anticipación (cancelar/modificar)

Las acciones `google_calendar_cancel_event` y `google_calendar_update_event` verifican automáticamente que el evento empiece en **más de 1 hora**. Si no, devuelven un error amigable al LLM:

```
"No es posible modificar o cancelar eventos con menos de 1 hora de anticipación.
 El evento comienza a las 14:30 y son las 14:10 (UTC)."
```

El LLM relayea este mensaje al usuario de forma natural.  
Puedes cambiar el umbral por acción con `"advance_notice_hours": 2` en el `config`.

---

## Action Types disponibles (referencia completa)

| `action_type` | Requiere `credentials` | Requiere `config` |
|---|---|---|
| `shopify_get_order` | `access_token` | `store_url` |
| `shopify_confirm_order` | `access_token` | `store_url` |
| `shopify_list_orders` | `access_token` | `store_url` |
| `shopify_cancel_order` | `access_token` | `store_url` |
| `google_calendar_create_event` | `service_account_json` o `oauth_token` | `calendars[]` + `timezone` |
| `google_calendar_list_events` | `service_account_json` o `oauth_token` | `calendars[]` + `timezone` |
| `google_calendar_cancel_event` | `service_account_json` o `oauth_token` | `calendars[]` + `timezone` + `advance_notice_hours` |
| `google_calendar_update_event` | `service_account_json` o `oauth_token` | `calendars[]` + `timezone` + `advance_notice_hours` |
| `custom_rest` | `headers` (opcionales) | `url`, `method`, `headers` (opcionales) |

---

## Integración Twilio (WhatsApp real)

### 1. Crear cuenta Twilio

1. Regístrate en [twilio.com](https://www.twilio.com)
2. Ve a **Messaging** → **Try it out** → **Send a WhatsApp message**
3. Sigue los pasos del sandbox (envía el código de activación desde tu WhatsApp)

Para producción, solicita un número de WhatsApp Business en la misma sección.

### 2. Configurar el webhook

En la consola Twilio → **Messaging** → **WhatsApp Sandbox** (o la config del número):

- **"When a message comes in"**: `https://tudominio.com/webhooks/twilio/whatsapp/{agent_id}`
- Método: **HTTP POST**

> Para desarrollo local puedes usar [ngrok](https://ngrok.com):
> ```bash
> ngrok http 8000
> # Copia la URL pública, ej: https://abc123.ngrok.io
> # Webhook: https://abc123.ngrok.io/webhooks/twilio/whatsapp/{agent_id}
> ```

### 3. Instalar twilio SDK (opcional, para validación de firma)

```bash
pip install twilio
```

Añade a `.env`:
```
TWILIO_AUTH_TOKEN=tu_auth_token_de_twilio
```

Sin esta variable el webhook funciona igual pero sin validación de firma (OK para desarrollo).

### 4. Configurar el AgentTool para WhatsApp

El agente debe tener un Tool con `channel="whatsapp"`:

```json
POST /agents/{agent_id}/tools
{
  "channel": "whatsapp",
  "identifier_type": "phone",
  "user_type": "external",
  "resolver_type": "none",
  "onboarding_questions": [
    { "question": "¿Cuál es tu nombre?", "memory_key": "nombre" }
  ]
}
```

### 5. Probar

Envía un WhatsApp al número del sandbox de Twilio y el chatbot responderá automáticamente.

### Endpoint del webhook

```
POST /webhooks/twilio/whatsapp/{agent_id}
```

Twilio envía (form-encoded):
```
From=whatsapp%3A%2B573001234567
Body=Hola%2C+necesito+ayuda
```

El servidor responde con TwiML:
```xml
<?xml version="1.0" encoding="UTF-8"?>
<Response>
  <Message>¡Hola! Soy el asistente. ¿En qué puedo ayudarte hoy?</Message>
</Response>
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
| `[chat-tools]` | Llamadas al modelo con function calling activo |
| `[tool-action]` | Ejecución de tool actions (nombre, tipo, parámetros, resultado) |
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
